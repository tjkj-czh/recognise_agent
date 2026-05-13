#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


def load_config(skill_base: Path) -> dict:
    p = skill_base / "config.yaml"
    if not p.exists() or yaml is None:
        return {}
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


def run_cmd(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace")


def detect_default_python_cmd() -> str:
    if shutil.which("py"):
        return "py -3"
    if shutil.which("python"):
        return "python"
    if shutil.which("python3"):
        return "python3"
    return "python"


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    skill_base = script_dir.parent
    creator_base = skill_base.parent / "DazhuangSkill-Creator-main"
    cfg = load_config(skill_base)

    parser = argparse.ArgumentParser(description="按 Dazhuang 标准执行 skill 校验/测评")
    parser.add_argument("--mode", choices=["validate", "trigger", "smoke"], default="validate")
    parser.add_argument("--python-cmd", default=detect_default_python_cmd(), help="自动探测 py/python/python3，也可手动覆盖")
    parser.add_argument("--tiff", default="", help="smoke 模式需要的 TIFF 文件路径")
    parser.add_argument("--base-url", default=((cfg.get("pipeline") or {}).get("base_url", "http://127.0.0.1:5000")))
    args = parser.parse_args()

    py_cmd = args.python_cmd.split()

    quick_validate = creator_base / "scripts" / "quick_validate.py"
    validate_cmd = [*py_cmd, str(quick_validate), str(skill_base), "--strict"]
    validate = run_cmd(validate_cmd, cwd=skill_base)

    output = {
        "mode": args.mode,
        "python_cmd": args.python_cmd,
        "validate": {
            "cmd": " ".join(validate_cmd),
            "returncode": validate.returncode,
            "stdout": validate.stdout,
            "stderr": validate.stderr,
        },
    }

    if validate.returncode != 0:
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return validate.returncode

    if args.mode == "validate":
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0

    if args.mode == "trigger":
        run_eval = creator_base / "scripts" / "run_eval.py"
        eval_set = (cfg.get("evaluation") or {}).get("trigger_eval_set", "evals/trigger-eval-set.json")
        trigger_cmd = [
            *py_cmd,
            str(run_eval),
            "--eval-set",
            str(skill_base / eval_set),
            "--skill-path",
            str(skill_base),
            "--verbose",
        ]
        trigger = run_cmd(trigger_cmd, cwd=skill_base)
        output["trigger_eval"] = {
            "cmd": " ".join(trigger_cmd),
            "returncode": trigger.returncode,
            "stdout": trigger.stdout,
            "stderr": trigger.stderr,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return trigger.returncode

    if args.mode == "smoke":
        if not args.tiff:
            output["smoke"] = {"error": "smoke 模式必须提供 --tiff"}
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return 2

        pipeline_cmd = [
            *py_cmd,
            str(skill_base / "scripts" / "run_pipeline.py"),
            "--base-url",
            args.base_url,
            "--tiff",
            args.tiff,
        ]
        smoke = run_cmd(pipeline_cmd, cwd=skill_base)
        output["smoke"] = {
            "cmd": " ".join(pipeline_cmd),
            "returncode": smoke.returncode,
            "stdout": smoke.stdout,
            "stderr": smoke.stderr,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return smoke.returncode

    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
