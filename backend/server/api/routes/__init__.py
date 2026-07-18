# ============================================================
# backend/server/api/routes/__init__.py
# 路由模块聚合
# ============================================================

from server.api.routes.vehicle import router as vehicle_router

__all__ = ['vehicle_router']
