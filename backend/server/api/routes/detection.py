# ============================================================
# backend/server/api/routes/detection.py
# 检测服务接口：结果查询、单张图像静态检测
#
# 设计与用法:
#   导出 router (APIRouter)
#   GET  /result            查询最新检测结果
#   GET  /result/annotated   查询最新检测结果（含 YOLOv8 标注图）
#   POST /image              上传单张图像进行静态检测
# ============================================================

from fastapi import APIRouter

from server.api.schemas.detection import (
    ImageDetectRequest, DetectionResultResponse, DetectionAnnotatedResponse,
)
from server.detection import Detector

router = APIRouter(prefix="/api/detection", tags=["detection"])


@router.get("/result", response_model=DetectionResultResponse)
def get_result() -> DetectionResultResponse:
    detector = Detector.create()
    dets = detector.latest()
    return DetectionResultResponse(detections=dets, count=len(dets))


@router.post("/image", response_model=DetectionResultResponse)
def detect_image(body: ImageDetectRequest) -> DetectionResultResponse:
    detector = Detector.create()
    dets = detector.detect(body.image)
    return DetectionResultResponse(detections=dets, count=len(dets))


@router.get("/result/annotated", response_model=DetectionAnnotatedResponse)
def get_result_annotated() -> DetectionAnnotatedResponse:
    """查询最新检测结果，含 YOLOv8 风格标注图"""
    detector = Detector.create()
    data = detector.latest_annotated()
    return DetectionAnnotatedResponse(**data)
