# ============================================================
# script/stop_frontend.py
# 停止前端服务 — 查找并终止占用 5173 端口的 node 进程
#
# 用法:
#   python script/stop_frontend.py
# ============================================================

import subprocess
import sys

PORT = 5173


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
                print(f"已终止 PID {pid} (前端端口 {PORT})")
                return
    except Exception:
        pass

    try:
        subprocess.run(["taskkill", "/F", "/IM", "node.exe"],
                       capture_output=True, shell=True)
        print("已终止所有 node.exe 进程")
    except Exception:
        pass

    print("前端停止完成")


if __name__ == "__main__":
    stop()
