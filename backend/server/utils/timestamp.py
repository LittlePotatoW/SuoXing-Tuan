# ============================================================
# backend/server/utils/timestamp.py
# 时间戳工具：当前时间、格式转换
#
# 设计与用法:
#   导出 now() — 当前 Unix 时间戳 (秒, float)
#   导出 from_iso() — ISO 字符串 → float
# ============================================================

import time
from datetime import datetime, timezone


def now() -> float:
    """当前 Unix 时间戳（秒）"""
    return time.time()


def from_iso(iso_str: str) -> float:
    """ISO 8601 字符串 → Unix 时间戳"""
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()
