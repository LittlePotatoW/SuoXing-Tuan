# ============================================================
# backend/server/main.py
# FastAPI 应用入口：创建 app、注册中间件、启动服务
#
# 设计与用法:
#   导出 create_app() 工厂函数
#   直接运行本文件启动开发服务器: python -m server.main
#
# 完整 API 接口 (11个):
#   POST   /api/vehicle/telemetry          接收遥测 (speed + steering)
#   POST   /api/vehicle/frame              接收帧数据 (RGB + 深度图)
#   GET    /api/vehicle/position           查询小车当前位置
#   POST   /api/vehicle/estimator/reset    重置位置估计器 + 切模式
#   GET    /api/vehicle/estimator/config   查询估计器配置和位置
#   GET    /api/reconstruction/status      重建进度查询
#   GET    /api/reconstruction/result      重建结果获取 (支持 ?since=)
#   POST   /api/reconstruction/reset       重置重建引擎 + 改参数
#   GET    /api/reconstruction/config      查询引擎配置和状态
#   GET    /api/detection/result           检测结果查询
#   POST   /api/detection/image            接收单张图像（用于静态检测）
# ============================================================

import uvicorn
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.api.routes import (
    vehicle_router,
    reconstruction_router,
    detection_router,
    session_router,
    report_router,
)


def create_app() -> FastAPI:
    app = FastAPI(title="SuoXing-Tuan", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(vehicle_router)
    app.include_router(reconstruction_router)
    app.include_router(detection_router)
    app.include_router(session_router)
    app.include_router(report_router)

    output_dir = Path(__file__).resolve().parent.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/output", StaticFiles(directory=str(output_dir)), name="output")

    return app


app = create_app()

if __name__ == "__main__":
    from server.config import get_config
    cfg = get_config()
    server = cfg.get('server', {})
    host = server.get('host', '127.0.0.1')
    port = server.get('port', 8000)
    uvicorn.run("server.main:app", host=host, port=port, reload=True)
