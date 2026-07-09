# ============================================================
# script/stop_simulator.py
# 停止模拟器服务 — 查找并终止占用 9000 端口的进程
#
# 用法:
#   python script/stop_simulator.py
# ============================================================

import subprocess
import sys

PORT = 9000


def stop():
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
                print(f"已终止 PID {pid} (模拟器端口 {PORT})")
                return
    except Exception:
        pass

    print("模拟器停止完成")


if __name__ == "__main__":
    stop()
