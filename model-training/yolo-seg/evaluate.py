# ============================================================
# tunnel-defect-ml/evaluate.py
# 评估脚本 — 计算 mAP / 各类别 AP / Precision / Recall
#
# 用法:
#   python evaluate.py
#   python evaluate.py --model runs/segment/tunnel-seg/weights/best.pt
#   python evaluate.py --model best.pt --seg --batch 32
#
# 论文参考指标 (Huang et al. 2025):
#   mAP@0.5 = 0.87, F1 = 0.80
#   crack AP=0.64, leakage AP=0.97, spalling AP=0.96
# ============================================================

import argparse
from pathlib import Path
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(
        description="YOLO 隧道缺陷模型评估 (检测/分割)"
    )
    parser.add_argument("--model",
                        default="runs/segment/tunnel-seg/weights/best.pt")
    parser.add_argument("--data",
                        default="datasets/tunnel_defects.yaml")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.5)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default="")
    parser.add_argument("--seg", action="store_true",
                        help="评估分割 mask 指标")
    args = parser.parse_args()

    model_path = Path(args.model)
    if not model_path.exists():
        print(f"ERROR: 模型不存在: {args.model}")
        return

    print(f"Model: {args.model}")
    print(f"Data:  {args.data}")
    print(f"Mode:  {'segmentation' if args.seg else 'detection'}")
    print(f"Conf:  {args.conf}  IoU: {args.iou}  Batch: {args.batch}")

    model = YOLO(str(model_path))
    class_names = list(model.names.values()) if hasattr(model, "names") else []

    # 评估
    metrics = model.val(
        data=args.data,
        conf=args.conf,
        iou=args.iou,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        split="val",
    )

    # 打印结果
    print(f"\n{'='*60}")
    print("评估结果")
    print(f"论文参考: mAP@0.5=0.87, F1=0.80")
    print(f"          裂缝 AP=0.64, 渗漏 AP=0.97, 剥落 AP=0.96")
    print(f"{'='*60}")

    # Box 指标
    print(f"\n--- BBox 指标 ---")
    print(f"mAP@0.5:       {metrics.box.map50:.4f}")
    print(f"mAP@0.5:0.95:  {metrics.box.map:.4f}")
    print(f"Precision:     {metrics.box.mp:.4f}")
    print(f"Recall:        {metrics.box.mr:.4f}")

    # Seg 指标
    if args.seg and hasattr(metrics, "seg"):
        print(f"\n--- Mask 指标 ---")
        print(f"mAP@0.5:       {metrics.seg.map50:.4f}")
        print(f"mAP@0.5:0.95:  {metrics.seg.map:.4f}")

    # 各类别
    print(f"\n{'类别':<15} {'AP@0.5':>8}  {'P':>8}  {'R':>8}")
    print("-" * 43)
    for i in range(metrics.box.nc):
        p, r, ap50, ap = metrics.box.class_result(i)
        name = class_names[i] if i < len(class_names) else f"class_{i}"
        print(f"{name:<15} {ap50:>8.4f}  {p:>8.4f}  {r:>8.4f}")

    print(f"\nDone.")


if __name__ == "__main__":
    main()
