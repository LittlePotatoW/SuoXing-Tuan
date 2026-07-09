# ============================================================
# backend/realtime/preprocessor.py
# 数据预处理模块 — 输入输出均为 final_data (SensorFrame)
#
# TODO: 在此实现数据清洗/增强/去噪等预处理逻辑
# ============================================================

import logging

logger = logging.getLogger("realtime.preprocessor")


def preprocess(frame: dict) -> dict:
    """
    对融合后的 final_data 做预处理。

    当前为占位实现 — 直接透传。
    """
    return frame
