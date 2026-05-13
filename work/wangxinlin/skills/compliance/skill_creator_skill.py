"""Skill Creator Skill：封装 DazhuangSkill-Creator 框架，为用地识别智能体提供 skill 生命周期管理能力。

提供的工具：
- skill_create：创建新 skill 脚手架
- skill_validate：验证 skill 结构合规性
- skill_package：打包 skill 为可分发 .skill 文件
- skill_evaluate_trigger：评估 skill 描述的触发准确率
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from langchain_core.tools import tool

# 定位 DazhuangSkill-Creator 根目录
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WORKSPACE_DIR = os.path.dirname(_PROJECT_ROOT)
_DAZHUANG_DIR = os.path.join(_WORKSPACE_DIR, "skills", "DazhuangSkill-Creator-main")
_SCRIPTS_DIR = os.path.join(_DAZHUANG_DIR, "scripts")


def _run_script(script_name: str, args: list[str], cwd: str | None = None, timeout: int = 60) -> dict:
    """调用 DazhuangSkill-Creator 脚本并返回结构化结果。"""
    script_path = os.path.join(_SCRIPTS_DIR, script_name)
    if not os.path.isfile(script_path):
        return {"success": False, "error": f"脚本不存在: {script_path}"}

    cmd = [sys.executable, script_path] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd or _DAZHUANG_DIR,
            timeout=timeout,
            encoding="utf-8",
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"脚本执行超时（>{timeout}s）"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def skill_create(
    name: str,
    output_path: str = "",
    intent: str = "",
    memory_mode: str = "auto",
    resources: str = "scripts,references,assets",
    sections: str = "role,examples,output-format,index",
    with_examples: bool = False,
    with_config: bool = False,
) -> str:
    """创建一个新的 Claude Code skill 脚手架。

    Args:
        name: skill 名称（英文，连字符连接，如 landuse-analyzer）
        output_path: 输出目录，留空则使用默认路径
        intent: skill 用途意图描述（用于 auto memory 分类）
        memory_mode: off | lessons | adaptive | auto
        resources: 逗号分隔的资源类型，如 scripts,references,assets
        sections: 逗号分隔的 SKILL.md 内联章节，如 role,examples,output-format,index
        with_examples: 是否包含示例
        with_config: 是否生成 config.yaml

    Returns:
        JSON 字符串，包含 success、message、skill_path
    """
    args = [name]
    if output_path:
        args += ["--path", output_path]
    if intent:
        args += ["--intent", intent]
    if memory_mode:
        args += ["--memory-mode", memory_mode]
    if resources:
        args += ["--resources", resources]
    if sections:
        args += ["--sections", sections]
    if with_examples:
        args.append("--examples")
    if with_config:
        args.append("--config-file")

    result = _run_script("init_skill.py", args, timeout=30)
    if not result["success"]:
        return json.dumps(
            {"success": False, "error": result.get("stderr") or result.get("error")},
            ensure_ascii=False,
        )

    # 解析 stdout 找出生成的路径
    stdout = result.get("stdout", "")
    skill_path = ""
    for line in stdout.splitlines():
        if "已创建" in line or "Created" in line or line.strip().startswith(os.sep):
            skill_path = line.strip().split()[-1]

    return json.dumps(
        {
            "success": True,
            "message": f"Skill '{name}' 创建成功。",
            "stdout": stdout,
            "stderr": result.get("stderr", ""),
            "skill_path": skill_path,
        },
        ensure_ascii=False,
    )


@tool
def skill_validate(skill_path: str, strict: bool = False) -> str:
    """验证 skill 目录结构是否符合 DazhuangSkill-Creator 规范。

    Args:
        skill_path: skill 目录的绝对或相对路径
        strict: 是否启用严格模式（检查 TODO/占位符等）

    Returns:
        JSON 字符串，包含 success、errors、warnings
    """
    args = [skill_path]
    if strict:
        args.append("--strict")

    result = _run_script("quick_validate.py", args, timeout=30)
    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")

    # quick_validate.py 返回 0 表示通过，非 0 表示有问题
    errors = []
    warnings = []
    for line in (stdout + "\n" + stderr).splitlines():
        line_stripped = line.strip()
        if line_stripped.startswith("[错误]") or line_stripped.startswith("[ERROR]"):
            errors.append(line_stripped)
        elif line_stripped.startswith("[警告]") or line_stripped.startswith("[WARN]"):
            warnings.append(line_stripped)

    return json.dumps(
        {
            "success": result["success"] and not errors,
            "valid": result["success"] and not errors,
            "errors": errors,
            "warnings": warnings,
            "stdout": stdout,
            "stderr": stderr,
        },
        ensure_ascii=False,
    )


@tool
def skill_package(skill_path: str, output_dir: str = "") -> str:
    """将 skill 目录打包为可分发的 .skill 文件。

    Args:
        skill_path: 要打包的 skill 目录路径
        output_dir: .skill 文件输出目录，留空则默认当前目录

    Returns:
        JSON 字符串，包含 success、package_path、message
    """
    args = [skill_path]
    if output_dir:
        args.append(output_dir)

    result = _run_script("package_skill.py", args, timeout=30)
    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")

    package_path = ""
    for line in stdout.splitlines():
        if line.strip().endswith(".skill"):
            package_path = line.strip().split()[-1]

    return json.dumps(
        {
            "success": result["success"],
            "message": f"打包{'成功' if result['success'] else '失败'}",
            "package_path": package_path,
            "stdout": stdout,
            "stderr": stderr,
        },
        ensure_ascii=False,
    )


@tool
def skill_evaluate_trigger(
    skill_path: str,
    eval_set_path: str = "",
    num_workers: int = 5,
    timeout: int = 30,
) -> str:
    """评估 skill 描述的触发准确率（Trigger Evaluation）。

    检查 skill 的 description 是否会让 Claude 在一组 query 上正确触发。

    Args:
        skill_path: skill 目录路径（需包含 SKILL.md）
        eval_set_path: 评测问题集 JSON 文件路径，留空则使用默认
        num_workers: 并行 worker 数量
        timeout: 每个 query 的超时秒数

    Returns:
        JSON 字符串，包含 trigger_rate、details、report_path
    """
    args = ["--skill-path", skill_path]
    if eval_set_path:
        args += ["--eval-set", eval_set_path]
    if num_workers != 5:
        args += ["--num-workers", str(num_workers)]
    if timeout != 30:
        args += ["--timeout", str(timeout)]

    result = _run_script("run_eval.py", args, timeout=300)
    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")

    # 尝试从 stdout 解析 JSON 报告
    report_data = {}
    try:
        # run_eval.py 可能在最后一行输出 JSON
        lines = stdout.strip().splitlines()
        for line in reversed(lines):
            line = line.strip()
            if line.startswith("{"):
                report_data = json.loads(line)
                break
    except (json.JSONDecodeError, ValueError):
        pass

    return json.dumps(
        {
            "success": result["success"],
            "report": report_data,
            "stdout": stdout,
            "stderr": stderr,
        },
        ensure_ascii=False,
    )


# ── 便捷函数（非 tool，供直接调用） ──
def list_dazhuang_scripts() -> list[str]:
    """列出 DazhuangSkill-Creator 提供的所有可用脚本。"""
    if not os.path.isdir(_SCRIPTS_DIR):
        return []
    return [f for f in os.listdir(_SCRIPTS_DIR) if f.endswith(".py")]


def get_dazhuang_info() -> dict:
    """获取 DazhuangSkill-Creator 基本信息。"""
    version_file = os.path.join(_DAZHUANG_DIR, "VERSION")
    version = "unknown"
    if os.path.isfile(version_file):
        with open(version_file, "r", encoding="utf-8") as f:
            version = f.read().strip()

    return {
        "version": version,
        "path": _DAZHUANG_DIR,
        "scripts": list_dazhuang_scripts(),
        "available_tools": ["skill_create", "skill_validate", "skill_package", "skill_evaluate_trigger"],
    }
