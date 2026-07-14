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
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        print(f"[WARN] {path} not found, using defaults")
        return {}
    except yaml.YAMLError as e:
        print(f"[WARN] {path} parse error: {e}")
        return {}


CONFIG = _load()
