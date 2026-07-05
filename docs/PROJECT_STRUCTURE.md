# 项目文件结构

```
SuoXing-Tuan/
├── CLAUDE.md                          # 项目规则 + 代码头部注释规范
├── .gitignore                         # 已添加前端 env + 模型文件 + config.json
│
├── backend/                           # Python 后端（3个文件）
│   ├── main.py                        # FastAPI 应用（路由、WebSocket、启动）
│   ├── inference.py                   # YOLO 推理引擎（加载、推理、卸载）
│   └── requirements.txt               # 依赖
│
├── frontend/                          # Vue 3 + Vite 前端（浏览器运行，无 Electron）
│   ├── src/
│   │   ├── App.vue                    # 根组件（布局 + 状态）
│   │   ├── main.ts                    # 入口
│   │   ├── constants/
│   │   │   └── colors.ts              # 全部颜色集中管理，带中文注释
│   │   ├── services/
│   │   │   └── apiClient.ts           # 后端 API 客户端
│   │   └── components/
│   │       ├── ConnectionBar.vue      # IP:端口 连接栏
│   │       ├── ModelSelector.vue      # .pt 文件选择 → 上传后端加载
│   │       ├── DragDropZone.vue       # 拖拽图片 → 发后端推理
│   │       ├── ImageViewer.vue        # Canvas 图像 + 检测框叠加
│   │       └── ResultPanel.vue        # 检测结果表格
│   ├── config.example.json            # 配置模板（入仓库）
│   └── config.json                    # 本地配置（gitignored）
│
├── scripts/
│   └── start.bat                      # 一键启动：后端 → 前端 → 浏览器
│
└── docs/
    ├── ARCHITECTURE.md
    ├── PROJECT_STRUCTURE.md
    ├── FRONTEND_DESIGN.md             # 前端设计文档
    ├── BACKEND_DESIGN.md              # 后端设计文档
    └── MODEL_DESIGN.md                # 多模态模型架构设计
```

## 数据流（遵循 ARCHITECTURE.md 边界）

```
前端（仅展示）                后端（计算）
─────────────               ────────────
连接后端 ────── GET /api/health ──────→ 返回状态
选 .pt 文件 ── POST /api/model/load ──→ 热加载模型
拖拽图片 ──── POST /api/inference ───→ YOLO 推理
                                            │
Canvas 显示 ←────── 返回 bbox 列表 ←────────┘
```

- 前端 71KB 构建产物，零依赖（仅 Vue 3）
- 后端 2 个文件，拔插式换 .pt 模型
- 启动：双击 `scripts/start.bat`
