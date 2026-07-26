# ============================================================
# backend/server/api/routes/__init__.py
# 路由模块聚合
# ============================================================

from server.api.routes.vehicle import router as vehicle_router
from server.api.routes.reconstruction import router as reconstruction_router
from server.api.routes.detection import router as detection_router
from server.api.routes.session import router as session_router
from server.api.routes.report import router as report_router
from server.api.routes.network import router as network_router

__all__ = ['vehicle_router', 'reconstruction_router',
           'detection_router', 'session_router', 'report_router',
           'network_router']
