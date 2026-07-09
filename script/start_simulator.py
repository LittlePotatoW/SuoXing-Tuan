# ============================================================
# script/start_simulator.py
# 启动小车数据模拟器 — 在 test_end/ 下启动，浏览器打开界面
#
# 用法:
#   python script/start_simulator.py
# ============================================================

import subprocess
import os
import webbrowser
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
SIMULATOR_DIR = os.path.join(PROJECT_DIR, "test_end")
VENV_PYTHON = os.path.join(PROJECT_DIR, ".venv", "python.exe")

PORT = 9000
URL = f"http://localhost:9000"


def main():
    if not os.path.exists(VENV_PYTHON):
        print(f"虚拟环境 Python 未找到: {VENV_PYTHON}")
        return

    print(f"启动模拟器 → {URL}")
    # 启动 uvicorn
    subprocess.Popen(
        [VENV_PYTHON, "simulator.py"],
        cwd=SIMULATOR_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    time.sleep(2)

    webbrowser.open(URL)
    print("模拟器已启动")


if __name__ == "__main__":
    main()
