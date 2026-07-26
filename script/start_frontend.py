# ============================================================
# script/start_frontend.py
# 启动前端 Vite 开发服务器（后台运行）
#
# 用法:
#   python script/start_frontend.py
# ============================================================

import subprocess
import os
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

if not FRONTEND_DIR.is_dir():
    print(f"前端目录不存在: {FRONTEND_DIR}")
    exit(1)

os.chdir(str(FRONTEND_DIR))
print(f"启动前端: http://localhost:5173")

subprocess.Popen(
    "npx vite --host localhost --port 5173",
    shell=True,
    creationflags=subprocess.CREATE_NEW_CONSOLE,
)
