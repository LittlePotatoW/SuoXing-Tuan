# Backend — Python 后端

## 这个文件夹是干啥的？

这里是整个平台的"大脑"，负责：
- 连接工业相机、激光雷达等硬件设备，读取原始数据
- 对图像、点云做预处理（去噪、缩放、对齐）
- 跑 AI 模型做缺陷检测
- 做三维重建（3D Gaussian Splatting），把产品变成 3D 模型
- 提供 API 给前端调用（REST + WebSocket 实时推送）

## 目录说明

| 目录 | 干啥的 |
|------|--------|
| `communication/` | 跟硬件打交道——连相机、激光雷达、串口传感器 |
| `pipeline/` | 数据流水线——图像预处理、点云处理、多传感器融合 |
| `inference/` | AI 推理——加载模型，喂图片进去，输出检测结果 |
| `reconstruction/` | 三维重建——把多张图片/点云拼成 3D 场景 |
| `gateway/` | API 网关——前端访问后端的唯一入口 |
| `common/` | 工具库——日志、配置加载、公共类型 |
| `config/` | 配置文件（YAML） |
| `tests/` | 测试代码 |

## 技术栈

| 技术 | 用途 | 官方文档 |
|------|------|----------|
| **Python 3.10+** | 编程语言 | https://docs.python.org/zh-cn/3/ |
| **FastAPI** | Web 框架（REST + WebSocket） | https://fastapi.tiangolo.com/zh/ |
| **NumPy / SciPy** | 矩阵运算、科学计算 | https://numpy.org/doc/ |
| **OpenCV** | 图像处理（去噪、缩放、格式转换） | https://docs.opencv.org/4.x/ |
| **Open3D** | 点云处理（降采样、配准） | https://www.open3d.org/docs/ |
| **Gaussian Splatting** | 三维重建算法 | https://github.com/graphdeco-inria/gaussian-splatting |
| **PyTorch / ONNX Runtime** | 模型推理 | https://pytorch.org/docs/ |
| **NATS / Redis Streams** | 消息队列（模块间解耦） | https://docs.nats.io/ |

## 怎么学？（推荐学习路线）

如果你是新手，建议按这个顺序学：

1. **先跑起来** — 装 Python，写个 `print("hello")`
   - 教程：https://docs.python.org/zh-cn/3/tutorial/

2. **FastAPI 入门** — 写一个简单的 API 接口
   - 教程：https://fastapi.tiangolo.com/zh/tutorial/first-steps/
   - 花半天就能写个 "Hello World" 接口

3. **NumPy + OpenCV** — 图片怎么用代码处理
   - NumPy 快速入门：https://numpy.org/doc/stable/user/quickstart.html
   - OpenCV 教程：https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html

4. **WebSocket** — 后端怎么实时推数据给前端
   - FastAPI WebSocket：https://fastapi.tiangolo.com/zh/advanced/websockets/

5. **Gaussian Splatting 概念** — 不用深入数学，先理解"用一堆高斯球表示三维物体"这个思想
   - 科普视频（B站搜"3D Gaussian Splatting 原理"）

## 怎么跑起来？

```bash
cd backend
python -m venv venv                    # 创建虚拟环境
source venv/bin/activate               # 激活（Windows: venv\Scripts\activate）
pip install -r requirements.txt        # 装依赖
cd gateway
python app.py                          # 启动后端
```

## 参考设计

后端的组织方式参考了"微服务 + 消息驱动"架构：
- 每个子目录是一个独立模块，通过消息队列通信
- 模块之间不直接调用，靠发消息解耦
- 好处：某个模块挂了不影响整体；想换一个 AI 模型只需改 inference，别的不用动

简化说明：
- 硬件层只管"拿数据"，不管数据怎么用
- 处理层只管"洗数据"，不管数据从哪来、去哪用
- 推理层只管"跑模型"，不管图片是哪个相机拍的
- 网关门面只管"接待前端"，不干业务逻辑
