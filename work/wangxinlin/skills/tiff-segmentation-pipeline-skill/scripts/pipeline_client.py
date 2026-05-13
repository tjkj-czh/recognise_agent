from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import requests


class PipelineClient:
    """recognise_agent TIFF→切片→分割→矢量链路客户端。"""

    def __init__(self, base_url: str, timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.timeout = int(timeout)
        self.session = requests.Session()

    def upload_imagery(self, tiff_path: str) -> dict[str, Any]:
        p = Path(tiff_path)
        if not p.exists() or not p.is_file():
            raise FileNotFoundError(f"影像文件不存在: {tiff_path}")

        with p.open("rb") as f:
            resp = self.session.post(
                f"{self.base_url}/api/imagery/upload",
                files={"file": (p.name, f, "application/octet-stream")},
                timeout=max(self.timeout, 120),
            )
        return self._json_or_raise(resp)

    def get_imagery(self, image_id: str) -> dict[str, Any]:
        resp = self.session.get(f"{self.base_url}/api/imagery/{image_id}", timeout=self.timeout)
        return self._json_or_raise(resp)

    def wait_imagery_ready(self, image_id: str, poll_interval_s: float, timeout_s: float) -> dict[str, Any]:
        start = time.time()
        last = None
        while time.time() - start <= timeout_s:
            last = self.get_imagery(image_id)
            status = str(last.get("status") or "")
            if status == "ready":
                return last
            if status == "failed":
                raise RuntimeError(last.get("error_message") or "影像切片失败")
            time.sleep(max(0.1, poll_interval_s))
        raise TimeoutError(f"等待影像切片就绪超时: {timeout_s}s, last_status={last.get('status') if isinstance(last, dict) else None}")

    def create_segment_task(self, image_id: str, tile_size: int, overlap: int, model: str = "falcon") -> dict[str, Any]:
        payload = {
            "image_id": image_id,
            "model": model,
            "tile_size": int(tile_size),
            "overlap": int(overlap),
        }
        resp = self.session.post(f"{self.base_url}/api/tasks/segment", json=payload, timeout=max(self.timeout, 120))
        return self._json_or_raise(resp)

    def get_task(self, task_id: str) -> dict[str, Any]:
        resp = self.session.get(f"{self.base_url}/api/tasks/{task_id}", timeout=self.timeout)
        return self._json_or_raise(resp)

    def wait_task_done(self, task_id: str, poll_interval_s: float, timeout_s: float) -> dict[str, Any]:
        start = time.time()
        last = None
        while time.time() - start <= timeout_s:
            last = self.get_task(task_id)
            status = str(last.get("status") or "")
            if status in {"success", "failed"}:
                return last
            time.sleep(max(0.1, poll_interval_s))
        raise TimeoutError(f"等待任务结束超时: {timeout_s}s, last_status={last.get('status') if isinstance(last, dict) else None}")

    def get_vectors_geojson(self, image_id: str) -> dict[str, Any]:
        resp = self.session.get(f"{self.base_url}/api/layers/{image_id}/vectors.geojson", timeout=self.timeout)
        return self._json_or_raise(resp)

    @staticmethod
    def _json_or_raise(resp: requests.Response) -> dict[str, Any]:
        try:
            data = resp.json()
        except Exception:
            data = {"error": resp.text}

        if not resp.ok:
            raise RuntimeError(data.get("error") or f"HTTP {resp.status_code}")
        if not isinstance(data, dict):
            raise RuntimeError("接口返回非 JSON 对象")
        return data
