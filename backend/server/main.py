# ============================================================
# backend/server/main.py
# FastAPI 应用入口：创建 app、注册中间件、启动服务
#
# 设计与用法:
#   导出 create_app() 工厂函数
#   直接运行本文件启动开发服务器: python -m server.main
#
# 完整 API 接口:
#   POST   /api/vehicle/telemetry       接收遥测 (speed + steering)
#   POST   /api/vehicle/frame           接收帧数据 (RGB + 深度图)
#   GET    /api/vehicle/position        查询小车当前位置
#   GET    /api/reconstruction/status   重建进度查询
#   GET    /api/reconstruction/result   重建结果获取 (支持 ?since=)
#   GET    /api/detection/result        检测结果查询
#   POST   /api/detection/image         接收单张图像（用于静态检测）
# ============================================================

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api.routes import (
    vehicle_router,
    reconstruction_router,
    detection_router,
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

    return app


app = create_app()

if __name__ == "__main__":
    from server.config import get_config
    cfg = get_config()
    server = cfg.get('server', {})
    host = server.get('host', '127.0.0.1')
    port = server.get('port', 8000)
    uvicorn.run("server.main:app", host=host, port=port, reload=True)
