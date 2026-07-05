# ============================================================
# model-training/yolo-training/evaluate.py
# 评估脚本 — 计算 mAP / 各类召回率 / PR 曲线
#
# 用法:
#   python evaluate.py
#   python evaluate.py --model runs/train/tunnel-det/weights/best.pt
# ============================================================

import argparse
from pathlib import Path
from ultralytics import YOLO

# ---- 8 类隧道缺陷 (与 train.ipynb 保持一致) ----
CLASS_NAMES = [
    "crack", "water_leakage", "spalling",
    "fastener_missing", "fastener_loose", "fastener_broken",
    "bracket_loose", "contact_wire_intrusion",
]


def main():
    parser = argparse.ArgumentParser(description="YOLOv8 模型评估")
    parser.add_argument("--model", default="runs/train/tunnel-det/weights/best.pt",
                        help="模型权重路径")
    parser.add_argument("--data", default="datasets/tunnel_defects.yaml",
                        help="数据配置 yaml")
    parser.add_argument("--conf", type=float, default=0.25, help="置信度阈值")
    parser.add_argument("--iou", type=float, default=0.5, help="NMS IoU 阈值")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default="")
    args = parser.parse_args()

    # ---- 检查模型 ----
    model_path = Path(args.model)
    if not model_path.exists():
        print(f"ERROR: 模型文件不存在: {args.model}")
        print("请先运行 train.py 训练模型")
        return

    # ---- 加载模型 ----
    print(f"Loading model: {args.model}")
    model = YOLO(str(model_path))

    # ---- 评估 ----
    print(f"\nEvaluating on: {args.data}")
    print(f"Conf threshold: {args.conf}, IoU threshold: {args.iou}")
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

    # ---- 打印结果 ----
    print("\n" + "=" * 60)
    print("评估结果")
    print("=" * 60)
    print(f"mAP@0.5:       {metrics.box.map50:.4f}")
    print(f"mAP@0.5:0.95:  {metrics.box.map:.4f}")
    print(f"Precision:     {metrics.box.mp:.4f}")
    print(f"Recall:        {metrics.box.mr:.4f}")

    # 各类别结果
    if metrics.box.ap50_per_class is not None:
        print("\n各类别 AP@0.5:")
        ap50_list = metrics.box.ap50_per_class.tolist() if hasattr(metrics.box.ap50_per_class, "tolist") else metrics.box.ap50_per_class
        for i, ap in enumerate(ap50_list):
            name = CLASS_NAMES[i] if i < len(CLASS_NAMES) else f"class_{i}"
            status = "PASS" if ap >= 0.95 else "FAIL"
            print(f"  {name:30s} {ap:.4f}  [{status}]")

    print("\n各类别 Recall (检出率):")
    if hasattr(metrics.box, "recall_per_class") and metrics.box.recall_per_class is not None:
        rec_list = metrics.box.recall_per_class.tolist() if hasattr(metrics.box.recall_per_class, "tolist") else metrics.box.recall_per_class
        for i, rec in enumerate(rec_list):
            name = CLASS_NAMES[i] if i < len(CLASS_NAMES) else f"class_{i}"
            print(f"  {name:30s} {rec:.4f}")

    # ---- 比赛指标检查 ----
    print("\n" + "=" * 60)
    print("比赛达标检查")
    print("=" * 60)
    thresholds = {
        "crack": 0.95, "water_leakage": 0.95, "spalling": 0.95,
        "fastener_missing": 0.95, "fastener_loose": 0.95, "fastener_broken": 0.95,
        "bracket_loose": 0.97, "contact_wire_intrusion": 0.97,
    }

    # 注意: 这是 AP 不是 Recall, 比赛要求的是检出率(Recall)
    # 真正的 Recall 需要另算, 这里只是参考
    ap50_list = metrics.box.ap50_per_class
    if ap50_list is not None:
        all_pass = True
        for i, name in enumerate(CLASS_NAMES):
            if name in thresholds:
                ap = ap50_list[i].item() if hasattr(ap50_list[i], "item") else ap50_list[i]
                req = thresholds[name]
                if ap >= req:
                    print(f"  {name}: {ap:.4f} >= {req}  PASS")
                else:
                    print(f"  {name}: {ap:.4f} <  {req}  FAIL (差 {req-ap:.4f})")
                    all_pass = False

        if all_pass:
            print("\n  全部类别达标!")
        else:
            print("\n  部分类别未达标, 需要更多数据或调参")


if __name__ == "__main__":
    main()
