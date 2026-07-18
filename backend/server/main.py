# ============================================================
# backend/server/main.py
# FastAPI 应用入口：创建 app、注册中间件、启动服务
#
# 设计与用法:
#   导出 create_app() 工厂函数
#   直接运行本文件启动开发服务器: python -m server.main
# ============================================================

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api.routes import vehicle_router


def create_app() -> FastAPI:
    app = FastAPI(title="SuoXing-Tuan", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(vehicle_router)

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
