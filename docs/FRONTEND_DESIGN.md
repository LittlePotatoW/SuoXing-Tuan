# 前端设计文档

## 1. 定位

前端是**纯展示层**。遵循 [ARCHITECTURE.md](ARCHITECTURE.md) 中定义的边界：

> "前端边界：不直接访问硬件、不直接加载模型。所有数据通过后端 API 获取，或加载离线数据包。"

| 前端做 | 前端不做 |
|--------|---------|
| 显示图像 + 检测框/mask 叠加 | 加载 AI 模型 |
| 接收后端 WebSocket 实时推送 | 运行推理 |
| 通过 REST API 请求后端推理 | 处理点云 |
| 上传图片/模型文件到后端 | 访问工业相机/传感器 |
| 本地数据包离线回放 | 三维重建计算 |

## 2. 技术选型

| 技术 | 用途 |
|------|------|
| Vue 3 (Composition API) | UI 框架 |
| Vite | 构建工具 |
| TypeScript | 类型安全 |
| Pinia | 全局状态管理 |
| Canvas 2D | 图像渲染 + 检测框叠加 |

## 3. 目录结构

```
frontend/
├── src/
│   ├── constants/
│   │   └── colors.ts              # 全局颜色常量（所有颜色集中管理，有注释）
│   ├── services/
│   │   ├── apiClient.ts           # 后端 REST API 请求（推理、模型管理、健康检查）
│   │   └── wsClient.ts            # WebSocket 客户端（接收实时图像帧+检测结果）
│   ├── stores/
│   │   └── appStore.ts            # Pinia 全局状态
│   ├── components/
│   │   ├── ImageViewer.vue        # 纯显示：图像 + bbox/mask 叠加
│   │   ├── ResultPanel.vue        # 检测结果列表
│   │   ├── DragDropZone.vue       # 拖拽文件 → 发后端推理
│   │   ├── ModelSelector.vue      # 选 .pt 文件 → 上传后端加载
│   │   ├── ConnectionBar.vue      # 后端 IP:端口 连接
│   │   └── StatusBar.vue          # 底部状态（模式、模型名、FPS）
│   ├── App.vue                    # 根组件
│   ├── main.ts                    # 入口
│   └── types/
│       └── index.ts               # TypeScript 类型定义
├── config.json                    # 后端 IP 等配置（gitignored）
├── config.example.json            # 配置文件模板（入仓库）
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## 4. 数据流

### 4.1 在线实时模式

```
后端 WebSocket ──[图像帧JPEG]──▶ 前端 ImageViewer 显示
后端 WebSocket ──[检测结果JSON]──▶ 前端 ResultPanel + ImageViewer 叠加框
```

前端只是被动接收和渲染，不主动触发推理。

### 4.2 手动上传推理模式

```
用户拖拽/选择图片
      │
      ▼
前端显示本地预览
      │
      ▼
POST /api/inference (文件上传)
      │
      ▼
后端推理 → 返回检测结果 JSON
      │
      ▼
前端 ImageViewer 叠加框 + ResultPanel 显示
```

### 4.3 模型切换模式

```
用户选择 .pt 文件
      │
      ▼
POST /api/model/load (文件上传)
      │
      ▼
后端加载模型 → 热切换
      │
      ▼
后续推理请求自动使用新模型
```

## 5. API 依赖

| 方法 | 路径 | 前端调用场景 |
|------|------|-------------|
| GET | `/api/health` | 连接后端时检查状态 |
| POST | `/api/inference` | 用户上传图片后请求推理 |
| POST | `/api/model/load` | 用户选择 .pt 文件后上传到后端加载 |
| GET | `/api/models` | 获取后端已加载的模型列表 |
| WS | `ws://{host}/ws/realtime` | 接收实时图像帧和检测结果 |

## 6. 组件层级

```
App.vue
├── ConnectionBar.vue          ← 输入后端 IP:端口，连接/断开
├── ModelSelector.vue          ← 选 .pt 文件 → 上传到后端
├── DragDropZone.vue           ← 拖拽图片 → 发后端推理 → 展示
│   └── ImageViewer.vue        ← Canvas 渲染：原始图像 + 检测框 + mask
├── ResultPanel.vue            ← 检测结果表格
└── StatusBar.vue              ← 模式、模型名、推理耗时
```

## 7. 颜色管理

所有颜色常量定义在 `src/constants/colors.ts`，按功能分组并有中文注释。组件通过 import 引用颜色常量，不在组件中写死颜色值。

## 8. 无样式原则

- 无 CSS 框架、无 UI 组件库
- 仅使用功能性 flex/grid 布局
- 所有颜色从 colors.ts 引用
- 不做任何美化
