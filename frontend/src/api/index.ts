// ============================================================
// frontend/src/api/index.ts
// 前端API层 (Layer 2) 统一入口：聚合后端 API 函数
//
// 设计与用法:
//   导入本文件即可调用所有后端 API
//   底层连接由 Layer 0 (network/) 提供
// ============================================================

export { httpClient, setBaseURL } from '@/network/http-client'
export * from './vehicle'
export * from './reconstruction'
export * from './detection'
