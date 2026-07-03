# Model Training — 模型训练

## 这个文件夹是干啥的？

这里和"跑检测"无关——这是**训练模型**的地方。

打个比方：
- `backend/inference/` 是"开车"（用训练好的模型做推理）
- `model-training/` 是"造车"（从零训练出一个模型）

具体干了这些事：
- 管理标注好的数据集（图片 + 标注框）
- 用 PyTorch 训练检测/分割模型
- 评估模型效果好不好（准确率、速度）
- 把训练好的模型导出为 ONNX/TensorRT 格式
- 存到模型仓库，供后端 `inference/` 调用

## 目录说明

| 目录 | 干啥的 |
|------|--------|
| `data/` | 数据集管理——加载图片、数据增强、划分训练集/验证集 |
| `models/` | 模型定义——YOLO、DETR、分割模型等的 PyTorch 代码 |
| `training/` | 训练脚本——训练循环、保存 checkpoint、早停策略 |
| `evaluation/` | 模型评估——算 mAP（平均精度）、画 PR 曲线、测推理速度 |
| `export/` | 模型导出——PyTorch → ONNX → TensorRT，部署到后端用 |
| `configs/` | 实验配置——学习率、batch size、模型参数等 YAML 文件 |
| `registry/` | 模型仓库——存训练好的模型文件和版本信息 |

## 技术栈

| 技术 | 用途 | 官方文档 |
|------|------|----------|
| **Python 3.10+** | 编程语言 | https://docs.python.org/zh-cn/3/ |
| **PyTorch** | 深度学习框架 | https://pytorch.org/docs/ |
| **PyTorch Lightning**（可选） | 训练脚手架，少写重复代码 | https://lightning.ai/docs/pytorch/stable/ |
| **Torchvision** | 图像相关工具（数据增强、预训练模型） | https://pytorch.org/vision/stable/ |
| **Ultralytics** | YOLO 官方训练工具 | https://docs.ultralytics.com/zh/ |
| **ONNX** | 模型交换格式（PyTorch 导出后到处都能跑） | https://onnx.ai/onnx/ |
| **TensorRT** | NVIDIA GPU 推理加速 | https://developer.nvidia.com/tensorrt |
| **NumPy / OpenCV** | 图像处理 | 见 backend README |

## 怎么学？（推荐学习路线）

> 训练模型比推理难不少，建议先把后端推理跑通再来搞训练。

1. **Python + NumPy 基础** — 同后端的学习路线第 1-3 步

2. **PyTorch 入门** — 理解什么是张量（Tensor）、自动求导
   - 官方 60 分钟教程：https://pytorch.org/tutorials/beginner/deep_learning_60min_blitz.html
   - 中文版（B站搜"PyTorch 入门"）

3. **目标检测概念** — 理解 IoU、mAP、bbox、NMS 这些术语
   - 文章：https://zhuanlan.zhihu.com/p/34142321（目标检测入门必读）

4. **用 YOLO 训练你的第一个模型** — 最快出成果
   - Ultralytics 官方教程：https://docs.ultralytics.com/zh/modes/train/
   - 拿公开数据集跑一遍，感受一下训练流程

5. **模型导出** — ONNX 怎么导出、TensorRT 怎么加速
   - ONNX 导出教程：https://pytorch.org/docs/stable/onnx.html
   - TensorRT 入门：https://developer.nvidia.com/blog/speeding-up-deep-learning-inference-using-tensorrt/

## 怎么跑训练？

```bash
cd model-training
pip install -r requirements.txt
python training/train.py --config configs/yolo_v1.yaml
```

## 参考设计

训练和推理分离是工业场景的常见做法：
- 训练跑在 GPU 集群上，吃大显存，跑几个小时甚至几天
- 推理跑在生产环境，用小显存，模型必须快（几十毫秒出结果）
- 中间通过 ONNX/TensorRT 导出作为桥梁：训练用 PyTorch（灵活），推理用 ONNX Runtime/TensorRT（快）
