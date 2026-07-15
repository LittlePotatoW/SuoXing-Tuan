# ============================================================
# tunnel-defect-ml/predict.py
# 推理脚本 — 支持检测 (bbox) 和实例分割 (mask)
#
# 用法:
#   python predict.py --image test.jpg
#   python predict.py --folder test_dir/ --conf 0.3 --seg
#   python predict.py --image test.jpg --json detections.json
#
# 输出:
#   runs/predict/  标注结果图片
#   可选: JSON 格式检测结果 (含 bbox + polygon)
# ============================================================

import argparse
import json
import time
from pathlib import Path
from ultralytics import YOLO


def predict_image(model: YOLO, image_path: str, conf: float = 0.3,
                  iou: float = 0.5, imgsz: int = 640, save: bool = False,
                  mode: str = "seg") -> list:
    """
    单张图片推理

    参数:
      model:      加载好的 YOLO 模型
      image_path: 图片路径
      conf:       置信度阈值 (论文: 0.25~0.52)
      iou:        NMS IoU 阈值
      imgsz:      输入尺寸
      save:       是否保存标注图
      mode:       "seg" 输出 polygon, "det" 仅 bbox

    返回:
      [{class, class_id, confidence, bbox, polygon?}, ...]
    """
    class_names = list(model.names.values()) if hasattr(model, "names") else []

    results = model.predict(source=image_path, conf=conf, iou=iou,
                            imgsz=imgsz, save=save, verbose=False)
    detections = []
    for result in results:
        boxes = result.boxes
        masks = result.masks if mode == "seg" else None
        if boxes is None:
            continue

        for i in range(len(boxes)):
            cls_id = int(boxes.cls[i].item())
            det = {
                "class": class_names[cls_id] if cls_id < len(class_names)
                         else f"class_{cls_id}",
                "class_id": cls_id,
                "confidence": round(float(boxes.conf[i].item()), 4),
                "bbox": [round(v, 1) for v in boxes.xyxy[i].tolist()],
            }
            # 分割 mask → polygon
            if masks is not None and i < len(masks):
                mask_xy = masks.xy[i] if hasattr(masks, "xy") else []
                if len(mask_xy) > 0:
                    det["polygon"] = [[round(float(p[0]), 1),
                                       round(float(p[1]), 1)]
                                      for p in mask_xy]
            detections.append(det)
    return detections


def main():
    parser = argparse.ArgumentParser(
        description="YOLO 隧道缺陷推理 (检测/分割)"
    )
    parser.add_argument("--model", default="runs/segment/tunnel-seg/weights/best.pt",
                        help="模型权重路径")
    parser.add_argument("--image", default="")
    parser.add_argument("--folder", default="")
    parser.add_argument("--conf", type=float, default=0.3,
                        help="置信度阈值")
    parser.add_argument("--iou", type=float, default=0.5,
                        help="NMS IoU 阈值")
    parser.add_argument("--imgsz", type=int, default=640,
                        help="输入尺寸")
    parser.add_argument("--seg", action="store_true",
                        help="分割模式 (输出 mask polygon)")
    parser.add_argument("--no-save", action="store_true",
                        help="不保存标注图片")
    parser.add_argument("--json", default="",
                        help="JSON 输出路径")
    args = parser.parse_args()

    # 校验输入
    source = args.image or args.folder
    if not source:
        print("ERROR: 请指定 --image 或 --folder")
        return
    if not Path(source).exists():
        print(f"ERROR: 路径不存在: {source}")
        return
    model_path = Path(args.model)
    if not model_path.exists():
        print(f"ERROR: 模型不存在: {args.model}")
        return

    mode = "seg" if args.seg else "det"
    print(f"Model: {args.model}")
    print(f"Source: {source}")
    print(f"Mode: {mode}  Conf: {args.conf}  IoU: {args.iou}  ImgSz: {args.imgsz}")

    model = YOLO(str(model_path))
    class_names = list(model.names.values()) if hasattr(model, "names") else []

    # 推理
    t0 = time.time()
    results = model.predict(
        source=source,
        conf=args.conf,
        iou=args.iou,
        imgsz=args.imgsz,
        save=not args.no_save,
    )
    elapsed = time.time() - t0

    # 收集结果
    all_detections = {}
    total = 0
    for r in results:
        img_path = getattr(r, "path", "unknown")
        dets = []
        if r.boxes:
            masks = r.masks if args.seg else None
            for i in range(len(r.boxes)):
                cls_id = int(r.boxes.cls[i].item())
                name = (class_names[cls_id] if cls_id < len(class_names)
                        else f"class_{cls_id}")
                det = {
                    "class": name,
                    "class_id": cls_id,
                    "confidence": round(float(r.boxes.conf[i].item()), 4),
                    "bbox": [round(v, 1) for v in r.boxes.xyxy[i].tolist()],
                }
                if args.seg and masks is not None and i < len(masks):
                    mask_xy = masks.xy[i] if hasattr(masks, "xy") else []
                    if len(mask_xy) > 0:
                        det["polygon"] = [[round(float(p[0]), 1),
                                           round(float(p[1]), 1)]
                                          for p in mask_xy]
                dets.append(det)
            total += len(dets)
        all_detections[str(img_path)] = dets

    # 输出
    if args.image:
        print(f"\n检测到 {total} 个缺陷 ({elapsed*1000:.0f} ms):")
        for d in all_detections[str(source)]:
            poly_info = f"  {len(d['polygon'])}pts" if "polygon" in d else ""
            print(f"  [{d['confidence']:.2f}] {d['class']:15s} @ {d['bbox']} {poly_info}")
    else:
        n_imgs = len(results)
        print(f"\n处理 {n_imgs} 张图片, {total} 个缺陷, "
              f"耗时 {elapsed:.1f}s ({elapsed/n_imgs*1000:.0f} ms/张)")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(all_detections, f, ensure_ascii=False, indent=2)
        print(f"[OK] JSON → {args.json}")

    print("Done.")


if __name__ == "__main__":
    main()
