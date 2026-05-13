#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from run_pipeline import main as run_pipeline_main


"""
上传事件专用入口：
- 对外暴露更少参数，便于第三方系统集成；
- 内部复用 run_pipeline.py 完整逻辑。
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="上传事件触发分割链路（封装入口）")
    parser.add_argument("--base-url", default="", help="服务地址，不传则使用 config.yaml 默认值")
    parser.add_argument("--event-file", default="", help="事件 JSON 文件")
    parser.add_argument("--event-json", default="", help="事件 JSON 字符串")
    parser.add_argument("--event-stdin", action="store_true", help="从标准输入读取事件 JSON")
    parser.add_argument("--tile-size", type=int, default=None, help="可选覆盖切片尺寸")
    parser.add_argument("--overlap", type=int, default=None, help="可选覆盖切片重叠")
    parser.add_argument("--imagery-timeout", type=float, default=None, help="可选覆盖切片等待超时秒数")
    parser.add_argument("--task-timeout", type=float, default=None, help="可选覆盖任务等待超时秒数")
    args = parser.parse_args()

    forwarded_args: list[str] = []
    if args.base_url:
        forwarded_args += ["--base-url", args.base_url]

    if args.event_file:
        if not Path(args.event_file).exists():
            raise FileNotFoundError(f"事件文件不存在: {args.event_file}")
        forwarded_args += ["--event-file", args.event_file]

    if args.event_json:
        forwarded_args += ["--event-json", args.event_json]

    if args.event_stdin:
        forwarded_args.append("--event-stdin")

    if args.tile_size is not None:
        forwarded_args += ["--tile-size", str(args.tile_size)]

    if args.overlap is not None:
        forwarded_args += ["--overlap", str(args.overlap)]

    if args.imagery_timeout is not None:
        forwarded_args += ["--imagery-timeout", str(args.imagery_timeout)]

    if args.task_timeout is not None:
        forwarded_args += ["--task-timeout", str(args.task_timeout)]

    return run_pipeline_main(forwarded_args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        import json

        print(json.dumps({"error": str(e)}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
