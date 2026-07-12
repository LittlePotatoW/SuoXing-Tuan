<!-- ============================================================ -->
<!-- frontend/src/views/RealtimeView.vue                                  -->
<!-- 实时融合页面 — 编排中继/回放/手动三模式 + 保存 + 匀速直线             -->
<!-- ============================================================ -->

<template>
  <div style="display: flex; flex-direction: column; height: 100%">
    <!-- 顶部工具栏 -->
    <TopToolbar
      :running="running"
      :mode="mode"
      :subMode="subMode"
      :yoloOn="yoloOn"
      :reconOn="reconOn"
      :stats="stats"
      :meshFrames="meshStats.frames"
      @toggleRunning="toggleRunning"
      @switchMode="onSwitchMode"
      @update:subMode="onChangeSubMode"
      @toggleYolo="toggleYolo"
      @toggleRecon="toggleRecon"
      @clearAll="clearAll"
    />

    <!-- 主区域 -->
    <div style="flex:1;display:flex;overflow:hidden">
      <div style="flex:1;position:relative">
        <ReconstructionViewer ref="viewerRef" />
        <div style="position:absolute;top:8px;right:8px;background:rgba(0,0,0,0.7);padding:4px 8px;font-size:11px;color:#ccc;border-radius:3px">
          <div>{{ pageLabel() }} | 缺陷:{{ crackList.length }}</div>
        </div>
      </div>

      <!-- 右侧面板 -->
      <DebugSidebar :activeTab="sidebarTab" @update:activeTab="sidebarTab = $event">
        <!-- 调试标签页内容 -->
        <template #debug>
          <!-- 保存模式 (始终可见) -->
          <SaveModePanel
            :saveOn="saveOn" :saveName="saveName"
            :saveLoc="saveLoc" :saveDet="saveDet" :saveFusion="saveFusion"
            @update:saveOn="saveOn = $event"
            @update:saveName="saveName = $event"
            @update:saveLoc="saveLoc = $event"
            @update:saveDet="saveDet = $event"
            @update:saveFusion="saveFusion = $event"
          />

          <!-- 匀速直线 (始终可见) -->
          <StraightLinePanel
            :on="straightLineOn" :speed="straightLineSpeed"
            @update:on="straightLineOn = $event"
            @update:speed="straightLineSpeed = $event"
          />

          <div style="border-top:1px solid #333;margin:6px 0;padding-top:6px"></div>

          <!-- 数据源 (仅主动模式) -->
          <div v-if="mode === 'active'">
            <RelayPanel v-if="subMode === 'relay'"
              :relayUrl="relayUrl" :relayInterval="relayInterval"
              :relayConnected="relayConnected" :relayCache="relayCache"
              @update:relayUrl="relayUrl = $event"
              @update:relayInterval="relayInterval = $event"
            />
            <ReplayPanel v-else-if="subMode === 'replay'"
              :relayUrl="relayUrl" @update:relayUrl="relayUrl = $event"
              :rangeType="replayRangeType" :startN="replayStartN" :endN="replayEndN"
              :startMin="replayStartMin" :endMin="replayEndMin"
              :loaded="replayLoaded" :locCount="replayLocCount" :detCount="replayDetCount"
              :playing="replayPlaying"
              :current="replayCurrent" :total="replayTotal"
              @update:rangeType="replayRangeType = $event"
              @update:startN="replayStartN = $event"
              @update:endN="replayEndN = $event"
              @update:startMin="replayStartMin = $event"
              @update:endMin="replayEndMin = $event"
              @load="replayLoad"
              @play="replayPlay"
              @pause="replayPause"
              @stop="replayStop"
              @renderAll="replayRenderAll"
            />
            <ManualPanel v-else-if="subMode === 'manual'"
              :folderName="manualFolder" :dataStatus="manualDataStatus"
              :locCount="manualLocCount" :detCount="manualDetCount" :fusionCount="manualFusionCount"
              :playing="manualPlaying" :current="manualCurrent" :total="manualTotal"
              @update:folderName="manualFolder = $event"
              @load="manualLoad"
              @play="manualPlay"
              @pause="manualPause"
              @stop="manualStop"
            />
          </div>
          <div v-else style="font-size:10px;color:#666">被动模式: 等待外部数据推送</div>
        </template>

        <!-- 缺陷列表标签页 -->
        <template #defects>
          <DefectPanel :list="crackList" />
        </template>

        <!-- 状态标签页 -->
        <template #status>
          <StatusPanel
            :backendConnected="backendConnected"
            :transpondConnected="relayConnected"
            :stats="stats"
            :meshFrames="meshStats.frames"
            :relayCache="relayCache"
          />
        </template>
      </DebugSidebar>
    </div>

    <!-- 底部日志 -->
    <ActionLogBar :entries="actionLog" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import ReconstructionViewer from '../components/ReconstructionViewer.vue'
import TopToolbar from '../components/TopToolbar.vue'
import DebugSidebar from '../components/DebugSidebar.vue'
import DefectPanel from '../components/DefectPanel.vue'
import StatusPanel from '../components/StatusPanel.vue'
import SaveModePanel from '../components/SaveModePanel.vue'
import StraightLinePanel from '../components/StraightLinePanel.vue'
import RelayPanel from '../components/RelayPanel.vue'
import ReplayPanel from '../components/ReplayPanel.vue'
import ManualPanel from '../components/ManualPanel.vue'
import ActionLogBar, { type LogEntry } from '../components/ActionLogBar.vue'
import { getBaseUrl } from '../services/apiClient'
import { getTranspondUrl } from '../services/config'
import { createTranspondClient, type TranspondClient } from '../services/transpondClient'
import { makeSyntheticJpegBase64, makeLocationData, makeSensorFrame, makeSensorFrameStraight, Car } from '../services/dataGenerator'

const viewerRef = ref<any>(null)

// ── 模式状态 ──
const mode = ref<'passive' | 'active'>('passive')
const subMode = ref<'relay' | 'replay' | 'manual'>('relay')
const running = ref(false)
const sidebarTab = ref<'debug' | 'defects' | 'status'>('debug')

// ── 全局开关 ──
const yoloOn = ref(true)
const reconOn = ref(true)

// ── 匀速直线 ──
const straightLineOn = ref(false)
const straightLineSpeed = ref(0.5)
let straightLineT0 = 0

// ── 保存模式 ──
const saveOn = ref(false)
const saveName = ref('')
const saveLoc = ref(true)
const saveDet = ref(true)
const saveFusion = ref(true)

// ── 中继模式 ──
const relayUrl = ref(getTranspondUrl())
const relayInterval = ref(5000)
const relayConnected = ref(false)
const relayCache = ref<{ location: number; sensor: number } | null>(null)
let relayTimer: any = null
const seenLoc = new Set<number>()
const seenDet = new Set<string>()
let transpond: TranspondClient | null = null

// ── 回放模式 ──
const replayRangeType = ref<'frames' | 'time'>('frames')
const replayStartN = ref(50)
const replayEndN = ref(0)
const replayStartMin = ref(5)
const replayEndMin = ref(0)
const replayLoaded = ref(false)
const replayLocCount = ref(0)
const replayDetCount = ref(0)
const replayPlaying = ref(false)
const replayCurrent = ref(0)
const replayTotal = ref(0)
const replayLocFrames = ref<any[]>([])
const replayDetFrames = ref<any[]>([])
let replayTimer: any = null

// ── 手动模式 ──
const manualFolder = ref('')
const manualDataStatus = ref<'none' | 'loading' | 'full' | 'fusion_only' | 'error'>('none')
const manualLocCount = ref(0)
const manualDetCount = ref(0)
const manualFusionCount = ref(0)
const manualPlaying = ref(false)
const manualCurrent = ref(0)
const manualTotal = ref(0)
const manualLocFrames = ref<any[]>([])
const manualDetFrames = ref<any[]>([])
const manualFusionFrames = ref<any[]>([])
let manualTimer: any = null

// ── 统计 ──
const stats = reactive({ location: 0, detection: 0 })
const meshStats = reactive({ frames: 0 })
const crackList = ref<any[]>([])
const backendConnected = ref(false)
let _meshLayers: any[] = []  // 累计的 mesh 层

// ── 日志 ──
const actionLog = ref<LogEntry[]>([])
function log(msg: string, level: LogEntry['level'] = 'info') {
  const time = new Date().toLocaleTimeString()
  actionLog.value = [...actionLog.value.slice(-50), { time, msg, level }]
}

// ── 后端连接 ──
let backendWs: WebSocket | null = null
let pollTimer: any = null

const backend = getBaseUrl()

function postJson(url: string, body: any) {
  return fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
}

// ── 标签 ──
function pageLabel() {
  if (mode.value === 'passive') return '被动接收'
  const sub: Record<string, string> = { relay: '中继拉取', replay: '回放播放', manual: '手动加载' }
  return sub[subMode.value] || '主动'
}

// ── 模式切换 (停止当前运行 + 清空场景 + 恢复启动按钮) ──
function onSwitchMode(m: 'passive' | 'active') {
  if (running.value) {
    stopAllTimers()
    running.value = false
  }
  clearData()
  fetch(`${backend}/api/reconstruction/reset`, { method: 'POST' })
  mode.value = m
  seenLoc.clear()
  seenDet.clear()
}

function onChangeSubMode(sm: string) {
  if (running.value) {
    stopAllTimers()
    running.value = false
  }
  clearData()
  fetch(`${backend}/api/reconstruction/reset`, { method: 'POST' })
  // 清除回放加载数据
  replayLocFrames.value = []; replayDetFrames.value = []
  replayLoaded.value = false; replayLocCount.value = 0; replayDetCount.value = 0
  replayCurrent.value = 0; replayTotal.value = 0
  // 清除手动加载数据
  manualLocFrames.value = []; manualDetFrames.value = []
  manualDataStatus.value = 'none'; manualLocCount.value = 0; manualDetCount.value = 0
  manualFusionCount.value = 0; manualCurrent.value = 0; manualTotal.value = 0
  subMode.value = sm as 'relay' | 'replay' | 'manual'
  seenLoc.clear()
  seenDet.clear()
}

function stopAllTimers() {
  if (relayTimer) { clearInterval(relayTimer); relayTimer = null }
  if (replayTimer) { clearInterval(replayTimer); replayTimer = null }
  if (manualTimer) { clearInterval(manualTimer); manualTimer = null }
}

// ── 启动/停止 ──
function toggleRunning() {
  running.value = !running.value
  if (!running.value) {
    stopAllTimers()
    relayConnected.value = false
  } else if (mode.value === 'active') {
    startActive()
  }
}

function startActive() {
  if (subMode.value === 'relay') startRelay()
  else if (subMode.value === 'replay' && replayLoaded.value) replayPlay()
  else if (subMode.value === 'manual' && (manualDataStatus.value === 'full' || manualDataStatus.value === 'fusion_only')) manualPlay()
}

// ── 保存辅助 ──
async function doSave(type: 'location' | 'sensor' | 'fusion', data: any) {
  if (!saveOn.value || !saveName.value) return
  const flag = type === 'location' ? saveLoc.value : type === 'sensor' ? saveDet.value : saveFusion.value
  if (!flag) return
  try {
    await fetch(`${backend}/api/debug/save/${type}?session=${encodeURIComponent(saveName.value)}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
    })
  } catch { /* ignore save errors */ }
}

// ── 管线转发 ──
async function forwardLocation(data: any) {
  try {
    const ts = data.timestamp_ns
    if (seenLoc.has(ts)) return
    seenLoc.add(ts)
    const r = await postJson(`${backend}/api/preprocessing/kinematics`, {
      velocity: data.car?.kinematics?.velocity ?? 0.5,
      steering_angle: data.car?.kinematics?.steering_angle ?? 0,
      wheel_base: data.car?.kinematics?.wheel_base ?? 1.5,
      timestamp_ns: ts,
    })
    if (r.ok) stats.location++
    await doSave('location', data)
    log(`POST /kinematics ts=${ts}`, 'success')
  } catch (e: any) {
    log(`Location forward error: ${e.message}`, 'error')
  }
}

async function forwardSensor(data: any) {
  try {
    const fid = data.frame_id || String(data.timestamp_ns)
    if (seenDet.has(fid)) return
    seenDet.add(fid)

    // 匀速直线: 覆盖 car_position
    if (straightLineOn.value) {
      if (!straightLineT0) straightLineT0 = data.timestamp_ns
      const dt = (data.timestamp_ns - straightLineT0) / 1e9
      const x = straightLineSpeed.value * dt
      data = { ...data, car_position: { pose: { position: { x, y: 0, z: 0 }, rotation: { qw: 1, qx: 0, qy: 0, qz: 0 } }, timestamp_ns: data.timestamp_ns } }
    }

    const r = await postJson(`${backend}/api/reconstruction/frame`, data)
    const j = await r.json()
    if (j.status === 'ok') stats.detection++
    await doSave('sensor', data)
    log(`POST /frame ${fid}`, j.status === 'ok' ? 'success' : 'error')
  } catch (e: any) {
    log(`Sensor forward error: ${e.message}`, 'error')
  }
}

// ════════════════════════════════════════════════════════════
//  中继模式 (Relay)
// ════════════════════════════════════════════════════════════

function startRelay() {
  if (!running.value || mode.value !== 'active' || subMode.value !== 'relay') return
  transpond = createTranspondClient(relayUrl.value.trim())
  relayPoll()
  relayTimer = setInterval(relayPoll, relayInterval.value)
}

async function relayPoll() {
  if (!transpond) return
  const base = relayUrl.value.trim()
  if (!base) return

  try {
    // 轮询 location（匀速直线模式跳过）
    if (!straightLineOn.value) {
      const { data: locData } = await transpond.getLocations({ limit: 10 })
      if (locData?.frames) {
        for (const item of locData.frames) await forwardLocation(item)
      }
    }

    // 轮询 sensor
    const { data: detData } = await transpond.getSensors({ limit: 20 })
    if (detData?.frames) {
      for (const frame of detData.frames) await forwardSensor(frame)
    }

    // 缓存状态
    const { data: status } = await transpond.getStatus()
    if (status) {
      relayCache.value = { location: status.location_cached ?? 0, sensor: status.sensor_cached ?? 0 }
    }
    relayConnected.value = true
  } catch {
    relayConnected.value = false
  }
}

// ════════════════════════════════════════════════════════════
//  回放模式 (Replay)
// ════════════════════════════════════════════════════════════

async function replayLoad() {
  const tc = createTranspondClient(relayUrl.value.trim())
  let locResult: any = null
  let detResult: any = null

  try {
    if (replayRangeType.value === 'frames') {
      // 按帧数: 取最近 N 条
      const locN = replayStartN.value
      const detN = replayStartN.value
      const locR = await tc.getLocations({ limit: locN > 0 ? locN : 50 })
      const detR = await tc.getSensors({ limit: detN > 0 ? detN : 50 })
      console.log('replayLoad raw:', { locStatus: locR.status, locCount: locR.data?.count, locFrames: locR.data?.frames?.length, detCount: detR.data?.count, detFrames: detR.data?.frames?.length })
      locResult = locR.data
      detResult = detR.data
    } else {
      // 按时间: after = now - startMin*60*1e9 ns
      const startNs = Date.now() * 1_000_000 - replayStartMin.value * 60 * 1_000_000_000
      const locR = await tc.getLocations({ after: Math.max(0, startNs) })
      const detR = await tc.getSensors({ after: Math.max(0, startNs) })
      locResult = locR.data
      detResult = detR.data
    }

    replayLocFrames.value = locResult?.frames || []
    replayDetFrames.value = detResult?.frames || []

    // 按时间戳排序
    replayLocFrames.value.sort((a: any, b: any) => a.timestamp_ns - b.timestamp_ns)
    replayDetFrames.value.sort((a: any, b: any) => a.timestamp_ns - b.timestamp_ns)

    replayLocCount.value = replayLocFrames.value.length
    replayDetCount.value = replayDetFrames.value.length
    replayTotal.value = replayLocFrames.value.length + replayDetFrames.value.length
    replayCurrent.value = 0
    replayLoaded.value = true
    log(`回放加载完成: Loc=${replayLocCount.value} Det=${replayDetCount.value}`, 'success')
  } catch (e: any) {
    log(`回放加载失败: ${e.message}`, 'error')
  }
}

function replayPlay() {
  if (!replayLoaded.value) return
  replayPlaying.value = true
  replayCurrent.value = 0
  seenLoc.clear()
  seenDet.clear()
  straightLineT0 = 0
  doReplayStep()
}

function replayPause() {
  replayPlaying.value = false
  if (replayTimer) { clearTimeout(replayTimer); replayTimer = null }
}

function replayStop() {
  replayPlaying.value = false
  if (replayTimer) { clearTimeout(replayTimer); replayTimer = null }
  replayCurrent.value = 0
}

async function replayRenderAll() {
  if (!replayLoaded.value) return
  const locs = replayLocFrames.value
  const dets = replayDetFrames.value
  const allFrames: { type: 'loc' | 'det'; data: any; ts: number }[] = [
    ...locs.map((f: any) => ({ type: 'loc' as const, data: f, ts: f.timestamp_ns })),
    ...dets.map((f: any) => ({ type: 'det' as const, data: f, ts: f.timestamp_ns })),
  ].sort((a, b) => a.ts - b.ts)

  const BATCH = 10
  for (let i = 0; i < allFrames.length; i += BATCH) {
    const batch = allFrames.slice(i, i + BATCH)
    await Promise.all(batch.map(f => f.type === 'loc' && !straightLineOn.value ? forwardLocation(f.data) : f.type === 'det' ? forwardSensor(f.data) : Promise.resolve()))
    replayCurrent.value = Math.min(i + BATCH, allFrames.length)
  }
  replayCurrent.value = allFrames.length
  log(`一键渲染完成: ${allFrames.length} 帧`, 'success')
}

function doReplayStep() {
  if (!replayPlaying.value) return

  const locs = replayLocFrames.value
  const dets = replayDetFrames.value
  const allFrames: { type: 'loc' | 'det'; data: any; ts: number }[] = [
    ...locs.map((f: any) => ({ type: 'loc' as const, data: f, ts: f.timestamp_ns })),
    ...dets.map((f: any) => ({ type: 'det' as const, data: f, ts: f.timestamp_ns })),
  ].sort((a, b) => a.ts - b.ts)

  if (replayCurrent.value >= allFrames.length) {
    replayPlaying.value = false
    log('回放完成', 'success')
    return
  }

  const frame = allFrames[replayCurrent.value]
  if (frame.type === 'loc' && !straightLineOn.value) {
    forwardLocation(frame.data)
  } else if (frame.type === 'det') {
    forwardSensor(frame.data)
  }

  replayCurrent.value++

  // 计算下一帧延迟
  if (replayCurrent.value < allFrames.length) {
    const nextTs = allFrames[replayCurrent.value].ts
    const delay = Math.max(10, (nextTs - frame.ts) / 1e6)
    replayTimer = setTimeout(doReplayStep, delay)
  } else {
    replayTimer = setTimeout(doReplayStep, 100)
  }
}

// ════════════════════════════════════════════════════════════
//  手动模式 (Manual)
// ════════════════════════════════════════════════════════════

async function manualLoad() {
  const folder = manualFolder.value.trim()
  if (!folder) {
    manualDataStatus.value = 'error'
    return
  }

  manualDataStatus.value = 'loading'
  try {
    const [locR, detR, fusR] = await Promise.all([
      fetch(`${backend}/api/debug/sessions/${encodeURIComponent(folder)}/location`).then(r => r.json()),
      fetch(`${backend}/api/debug/sessions/${encodeURIComponent(folder)}/sensor`).then(r => r.json()),
      fetch(`${backend}/api/debug/sessions/${encodeURIComponent(folder)}/fusion`).then(r => r.json()),
    ])

    const locs: any[] = locR?.frames || []
    const dets: any[] = detR?.frames || []
    const fusions: any[] = fusR?.frames || []

    manualLocCount.value = locs.length
    manualDetCount.value = dets.length
    manualFusionCount.value = fusions.length

    if (locs.length > 0 && dets.length > 0) {
      // 情况A: loc + det 齐全
      manualLocFrames.value = locs.sort((a: any, b: any) => a.timestamp_ns - b.timestamp_ns)
      manualDetFrames.value = dets.sort((a: any, b: any) => a.timestamp_ns - b.timestamp_ns)
      manualTotal.value = locs.length + dets.length
      manualDataStatus.value = 'full'
      log(`手动加载: Loc=${locs.length} Det=${dets.length} (后端融合)`, 'success')
    } else if (fusions.length > 0) {
      // 情况B: 仅有 fusion
      manualFusionFrames.value = fusions
      manualTotal.value = fusions.length
      manualDataStatus.value = 'fusion_only'
      log(`手动加载: Fusion=${fusions.length} (跳过融合直接渲染)`, 'success')
    } else {
      // 情况C: 数据缺失
      manualDataStatus.value = 'error'
      log('数据缺失: 需要 (Loc+Det) 或 Fusion 数据', 'error')
    }
  } catch (e: any) {
    manualDataStatus.value = 'error'
    log(`加载失败: ${e.message}`, 'error')
  }
}

function manualPlay() {
  if (manualDataStatus.value === 'full') {
    manualPlaying.value = true
    manualCurrent.value = 0
    seenLoc.clear()
    seenDet.clear()
    straightLineT0 = 0
    doManualStepFull()
  } else if (manualDataStatus.value === 'fusion_only') {
    // 直接渲染 fusion 数据
    manualPlaying.value = true
    manualCurrent.value = 0
    doManualStepFusion()
  }
}

function manualPause() {
  manualPlaying.value = false
  if (manualTimer) { clearTimeout(manualTimer); manualTimer = null }
}

function manualStop() {
  manualPlaying.value = false
  if (manualTimer) { clearTimeout(manualTimer); manualTimer = null }
  manualCurrent.value = 0
}

function doManualStepFull() {
  if (!manualPlaying.value) return

  const locs = manualLocFrames.value
  const dets = manualDetFrames.value
  const allFrames: { type: 'loc' | 'det'; data: any; ts: number }[] = [
    ...locs.map((f: any) => ({ type: 'loc' as const, data: f, ts: f.timestamp_ns })),
    ...dets.map((f: any) => ({ type: 'det' as const, data: f, ts: f.timestamp_ns })),
  ].sort((a, b) => a.ts - b.ts)

  if (manualCurrent.value >= allFrames.length) {
    manualPlaying.value = false
    log('手动播放完成', 'success')
    return
  }

  const frame = allFrames[manualCurrent.value]
  if (frame.type === 'loc' && !straightLineOn.value) {
    forwardLocation(frame.data)
  } else if (frame.type === 'det') {
    forwardSensor(frame.data)
  }

  manualCurrent.value++

  if (manualCurrent.value < allFrames.length) {
    const nextTs = allFrames[manualCurrent.value].ts
    const delay = Math.max(10, (nextTs - frame.ts) / 1e6)
    manualTimer = setTimeout(doManualStepFull, delay)
  } else {
    manualTimer = setTimeout(doManualStepFull, 100)
  }
}

function doManualStepFusion() {
  if (!manualPlaying.value) return

  const fusions = manualFusionFrames.value
  if (manualCurrent.value >= fusions.length) {
    manualPlaying.value = false
    log('Fusion 渲染完成', 'success')
    return
  }

  const f = fusions[manualCurrent.value]
  if (f.mesh) viewerRef.value?.addMesh(f.mesh)
  if (f.camera_trail) viewerRef.value?.updateTrail(f.camera_trail)
  if (f.cracks) {
    crackList.value = f.cracks
    viewerRef.value?.addCracks(f.cracks)
  }
  meshStats.frames = f.total_frames || manualCurrent.value + 1
  log(`渲染 Fusion #${manualCurrent.value + 1}`, 'success')

  manualCurrent.value++
  manualTimer = setTimeout(doManualStepFusion, 500)
}

// ════════════════════════════════════════════════════════════
//  通用
// ════════════════════════════════════════════════════════════

async function toggleYolo() {
  yoloOn.value = !yoloOn.value
  await postJson(`${backend}/api/realtime/toggle`, { yolo: yoloOn.value })
}

async function toggleRecon() {
  reconOn.value = !reconOn.value
  await postJson(`${backend}/api/realtime/toggle`, { reconstruction: reconOn.value })
}

function clearData() {
  stats.location = 0; stats.detection = 0; meshStats.frames = 0
  crackList.value = []
  relayCache.value = null
  _meshLayers.length = 0
  viewerRef.value?.resetScene()
}

async function clearAll() {
  stopAllTimers()
  running.value = false
  await Promise.all([
    fetch(`${backend}/api/reconstruction/reset`, { method: 'POST' }),
    fetch(`${backend}/api/preprocessing/reset`, { method: 'POST' }),
  ])
  clearData()
  seenLoc.clear(); seenDet.clear()
  straightLineT0 = 0
  replayLoaded.value = false; replayLocFrames.value = []; replayDetFrames.value = []
  manualDataStatus.value = 'none'; manualLocFrames.value = []; manualDetFrames.value = []; manualFusionFrames.value = []
  viewerRef.value?.resetScene()
  log('已清除', 'info')
}

// ── WebSocket (后端重建结果) ──
function connectBackendWs() {
  const wsUrl = backend.replace('http', 'ws') + '/api/reconstruction/ws'
  backendWs = new WebSocket(wsUrl)
  backendWs.onopen = () => { backendConnected.value = true; console.log('[Realtime] WS connected') }
  backendWs.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data)
      console.log('[Realtime] WS msg:', msg.type, msg.data?.mesh?.vertex_count)
      if (msg.type === 'rebuild_complete' && msg.data?.mesh) {
        const isLayered = !!msg.layered
        console.log(`[Realtime] rebuild: layered=${isLayered} verts=${msg.data.mesh.vertex_count} faces=${msg.data.mesh.face_count} layers=${_meshLayers.length}`)
        if (isLayered) {
          _meshLayers.push(msg.data.mesh)
        } else {
          _meshLayers = [msg.data.mesh]
        }
        const merged = viewerRef.value?._mergeLayers(_meshLayers)
        if (merged) {
          console.log(`[Realtime] merged: verts=${merged.vertex_count} faces=${merged.face_count} from ${_meshLayers.length} layers`)
          viewerRef.value?.addMesh(merged)
        }
        viewerRef.value?.updateTrail(msg.data.camera_trail)
        meshStats.frames = msg.data.total_frames || 0
        crackList.value = msg.data.cracks || []
        viewerRef.value?.addCracks(msg.data.cracks || [])
        doSave('fusion', msg.data)
        log(`重建完成 mesh=${meshStats.frames}`, 'success')
      }
    } catch { /* ignore */ }
  }
  backendWs.onerror = () => { backendConnected.value = false }
  backendWs.onclose = () => { backendConnected.value = false; setTimeout(connectBackendWs, 3000) }
}

// ── 被动模式状态轮询 ──
async function passivePoll() {
  try {
    const [estR, recR] = await Promise.all([
      fetch(`${backend}/api/preprocessing/estimator/stats`),
      fetch(`${backend}/api/reconstruction/status`),
    ])
    const est = await estR.json()
    const rec = await recR.json()
    stats.location = est.stats?.updates || 0
    stats.detection = rec.total_frames || 0
  } catch { /* ignore */ }
}

// ── 中继 URL 或间隔变更时重启 ──
watch([relayInterval], () => {
  if (mode.value === 'active' && subMode.value === 'relay' && relayTimer) {
    clearInterval(relayTimer)
    relayTimer = setInterval(relayPoll, relayInterval.value)
  }
})

// ── 生命周期 ──
onMounted(() => {
  connectBackendWs()
  pollTimer = setInterval(passivePoll, 1000)
})

onUnmounted(() => {
  backendWs?.close()
  if (pollTimer) clearInterval(pollTimer)
  stopAllTimers()
})
</script>
