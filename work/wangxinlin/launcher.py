#!/usr/bin/env python3
"""用地识别智能体启动器

用法:
    python launcher.py start    启动智能体
    python launcher.py stop     停止智能体
    python launcher.py restart  重启智能体
    python launcher.py status   查看运行状态
    python launcher.py logs     查看/跟踪日志
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# 修复 Windows 终端 UTF-8 编码
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

PROJECT_ROOT = Path(__file__).parent.resolve()
LOG_DIR = PROJECT_ROOT / "logs"
PID_FILE = PROJECT_ROOT / ".agent.pid"
APP_PATH = PROJECT_ROOT / "compliance_agent" / "web" / "app.py"


def _ensure_log_dir() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _is_running(pid: int) -> bool:
    """检查进程是否存活（Windows / 跨平台）。"""
    if sys.platform == "win32":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        return str(pid) in result.stdout
    else:
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False


def _get_pid() -> int | None:
    """读取已保存的 PID，若进程已死则清理残留文件。"""
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip())
    except ValueError:
        PID_FILE.unlink(missing_ok=True)
        return None

    if _is_running(pid):
        return pid
    else:
        PID_FILE.unlink(missing_ok=True)
        return None


def _stop_by_pid(pid: int) -> None:
    """通过 PID 终止进程（跨平台）。"""
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True, check=False
            )
        else:
            os.kill(pid, signal.SIGTERM)
    except Exception as e:
        print(f"[WARN] 终止进程时出错: {e}")


def start() -> None:
    """启动 Flask 服务，在前台实时显示日志并写入文件。"""
    _ensure_log_dir()

    existing = _get_pid()
    if existing:
        print(f"[INFO] Agent 已在运行 (PID: {existing})，访问 http://127.0.0.1:5000")
        return

    log_name = f"agent_{time.strftime('%Y%m%d_%H%M%S')}.log"
    log_path = LOG_DIR / log_name

    print(f"[START] 正在启动 Agent ...")
    print(f"[START] 日志文件: {log_path}")
    print(f"[START] 下方将实时显示运行日志，按 Ctrl+C 停止\n")

    kwargs: dict = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    with open(log_path, "w", encoding="utf-8") as f:
        proc = subprocess.Popen(
            [sys.executable, str(APP_PATH)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(PROJECT_ROOT),
            **kwargs,
        )

        PID_FILE.write_text(str(proc.pid), encoding="utf-8")

        try:
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                line_str = line.decode("utf-8", errors="replace")
                sys.stdout.write(line_str)
                sys.stdout.flush()
                f.write(line_str)
                f.flush()
        except KeyboardInterrupt:
            print("\n[STOP] 收到 Ctrl+C，正在停止 Agent ...")
            _stop_by_pid(proc.pid)
        finally:
            proc.stdout.close()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                _stop_by_pid(proc.pid)
                proc.wait()
            PID_FILE.unlink(missing_ok=True)

    if proc.returncode != 0 and proc.returncode is not None:
        print(f"[ERROR] Agent 异常退出 (exit code: {proc.returncode})，请检查日志: {log_path}")
    else:
        print("[INFO] Agent 已停止")


def stop() -> None:
    """停止正在运行的 Agent。"""
    pid = _get_pid()
    if not pid:
        print("[INFO] Agent 未在运行")
        return

    print(f"[STOP] 正在停止 Agent (PID: {pid}) ...")
    _stop_by_pid(pid)
    PID_FILE.unlink(missing_ok=True)
    print("[OK] Agent 已停止")


def restart() -> None:
    """重启 Agent。"""
    stop()
    time.sleep(1)
    start()


def status() -> None:
    """查看 Agent 运行状态。"""
    pid = _get_pid()
    if pid:
        print(f"[RUNNING] Agent 运行中 (PID: {pid})")
        print(f"[RUNNING] 访问地址: http://127.0.0.1:5000")
    else:
        print("[STOPPED] Agent 未运行")


def logs() -> None:
    """交互式日志查看器：列出日志文件，支持查看历史或实时跟踪。"""
    _ensure_log_dir()

    log_files = sorted(LOG_DIR.glob("agent_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not log_files:
        print("[INFO] 暂无日志文件")
        return

    print("\n[日志列表]")
    for idx, f in enumerate(log_files[:10], 1):
        size = f.stat().st_size
        mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(f.stat().st_mtime))
        print(f"  {idx}. {f.name}  ({size:,} bytes, {mtime})")

    print("\n操作选项:")
    print("  输入编号  查看对应日志全文")
    print("  r         实时跟踪最新日志 (tail -f 效果, Ctrl+C 退出)")
    print("  其他      退出")
    choice = input("> ").strip()

    if choice.lower() == "r":
        _tail_latest(log_files[0])
    elif choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(log_files):
            _show_log(log_files[idx])
        else:
            print("[WARN] 无效编号")
    else:
        print("[INFO] 已退出")


def _tail_latest(log_path: Path) -> None:
    """实时跟踪日志文件末尾（类似 tail -f）。"""
    print(f"\n[TAIL] 正在跟踪 {log_path.name} ...")
    print("[TAIL] 按 Ctrl+C 退出\n")
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            # 先输出已有内容
            existing = f.read()
            if existing:
                print(existing, end="")
            # 持续读取新内容
            while True:
                line = f.readline()
                if line:
                    print(line, end="")
                else:
                    time.sleep(0.3)
    except KeyboardInterrupt:
        print("\n\n[INFO] 已退出日志跟踪")


def _show_log(log_path: Path) -> None:
    """显示完整日志内容。"""
    print(f"\n[LOG] {log_path.name}")
    print("=" * 60)
    content = log_path.read_text(encoding="utf-8", errors="replace")
    print(content)
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="用地识别智能体启动器")
    parser.add_argument(
        "command",
        choices=["start", "stop", "restart", "status", "logs"],
        help="操作命令",
    )
    args = parser.parse_args()

    handlers = {
        "start": start,
        "stop": stop,
        "restart": restart,
        "status": status,
        "logs": logs,
    }
    handlers[args.command]()


if __name__ == "__main__":
    main()
