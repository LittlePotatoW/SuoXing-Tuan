# ============================================================
# backend/config_loader.py
# YAML 配置加载器 — 各模块统一从这里读取配置
#
# 用法:
#   from config_loader import CONFIG
#   host = CONFIG["server"]["host"]
# ============================================================

import os
import yaml


def _load() -> dict:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


CONFIG = _load()
