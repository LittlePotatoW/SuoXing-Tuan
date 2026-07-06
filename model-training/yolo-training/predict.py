# ============================================================
# model-training/yolo-training/predict.py
# 推理脚本 — 给定图片，输出检测结果
#
# 用法:
#   python predict.py --image test.jpg
#   python predict.py --folder test_images/   # 批量推理
#   python predict.py --image test.jpg --conf 0.5
#
# 输出:
#   runs/predict/  下保存标注后的图片
# ============================================================

import argparse
import json
from pathlib import Path
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(description="YOLOv8 隧道缺陷检测推理")
    parser.add_argument("--model", default="runs/detect/tunnel-det/weights/best.pt",
                        help="模型权重路径")
    parser.add_argument("--image", default="", help="单张图片路径")
    parser.add_argument("--folder", default="", help="图片文件夹路径")
    parser.add_argument("--conf", type=float, default=0.3, help="置信度阈值")
    parser.add_argument("--iou", type=float, default=0.5, help="NMS IoU 阈值")
    parser.add_argument("--imgsz", type=int, default=640, help="输入尺寸")
    parser.add_argument("--no-save", action="store_true", help="不保存标注图片")
    parser.add_argument("--json", default="", help="保存检测结果到 JSON")
    args = parser.parse_args()

    if not args.image and not args.folder:
        print("ERROR: 请指定 --image 或 --folder")
        return

    source = args.image or args.folder
    if not Path(source).exists():
        print(f"ERROR: 路径不存在: {source}")
        return

    model_path = Path(args.model)
    if not model_path.exists():
        print(f"ERROR: 模型文件不存在: {args.model}")
        return

    print(f"Loading model: {args.model}")
    model = YOLO(str(model_path))
    class_names = list(model.names.values()) if hasattr(model, "names") else []

    print(f"\nRunning inference on: {source}")
    print(f"Conf={args.conf}, IoU={args.iou}, ImgSz={args.imgsz}")

    results = model.predict(
        source=source,
        conf=args.conf,
        iou=args.iou,
        imgsz=args.imgsz,
        save=not args.no_save,
    )

    all_detections = {}
    total = 0
    for r, img_path in zip(results, [source] if args.image else [str(Path(p)) for p in sorted(Path(source).glob("*")) if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp")]):
        dets = []
        if r.boxes:
            for i in range(len(r.boxes)):
                cls_id = int(r.boxes.cls[i].item())
                name = class_names[cls_id] if cls_id < len(class_names) else f"class_{cls_id}"
                dets.append({
                    "class": name,
                    "class_id": cls_id,
                    "confidence": round(float(r.boxes.conf[i].item()), 4),
                    "bbox": [round(v, 1) for v in r.boxes.xyxy[i].tolist()],
                })
            total += len(dets)
        all_detections[str(img_path)] = dets

    if args.image:
        print(f"\nDetected {total} defects:")
        for d in all_detections[str(source)]:
            print(f"  [{d['confidence']:.2f}] {d['class']} @ {d['bbox']}")
    else:
        print(f"\nProcessed {len(results)} images, found {total} defects total")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(all_detections, f, ensure_ascii=False, indent=2)
        print(f"Results saved to: {args.json}")

    print("\nDone!")


if __name__ == "__main__":
    main()
