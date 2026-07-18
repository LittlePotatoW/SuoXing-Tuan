# ============================================================
# backend/server/api/routes/__init__.py
# 路由模块聚合
# ============================================================

from server.api.routes.vehicle import router as vehicle_router
from server.api.routes.reconstruction import router as reconstruction_router
from server.api.routes.detection import router as detection_router

__all__ = ['vehicle_router', 'reconstruction_router', 'detection_router']
