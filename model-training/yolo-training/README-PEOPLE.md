# YOLO 隧道缺陷检测训练

基于 YOLOv8 训练隧道缺陷检测模型。图片进去，框框出来。

**这是整个项目的最小化 Demo**
直接使用开源的YOLOv8模型，使用纯图像的训练数据
先跑通，在进行复杂的

## 启动指令

```bash
# 在项目根目录
.venv\Scripts\activate
cd model-training\yolo-training
jupyter lab
```

打开 `train.ipynb`，逐个 Cell 运行。

## 文件说明

| 文件 | 干啥 |
|------|------|
| `train.ipynb` | 训练入口，调参、看曲线全在这里 |
| `dataset.py` | 把各种格式的标注转成 YOLO 格式 |
| `evaluate.py` | 评估训练好的模型 |
| `predict.py` | 拿模型推理一张图 |
| `datasets/` | 放数据集 |
