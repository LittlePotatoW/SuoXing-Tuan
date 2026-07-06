# ============================================================
# model-training/yolo-training/evaluate.py
# 评估脚本 — 计算 mAP / 各类别 AP / Precision / Recall
#
# 用法:
#   python evaluate.py
#   python evaluate.py --model runs/detect/tunnel-det/weights/best.pt
# ============================================================

import argparse
from pathlib import Path
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(description="YOLOv8 模型评估")
    parser.add_argument("--model", default="runs/detect/tunnel-det/weights/best.pt",
                        help="模型权重路径")
    parser.add_argument("--data", default="datasets/tunnel_defects.yaml",
                        help="数据配置 yaml")
    parser.add_argument("--conf", type=float, default=0.25, help="置信度阈值")
    parser.add_argument("--iou", type=float, default=0.5, help="NMS IoU 阈值")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default="")
    args = parser.parse_args()

    model_path = Path(args.model)
    if not model_path.exists():
        print(f"ERROR: 模型文件不存在: {args.model}")
        return

    print(f"Loading model: {args.model}")
    model = YOLO(str(model_path))

    # 从模型读取真实类别名
    class_names = list(model.names.values()) if hasattr(model, "names") else []

    print(f"\nEvaluating on: {args.data}")
    print(f"Classes: {len(class_names)}")
    print(f"Conf: {args.conf}, IoU: {args.iou}")
    print()

    metrics = model.val(
        data=args.data,
        conf=args.conf,
        iou=args.iou,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        split="val",
    )

    print("\n" + "=" * 60)
    print("评估结果")
    print("=" * 60)
    print(f"mAP@0.5:       {metrics.box.map50:.4f}")
    print(f"mAP@0.5:0.95:  {metrics.box.map:.4f}")
    print(f"Precision:     {metrics.box.mp:.4f}")
    print(f"Recall:        {metrics.box.mr:.4f}")

    # 各类别 AP@0.5（使用新版 API class_result）
    print("\n各类别 AP@0.5:")
    for i in range(metrics.box.nc):
        p, r, ap50, ap = metrics.box.class_result(i)
        name = class_names[i] if i < len(class_names) else f"class_{i}"
        print(f"  {name:30s} AP@0.5={ap50:.4f}  P={p:.4f}  R={r:.4f}")


if __name__ == "__main__":
    main()
