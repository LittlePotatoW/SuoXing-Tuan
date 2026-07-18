// ============================================================
// frontend/src/network/http-client.ts
// 网络接发层 (Layer 0)：HTTP 连接实例，供 Layer 2 调用后端 API
//
// 设计与用法:
//   导出 httpClient (axios 实例)
//   导出 setBaseURL()  切换连接目标
// ============================================================

import axios from 'axios'

const httpClient = axios.create({
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
})

function setBaseURL(host: string, port: number): void {
  httpClient.defaults.baseURL = `http://${host}:${port}`
}

export { httpClient, setBaseURL }
