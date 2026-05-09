---
name: imagery-cesium-overlay
version: 0.1.0
author: recognise-agent
license: MIT
---

概述
- 功能：封装本项目已实现的 影像上传、影像解析、生成叠加预览、触发分割任务 与 获取分割矢量层 的统一调用接口，供其他智能体复用。
- 依赖：需要启动本项目 Flask Web 服务，并提供 base_url（如 http://127.0.0.1:5000）。
- 输入输出：见下方接口定义。

接口定义
1) upload_imagery(file_path: str) -> dict
- 说明：上传 GeoTIFF 影像，返回解析后的基础元数据与 overlay 预览信息（含 overlay_url）。
- 返回：{"image_id", "filename", "file_size", "crs", "bbox", "rows", "cols", "bands", "overlay_url", ...}

2) get_overlay_meta(image_id: str) -> dict
- 说明：根据 image_id 获取用于 Cesium 叠加的矩形范围与单张瓦片 URL。
- 返回：{"image_id", "bbox", "overlay_url"}

3) start_segmentation(image_id: str, model: str = "falcon", tile_size: int = 1024, overlap: int = 128) -> dict
- 说明：创建分割任务，当前服务端为占位实现，返回 task_id。
- 返回：{"task_id", "status", "result_layer_id"}

4) poll_task(task_id: str, max_retries: int = 20, interval_ms: int = 1500) -> dict
- 说明：轮询任务状态，直到成功/失败或超时。
- 返回：{"task_id", "status", ...}

5) get_segment_geojson(image_id: str) -> dict
- 说明：获取分割结果 GeoJSON（若已生成）。
- 返回：GeoJSON FeatureCollection

使用方式
- 推荐通过 Python 导入本 Skill 并初始化客户端：

    from skills.imagery-cesium-overlay.imagery_skill import ImageryOverlayClient
    client = ImageryOverlayClient(base_url="http://127.0.0.1:5000")
    meta = client.upload_imagery("/path/to/image.tif")
    overlay = client.get_overlay_meta(meta["image_id"])
    task = client.start_segmentation(meta["image_id"])  # 可选
    status = client.poll_task(task["task_id"])          # 可选
    seg = client.get_segment_geojson(meta["image_id"])  # 可选

注意
- 需要先启动 Flask 服务：python work/wangxinlin/compliance_agent/web/app.py
- 仅支持 .tif/.tiff，且需具备有效地理参考并可转换到 WGS84。
