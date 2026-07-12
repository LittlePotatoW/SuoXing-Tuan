<!-- ============================================================ -->
<!-- frontend/src/views/Page2.vue                                     -->
<!-- 实时监控 — HTTP 轮询 relay 数据，渲染照片 + 点云                  -->
<!-- ============================================================ -->

<template>
  <div style="display: flex; flex-direction: column; height: 100%">
    <!-- ── 顶部控制栏 ── -->
    <div style="display: flex; align-items: center; gap: 10px; padding: 6px 12px; background: #1e1e1e; border-bottom: 1px solid #333; flex-wrap: wrap">
      <span style="font-size: 14px; font-weight: bold; color: #4FC3F7">实时监控</span>

      <!-- 状态 -->
      <span :style="{ color: running ? '#4CAF50' : '#888', fontSize: '11px', fontWeight: 'bold' }">
        {{ running ? '● 运行中' : '○ 已停止' }}
      </span>

      <!-- 启动/停止 -->
      <button @click="toggleRunning"
        :style="{
          background: running ? '#f44336' : '#4CAF50',
          color: '#fff', border: 'none', padding: '3px 12px',
          fontSize: '11px', borderRadius: '3px',
          cursor: 'pointer', fontWeight: 'bold'
        }">
        {{ running ? '停止' : '启动' }}
      </button>

      <!-- 轮询间隔 -->
      <span style="font-size:10px;color:#888">间隔</span>
      <select v-model.number="pollInterval" :disabled="running"
        style="background:#2a2a2a;color:#ccc;border:1px solid #555;font-size:11px;padding:2px 4px;border-radius:3px">
        <option :value="200">200ms</option>
        <option :value="500">500ms</option>
        <option :value="1000">1s</option>
        <option :value="2000">2s</option>
      </select>

      <div style="width:1px;height:18px;background:#444;margin:0 2px" />

      <!-- 帧统计 -->
      <span style="font-size:10px;color:#888">帧: {{ frameCount }}</span>
      <span style="font-size:10px;color:#888">FPS: {{ fps.toFixed(1) }}</span>
      <span style="font-size:10px;color:#666">| {{ currentFrameId || '—' }}</span>

      <div style="flex:1" />

      <!-- 错误计数 -->
      <span v-if="failCount > 0" style="font-size:9px;color:#ff9800">错误 {{ failCount }}</span>

      <!-- 相机切换（多相机时显示） -->
      <template v-if="cameraCount > 1">
        <span style="font-size:10px;color:#888">相机:</span>
        <button v-for="ci in cameraCount" :key="ci" @click="activeCamera = ci - 1"
          :style="{
            background: activeCamera === ci - 1 ? '#2196F3' : '#444',
            color: '#fff', border: 'none', padding: '2px 8px', fontSize: '10px',
            borderRadius: '3px', cursor: 'pointer'
          }">
          #{{ ci }}
        </button>
      </template>
    </div>

    <!-- ── 错误提示 ── -->
    <div v-if="errorMsg"
      style="padding:6px 12px;background:#4a1a1a;color:#ef5350;font-size:11px;display:flex;align-items:center;gap:8px;border-bottom:1px solid #5a2828">
      <span>{{ errorMsg }}</span>
      <button @click="errorMsg=''" style="background:transparent;color:#ef5350;border:1px solid #5a2828;padding:1px 6px;font-size:10px;cursor:pointer;border-radius:2px">✕</button>
    </div>

    <!-- ── 主区域 ── -->
    <div style="flex: 1; display: flex; overflow: hidden">
      <!-- 左侧: 照片 -->
      <div style="width: 40%; min-width: 280px; background: #111; display: flex; flex-direction: column; border-right: 1px solid #333">
        <div style="flex:1;display:flex;align-items:center;justify-content:center;overflow:hidden;position:relative">
          <img v-if="currentImage" :src="currentImage"
            style="max-width:100%;max-height:100%;object-fit:contain" />
          <span v-else style="color:#555;font-size:14px">等待数据...</span>

          <div v-if="currentImage" style="position:absolute;bottom:6px;left:6px;background:rgba(0,0,0,0.65);padding:2px 6px;font-size:9px;color:#aaa;border-radius:2px">
            {{ imageSize }}
          </div>
        </div>
        <!-- 帧信息条 -->
        <div style="padding:4px 8px;background:#1a1a1a;border-top:1px solid #333;font-size:10px;color:#777;display:flex;gap:12px">
          <span>frame: {{ currentFrameId || '—' }}</span>
          <span>ts: {{ formatNs(currentTimestamp) }}</span>
          <span v-if="carPos">pos: ({{ carPos.x?.toFixed(2) }}, {{ carPos.y?.toFixed(2) }}, {{ carPos.z?.toFixed(2) }})</span>
        </div>
      </div>

      <!-- 右侧: 点云 3D -->
      <div style="flex:1;min-width:0">
        <PointCloudViewer ref="pcViewerRef" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import PointCloudViewer from '../components/PointCloudViewer.vue'

// ── 状态 ──
const running = ref(false)
const errorMsg = ref('')
const failCount = ref(0)
const pollInterval = ref(200)
const frameCount = ref(0)
const currentFrameId = ref('')
const currentTimestamp = ref(0)
const activeCamera = ref(0)
const cameraCount = ref(0)
const carPos = ref<{ x: number; y: number; z: number } | null>(null)

let pollTimer: ReturnType<typeof setInterval> | null = null
let fpsTimer = 0
let fpsFrames = 0
const fps = ref(0)
const lastImage = ref<{ src: string; w: number; h: number } | null>(null)
const imageSize = ref('')

const pcViewerRef = ref<InstanceType<typeof PointCloudViewer> | null>(null)
const currentImage = computed(() => lastImage.value?.src || '')

// ── 轮询 ──

function toggleRunning() {
  if (running.value) {
    stopPolling()
  } else {
    startPolling()
  }
}

function startPolling() {
  running.value = true
  errorMsg.value = ''
  failCount.value = 0
  fpsFrames = 0
  fpsTimer = performance.now()
  pollOnce() // 立即发一次
  pollTimer = setInterval(pollOnce, pollInterval.value)
}

function stopPolling() {
  running.value = false
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

async function pollOnce() {
  try {
    const resp = await fetch('/relay/sensor?limit=1')
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const data = await resp.json()
    if (data.frames?.length) {
      processFrames(data.frames)
      failCount.value = 0 // 成功后清零
    }
  } catch (e: any) {
    failCount.value++
    if (failCount.value >= 3) {
      errorMsg.value = `请求失败 (${failCount.value}次): ${e.message || e}`
    }
  }
}

// ── 帧处理 ──

function processFrames(frames: any[]) {
  const latest = frames[frames.length - 1]
  if (!latest) return

  frameCount.value += frames.length

  // FPS
  fpsFrames++
  const now = performance.now()
  if (now - fpsTimer >= 1000) {
    fps.value = fpsFrames / ((now - fpsTimer) / 1000)
    fpsFrames = 0
    fpsTimer = now
  }

  // 帧信息
  currentFrameId.value = latest.frame_id || ''
  currentTimestamp.value = latest.timestamp_ns || 0

  // 小车位置
  if (latest.car_position?.pose?.position) {
    carPos.value = latest.car_position.pose.position
  }

  // ── 照片 ──
  const views = latest.camera_views || []
  cameraCount.value = views.length
  const ci = Math.min(activeCamera.value, Math.max(0, views.length - 1))
  const view = views[ci]
  if (view?.image_data) {
    const w = view.width || 0
    const h = view.height || 0
    lastImage.value = {
      src: 'data:image/jpeg;base64,' + view.image_data,
      w, h,
    }
    imageSize.value = w && h ? `${w}×${h}` : ''
  }

  // ── 点云 ──
  const pc = latest.point_cloud
  if (pc?.points && pc.points.length >= 3) {
    pcViewerRef.value?.updatePointCloud(pc.points)
  }
}

// ── 工具 ──

function formatNs(ns: number): string {
  if (!ns) return '—'
  const d = new Date(ns / 1e6)
  return d.toLocaleTimeString('zh-CN', { hour12: false }) + '.' + String(d.getMilliseconds()).padStart(3, '0')
}

// ── 生命周期 ──

onUnmounted(() => {
  stopPolling()
})
</script>
