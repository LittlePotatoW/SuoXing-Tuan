// ============================================================
// frontend/src/api/index.ts
// 前端API层 (Layer 2) 统一入口：创建 axios/WS 实例，导出各模块 API
//
// 设计与用法:
//   导出 httpClient (axios 实例)
//   导出 wsClient (WebSocket 实例)
//   聚合导出 reconstruction / detection / vehicle 子模块
// ============================================================
