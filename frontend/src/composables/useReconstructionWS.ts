// ============================================================
// frontend/src/composables/useReconstructionWS.ts
// 重建结果 WebSocket 客户端：接收后端推送的 rebuild_complete 消息
//
// 设计与用法:
//   导出 useReconstructionWS(onMeshData, onCracks) → { connect, disconnect }
//   onMeshData: 收到 mesh 数据时回调 (参考 MeshData 格式)
//   onCracks:   收到裂缝数据时回调
//   自动重连 (3s 间隔)
// ============================================================

import { ref, onUnmounted } from 'vue'
import { useSettingsStore } from '@/stores/settings'

export interface MeshData {
  vertices: number[]
  faces: number[]
  vertex_count: number
  face_count: number
  vertex_colors: number[]
}

export function useReconstructionWS(
  onMeshData: (data: MeshData) => void,
  onCracks: (detections: any[]) => void,
) {
  const settings = useSettingsStore()
  const connected = ref(false)

  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let _stopped = false

  function getWsUrl(): string {
    const host = settings.backend?.host || '127.0.0.1'
    const port = settings.backend?.port || 8000
    return `ws://${host}:${port}/api/reconstruction/ws`
  }

  function connect(): void {
    _stopped = false
    if (ws && ws.readyState === WebSocket.OPEN) return

    try {
      ws = new WebSocket(getWsUrl())
    } catch {
      scheduleReconnect()
      return
    }

    ws.onopen = () => {
      connected.value = true
      console.log('[reconWS] connected')
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        console.log('[reconWS] received:', msg.type, msg.data ? `ts=${msg.data.timestamp} mesh=${!!msg.data.mesh_data}` : '')
        if (msg.type === 'rebuild_complete' && msg.data) {
          if (msg.data.mesh_data) {
            console.log('[reconWS] calling onMeshData, verts:', msg.data.mesh_data.vertex_count)
            onMeshData(msg.data.mesh_data)
          }
          if (msg.data.detections && msg.data.detections.length > 0) {
            onCracks(msg.data.detections)
          }
        }
      } catch { /* 忽略格式错误 */ }
    }

    ws.onclose = () => {
      connected.value = false
      console.log('[reconWS] disconnected, will reconnect')
      ws = null
      scheduleReconnect()
    }

    ws.onerror = (e) => {
      console.warn('[reconWS] error:', e)
    }
  }

  function scheduleReconnect(): void {
    if (_stopped) return
    if (reconnectTimer) clearTimeout(reconnectTimer)
    reconnectTimer = setTimeout(connect, 3000)
  }

  function disconnect(): void {
    _stopped = true
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
    if (ws) {
      ws.onclose = null
      ws.close()
      ws = null
    }
    connected.value = false
  }

  onUnmounted(() => disconnect())

  return { connected, connect, disconnect }
}
