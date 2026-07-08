# ============================================================
# backend/inference/engine.py
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

import gc
import time
import logging
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

logger = logging.getLogger("inference")


from inference.schemas import DetectionResult, InferenceResponse


class InferenceEngine:
    """
    YOLO 推理引擎。
    线程安全：load/infer 通过锁串行化，避免并发读写半初始化状态。
    """

    def __init__(self):
        self._lock = threading.RLock()
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
        from ultralytics import YOLO

        self._conf = conf
        self._iou = iou

        logger.info("Loading model: %s", model_path)

        with self._lock:
            # 卸载旧模型（先删再建，失败也会清理干净）
            if self._model is not None:
                del self._model
                self._model = None
                self._class_names = []
                self._model_path = ""
                self._model_name = ""
                if self._has_cuda():
                    import torch
                    torch.cuda.empty_cache()
                gc.collect()

            new_model = YOLO(model_path)
            self._model = new_model
            self._model_path = str(model_path)
            self._model_name = Path(model_path).stem

            # 读取类别名
            if hasattr(self._model, "names"):
                self._class_names = list(self._model.names.values())

            # 从模型读取实际输入尺寸做预热
            imgsz = 640
            if hasattr(self._model, "model") and hasattr(self._model.model, "args"):
                imgsz = self._model.model.args.get("imgsz", 640)
                if isinstance(imgsz, (list, tuple)):
                    imgsz = imgsz[0]

            dummy = np.zeros((imgsz, imgsz, 3), dtype=np.uint8)
            self._model(dummy, conf=conf, iou=iou, verbose=False)

        logger.info("Model ready: %s (%d classes)", self._model_name, len(self._class_names))

    def unload(self) -> None:
        with self._lock:
            if self._model is not None:
                del self._model
                self._model = None
                self._class_names = []
                self._model_path = ""
                self._model_name = ""
                if self._has_cuda():
                    import torch
                    torch.cuda.empty_cache()
                gc.collect()
                logger.info("Model unloaded")

    # ==================== 推理 ====================

    def infer(self, image: np.ndarray) -> InferenceResponse:
        h, w = image.shape[:2]
        t0 = time.perf_counter()

        with self._lock:
            if self._model is None:
                raise RuntimeError("No model loaded")
            results = self._model(image, conf=self._conf, iou=self._iou, verbose=False)

        detections: list[DetectionResult] = []
        for r in results:
            if r.boxes is None:
                continue
            for i in range(len(r.boxes)):
                cls_id = int(r.boxes.cls[i].item())
                conf_val = float(r.boxes.conf[i].item())
                xyxy = r.boxes.xyxy[i].tolist()

                # Clamp to image bounds
                x1, y1, x2, y2 = xyxy
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                if x2 <= x1 or y2 <= y1:
                    continue

                class_name = (
                    self._class_names[cls_id]
                    if cls_id < len(self._class_names)
                    else f"class_{cls_id}"
                )

                detections.append(DetectionResult(
                    class_name=class_name,
                    confidence=conf_val,
                    bbox=[round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)],
                ))

        elapsed = (time.perf_counter() - t0) * 1000
        return InferenceResponse(
            detections=detections,
            inference_time_ms=round(elapsed, 1),
            image_width=w,
            image_height=h,
        )

    @staticmethod
    def _has_cuda() -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except Exception:
            return False
