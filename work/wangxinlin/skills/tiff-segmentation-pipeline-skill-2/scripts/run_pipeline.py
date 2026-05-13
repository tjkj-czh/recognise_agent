#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import sys
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


def _parse_event_text(text: str) -> dict[str, Any]:
    if not text:
        return {}

    # 兼容 Windows 管道里可能出现的 BOM/前后噪声字符
    cleaned = text.replace("\ufeff", "").strip()
    if not cleaned:
        return {}

    if "{" in cleaned and "}" in cleaned:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if end > start:
            cleaned = cleaned[start:end + 1]

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # 兼容部分 shell 里传入的 Python 风格字典字符串
        data = ast.literal_eval(cleaned)
    return data if isinstance(data, dict) else {}


def _load_event_payload(event_file: str, event_json: str, event_stdin: bool = False) -> dict[str, Any]:
    if event_json:
        return _parse_event_text(event_json)

    if event_file:
        with Path(event_file).open("r", encoding="utf-8-sig") as f:
            return _parse_event_text(f.read())

    if event_stdin and not sys.stdin.isatty():
        return _parse_event_text(sys.stdin.read())

    return {}


def _extract_str(payload: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _resolve_inputs(args: argparse.Namespace) -> tuple[str, str, dict[str, Any]]:
    event_payload = _load_event_payload(
        str(args.event_file or ""),
        str(args.event_json or ""),
        bool(getattr(args, "event_stdin", False)),
    )
    event_data = event_payload.get("data") if isinstance(event_payload.get("data"), dict) else {}
    event_payload_inner = event_payload.get("payload") if isinstance(event_payload.get("payload"), dict) else {}

    image_id = str(args.image_id or "").strip()
    tiff_path = str(args.tiff or "").strip()

    if not image_id:
        image_id = (
            _extract_str(event_payload, ["image_id"])
            or _extract_str(event_data, ["image_id"])
            or _extract_str(event_payload_inner, ["image_id"])
        )

    if not tiff_path:
        tiff_path = (
            _extract_str(event_payload, ["tiff_path", "file_path", "path"])
            or _extract_str(event_data, ["tiff_path", "file_path", "path"])
            or _extract_str(event_payload_inner, ["tiff_path", "file_path", "path"])
        )

    if image_id and tiff_path:
        # 优先复用已上传事件携带的 image_id，避免重复上传
        tiff_path = ""

    if not image_id and not tiff_path:
        raise RuntimeError("必须提供 --tiff 或 --image-id，或在事件中包含 image_id/tiff_path")

    return image_id, tiff_path, event_payload


def main(argv: list[str] | None = None) -> int:
    script_dir = Path(__file__).resolve().parent
    skill_base = script_dir.parent
    cfg = load_config(skill_base)
    p_cfg = (cfg.get("pipeline") or {}) if isinstance(cfg, dict) else {}

    parser = argparse.ArgumentParser(description="执行 TIFF→切片→识别→拉取矢量 全链路")
    parser.add_argument("--base-url", default=p_cfg.get("base_url", "http://127.0.0.1:5000"))
    parser.add_argument("--tiff", default="", help="TIFF 绝对路径（与 --image-id 二选一）")
    parser.add_argument("--image-id", default="", help="已上传影像的 image_id（用于上传事件续跑）")
    parser.add_argument("--event-file", default="", help="上传事件 JSON 文件路径（可选，含 image_id/tiff_path）")
    parser.add_argument("--event-json", default="", help="上传事件 JSON 字符串（可选，含 image_id/tiff_path）")
    parser.add_argument("--event-stdin", action="store_true", help="从标准输入读取事件 JSON（适合消息队列/管道调用）")
    parser.add_argument("--tile-size", type=int, default=int(p_cfg.get("tile_size", 448)))
    parser.add_argument("--overlap", type=int, default=int(p_cfg.get("overlap", 90)))
    parser.add_argument("--imagery-poll-interval", type=float, default=float(p_cfg.get("imagery_poll_interval_seconds", 1.5)))
    parser.add_argument("--imagery-timeout", type=float, default=float(p_cfg.get("imagery_poll_timeout_seconds", 300)))
    parser.add_argument("--task-poll-interval", type=float, default=float(p_cfg.get("task_poll_interval_seconds", 2.0)))
    parser.add_argument("--task-timeout", type=float, default=float(p_cfg.get("task_poll_timeout_seconds", 1800)))
    args = parser.parse_args(argv)

    image_id, tiff_path, event_payload = _resolve_inputs(args)
    client = PipelineClient(base_url=args.base_url)

    trigger_mode = "image_id"
    upload: dict[str, Any] = {}

    if tiff_path:
        trigger_mode = "tiff_upload"
        upload = client.upload_imagery(tiff_path)
        image_id = str(upload.get("image_id") or "")
        if not image_id:
            raise RuntimeError("上传成功但未返回 image_id")

    imagery = client.get_imagery(image_id)
    imagery_status = str(imagery.get("status") or "")
    if imagery_status != "ready":
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

    task_status = str(task_done.get("status") or "")
    if task_status == "failed":
        raise RuntimeError(task_done.get("error_message") or f"分割任务失败: task_id={task_id}")

    vectors = client.get_vectors_geojson(image_id)
    features = vectors.get("features") if isinstance(vectors, dict) else []
    features_count = len(features) if isinstance(features, list) else 0

    result = {
        "base_url": args.base_url,
        "trigger_mode": trigger_mode,
        "event_present": bool(event_payload),
        "tiff_path": tiff_path or None,
        "image_id": image_id,
        "task_id": task_id,
        "imagery_status": imagery.get("status"),
        "task_status": task_done.get("status"),
        "task_feature_count": task_done.get("feature_count"),
        "geojson_feature_count": features_count,
        "vectors_url": f"{args.base_url.rstrip('/')}/api/layers/{image_id}/vectors.geojson",
    }
    if upload:
        result["upload_status"] = upload.get("status")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
