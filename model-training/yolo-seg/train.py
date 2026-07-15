# ============================================================
# tunnel-defect-ml/train.py
# CLI 训练入口 — YOLOv8-seg 隧道缺陷实例分割
#
# 对标论文:
#   Huang et al. (2025) "Automated 3D defect inspection in
#   shield tunnel linings..."  AI in Civil Engineering, 4:12
#
# 用法:
#   python train.py                           # 默认参数
#   python train.py --preset fast             # 快速验证管线
#   python train.py --preset paper            # 对标论文参数
#   python train.py --model yolov8m-seg.pt --epochs 300
#   python train.py --resume                  # 从中断处恢复
# ============================================================

import argparse
from pathlib import Path
from ultralytics import YOLO
from dataset import generate_data_yaml


# ============================================================
# 配置
# ============================================================

CLASS_NAMES = ["crack", "leakage", "spalling"]

PRESETS = {
    "fast": {
        "model": "yolov8n-seg.pt",
        "batch": 32,
        "epochs": 50,
        "imgsz": 640,
        "desc": "快速验证 (nano 模型, 50 轮)",
    },
    "paper": {
        "model": "yolov8s-seg.pt",
        "batch": 16,
        "epochs": 200,
        "imgsz": 640,
        "desc": "对标论文 (small 模型, 200 轮)",
    },
    "accurate": {
        "model": "yolov8m-seg.pt",
        "batch": 8,
        "epochs": 300,
        "imgsz": 1280,
        "desc": "高精度 (medium 模型, 300 轮)",
    },
}


# ============================================================
# 主函数
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="YOLOv8-seg 隧道缺陷实例分割训练"
    )

    # 预设
    parser.add_argument("--preset", choices=PRESETS.keys(), default="paper",
                        help=f"预设: {list(PRESETS.keys())}")

    # 模型 & 数据
    parser.add_argument("--model", default="",
                        help="预训练权重 (覆盖 preset)")
    parser.add_argument("--data", default="datasets/tunnel_defects.yaml",
                        help="数据配置文件")

    # 类别 (同时用于自动生成 yaml)
    parser.add_argument("--classes", nargs="+", default=CLASS_NAMES,
                        help="类别名列表")

    # 训练参数 (0 = 用 preset 默认值)
    parser.add_argument("--epochs", type=int, default=0)
    parser.add_argument("--batch", type=int, default=0)
    parser.add_argument("--imgsz", type=int, default=0)

    # 学习率
    parser.add_argument("--lr0", type=float, default=0.01)
    parser.add_argument("--lrf", type=float, default=0.01)
    parser.add_argument("--warmup", type=float, default=3.0,
                        help="预热轮数")

    # 数据增强
    parser.add_argument("--mosaic", type=float, default=1.0)
    parser.add_argument("--mixup", type=float, default=0.1)
    parser.add_argument("--degrees", type=float, default=15.0)
    parser.add_argument("--scale", type=float, default=0.5)
    parser.add_argument("--erasing", type=float, default=0.4,
                        help="随机擦除概率 (模拟遮挡)")

    # 早停 & 保存
    parser.add_argument("--patience", type=int, default=50)
    parser.add_argument("--save-period", type=int, default=5,
                        help="每 N 轮存一次 checkpoint")

    # 系统
    parser.add_argument("--device", default="",
                        help="GPU 编号 (空=自动)")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--no-amp", action="store_true",
                        help="禁用混合精度 (CPU 训练时)")

    # 输出
    parser.add_argument("--name", default="tunnel-seg",
                        help="实验名称")

    # 恢复
    parser.add_argument("--resume", action="store_true",
                        help="从 last.pt 恢复训练")

    args = parser.parse_args()

    # ---- 合并 preset ----
    preset = PRESETS[args.preset]
    model_path = args.model or preset["model"]
    epochs = args.epochs or preset["epochs"]
    batch = args.batch or preset["batch"]
    imgsz = args.imgsz or preset["imgsz"]

    # ---- 自动生成数据配置 ----
    data_yaml = Path(args.data)
    if not data_yaml.exists():
        print(f"[INFO] {args.data} 不存在, 自动生成...")
        generate_data_yaml(
            output_path=str(data_yaml),
            class_names=args.classes,
        )
    else:
        print(f"[OK] 数据配置: {args.data}  ({len(args.classes)} 类)")

    # ---- 打印训练信息 ----
    print(f"""
{'='*60}
训练配置
{'='*60}
  预设:     {args.preset} — {preset['desc']}
  模型:     {model_path}
  数据:     {args.data}
  类别:     {args.classes}
  轮数:     {epochs}
  批次:     {batch}
  尺寸:     {imgsz}
  学习率:   lr0={args.lr0}, lrf={args.lrf}
  早停:     {args.patience} 轮不涨即停
  设备:     {args.device or 'auto'}
  AMP:      {'OFF' if args.no_amp else 'ON'}
  Resuming: {'YES' if args.resume else 'NO'}
{'='*60}
""")

    # ---- 加载模型 ----
    if args.resume:
        resume_path = f"runs/segment/{args.name}/weights/last.pt"
        if Path(resume_path).exists():
            print(f"[RESUME] 从 {resume_path} 恢复")
            model = YOLO(resume_path)
        else:
            print(f"WARNING: 未找到 {resume_path}, 全新训练")
            model = YOLO(model_path)
    else:
        model = YOLO(model_path)

    # ---- 训练 ----
    results = model.train(
        data=str(data_yaml),
        epochs=epochs,
        batch=batch,
        imgsz=imgsz,

        # 学习率
        lr0=args.lr0,
        lrf=args.lrf,
        momentum=0.937,
        weight_decay=0.0005,
        warmup_epochs=args.warmup,

        # 数据增强 (对标论文)
        mosaic=args.mosaic,
        mixup=args.mixup,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        degrees=args.degrees,
        translate=0.1,
        scale=args.scale,
        fliplr=0.5,
        flipud=0.0,
        erasing=args.erasing,

        # 早停 & 保存
        patience=args.patience,
        save_period=args.save_period,

        # 系统
        device=args.device,
        workers=args.workers,
        amp=not args.no_amp,
        seed=0,

        # 输出
        project="runs",
        name=args.name,
        exist_ok=True,
        plots=True,
    )

    # ---- 总结 ----
    best = f"runs/segment/{args.name}/weights/best.pt"
    last = f"runs/segment/{args.name}/weights/last.pt"

    print(f"""
{'='*60}
训练完成
{'='*60}
  最佳: {best}
  最后: {last}

  评估: python evaluate.py --model {best}
  推理: python predict.py --image test.jpg --model {best}
  导出: python -c "from ultralytics import YOLO; \\
         YOLO('{best}').export(format='onnx', half=True)"
{'='*60}
""")


if __name__ == "__main__":
    main()
