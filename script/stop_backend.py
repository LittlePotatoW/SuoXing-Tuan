# ============================================================
# script/stop_backend.py
# 关闭后端 uvicorn 服务进程（查找并终止）
#
# 设计与用法:
#   用法: python script/stop_backend.py
#   查找运行中的 uvicorn 进程并终止
# ============================================================

import os
import sys
import signal
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_backend_pids():
    """查找所有 uvicorn 相关进程的 PID"""
    pids = []
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True,
        )
        raw_pids = result.stdout.strip()
        if not raw_pids:
            return pids

        for line in raw_pids.splitlines():
            parts = line.replace('"', "").split(",")
            if len(parts) >= 2:
                pid_str = parts[1].strip()
                try:
                    pid = int(pid_str)
                    pids.append(pid)
                except ValueError:
                    continue
    except Exception:
        pass
    return pids


def find_uvicorn_pids():
    """通过 netstat 找到监听 8000 端口的进程 PID"""
    pids = set()
    try:
        result = subprocess.run(
            ["netstat", "-ano", "-p", "TCP"],
            capture_output=True, text=True,
        )
        for line in result.stdout.splitlines():
            if ":8000" in line and "LISTENING" in line:
                parts = line.strip().split()
                pid = parts[-1]
                if pid.isdigit():
                    pids.add(int(pid))
    except Exception:
        pass
    return pids


def kill_pid(pid):
    """终止指定 PID 的进程"""
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"  已发送终止信号到 PID {pid}")
        return True
    except Exception:
        return False


def main():
    print("正在查找后端服务进程...")

    # 方法1: 通过端口查找
    pids = find_uvicorn_pids()

    if not pids:
        print("未找到监听 8000 端口的进程，后端可能未运行")
        return

    print(f"找到 {len(pids)} 个进程占用 8000 端口")
    for pid in pids:
        kill_pid(pid)

    print("完成")


if __name__ == "__main__":
    main()
