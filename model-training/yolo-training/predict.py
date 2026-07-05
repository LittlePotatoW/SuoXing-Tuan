# ============================================================
# model-training/yolo-training/predict.py
# 推理脚本 — 给定图片，输出检测结果
#
# 用法:
#   python predict.py --image test.jpg
#   python predict.py --folder test_images/   # 批量推理
#   python predict.py --image test.jpg --conf 0.5  # 调高阈值减少误检
#
# 输出:
#   runs/predict/  下保存标注后的图片
# ============================================================

import argparse
import json
from pathlib import Path
from ultralytics import YOLO

# ---- 8 类隧道缺陷 (与 train.ipynb 保持一致) ----
CLASS_NAMES = [
    "crack", "water_leakage", "spalling",
    "fastener_missing", "fastener_loose", "fastener_broken",
    "bracket_loose", "contact_wire_intrusion",
]


def predict_image(model: YOLO, image_path: str, conf: float, iou: float, imgsz: int,
                  save: bool = True, save_json: bool = True) -> list:
    """
    对单张图片做推理, 返回检测结果列表

    返回格式:
      [{"class": "裂缝", "class_id": 0, "confidence": 0.95,
        "bbox": [x1, y1, x2, y2]}, ...]
    """
    results = model.predict(
        source=image_path,
        conf=conf,
        iou=iou,
        imgsz=imgsz,
        save=save,
        verbose=False,
    )

    detections = []
    for result in results:
        boxes = result.boxes
        if boxes is None:
            continue

        for i in range(len(boxes)):
            cls_id = int(boxes.cls[i].item())
            conf_val = float(boxes.conf[i].item())
            bbox = boxes.xyxy[i].tolist()  # [x1, y1, x2, y2] 像素坐标

            detections.append({
                "class": CLASS_NAMES[cls_id] if cls_id < len(CLASS_NAMES) else f"class_{cls_id}",
                "class_id": cls_id,
                "confidence": round(conf_val, 4),
                "bbox": [round(v, 1) for v in bbox],
            })

    return detections


def main():
    parser = argparse.ArgumentParser(description="YOLOv8 隧道缺陷检测推理")
    parser.add_argument("--model", default="runs/train/tunnel-det/weights/best.pt",
                        help="模型权重路径")
    parser.add_argument("--image", default="", help="单张图片路径")
    parser.add_argument("--folder", default="", help="图片文件夹路径")
    parser.add_argument("--conf", type=float, default=0.3, help="置信度阈值")
    parser.add_argument("--iou", type=float, default=0.5, help="NMS IoU 阈值")
    parser.add_argument("--imgsz", type=int, default=640, help="输入尺寸")
    parser.add_argument("--no-save", action="store_true", help="不保存标注图片")
    parser.add_argument("--json", default="", help="保存检测结果到 JSON 文件")
    args = parser.parse_args()

    # ---- 确定输入源 ----
    if args.image:
        source = args.image
    elif args.folder:
        source = args.folder
    else:
        print("ERROR: 请指定 --image 或 --folder")
        print("示例: python predict.py --image test.jpg")
        print("示例: python predict.py --folder test_images/")
        return

    if not Path(source).exists():
        print(f"ERROR: 路径不存在: {source}")
        return

    # ---- 加载模型 ----
    model_path = Path(args.model)
    if not model_path.exists():
        print(f"ERROR: 模型文件不存在: {args.model}")
        print("请先运行 train.py 训练模型")
        return

    print(f"Loading model: {args.model}")
    model = YOLO(str(model_path))

    # ---- 推理 ----
    print(f"\nRunning inference on: {source}")
    print(f"Conf={args.conf}, IoU={args.iou}, ImgSz={args.imgsz}")

    # 单张图片
    if args.image:
        detections = predict_image(
            model, args.image, args.conf, args.iou, args.imgsz,
            save=not args.no_save,
        )
        print(f"\nDetected {len(detections)} defects:")
        for d in detections:
            print(f"  [{d['confidence']:.2f}] {d['class']} @ {d['bbox']}")

        if args.json:
            with open(args.json, "w") as f:
                json.dump({args.image: detections}, f, ensure_ascii=False, indent=2)
            print(f"\nResults saved to: {args.json}")

    # 文件夹批量
    elif args.folder:
        results = model.predict(
            source=args.folder,
            conf=args.conf,
            iou=args.iou,
            imgsz=args.imgsz,
            save=not args.no_save,
        )
        total = 0
        for r in results:
            if r.boxes:
                total += len(r.boxes)
        print(f"\nProcessed {len(results)} images, found {total} defects total")
        print(f"Annotated images saved to: runs/predict/")

    print("\nDone!")


if __name__ == "__main__":
    main()
