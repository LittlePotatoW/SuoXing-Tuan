# ============================================================
# script/start_frontend.py
# 启动前端 Vite 开发服务器
#
# 用法:
#   python script/start_frontend.py
# ============================================================

import subprocess
import os
import sys

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

def start():
    if not os.path.isdir(FRONTEND_DIR):
        print(f"前端目录不存在: {FRONTEND_DIR}")
        sys.exit(1)

    os.chdir(FRONTEND_DIR)
    print(f"启动前端: {FRONTEND_DIR}")
    print("Vite 开发服务器: http://localhost:5173")

    subprocess.Popen(
        ["npx", "vite", "--host", "localhost", "--port", "5173"],
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

if __name__ == "__main__":
    start()
