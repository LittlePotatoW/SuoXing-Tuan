# SuoXing-Tuan 文档中心

## 快速开始

**控制端**:
```bash
cd backend && uvicorn main:app --host 127.0.0.1 --port 8000
```

**前端**:
```bash
cd frontend && npm run dev
```

**模拟器**:
```bash
cd test_end && python serve.py
# → http://localhost:8765/simulator.html
```

**API 文档**: `http://127.0.0.1:8000/docs`

## 文档目录

### 架构设计
- [系统架构](架构设计/系统架构.md) — 系统整体架构、子系统清单、推荐从这里开始
- [后端设计](架构设计/后端设计.md) — 后端模块目录、数据流、全部 API 端点

### 功能模块
- [三维重建管线](功能模块/三维重建管线.md) — 重建数据流、投影公式、Poisson 重建、论文对比
- [实时融合设计](功能模块/实时融合设计.md) — 实时融合页布局、双模式（被动/主动）、数据流

### API 参考
- [实时融合 API](API参考/实时融合API.md) — 运动学/检测/重建/WebSocket 接口 JSON Schema

### 其他
- [参考文献](参考文献.md)

### 外部模块文档

| 模块 | 文档位置 |
|------|----------|
| 数据中继站 (Transpond_Server) | `OTHER_END/Transpond_Server/API.md` |
| 控制中转 (Control_Server) | `OTHER_END/Control_Server/API.md` |
| 车端采集 (Car_detection_end) | `OTHER_END/Car_detection_end/README.md` |
| 模型训练 | `model-training/README-PEOPLE.md` |
