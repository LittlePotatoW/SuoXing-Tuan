// ============================================================
// frontend/src/composables/useLanScan.ts
// LAN 设备发现：调后端 API 扫描同网段 IP 的 WS 端口
//
// 设计与用法:
//   导出 useLanScan()
//     devices / scanning / progress / subnet — 响应式状态
//     scan() — 扫描 1-254，5 秒内重复调用返回缓存
//     forceScan() — 跳过缓存强制重扫
//   导出 LanDevice 类型
//
// 注意: 端口探测由后端 POST /api/network/scan 完成，
//   绕过浏览器 Private Network Access 限制
// ============================================================

import { ref } from 'vue'
import { httpClient } from '@/network/http-client'

export interface LanDevice {
  ip: string
  telemetry: boolean
  frame: boolean
}

// ---------- 扫描缓存 ----------
let lastScanTime = 0
let cachedDevices: LanDevice[] = []
let cachedSubnet = ''
const CACHE_TTL = 5000

export function useLanScan() {
  const devices = ref<LanDevice[]>([])
  const scanning = ref(false)
  const progress = ref(0)
  const subnet = ref('')

  async function doScan(telemetryPort = 8001, framePort = 8002, timeout = 1.0) {
    scanning.value = true
    progress.value = 0
    devices.value = []

    try {
      const res = await httpClient.post('/api/network/scan', null, {
        params: { telemetry_port: telemetryPort, frame_port: framePort, timeout },
        timeout: 30000,
      })
      const data = res.data
      subnet.value = data.subnet || ''
      devices.value = data.devices || []
      progress.value = 254

      lastScanTime = Date.now()
      cachedDevices = devices.value
      cachedSubnet = subnet.value
    } catch {
      devices.value = []
    } finally {
      scanning.value = false
    }
  }

  async function scan(telemetryPort?: number, framePort?: number, timeout?: number) {
    if (Date.now() - lastScanTime < CACHE_TTL) {
      devices.value = cachedDevices
      subnet.value = cachedSubnet
      progress.value = 254
      return
    }
    return doScan(telemetryPort, framePort, timeout)
  }

  async function forceScan(telemetryPort?: number, framePort?: number, timeout?: number) {
    return doScan(telemetryPort, framePort, timeout)
  }

  return { devices, scanning, progress, subnet, scan, forceScan }
}
