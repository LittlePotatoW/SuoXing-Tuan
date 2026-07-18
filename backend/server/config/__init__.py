# ============================================================
# backend/server/config/__init__.py
# 配置加载器：读取 config.yaml，暴露配置对象供各模块使用
#
# 设计与用法:
#   导出 load_config() 函数，返回配置字典
#   导出 get_config() 函数，获取已加载的配置（懒加载）
# ============================================================

import os
from pathlib import Path

import yaml

_config: dict | None = None


def _find_config() -> Path:
    """向上查找 config.yaml"""
    current = Path.cwd()
    for _ in range(10):
        candidate = current / "config.yaml"
        if candidate.exists():
            return candidate
        if current.parent == current:
            break
        current = current.parent
    raise FileNotFoundError("找不到 config.yaml")


def load_config(path: str | Path | None = None) -> dict:
    """读取并返回 YAML 配置"""
    if path is None:
        path = _find_config()
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_config() -> dict:
    """懒加载配置（首次调用时读取，后续复用缓存）"""
    global _config
    if _config is None:
        _config = load_config()
    return _config
