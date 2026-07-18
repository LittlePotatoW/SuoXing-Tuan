# ============================================================
# backend/server/detection/detector.py
# YOLO 检测器：模型加载、推理
#
# 设计与用法:
#   导出 Detector 类（单例）
#   导出 detect() 方法（输入 base64 图像, 输出检测框列表）
# ============================================================
#   MODEL_PATH       默认模型路径 (config.detection.model_path)
#   CONF_THRESHOLD   默认置信度阈值 (config.detection.conf_threshold)
#   DEVICE           推理设备 (config.detection.device)
# ============================================================

import base64
import logging
import threading
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

_instance = None
_lock = threading.Lock()


class Detector:
    """YOLO 检测器（单例）"""

    def __init__(self, config: dict):
        det_cfg = config.get('detection', {})
        self._model_path = det_cfg.get('model_path', 'models/yolo.pt')
        self._conf_threshold = det_cfg.get('conf_threshold', 0.5)
        self._device = det_cfg.get('device', 'cpu')

        self._model = None
        self._model_available = False
        self._latest_detections: list[dict] = []
        self._rwlock = threading.Lock()

        self._try_load()

    def _try_load(self) -> None:
        """尝试加载模型"""
        model_file = Path(self._model_path)
        if model_file.exists():
            try:
                from ultralytics import YOLO
                self._model = YOLO(str(model_file))
                self._model_available = True
                logger.info("YOLO 模型已加载: %s (device=%s)",
                            self._model_path, self._device)
            except ImportError:
                logger.warning(
                    "ultralytics 未安装, 检测功能不可用。"
                    "安装: pip install ultralytics")
            except Exception:
                logger.exception("模型加载失败: %s", self._model_path)
        else:
            logger.info("模型文件不存在: %s, 检测功能待模型就绪后可用",
                        model_file.resolve())

    @classmethod
    def create(cls, config: dict | None = None) -> 'Detector':
        global _instance
        with _lock:
            if _instance is None:
                if config is None:
                    from server.config import get_config
                    config = get_config()
                _instance = cls(config)
            return _instance

    @classmethod
    def stop(cls) -> None:
        global _instance
        _instance = None

    @property
    def available(self) -> bool:
        return self._model_available

    def detect(self, image_b64: str) -> list[dict]:
        """对 base64 图像执行检测

        Returns:
            [{id, class_name, confidence, bbox_2d: [x1,y1,x2,y2]}, ...]
        """
        if not self._model_available:
            logger.warning("检测模型不可用")
            return []

        try:
            image = _decode_image(image_b64)
            if image is None:
                return []
        except Exception:
            logger.exception("图像解码失败")
            return []

        results = self._model(
            image,
            conf=self._conf_threshold,
            device=self._device,
            verbose=False,
        )

        detections = []
        for i, r in enumerate(results[0].boxes.data.tolist() if results else []):
            x1, y1, x2, y2, conf, cls = r
            if conf >= self._conf_threshold:
                detections.append({
                    'id': i,
                    'class_name': self._model.names.get(int(cls), str(cls)),
                    'confidence': round(float(conf), 4),
                    'bbox_2d': [float(x1), float(y1), float(x2), float(y2)],
                })

        with self._rwlock:
            self._latest_detections = detections

        return detections

    def latest(self) -> list[dict]:
        with self._rwlock:
            return list(self._latest_detections)


def _decode_image(b64: str) -> np.ndarray | None:
    """Base64 JPEG → BGR numpy 数组"""
    try:
        import cv2
        data = base64.b64decode(b64)
        arr = np.frombuffer(data, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None
