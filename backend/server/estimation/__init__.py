# ============================================================
# backend/server/estimation/__init__.py
# 位置估计器包 —— 对外只暴露 manager 和 Position
#
# 设计与用法:
#   导出 Position         命名元组 (timestamp, x, y, heading)
#   导出 EstimatorManager 管理器（唯一对外接口）
#   导出 get_manager()    获取模块级 manager 单例
#
#   四个模式类和 BaseEstimator 均为内部实现，外部不可见
# ============================================================

from server.estimation.base import Position
from server.estimation.manager import EstimatorManager

_manager = EstimatorManager()


def get_manager() -> EstimatorManager:
    """获取模块级 manager 单例 —— 外部唯一入口"""
    return _manager


__all__ = ['Position', 'EstimatorManager', 'get_manager']
