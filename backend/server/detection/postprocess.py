# ============================================================
# backend/server/detection/postprocess.py
# 检测后处理：NMS、点云映射（2D检测框 → 3D中心点）
#
# 设计与用法:
#   导出 apply_nms()  — NMS 去重
#   导出 map_to_3d()  — 2D检测框 → 点云计算 3D 中心
# ============================================================

import numpy as np


def apply_nms(detections: list[dict],
              iou_threshold: float = 0.5) -> list[dict]:
    """按类别分别执行 NMS 去重"""
    if not detections:
        return []

    # 按 class 分组
    by_class: dict[str, list] = {}
    for d in detections:
        by_class.setdefault(d['class_name'], []).append(d)

    kept = []
    for cls, items in by_class.items():
        boxes = np.array([it['bbox_2d'] for it in items])
        scores = np.array([it['confidence'] for it in items])
        indices = _nms(boxes, scores, iou_threshold)
        kept.extend([items[i] for i in indices])

    return kept


def _nms(boxes: np.ndarray, scores: np.ndarray,
         iou_threshold: float) -> list[int]:
    """简洁 NMS 实现"""
    if len(boxes) == 0:
        return []

    x1 = boxes[:, 0]; y1 = boxes[:, 1]
    x2 = boxes[:, 2]; y2 = boxes[:, 3]
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]

    keep = []
    while len(order) > 0:
        i = order[0]
        keep.append(int(i))

        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        overlap = (w * h) / areas[order[1:]]
        order = order[1:][overlap <= iou_threshold]

    return keep


def map_to_3d(detections: list[dict],
              point_cloud: np.ndarray,
              depth_img: np.ndarray) -> list[dict]:
    """将 2D 检测框映射到点云计算 3D 中心

    Args:
        detections: 检测结果 [{id, bbox_2d: [x1,y1,x2,y2]}, ...]
        point_cloud: (H, W, 3) 有序点云（与深度图同尺寸）
        depth_img:   (H, W) 深度图 (米), 用于过滤无效点

    Returns:
        带 center_3d 的检测结果
    """
    h, w = depth_img.shape[:2]
    for d in detections:
        x1, y1, x2, y2 = [int(v) for v in d['bbox_2d']]
        x1 = max(0, min(x1, w - 1))
        x2 = max(0, min(x2, w - 1))
        y1 = max(0, min(y1, h - 1))
        y2 = max(0, min(y2, h - 1))

        crop_pc = point_cloud[y1:y2 + 1, x1:x2 + 1]
        crop_d = depth_img[y1:y2 + 1, x1:x2 + 1]
        valid = (crop_d > 0) & np.isfinite(crop_pc[:, :, 2])
        if np.any(valid):
            center = np.mean(crop_pc[valid], axis=0)
            d['center_3d'] = center.tolist()
        else:
            d['center_3d'] = [0.0, 0.0, 0.0]

    return detections
