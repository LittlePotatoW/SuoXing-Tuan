// ============================================================
// frontend/src/composables/useLanScan.ts
// LAN 设备发现：扫描同网段 IP，尝试 WS 连接
//
// 设计与用法:
//   导出 useLanScan()
//     devices / scanning — 响应式状态
//     scan() — 扫描 1-254
//   导出 LanDevice 类型
// ============================================================

import { ref } from 'vue'

export interface LanDevice {
  ip: string
  telemetry: boolean    // 8001 端口可达
  frame: boolean        // 8002 端口可达
}

export function useLanScan() {
  const devices = ref<LanDevice[]>([])
  const scanning = ref(false)

  async function getBaseIP(): Promise<string> {
    // 通过 WebRTC 获取本机局域网 IP 段
    return new Promise<string>((resolve) => {
      const pc = new RTCPeerConnection({ iceServers: [] })
      pc.createDataChannel('')
      pc.createOffer().then((offer) => pc.setLocalDescription(offer))
      pc.onicecandidate = (e) => {
        if (!e.candidate) return
        const addr = e.candidate.address || e.candidate.candidate?.match(/(\d+\.\d+\.\d+)\.\d+/)?.[1]
        if (addr && !addr.startsWith('127.')) {
          resolve(addr)
          pc.close()
        }
      }
      setTimeout(() => resolve('192.168.1'), 2000) // fallback
    })
  }

  async function tryPort(ip: string, port: number, timeout: number): Promise<boolean> {
    return new Promise((resolve) => {
      const ws = new WebSocket(`ws://${ip}:${port}`)
      const timer = setTimeout(() => { ws.close(); resolve(false) }, timeout)
      ws.onopen = () => { clearTimeout(timer); ws.close(); resolve(true) }
      ws.onerror = () => { clearTimeout(timer); resolve(false) }
    })
  }

  async function scan(telemetryPort = 8001, framePort = 8002, timeout = 800) {
    scanning.value = true
    devices.value = []

    const base = await getBaseIP()
    const batchSize = 50
    const results: LanDevice[] = []

    for (let start = 1; start <= 254; start += batchSize) {
      const end = Math.min(start + batchSize - 1, 254)
      const tasks: Promise<void>[] = []
      for (let i = start; i <= end; i++) {
        const ip = `${base}.${i}`
        tasks.push(
          Promise.all([
            tryPort(ip, telemetryPort, timeout),
            tryPort(ip, framePort, timeout),
          ]).then(([t, f]) => {
            if (t || f) results.push({ ip, telemetry: t, frame: f })
          })
        )
      }
      await Promise.all(tasks)
    }

    devices.value = results
    scanning.value = false
  }

  return { devices, scanning, scan }
}
