# ============================================================
# script/stop_backend.py
# 停止后端服务 — 查找并终止占用 8000 端口的 Python 进程
#
# 用法:
#   python script/stop_backend.py
# ============================================================

import subprocess
import sys

PORT = 8000

def stop():
    # 方法1: 直接杀 python 进程（简单粗暴）
    try:
        subprocess.run(["taskkill", "/F", "/IM", "python.exe"],
                       capture_output=True, shell=True)
    except Exception:
        pass

    # 方法2: 用 netstat 找到占用端口的 PID 然后杀（更精确）
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, shell=True,
        )
        for line in result.stdout.splitlines():
            if f":{PORT}" in line and "LISTENING" in line:
                pid = line.strip().split()[-1]
                subprocess.run(["taskkill", "/F", "/PID", pid],
                               capture_output=True, shell=True)
                print(f"已终止 PID {pid} (端口 {PORT})")
                return
    except Exception:
        pass

    print("后端停止完成")

if __name__ == "__main__":
    stop()
