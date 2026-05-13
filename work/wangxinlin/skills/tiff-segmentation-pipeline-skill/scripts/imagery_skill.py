from __future__ import annotations

import os
import re
import time
from collections import deque
from pathlib import Path
from typing import Dict, Any


import requests

OVERLAY_MAX_SIZE = 2048
OVERLAY_FILENAME = "overlay_preview.png"
TILE_SIZE = 448


def _ensure_proj_data_env() -> None:
    """修复Windows环境下外部PROJ_LIB污染，优先使用rasterio自带proj_data。"""
    try:
        import rasterio

        proj_data = os.path.join(os.path.dirname(rasterio.__file__), "proj_data")
        if os.path.isdir(proj_data):
            os.environ["PROJ_LIB"] = proj_data
    except Exception:
        return


def _infer_cgcs2000_gk_crs_from_name(crs_name: str):
    """从类似“CGCS2000 / 3-degree Gauss-Kruger CM 120E”名称推断投影CRS。"""
    if not crs_name:
        return None

    name_lower = crs_name.lower()
    if "cgcs2000" not in name_lower or "gauss-kruger" not in name_lower:
        return None

    match = re.search(r"cm\s*(\d+(?:\.\d+)?)\s*e", crs_name, flags=re.IGNORECASE)
    if not match:
        return None

    lon0 = float(match.group(1))

    try:
        from rasterio.crs import CRS

        proj4 = (
            f"+proj=tmerc +lat_0=0 +lon_0={lon0} +k=1 "
            f"+x_0=500000 +y_0=0 +ellps=GRS80 +units=m +no_defs"
        )
        return CRS.from_string(proj4)
    except Exception:
        return None


def _transform_bounds_to_wgs84(bounds: list[float], src_crs, crs_text: str | None = None) -> tuple[list[float] | None, bool]:
    """将任意坐标系bbox转换为WGS84经纬度bbox，返回(转换结果, 是否为推断CRS)。"""
    _ensure_proj_data_env()

    try:
        from rasterio.crs import CRS
        from rasterio.warp import transform_bounds

        dst_crs = CRS.from_string("+proj=longlat +datum=WGS84 +no_defs")
        minx, miny, maxx, maxy = bounds
        bbox_wgs84 = transform_bounds(src_crs, dst_crs, minx, miny, maxx, maxy, densify_pts=21)
        return [bbox_wgs84[0], bbox_wgs84[1], bbox_wgs84[2], bbox_wgs84[3]], False
    except Exception:
        inferred_crs = _infer_cgcs2000_gk_crs_from_name(crs_text or "")
        if inferred_crs is None:
            return None, False

        try:
            from rasterio.crs import CRS
            from rasterio.warp import transform_bounds

            dst_crs = CRS.from_string("+proj=longlat +datum=WGS84 +no_defs")
            minx, miny, maxx, maxy = bounds
            bbox_wgs84 = transform_bounds(inferred_crs, dst_crs, minx, miny, maxx, maxy, densify_pts=21)
            return [bbox_wgs84[0], bbox_wgs84[1], bbox_wgs84[2], bbox_wgs84[3]], True
        except Exception:
            return None, False


def _extract_geotiff_metadata(file_path: str) -> dict:
    _ensure_proj_data_env()

    try:
        import rasterio
    except Exception as e:
        raise RuntimeError("缺少 rasterio 依赖，无法解析 GeoTIFF 元数据，请先安装 rasterio") from e

    with rasterio.open(file_path) as ds:
        crs_obj = ds.crs
        crs = crs_obj.to_string() if crs_obj else None
        bounds = ds.bounds
        bbox = [bounds.left, bounds.bottom, bounds.right, bounds.top]
        transform = ds.transform
        has_transform = transform is not None and str(transform) != str(rasterio.Affine.identity())
        has_georef = bool(crs and has_transform)

        bbox_wgs84 = None
        crs_inferred = False
        if has_georef and crs_obj:
            bbox_wgs84, crs_inferred = _transform_bounds_to_wgs84(bbox, crs_obj, crs)

        return {
            "crs": crs,
            "bbox": bbox,
            "bbox_wgs84": bbox_wgs84,
            "crs_inferred": crs_inferred,
            "rows": ds.height,
            "cols": ds.width,
            "bands": ds.count,
            "dtype": str(ds.dtypes[0]) if ds.dtypes else None,
            "has_georef": has_georef,
        }


def _remove_edge_connected_black_pixels(rgba, black_threshold=8):
    """将边缘连通的黑色像素置为透明（原地修改 rgba）。"""
    import numpy as np

    h, w = rgba.shape[1], rgba.shape[2]
    black_mask = (
        (rgba[0] <= black_threshold)
        & (rgba[1] <= black_threshold)
        & (rgba[2] <= black_threshold)
        & (rgba[3] > 0)
    )
    if not black_mask.any():
        return

    visited = np.zeros((h, w), dtype=bool)
    q = deque()

    for x in range(w):
        if black_mask[0, x] and not visited[0, x]:
            q.append((0, x))
            visited[0, x] = True
        if black_mask[h - 1, x] and not visited[h - 1, x]:
            q.append((h - 1, x))
            visited[h - 1, x] = True
    for y in range(h):
        if black_mask[y, 0] and not visited[y, 0]:
            q.append((y, 0))
            visited[y, 0] = True
        if black_mask[y, w - 1] and not visited[y, w - 1]:
            q.append((y, w - 1))
            visited[y, w - 1] = True

    while q:
        y, x = q.popleft()
        rgba[3, y, x] = 0
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and black_mask[ny, nx]:
                visited[ny, nx] = True
                q.append((ny, nx))


def _get_stretch_params(file_path: str) -> tuple[list[float], list[float]]:
    """读取降采样影像，计算各波段全局 2%/98% 分位数，保证瓦片拉伸一致性。"""
    import numpy as np
    import rasterio
    from rasterio.enums import Resampling

    with rasterio.open(file_path) as ds:
        if ds.count >= 3:
            indexes = [1, 2, 3]
        elif ds.count == 2:
            indexes = [1, 2, 2]
        else:
            indexes = [1, 1, 1]

        max_side = max(ds.width, ds.height)
        scale = min(1.0, 4096 / max_side) if max_side > 0 else 1.0
        out_w = max(1, int(ds.width * scale))
        out_h = max(1, int(ds.height * scale))

        data = ds.read(indexes=indexes, out_shape=(len(indexes), out_h, out_w), resampling=Resampling.bilinear)
        data = data.astype("float32")

        v2, v98 = [], []
        for i in range(len(indexes)):
            band = data[i]
            p2 = float(np.nanpercentile(band, 2))
            p98 = float(np.nanpercentile(band, 98))
            if p98 <= p2:
                p2 = float(np.nanmin(band))
                p98 = float(np.nanmax(band))
            v2.append(p2)
            v98.append(p98)

    return v2, v98


def _generate_tiles(file_path: str, tiles_dir: str, tile_size: int = TILE_SIZE) -> dict:
    """将 GeoTIFF 切分为固定尺寸 PNG 瓦片，采用 TMS 风格目录结构（y 从底部起算）。"""
    _ensure_proj_data_env()

    import json
    import numpy as np
    import rasterio
    from rasterio.windows import Window

    os.makedirs(tiles_dir, exist_ok=True)

    v2, v98 = _get_stretch_params(file_path)

    with rasterio.open(file_path) as ds:
        cols = ds.width
        rows = ds.height
        band_count = ds.count
        src_crs = ds.crs

        num_tiles_x = (cols + tile_size - 1) // tile_size
        num_tiles_y = (rows + tile_size - 1) // tile_size

        tiles_meta = []

        for ty in range(num_tiles_y):
            row_off = ty * tile_size
            h = min(tile_size, rows - row_off)

            for tx in range(num_tiles_x):
                col_off = tx * tile_size
                w = min(tile_size, cols - col_off)

                window = Window(col_off, row_off, w, h)

                if band_count >= 3:
                    data = ds.read([1, 2, 3], window=window)
                elif band_count == 2:
                    b1 = ds.read(1, window=window)
                    b2 = ds.read(2, window=window)
                    data = np.stack([b1, b2, b2], axis=0)
                else:
                    b1 = ds.read(1, window=window)
                    data = np.stack([b1, b1, b1], axis=0)

                canvas = np.zeros((3, tile_size, tile_size), dtype="float32")
                canvas[:, :h, :w] = data.astype("float32")

                for i in range(3):
                    p2, p98 = v2[i], v98[i]
                    if p98 > p2:
                        canvas[i] = (canvas[i] - p2) * 255.0 / (p98 - p2)
                    else:
                        canvas[i] = 0

                rgb = np.clip(canvas, 0, 255).astype("uint8")

                # TMS y：从底部起算
                tms_y = num_tiles_y - 1 - ty
                tile_path = os.path.join(tiles_dir, "0", str(tx), f"{tms_y}.png")
                os.makedirs(os.path.dirname(tile_path), exist_ok=True)

                with rasterio.open(
                    tile_path,
                    "w",
                    driver="PNG",
                    width=tile_size,
                    height=tile_size,
                    count=3,
                    dtype="uint8",
                ) as out_ds:
                    out_ds.write(rgb)

                # 计算瓦片地理范围
                left, top = ds.xy(row_off, col_off, offset="ul")
                right, bottom = ds.xy(row_off + h - 1, col_off + w - 1, offset="lr")

                tiles_meta.append({
                    "x": tx,
                    "y": tms_y,
                    "width": w,
                    "height": h,
                    "bbox": [left, bottom, right, top],
                })

        meta = {
            "tile_size": tile_size,
            "num_tiles_x": num_tiles_x,
            "num_tiles_y": num_tiles_y,
            "total_tiles": num_tiles_x * num_tiles_y,
            "image_width": cols,
            "image_height": rows,
            "crs": str(src_crs) if src_crs else None,
            "tiles_dir": tiles_dir,
            "tiles": tiles_meta,
        }

        meta_path = os.path.join(tiles_dir, "tiles_meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        return meta


def _ensure_overlay_png(file_path: str, overlay_filename: str = OVERLAY_FILENAME, overlay_max_size: int = OVERLAY_MAX_SIZE) -> str:
    """按需生成用于Cesium叠加的预览PNG（非切片，RGBA透明背景）。"""
    _ensure_proj_data_env()

    try:
        import numpy as np
        import rasterio
        from rasterio.enums import Resampling
    except Exception as e:
        raise RuntimeError("缺少影像处理依赖，无法生成PNG叠加层") from e

    image_dir = os.path.dirname(file_path)
    overlay_path = os.path.join(image_dir, overlay_filename)

    if os.path.exists(overlay_path):
        try:
            with rasterio.open(overlay_path) as old_ds:
                if old_ds.count == 4:
                    return overlay_path
        except Exception:
            pass
        try:
            os.remove(overlay_path)
        except Exception:
            return overlay_path

    with rasterio.open(file_path) as ds:
        max_side = max(ds.width, ds.height)
        scale = min(1.0, overlay_max_size / max_side) if max_side > 0 else 1.0
        out_w = max(1, int(ds.width * scale))
        out_h = max(1, int(ds.height * scale))

        if ds.count >= 3:
            indexes = [1, 2, 3]
        elif ds.count == 2:
            indexes = [1, 2, 2]
        else:
            indexes = [1, 1, 1]

        rgb = ds.read(indexes=indexes, out_shape=(3, out_h, out_w), resampling=Resampling.bilinear)

        if rgb.dtype != "uint8":
            rgb = rgb.astype("float32")
            stretched = np.zeros_like(rgb, dtype="float32")
            for i in range(rgb.shape[0]):
                band = rgb[i]
                p2 = float(np.nanpercentile(band, 2))
                p98 = float(np.nanpercentile(band, 98))
                if p98 <= p2:
                    p2 = float(np.nanmin(band))
                    p98 = float(np.nanmax(band))
                if p98 > p2:
                    stretched[i] = (band - p2) * 255.0 / (p98 - p2)
                else:
                    stretched[i] = 0
            rgb = np.clip(stretched, 0, 255).astype("uint8")

        alpha = ds.dataset_mask(out_shape=(out_h, out_w), resampling=Resampling.nearest)
        rgba = np.concatenate([rgb, alpha[np.newaxis, :, :]], axis=0).astype("uint8")

        # 额外处理：将边缘连通的黑像素置透明，避免黑边遮挡底图
        _remove_edge_connected_black_pixels(rgba, black_threshold=8)


    os.makedirs(os.path.dirname(overlay_path), exist_ok=True)
    with rasterio.open(
        overlay_path,
        "w",
        driver="PNG",
        width=rgba.shape[2],
        height=rgba.shape[1],
        count=4,
        dtype="uint8",
    ) as out_ds:
        out_ds.write(rgba)

    return overlay_path


def process_uploaded_imagery(file_path: str, generate_tiles: bool = False, tiles_dir: str | None = None) -> Dict[str, Any]:
    """本地处理入口：解析GeoTIFF并生成Cesium叠加PNG，可选生成瓦片，供Web后端直接调用。"""
    p = Path(file_path)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"影像不存在: {file_path}")

    metadata = _extract_geotiff_metadata(str(p))

    if not metadata.get("has_georef"):
        raise RuntimeError("该TIFF缺少有效地理参考信息，无法用于地图叠加")

    if not metadata.get("bbox_wgs84"):
        raise RuntimeError("影像坐标系无法转换为WGS84经纬度，暂不支持地图叠加")

    overlay_path = _ensure_overlay_png(str(p))

    result = {
        **metadata,
        "overlay_path": overlay_path,
    }

    if generate_tiles:
        if not tiles_dir:
            tiles_dir = os.path.join(os.path.dirname(str(p)), "tiles")
        tiles_meta = _generate_tiles(str(p), tiles_dir, tile_size=TILE_SIZE)
        result["tiles_meta"] = tiles_meta

    return result


class ImageryOverlayClient:
    """
    影像上传 / 叠加预览 / 分割任务 的统一客户端封装。

    依赖：运行中的后端服务（Flask），其提供以下 REST 接口：
    - POST /api/imagery/upload
    - GET  /api/layers/<image_id>/overlay
    - POST /api/tasks/segment
    - GET  /api/tasks/<task_id>
    - GET  /api/layers/<image_id>/vectors.geojson
    """

    def __init__(self, base_url: str = "http://127.0.0.1:5000") -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    # === 核心能力 ===
    def upload_imagery(self, file_path: str) -> Dict[str, Any]:
        """
        上传 GeoTIFF 影像，返回解析后的基础元数据与 overlay 预览信息。
        :param file_path: 影像绝对路径
        :return: 服务端返回的 JSON dict
        """
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"影像不存在: {file_path}")

        url = f"{self.base_url}/api/imagery/upload"
        with p.open("rb") as f:
            files = {"file": (p.name, f, "application/octet-stream")}
            resp = self.session.post(url, files=files, timeout=600)
        self._raise_for_resp(resp)
        return resp.json()

    def get_overlay_meta(self, image_id: str) -> Dict[str, Any]:
        """
        获取 Cesium 叠加所需的单张瓦片 URL 与经纬度 bbox。
        """
        url = f"{self.base_url}/api/layers/{image_id}/overlay"
        resp = self.session.get(url, timeout=60)
        self._raise_for_resp(resp)
        return resp.json()

    def get_tiles_meta(self, image_id: str) -> Dict[str, Any]:
        """
        获取 448x448 瓦片元数据（网格行列数、各瓦片 bbox 等）。
        """
        url = f"{self.base_url}/api/layers/{image_id}/tiles"
        resp = self.session.get(url, timeout=60)
        self._raise_for_resp(resp)
        return resp.json()

    def start_segmentation(self, image_id: str, model: str = "falcon", tile_size: int = 1024, overlap: int = 128) -> Dict[str, Any]:
        """
        创建分割任务（服务端为占位实现，但具备完整状态流转）。
        """
        url = f"{self.base_url}/api/tasks/segment"
        payload = {
            "image_id": image_id,
            "model": model,
            "tile_size": int(tile_size),
            "overlap": int(overlap),
        }
        resp = self.session.post(url, json=payload, timeout=120)
        self._raise_for_resp(resp)
        return resp.json()

    def poll_task(self, task_id: str, max_retries: int = 20, interval_ms: int = 1500) -> Dict[str, Any]:
        """
        轮询任务状态，直到成功/失败或超时。
        """
        url = f"{self.base_url}/api/tasks/{task_id}"
        for _ in range(max_retries):
            resp = self.session.get(url, timeout=30)
            self._raise_for_resp(resp)
            data = resp.json()
            if data.get("status") in {"success", "failed"}:
                return data
            time.sleep(max(0.05, interval_ms / 1000))
        return {"task_id": task_id, "status": "running", "error_message": None}

    def get_segment_geojson(self, image_id: str) -> Dict[str, Any]:
        """
        获取分割结果 GeoJSON（若已生成）。
        """
        url = f"{self.base_url}/api/layers/{image_id}/vectors.geojson"
        resp = self.session.get(url, timeout=60)
        self._raise_for_resp(resp)
        return resp.json()

    # === 工具方法 ===
    @staticmethod
    def _raise_for_resp(resp: requests.Response) -> None:
        if not resp.ok:
            try:
                detail = resp.json()
            except Exception:
                detail = {"error": resp.text}
            raise RuntimeError(detail.get("error") or f"HTTP {resp.status_code}")

