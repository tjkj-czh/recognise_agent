#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None

from pipeline_client import PipelineClient



def load_config(skill_base: Path) -> dict[str, Any]:
    cfg_path = skill_base / "config.yaml"
    if not cfg_path.exists() or yaml is None:
        return {}
    with cfg_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}



def main() -> int:
    script_dir = Path(__file__).resolve().parent
    skill_base = script_dir.parent
    cfg = load_config(skill_base)
    p_cfg = (cfg.get("pipeline") or {}) if isinstance(cfg, dict) else {}

    parser = argparse.ArgumentParser(description="执行 TIFF→切片→识别→拉取矢量 全链路")
    parser.add_argument("--base-url", default=p_cfg.get("base_url", "http://127.0.0.1:5000"))
    parser.add_argument("--tiff", required=True, help="TIFF 绝对路径")
    parser.add_argument("--tile-size", type=int, default=int(p_cfg.get("tile_size", 448)))
    parser.add_argument("--overlap", type=int, default=int(p_cfg.get("overlap", 90)))
    parser.add_argument("--imagery-poll-interval", type=float, default=float(p_cfg.get("imagery_poll_interval_seconds", 1.5)))
    parser.add_argument("--imagery-timeout", type=float, default=float(p_cfg.get("imagery_poll_timeout_seconds", 300)))
    parser.add_argument("--task-poll-interval", type=float, default=float(p_cfg.get("task_poll_interval_seconds", 2.0)))
    parser.add_argument("--task-timeout", type=float, default=float(p_cfg.get("task_poll_timeout_seconds", 1800)))
    args = parser.parse_args()

    client = PipelineClient(base_url=args.base_url)

    upload = client.upload_imagery(args.tiff)
    image_id = str(upload.get("image_id") or "")
    if not image_id:
        raise RuntimeError("上传成功但未返回 image_id")

    imagery = client.wait_imagery_ready(
        image_id=image_id,
        poll_interval_s=float(args.imagery_poll_interval),
        timeout_s=float(args.imagery_timeout),
    )

    task = client.create_segment_task(
        image_id=image_id,
        tile_size=int(args.tile_size),
        overlap=int(args.overlap),
        model="falcon",
    )
    task_id = str(task.get("task_id") or "")
    if not task_id:
        raise RuntimeError("创建任务成功但未返回 task_id")

    task_done = client.wait_task_done(
        task_id=task_id,
        poll_interval_s=float(args.task_poll_interval),
        timeout_s=float(args.task_timeout),
    )

    vectors = client.get_vectors_geojson(image_id)
    features = vectors.get("features") if isinstance(vectors, dict) else []
    features_count = len(features) if isinstance(features, list) else 0

    result = {
        "base_url": args.base_url,
        "tiff_path": args.tiff,
        "image_id": image_id,
        "task_id": task_id,
        "imagery_status": imagery.get("status"),
        "task_status": task_done.get("status"),
        "task_feature_count": task_done.get("feature_count"),
        "geojson_feature_count": features_count,
        "vectors_url": f"{args.base_url.rstrip('/')}/api/layers/{image_id}/vectors.geojson",
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
