// ============================================================
// frontend/src/network/websocket-client.ts
// 网络接发层 (Layer 0)：WebSocket 连接管理，连外部数据源
//
// 设计与用法:
//   导出 createWSClient(url) → WSClient 实例
//   WSClient: connect / close / onMessage / onStatusChange / send
// ============================================================

export type WSStatus =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'reconnecting'

export interface WSClient {
  connect(): void
  close(): void
  onMessage(fn: (data: string) => void): void
  onStatusChange(fn: (status: WSStatus) => void): void
  send(data: string): void
}

export function createWSClient(url: string): WSClient {
  let ws: WebSocket | null = null
  let status: WSStatus = 'disconnected'
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null
  let reconnectDelay = 1000

  const messageCallbacks: Array<(data: string) => void> = []
  const statusCallbacks: Array<(s: WSStatus) => void> = []

  function setStatus(s: WSStatus) {
    status = s
    statusCallbacks.forEach((fn) => fn(s))
  }

  function clearTimers() {
    if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
    if (heartbeatTimer) { clearInterval(heartbeatTimer); heartbeatTimer = null }
  }

  function startHeartbeat() {
    heartbeatTimer = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send('ping')
      }
    }, 30000)
  }

  function doConnect() {
    if (ws) { ws.close() }
    setStatus('connecting')
    ws = new WebSocket(url)

    ws.onopen = () => {
      setStatus('connected')
      reconnectDelay = 1000
      startHeartbeat()
    }

    ws.onmessage = (event) => {
      if (event.data === 'pong') return
      messageCallbacks.forEach((fn) => fn(event.data))
    }

    ws.onclose = () => {
      clearTimers()
      if (status === 'connected' || status === 'connecting') {
        setStatus('reconnecting')
        reconnectTimer = setTimeout(() => {
          reconnectDelay = Math.min(reconnectDelay * 2, 30000)
          doConnect()
        }, reconnectDelay)
      } else {
        setStatus('disconnected')
      }
    }

    ws.onerror = () => {
      // onclose 会接着触发, 由 onclose 处理重连
    }
  }

  return {
    connect() {
      doConnect()
    },
    close() {
      clearTimers()
      reconnectDelay = 1000
      if (ws) { ws.close() }
      setStatus('disconnected')
    },
    onMessage(fn) {
      messageCallbacks.push(fn)
    },
    onStatusChange(fn) {
      statusCallbacks.push(fn)
    },
    send(data) {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(data)
      }
    },
  }
}
