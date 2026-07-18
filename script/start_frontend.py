# ============================================================
# script/start_frontend.py
# 启动前端开发服务器
#
# 用法:
#   python script/start_frontend.py
#   python script/start_frontend.py --port 3000
# ============================================================

import os
import sys
import argparse
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="启动 SuoXing-Tuan 前端")
    parser.add_argument("--port", type=int, default=5173, help="监听端口 (默认 5173)")
    parser.add_argument("--host", default="localhost", help="监听地址 (默认 localhost)")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    frontend_dir = project_root / "frontend"
    os.chdir(str(frontend_dir))

    print(f"启动前端: http://{args.host}:{args.port}")

    # 使用本地 node_modules 的 vite，不依赖系统 PATH
    import platform
    if platform.system() == 'Windows':
        vite_bin = str(frontend_dir / 'node_modules' / '.bin' / 'vite.cmd')
    else:
        vite_bin = str(frontend_dir / 'node_modules' / '.bin' / 'vite')

    subprocess.run(
        [vite_bin, "--host", args.host, "--port", str(args.port)],
        check=False,
    )


if __name__ == "__main__":
    main()
