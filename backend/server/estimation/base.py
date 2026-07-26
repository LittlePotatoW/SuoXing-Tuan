# ============================================================
# backend/server/estimation/base.py
# 抽象基类 + Position 命名元组 —— 纯接口，无任何实现
#
# 设计与用法:
#   导出 Position         命名元组 (timestamp, x, y, heading)
#   导出 BaseEstimator    四个模式类的抽象基类
#     get_position_at(ts)  引擎获取指定时刻位置
#     get_position()       获取当前实时位置
#     get_config()         获取当前配置和状态
#     shutdown()           停止后台资源（默认 no-op）
# ============================================================

from abc import ABC, abstractmethod
from collections import namedtuple

Position = namedtuple('Position', ['timestamp', 'x', 'y', 'heading'])


class BaseEstimator(ABC):
    """位置估计器抽象基类 —— 四个模式类的统一接口"""

    @abstractmethod
    def get_position_at(self, timestamp: float) -> Position:
        """引擎调用：获取指定时间戳的位置"""
        ...

    @abstractmethod
    def get_position(self) -> Position:
        """获取当前实时位置"""
        ...

    @abstractmethod
    def get_config(self) -> dict:
        """获取当前配置和状态"""
        ...

    def shutdown(self) -> None:
        """生命周期：停止后台资源（默认 no-op）"""
        pass
