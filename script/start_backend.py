# ============================================================
# script/start_backend.py
# 启动后端开发服务器（后台运行），host/port 从 config.yaml 读取
#
# 用法:
#   python script/start_backend.py
#   python script/start_backend.py --port 8080
#   python script/start_backend.py --reload
# ============================================================

import os
import sys
import argparse
from pathlib import Path

import yaml


def main():
    project_root = Path(__file__).resolve().parent.parent
    backend_dir = project_root / "backend"

    # 读取配置
    config_path = backend_dir / "config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    server_cfg = config.get('server', {})
    default_host = server_cfg.get('host', '127.0.0.1')
    default_port = server_cfg.get('port', 8000)

    parser = argparse.ArgumentParser(description="启动 SuoXing-Tuan 后端")
    parser.add_argument("--host", default=default_host,
                        help=f"监听地址 (默认 {default_host})")
    parser.add_argument("--port", type=int, default=default_port,
                        help=f"监听端口 (默认 {default_port})")
    parser.add_argument("--reload", action="store_true", help="启用热重载")
    args = parser.parse_args()

    os.chdir(str(backend_dir))
    sys.path.insert(0, str(backend_dir))

    print(f"启动后端: http://{args.host}:{args.port}")
    print(f"API 文档: http://{args.host}:{args.port}/docs")
    import uvicorn
    uvicorn.run("server.main:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
