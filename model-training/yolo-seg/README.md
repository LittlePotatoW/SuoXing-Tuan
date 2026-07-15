# 隧道缺陷实例分割 — YOLOv8-seg

对标论文: Huang et al. (2025) *"Automated 3D defect inspection in shield tunnel linings through integration of image and point cloud data"* — AI in Civil Engineering, 4:12.

## 目录结构

```
tunnel-defect-ml/
├── train.py           CLI 训练入口
├── predict.py         推理 (检测 + 分割)
├── evaluate.py        评估 (mAP/F1/各类别AP)
├── dataset.py         数据格式转换
├── requirements.txt   依赖
├── README.md          本文档
├── configs/           配置文件
├── scripts/           辅助脚本
├── datasets/          数据集 (放这里)
│   ├── images/{train,val,test}/
│   ├── labels/{train,val,test}/
│   └── tunnel_defects.yaml
└── notebooks/         Jupyter 笔记
```

## 快速启动

```bash
# 1. 装依赖
pip install -r requirements.txt

# 2. 准备数据 → 放到 datasets/ 下

# 3. 一键训练
python train.py --preset fast        # 快速验证管线 (nano, 50轮)
python train.py --preset paper       # 正式训练 (small, 200轮)
python train.py --preset accurate    # 高精度 (medium, 300轮)

# 4. 评估
python evaluate.py --model runs/segment/tunnel-seg/weights/best.pt --seg

# 5. 推理
python predict.py --image test.jpg --model runs/segment/tunnel-seg/weights/best.pt --seg
```

## 数据准备

### 格式一: mask png → YOLOv8-seg polygon

```python
from dataset import convert_mask_dataset, generate_data_yaml

convert_mask_dataset(
    image_dir="raw/images/",
    mask_dir="raw/masks/",
    output_dir="datasets/",
    class_map={255: 0, 128: 1, 64: 2},  # 像素值 → 类别
    split="train",
    mode="seg",
)

generate_data_yaml("datasets/tunnel_defects.yaml",
                   ["crack", "leakage", "spalling"])
```

### 格式二: COCO JSON → YOLOv8-seg polygon

```python
from dataset import convert_coco_dataset

convert_coco_dataset(
    coco_json="annotations.json",
    image_dir="raw/images/",
    output_dir="datasets/",
    split="train",
)
```

### 格式三: VOC XML → YOLO bbox

```python
from dataset import convert_voc_dataset

convert_voc_dataset(
    xml_dir="Annotations/",
    image_dir="JPEGImages/",
    output_dir="datasets/",
    class_map={"crack": 0, "leakage": 1, "spalling": 2},
    split="train",
)
```

### 自动划分

```python
from dataset import split_dataset

split_dataset(
    image_dir="raw/all_images/",
    output_dir="datasets/",
    train_ratio=0.7, val_ratio=0.2, test_ratio=0.1,
)
```

## 预设说明

| 预设 | 模型 | 参数量 | Batch | Epochs | ImgSz | 场景 |
|:---|:---|:---:|:---:|:---:|:---:|:---|
| `fast` | yolov8n-seg | 3.4M | 32 | 50 | 640 | 跑通管线 |
| `paper` | yolov8s-seg | 11.8M | 16 | 200 | 640 | 对标论文 |
| `accurate` | yolov8m-seg | 27.3M | 8 | 300 | 1280 | 追求精度 |

## 论文指标参考

| 类别 | AP@0.5 | F1 | 难点 |
|:---|:---:|:---:|:---|
| crack (裂缝) | 0.64 | 0.60 | 尺寸小、边界模糊 |
| leakage (渗漏) | 0.97 | 0.92 | 纹理特征明显 |
| spalling (剥落) | 0.96 | 0.89 | 区域特征突出 |
| **平均** | **0.87** | **0.80** | |

## 提速参考

| 优化手段 | 速度提升 | 精度损失 |
|:---|:---:|:---:|
| imgsz 640→480 | ~1.5× | <2% mAP |
| FP16 量化 | ~1.5~2× | <0.5% mAP |
| ONNX Runtime | ~1.5× | 0 |
| TensorRT INT8 | ~2~4× | 1~3% mAP |
| yolov8n-seg (换小模型) | ~3× | ~5% mAP |
