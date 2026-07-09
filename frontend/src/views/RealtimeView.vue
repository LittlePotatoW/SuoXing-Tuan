<!-- ============================================================ -->
<!-- frontend/src/views/RealtimeView.vue                              -->
<!-- 实时融合检测 — 被动/主动双模式                                     -->
<!-- ============================================================ -->

<template>
  <div style="display: flex; flex-direction: column; height: 100%">
    <!-- 顶部控制栏 -->
    <div style="display: flex; align-items: center; gap: 12px; padding: 6px 12px; background: #1e1e1e; border-bottom: 1px solid #333; flex-wrap: wrap">
      <span style="font-size: 14px; font-weight: bold; color: #4FC3F7">实时融合</span>

      <!-- 启动/停止 -->
      <button @click="toggleRunning"
        :style="{ background: running ? '#f44336' : '#4CAF50', color: '#fff', border: 'none', padding: '3px 12px', fontSize: '11px', borderRadius: '3px', cursor: 'pointer', fontWeight: 'bold' }">
        {{ running ? '停止' : '启动' }}
      </button>

      <!-- 模式切换 -->
      <button @click="switchMode(mode === 'passive' ? 'active' : 'passive')"
        :style="{ background: mode === 'active' ? '#4CAF50' : '#2196F3', color: '#fff', border: 'none', padding: '3px 10px', fontSize: '11px', borderRadius: '3px', cursor: 'pointer' }">
        {{ mode === 'passive' ? '被动' : '主动' }}
      </button>

      <!-- 中继站地址 (主动模式) -->
      <template v-if="mode === 'active'">
        <input v-model="relayUrl" placeholder="http://x.x.x.x:8001"
          style="width:140px;background:#2a2a2a;color:#ccc;border:1px solid #555;padding:2px 6px;font-size:11px" />
        <span style="font-size:10px;color:#888">间隔</span>
        <select v-model="relayInterval" style="background:#2a2a2a;color:#ccc;border:1px solid #555;font-size:11px;padding:2px">
          <option :value="1000">1s</option>
          <option :value="2000">2s</option>
          <option :value="5000">5s</option>
        </select>
      </template>

      <div style="width:1px;height:20px;background:#444;margin:0 4px" />

      <!-- 临时: 忽略中继站定位，直接用 detection 帧内 car_position -->
      <label style="display:flex;align-items:center;gap:4px;color:#ffa726;font-size:11px;cursor:pointer" title="忽略中继站定位，直接用帧内 car_position">
        <input type="checkbox" v-model="fakeLocOn" />测试定位
      </label>
      <input v-if="fakeLocOn" v-model.number="fakeSpeed" type="number" step="0.1" min="0.1" max="2"
        style="width:45px;background:#2a2a2a;color:#ffa726;border:1px solid #555;padding:2px 4px;font-size:11px" />
      <span v-if="fakeLocOn" style="color:#ffa726;font-size:10px">m/s</span>

      <div style="width:1px;height:20px;background:#444;margin:0 4px" />

      <label style="display:flex;align-items:center;gap:4px;color:#ccc;font-size:12px;cursor:pointer">
        <input type="checkbox" v-model="yoloOn" @change="toggleYolo" />YOLO
      </label>
      <label style="display:flex;align-items:center;gap:4px;color:#ccc;font-size:12px;cursor:pointer">
        <input type="checkbox" v-model="reconOn" @change="toggleRecon" />重建
      </label>
      <button @click="clearAll" style="background:#555;color:#fff;border:none;padding:3px 10px;font-size:11px;cursor:pointer;border-radius:3px">清除</button>

      <div style="flex:1" />
      <span style="color:#888;font-size:11px">loc:{{ stats.location }} det:{{ stats.detection }} 重建:{{ meshStats.frames }}</span>
    </div>

    <!-- 主区域 -->
    <div style="flex:1;display:flex;overflow:hidden">
      <div style="flex:1;position:relative">
        <ReconstructionViewer ref="viewerRef" />
        <div style="position:absolute;top:8px;right:8px;background:rgba(0,0,0,0.7);padding:4px 8px;font-size:11px;color:#ccc;border-radius:3px">
          <div>{{ mode === 'active' ? '主动拉取' : '被动接收' }} | 缺陷:{{ crackCount }}</div>
        </div>
      </div>
      <div style="width:180px;background:#1e1e1e;border-left:1px solid #333;padding:10px;overflow-y:auto">
        <div style="font-size:12px;font-weight:bold;color:#ccc;margin-bottom:6px">缺陷 ({{ crackCount }})</div>
        <div v-for="(c,i) in crackList" :key="i"
          style="font-size:10px;color:#ccc;padding:4px 6px;margin-bottom:3px;background:#2a2a2a;border-radius:3px">
          <div :style="{color: crackColor(c.crack_type)}">&#9679; {{ c.crack_type || '缺陷' }}</div>
          <div style="color:#888">{{ pct(c.confidence) }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import ReconstructionViewer from '../components/ReconstructionViewer.vue'
import { getBaseUrl } from '../services/apiClient'
import { RELAY_URL } from '../services/relayConfig'

const viewerRef = ref<any>(null)
const yoloOn = ref(true)
const reconOn = ref(true)
const stats = reactive({ location: 0, detection: 0 })
const meshStats = reactive({ frames: 0 })
const crackList = ref<any[]>([])
const crackCount = computed(() => crackList.value.length)

// ── 模式 ──
const mode = ref<'passive' | 'active'>('passive')
const running = ref(false)
const relayUrl = ref(RELAY_URL)
const relayInterval = ref(5000)
const fakeLocOn = ref(false)
const fakeSpeed = ref(0.1)
let relayTimer: any = null
let fakeLocT0 = 0
let seenLoc = new Set<number>()
let seenDet = new Set<string>()

let ws: WebSocket | null = null
let timer: any = null

const CRACK_COLORS: Record<string, string> = {
  '裂缝': '#ef5350', '渗漏': '#42a5f5', '剥落': '#ffa726',
  'crack': '#ef5350', 'leakage': '#42a5f5', 'spalling': '#ffa726',
}

function crackColor(t: string): string { return CRACK_COLORS[t] || '#ccc' }
function pct(v: number): string { return ((v || 0) * 100).toFixed(0) + '%' }

async function toggleYolo() {
  await fetch(getBaseUrl() + '/api/realtime/toggle', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ yolo: yoloOn.value }),
  })
}

async function toggleRecon() {
  await fetch(getBaseUrl() + '/api/realtime/toggle', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reconstruction: reconOn.value }),
  })
}

async function clearAll() {
  await fetch(getBaseUrl() + '/api/reconstruction/reset', { method: 'POST' })
  await fetch(getBaseUrl() + '/api/preprocessing/reset', { method: 'POST' })
  stats.location = 0; stats.detection = 0; meshStats.frames = 0
  crackList.value = []
  seenLoc.clear(); seenDet.clear()
  viewerRef.value?.resetScene()
}

function postJson(url: string, body: any) {
  return fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
}

// ── 启动/停止 ──
function toggleRunning() { running.value = !running.value }
function switchMode(m: 'passive' | 'active') {
  if (relayTimer) { clearInterval(relayTimer); relayTimer = null }
  mode.value = m
  seenLoc.clear(); seenDet.clear()
}

// ── 主动模式: 轮询中继站 ──
async function activePoll() {
  if (!running.value) return
  const base = relayUrl.value.trim()
  if (!base) return
  const backend = getBaseUrl()

  try {
    // 拉取定位数据 (测试定位模式跳过)
    if (!fakeLocOn.value) {
      const locR = await fetch(base + '/location/latest')
      if (locR.ok) {
        const locData = await locR.json()
        const locFrames = locData.frames || []
        for (const item of locFrames) {
          const ts = item.timestamp_ns
          if (seenLoc.has(ts)) continue
          seenLoc.add(ts)
          await postJson(backend + '/api/preprocessing/kinematics', item)
          stats.location++
        }
      }
    }

    // 拉取传感器数据
    const detR = await fetch(base + '/sensor/latest')
    if (detR.ok) {
      const detData = await detR.json()
      const detFrames = detData.frames || []
      for (const frame of detFrames) {
        const fid = frame.frame_id || String(frame.timestamp_ns)
        if (seenDet.has(fid)) continue
        seenDet.add(fid)
        // 测试定位: 用帧时间戳×速度覆盖 car_position
        if (fakeLocOn.value) {
          if (!fakeLocT0) fakeLocT0 = frame.timestamp_ns
          const dt = (frame.timestamp_ns - fakeLocT0) / 1e9
          const x = fakeSpeed.value * dt
          frame.car_position = {
            pose: { position: { x, y: 0, z: 0 }, rotation: { qw: 1, qx: 0, qy: 0, qz: 0 } },
            timestamp_ns: frame.timestamp_ns,
          }
        }
        const r = await postJson(backend + '/api/reconstruction/frame', frame)
        const j = await r.json()
        if (j.status === 'ok') stats.detection++
      }
    }
  } catch { /* relay unreachable */ }
}
watch(relayInterval, () => {
  if (mode.value === 'active' && relayTimer) {
    clearInterval(relayTimer)
    relayTimer = setInterval(activePoll, relayInterval.value)
  }
})

// 启动时自动开始轮询
watch(running, (v) => {
  if (v) {
    activePoll()
    relayTimer = setInterval(activePoll, relayInterval.value)
  } else {
    if (relayTimer) { clearInterval(relayTimer); relayTimer = null }
  }
})

// ── 被动模式: 状态轮询 ──
async function poll() {
  try {
    const [estR, recR] = await Promise.all([
      fetch(getBaseUrl() + '/api/preprocessing/estimator/stats'),
      fetch(getBaseUrl() + '/api/reconstruction/status'),
    ])
    const est = await estR.json()
    const rec = await recR.json()
    stats.location = est.stats?.updates || 0
    stats.detection = rec.total_frames || 0
    meshStats.frames = rec.total_frames || 0
  } catch { /* ignore */ }
}

function connectWs() {
  const url = getBaseUrl().replace('http', 'ws') + '/api/reconstruction/ws'
  ws = new WebSocket(url)
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data)
    if (msg.type === 'rebuild_complete' && msg.data?.mesh) {
      viewerRef.value?.addMesh(msg.data.mesh)
      viewerRef.value?.updateTrail(msg.data.camera_trail)
      meshStats.frames = msg.data.total_frames || 0
      crackList.value = msg.data.cracks || []
      viewerRef.value?.addCracks(msg.data.cracks || [])
    }
  }
  ws.onerror = () => {}
  ws.onclose = () => { setTimeout(connectWs, 3000) }
}

onMounted(() => {
  connectWs()
  timer = setInterval(poll, 1000)
})

onUnmounted(() => {
  ws?.close()
  if (timer) clearInterval(timer)
  if (relayTimer) clearInterval(relayTimer)
})
</script>
