# ============================================================
# backend/inference.py
# YOLO 推理引擎 — 模型加载、推理、热切换
#
# 支持格式: .pt (PyTorch), .onnx (ONNX), .engine (TensorRT)
# 前端选文件上传 → 后端加载模型 → 拔插式切换
#
# 用法:
#   from inference import InferenceEngine
#   engine = InferenceEngine()
#   engine.load("yolov8n.pt")
#   results = engine.infer(image_array)
# ============================================================

import time
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger("inference")


@dataclass
class DetectionResult:
    """检测结果 — 前后端统一格式"""
    class_name: str
    confidence: float
    bbox: list[float]  # [x1, y1, x2, y2]


@dataclass
class InferenceResponse:
    """推理响应"""
    detections: list[DetectionResult] = field(default_factory=list)
    inference_time_ms: float = 0.0
    image_width: int = 0
    image_height: int = 0


class InferenceEngine:
    """
    YOLO 推理引擎。
    所有模型推理都走这个类，前端不参与推理。
    """

    def __init__(self):
        self._model = None
        self._model_path: str = ""
        self._model_name: str = ""
        self._class_names: list[str] = []
        self._conf: float = 0.3
        self._iou: float = 0.5

    @property
    def loaded(self) -> bool:
        return self._model is not None

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model_path(self) -> str:
        return self._model_path

    # ==================== 模型加载 ====================

    def load(self, model_path: str, conf: float = 0.3, iou: float = 0.5) -> None:
        """
        加载模型（拔插式：如果已加载则先卸载旧模型）。
        支持 .pt / .onnx / .engine
        """
        from ultralytics import YOLO

        if self._model is not None:
            self.unload()

        self._conf = conf
        self._iou = iou

        logger.info("Loading model: %s", model_path)
        self._model = YOLO(model_path)
        self._model_path = str(model_path)
        self._model_name = Path(model_path).stem

        # 读取类别名
        if hasattr(self._model, "names"):
            self._class_names = list(self._model.names.values())

        # 预热
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        self._model(dummy, conf=conf, iou=iou, verbose=False)

        logger.info("Model ready: %s (%d classes)", self._model_name, len(self._class_names))

    def unload(self) -> None:
        """卸载模型释放显存"""
        if self._model is not None:
            del self._model
            self._model = None
            self._class_names = []
            logger.info("Model unloaded")

    # ==================== 推理 ====================

    def infer(self, image: np.ndarray) -> InferenceResponse:
        """
        推理单张图像。
        输入: (H, W, 3) BGR uint8 numpy 数组
        输出: InferenceResponse
        """
        if self._model is None:
            raise RuntimeError("No model loaded")

        h, w = image.shape[:2]
        t0 = time.perf_counter()

        results = self._model(image, conf=self._conf, iou=self._iou, verbose=False)

        elapsed = (time.perf_counter() - t0) * 1000

        detections: list[DetectionResult] = []
        for r in results:
            if r.boxes is None:
                continue
            for i in range(len(r.boxes)):
                cls_id = int(r.boxes.cls[i].item())
                conf_val = float(r.boxes.conf[i].item())
                xyxy = r.boxes.xyxy[i].tolist()

                class_name = (
                    self._class_names[cls_id]
                    if cls_id < len(self._class_names)
                    else f"class_{cls_id}"
                )

                detections.append(DetectionResult(
                    class_name=class_name,
                    confidence=round(conf_val, 4),
                    bbox=[round(v, 2) for v in xyxy],
                ))

        logger.debug("%d detections in %.1fms", len(detections), elapsed)
        return InferenceResponse(
            detections=detections,
            inference_time_ms=round(elapsed, 1),
            image_width=w,
            image_height=h,
        )
