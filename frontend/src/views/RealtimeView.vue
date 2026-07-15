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
              :timeout="replayTimeout" @update:timeout="replayTimeout = $event"
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
              :replayMode="manualReplayMode" :hasFusion="manualHasFusion"
              :canRawRebuild="manualCanRawRebuild"
              :fusionCount="manualFusionCount" :sensorCount="manualSensorCount" :locCount="manualLocCount"
              :straightLineOn="straightLineOn"
              :playing="manualPlaying" :current="manualCurrent" :total="manualTotal"
              @update:folderName="manualFolder = $event"
              @update:replayMode="manualReplayMode = $event"
              @update:straightLineOn="straightLineOn = $event"
              @load="manualLoad"
              @play="manualPlay"
              @pause="manualPause"
              @stop="manualStop"
              @renderAll="manualRenderAll"
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
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
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
import { getConfig, getTranspondUrl } from '../services/config'
import { createTranspondClient, type TranspondClient } from '../services/transpondClient'

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
let lastRelayLocTs = 0
let lastRelayDetTs = 0
const DEDUP_MAX = 10_000
const seenLoc = new Set<number>()
const seenDet = new Set<string>()

function _capSet(s: Set<unknown>) {
  if (s.size <= DEDUP_MAX) return
  const it = s.values()
  for (let i = 0; i < 1000; i++) s.delete(it.next().value)
}

// 点云轴翻转 — forwardSensor 入口调用，保存原始数据，加载时重新翻转
function _flipPointCloud(data: any) {
  const cfg = getConfig()
  const flipX = cfg.pointcloud?.flip_x
  const flipY = cfg.pointcloud?.flip_y
  if (!flipX && !flipY) return
  const pc = data.point_cloud
  if (!pc) return
  let pts = pc.points
  if (pc.encoding === 'float32_base64' && typeof pts === 'string') {
    const raw = Uint8Array.from(atob(pts), c => c.charCodeAt(0))
    const f = new Float32Array(raw.buffer)
    for (let i = 0; i < f.length; i += 3) {
      if (flipX) f[i] = -f[i]
      if (flipY) f[i + 1] = -f[i + 1]
    }
    pc.points = btoa(String.fromCharCode(...new Uint8Array(f.buffer)))
  }
}
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
const replayTimeout = ref(30)
let replayTimer: any = null

// ── 手动模式 ──
const manualFolder = ref('')
const manualDataStatus = ref<'none' | 'loading' | 'full' | 'error'>('none')
const manualReplayMode = ref<'fusion' | 'raw'>('fusion')
const manualHasFusion = ref(false)
const manualHasSensor = ref(false)
const manualHasLoc = ref(false)
const manualPlaying = ref(false)
const manualCurrent = ref(0)
const manualTotal = ref(0)
const manualFusionFrames = ref<any[]>([])
const manualSensorFrames = ref<any[]>([])
const manualLocFrames = ref<any[]>([])
let manualTimer: any = null

const manualCanRawRebuild = computed(() => manualHasSensor.value && (manualHasLoc.value || straightLineOn.value))
const manualFusionCount = ref(0)
const manualSensorCount = ref(0)
const manualLocCount = ref(0)

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
let wsDisposed = false
let wsReconnectTimer: any = null

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
  fetch(`${backend}/api/reconstruction/reset`, { method: 'POST' }).catch(() => {})
  mode.value = m
  seenLoc.clear()
  seenDet.clear()
  if (m === 'passive') {
    if (!pollTimer) pollTimer = setInterval(passivePoll, 1000)
  } else {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  }
}

function onChangeSubMode(sm: string) {
  if (running.value) {
    stopAllTimers()
    running.value = false
  }
  clearData()
  fetch(`${backend}/api/reconstruction/reset`, { method: 'POST' }).catch(() => {})
  // 清除回放加载数据
  replayLocFrames.value = []; replayDetFrames.value = []
  replayLoaded.value = false; replayLocCount.value = 0; replayDetCount.value = 0
  replayCurrent.value = 0; replayTotal.value = 0
  // 清除手动加载数据
  manualFusionFrames.value = []; manualSensorFrames.value = []; manualLocFrames.value = []
  manualFusionCount.value = 0; manualSensorCount.value = 0; manualLocCount.value = 0
  manualDataStatus.value = 'none'; manualCurrent.value = 0; manualTotal.value = 0
  manualHasFusion.value = false; manualHasSensor.value = false; manualHasLoc.value = false
  subMode.value = sm as 'relay' | 'replay' | 'manual'
  seenLoc.clear()
  seenDet.clear()
}

function stopAllTimers() {
  if (relayTimer) { clearInterval(relayTimer); relayTimer = null }
  if (replayTimer) { clearInterval(replayTimer); replayTimer = null }
  if (manualTimer) { clearInterval(manualTimer); manualTimer = null }
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

// ── 启动/停止 ──
function toggleRunning() {
  running.value = !running.value
  if (!running.value) {
    stopAllTimers()
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
    relayConnected.value = false
  } else if (mode.value === 'active') {
    startActive()
  } else {
    // 被动模式启动: 开始状态轮询
    if (!pollTimer) pollTimer = setInterval(passivePoll, 1000)
  }
}

function startActive() {
  if (subMode.value === 'relay') startRelay()
  else if (subMode.value === 'replay' && replayLoaded.value) replayPlay()
  else if (subMode.value === 'manual' && manualDataStatus.value === 'full') manualPlay()
  else log('请先加载数据', 'error')
}

// ── 保存辅助 ──
async function doSave(type: 'location' | 'sensor' | 'fusion' | 'fusion', data: any) {
  if (!saveOn.value || !saveName.value) return
  const flag = type === 'location' ? saveLoc.value : type === 'sensor' ? saveDet.value : type === 'fusion' ? saveFusion.value : saveFusion.value
  if (!flag) return
  try {
    await fetch(`${backend}/api/debug/save/${type}?session=${encodeURIComponent(saveName.value)}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
    })
  } catch (e: any) { log(`保存失败: ${e.message || e}`, 'error') }
}

// ── 管线转发 ──
async function forwardLocation(data: any) {
  try {
    const ts = data.timestamp_ns
    if (seenLoc.has(ts)) return
    const r = await postJson(`${backend}/api/realtime/feed/location`, data)
    if (r.ok) {
      seenLoc.add(ts); _capSet(seenLoc)
      stats.location++
      await doSave('location', data)
      log(`POST /kinematics ts=${ts}`, 'success')
    } else {
      const j = await r.json().catch(() => ({}))
      log(`POST /kinematics ts=${ts}: ${j.status || 'failed'}`, 'error')
    }
  } catch (e: any) {
    log(`Location forward error: ${e.message}`, 'error')
  }
}

async function forwardSensor(data: any) {
  try {
    // 保存原始数据（翻转前），回放/手动加载时重新翻转
    await doSave('sensor', JSON.parse(JSON.stringify(data)))

    const fid = data.frame_id || String(data.timestamp_ns)
    if (seenDet.has(fid)) return
    seenDet.add(fid); _capSet(seenDet)

    // 匀速直线: 覆盖 car_position
    if (straightLineOn.value) {
      if (!straightLineT0) straightLineT0 = data.timestamp_ns
      const dt = (data.timestamp_ns - straightLineT0) / 1e9
      const x = straightLineSpeed.value * dt
      data = { ...data, car_position: { pose: { position: { x, y: 0, z: 0 }, rotation: { qw: 1, qx: 0, qy: 0, qz: 0 } }, timestamp_ns: data.timestamp_ns } }
    }

    // 翻转后发给后端
    _flipPointCloud(data)
    const r = await postJson(`${backend}/api/realtime/feed/detection`, data)
    const j = await r.json()
    if (j.status === 'ok') {
      stats.detection++
      // 存融合数据包 (点云+位姿+图片, 供手动模式回放)
      if (j.final) {
        // 精简格式: 去掉 camera_views 里的 camera_pose (配置常量)
        j.final.camera_views = j.final.camera_views?.map((cv: any) => {
          const { camera_pose, ...rest } = cv; return rest
        })
        j.final.car_position = j.final.car_position?.pose
        await doSave('fusion', j.final)
      }
    }
    log(`POST /frame ${fid}`, j.status === 'ok' ? 'success' : 'error')
  } catch (e: any) {
    log(`Sensor forward error: ${e.message}`, 'error')
  }
}

// ════════════════════════════════════════════════════════════
//  中继模式 (Relay)
// ════════════════════════════════════════════════════════════

let relayStreamWs: WebSocket | null = null

function startRelay() {
  if (!running.value || mode.value !== 'active' || subMode.value !== 'relay') return
  // 关旧 WS，阻止 HTTP 回退
  if (relayStreamWs) {
    relayStreamWs.onclose = null
    relayStreamWs.close()
    relayStreamWs = null
  }
  lastRelayLocTs = 0
  lastRelayDetTs = 0
  straightLineT0 = 0
  transpond = createTranspondClient(relayUrl.value.trim(), replayTimeout.value * 1000)

  // 优先 WS 实时推送
  try {
    relayStreamWs = transpond.connectStream('all', (msg: any) => {
      if (!running.value || mode.value !== 'active' || subMode.value !== 'relay') {
        relayStreamWs?.close(); return
      }
      if (msg.type === 'location' && msg.frames) {
        if (straightLineOn.value) {
          // 匀速直线: 丢弃 Transpond 的 loc，合成固定速度的 kinematics
          postJson(`${backend}/api/realtime/feed/location`, {
            timestamp_ns: Date.now() * 1_000_000,
            camera: [{ camera_pose: { position: { x: 0, y: 0, z: 1 }, rotation: { qw: 0.7071, qx: 0, qy: 0.7071, qz: 0 } } }],
            car: { kinematics: { velocity: straightLineSpeed.value, steering_angle: 0, wheel_base: 1.5 } },
          })
        } else {
          for (const f of msg.frames) {
            forwardLocation(f)
            if (f.timestamp_ns > lastRelayLocTs) lastRelayLocTs = f.timestamp_ns
          }
        }
      } else if (msg.type === 'sensor' && msg.frames) {
        for (const f of msg.frames) {
          forwardSensor(f)
          if (f.timestamp_ns > lastRelayDetTs) lastRelayDetTs = f.timestamp_ns
        }
      }
    })
    relayStreamWs.onopen = () => {
      relayConnected.value = true
      // 首次连接时快速拉取状态
      transpond?.getStatus().then(({ data }) => {
        if (data) relayCache.value = { location: data.location_cached ?? 0, sensor: data.sensor_cached ?? 0 }
      })
    }
    relayStreamWs.onclose = () => {
      relayConnected.value = false
      // WS 断开 → fallback HTTP 轮询
      if (running.value && mode.value === 'active' && subMode.value === 'relay') {
        relayPoll()
        relayTimer = setInterval(relayPoll, relayInterval.value)
      }
    }
    relayStreamWs.onerror = () => {
      relayConnected.value = false
      // WS 失败 → fallback HTTP 轮询
      if (running.value && mode.value === 'active' && subMode.value === 'relay') {
        relayPoll()
        relayTimer = setInterval(relayPoll, relayInterval.value)
      }
    }
  } catch {
    // WS 不支持 → HTTP 轮询
    relayPoll()
    relayTimer = setInterval(relayPoll, relayInterval.value)
  }
}

async function relayPoll() {
  if (!transpond) return
  try {
    if (!straightLineOn.value) {
      const params: { limit: number; after?: number } = { limit: 10 }
      if (lastRelayLocTs > 0) params.after = lastRelayLocTs
      const { data: locData } = await transpond.getLocations(params)
      if (locData?.frames) {
        for (const item of locData.frames) {
          await forwardLocation(item)
          if (item.timestamp_ns > lastRelayLocTs) lastRelayLocTs = item.timestamp_ns
        }
      }
    } else {
      await postJson(`${backend}/api/realtime/feed/location`, {
        timestamp_ns: Date.now() * 1_000_000,
        camera: [{ camera_pose: { position: { x: 0, y: 0, z: 1 }, rotation: { qw: 0.7071, qx: 0, qy: 0.7071, qz: 0 } } }],
        car: { kinematics: { velocity: straightLineSpeed.value, steering_angle: 0, wheel_base: 1.5 } },
      })
    }
    const detParams: { limit: number; after?: number } = { limit: 20 }
    if (lastRelayDetTs > 0) detParams.after = lastRelayDetTs
    const { data: detData } = await transpond.getSensors(detParams)
    if (detData?.frames) {
      for (const frame of detData.frames) {
        await forwardSensor(frame)
        if (frame.timestamp_ns > lastRelayDetTs) lastRelayDetTs = frame.timestamp_ns
      }
    }
    const { data: status } = await transpond.getStatus()
    if (status) relayCache.value = { location: status.location_cached ?? 0, sensor: status.sensor_cached ?? 0 }
    relayConnected.value = true
  } catch {
    relayConnected.value = false
  }
}

// ════════════════════════════════════════════════════════════
//  回放模式 (Replay)
// ════════════════════════════════════════════════════════════

async function replayLoad() {
  const tc = createTranspondClient(relayUrl.value.trim(), replayTimeout.value * 1000)
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
  if (!replayLoaded.value) { log('请先加载回放数据', 'error'); return }
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

  const total = allFrames.length
  if (!total) { log('无回放数据', 'error'); return }
  log(`开始一键渲染 ${total} 帧...`, 'info')
  straightLineT0 = 0
  const BATCH = 5
  for (let i = 0; i < total; i += BATCH) {
    const batch = allFrames.slice(i, i + BATCH)
    await Promise.all(batch.map(f => {
      if (f.type === 'loc') {
        if (straightLineOn.value) {
          return postJson(`${backend}/api/realtime/feed/location`, {
            timestamp_ns: Date.now() * 1_000_000,
            camera: [{ camera_pose: { position: { x: 0, y: 0, z: 1 }, rotation: { qw: 0.7071, qx: 0, qy: 0.7071, qz: 0 } } }],
            car: { kinematics: { velocity: straightLineSpeed.value, steering_angle: 0, wheel_base: 1.5 } },
          })
        }
        const body = {
          timestamp_ns: f.data.timestamp_ns,
          camera: f.data.camera || [{ camera_pose: { position: { x: 0, y: 0, z: 1 }, rotation: { qw: 0.7071, qx: 0, qy: 0.7071, qz: 0 } } }],
          car: f.data.car || { kinematics: { velocity: straightLineSpeed.value, steering_angle: 0, wheel_base: 1.5 } },
        }
        return postJson(`${backend}/api/realtime/feed/location`, body)
      }
      return postJson(`${backend}/api/realtime/feed/detection`, f.data)
    }))
    replayCurrent.value = Math.min(i + BATCH, total)
  }
  replayCurrent.value = total
  log(`一键渲染完成: ${total} 帧`, 'success')
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
  if (frame.type === 'loc') {
    if (straightLineOn.value) {
      postJson(`${backend}/api/realtime/feed/location`, {
        timestamp_ns: Date.now() * 1_000_000,
        camera: [{ camera_pose: { position: { x: 0, y: 0, z: 1 }, rotation: { qw: 0.7071, qx: 0, qy: 0.7071, qz: 0 } } }],
        car: { kinematics: { velocity: straightLineSpeed.value, steering_angle: 0, wheel_base: 1.5 } },
      })
    } else {
      forwardLocation(frame.data)
    }
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
  if (!folder) { manualDataStatus.value = 'error'; return }

  manualDataStatus.value = 'loading'
  try {
    // 用 info 端点查数量，不全量加载（大 session 会超时）
    const info = await fetch(`${backend}/api/debug/sessions/${encodeURIComponent(folder)}/info`).then(r => r.json())
    manualHasFusion.value = (info.fusion || 0) > 0
    manualHasSensor.value = (info.sensor || 0) > 0
    manualHasLoc.value = (info.location || 0) > 0

    // 记录总数
    manualTotal.value = manualHasFusion.value ? info.fusion : (manualHasSensor.value ? info.sensor : 0)
    manualFusionCount.value = info.fusion || 0
    manualSensorCount.value = info.sensor || 0
    manualLocCount.value = info.location || 0
    // 清空缓存
    manualFusionFrames.value = []
    manualSensorFrames.value = []
    manualLocFrames.value = []

    if (manualHasFusion.value) { manualReplayMode.value = 'fusion' }
    else if (manualCanRawRebuild.value) { manualReplayMode.value = 'raw' }

    manualDataStatus.value = (manualHasFusion.value || manualHasSensor.value) ? 'full' : 'error'
    log(`扫描: fusion=${manualFusionCount.value} sensor=${manualSensorCount.value} loc=${manualLocCount.value}`, 'success')
  } catch (e: any) {
    manualDataStatus.value = 'error'
    log(`加载失败: ${e.message}`, 'error')
  }
}

function manualPlay() {
  if (manualReplayMode.value === 'fusion') {
    if (manualFusionCount.value === 0) { log('无融合数据', 'error'); return }
    manualPlaying.value = true; manualCurrent.value = 0; doManualStepFusion()
  } else if (manualReplayMode.value === 'raw') {
    if (!manualHasSensor.value) { log('无 sensor 数据', 'error'); return }
    if (!manualHasLoc.value && !straightLineOn.value) { log('缺少定位数据, 请勾选匀速直线', 'error'); return }
    manualPlaying.value = true; manualCurrent.value = 0; straightLineT0 = 0; doManualStepRaw()
  } else {
    log('请先加载手动数据', 'error')
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

async function manualRenderAll() {
  const isFusion = manualReplayMode.value === 'fusion'
  const total = isFusion ? manualFusionCount.value : manualSensorCount.value
  if (!total) { log('无可用数据', 'error'); return }
  log(`开始一键渲染 ${total} 帧...`, 'info')
  straightLineT0 = 0
  const type = isFusion ? 'fusion' : 'sensor'
  const BATCH = 20
  for (let offset = 0; offset < total; offset += BATCH) {
    const res = await fetch(`${backend}/api/debug/sessions/${encodeURIComponent(manualFolder.value)}/${type}?offset=${offset}&limit=${BATCH}`)
    const data = await res.json()
    const frames: any[] = data?.frames || []
    for (const f of frames) {
      if (isFusion) {
        await postJson(`${backend}/api/realtime/feed/fusion`, f)
      } else {
        if (straightLineOn.value) {
          await postJson(`${backend}/api/realtime/feed/location`, {
            timestamp_ns: Date.now() * 1_000_000,
            camera: [{ camera_pose: { position: { x: 0, y: 0, z: 1 }, rotation: { qw: 0.7071, qx: 0, qy: 0.7071, qz: 0 } } }],
            car: { kinematics: { velocity: straightLineSpeed.value, steering_angle: 0, wheel_base: 1.5 } },
          })
        }
        await postJson(`${backend}/api/realtime/feed/detection`, f)
      }
      manualCurrent.value++
    }
  }
  manualCurrent.value = total
  log('一键渲染完成', 'success')
}

async function doManualStepFusion() {
  if (!manualPlaying.value) return
  const total = manualFusionCount.value
  if (manualCurrent.value >= total) { manualPlaying.value = false; log('手动播放完成', 'success'); return }
  const res = await fetch(`${backend}/api/debug/sessions/${encodeURIComponent(manualFolder.value)}/fusion?offset=${manualCurrent.value}&limit=1`)
  const frames = (await res.json())?.frames || []
  const f = frames[0]
  if (!f) { manualPlaying.value = false; return }
  await postJson(`${backend}/api/realtime/feed/fusion`, f)
  log(`POST /fusion #${manualCurrent.value + 1}`, 'success')
  manualCurrent.value++
  manualTimer = setTimeout(doManualStepFusion, 100)
}

async function doManualStepRaw() {
  if (!manualPlaying.value) return
  const total = manualSensorCount.value
  if (manualCurrent.value >= total) { manualPlaying.value = false; log('手动播放完成', 'success'); return }
  // 按需加载单帧
  const res = await fetch(`${backend}/api/debug/sessions/${encodeURIComponent(manualFolder.value)}/sensor?offset=${manualCurrent.value}&limit=1`)
  const frames = (await res.json())?.frames || []
  const f = frames[0]
  if (!f) { manualPlaying.value = false; return }
  // 匀速直线: 先喂合成 kinematics, 再发 sensor
  if (straightLineOn.value) {
    await postJson(`${backend}/api/realtime/feed/location`, {
      timestamp_ns: Date.now() * 1_000_000,
      camera: [{ camera_pose: { position: { x: 0, y: 0, z: 1 }, rotation: { qw: 0.7071, qx: 0, qy: 0.7071, qz: 0 } } }],
      car: { kinematics: { velocity: straightLineSpeed.value, steering_angle: 0, wheel_base: 1.5 } },
    })
  }
  forwardSensor(f)
  manualCurrent.value++
  manualTimer = setTimeout(doManualStepRaw, 100)
}

// ════════════════════════════════════════════════════════════
//  通用
// ════════════════════════════════════════════════════════════

async function toggleYolo() {
  yoloOn.value = !yoloOn.value
  try { await postJson(`${backend}/api/realtime/toggle`, { yolo: yoloOn.value }) } catch {}
}

async function toggleRecon() {
  reconOn.value = !reconOn.value
  try { await postJson(`${backend}/api/realtime/toggle`, { reconstruction: reconOn.value }) } catch {}
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
    fetch(`${backend}/api/reconstruction/reset`, { method: 'POST' }).catch(() => {}),
    fetch(`${backend}/api/preprocessing/reset`, { method: 'POST' }).catch(() => {}),
  ])
  clearData()
  seenLoc.clear(); seenDet.clear()
  straightLineT0 = 0
  replayLoaded.value = false; replayLocFrames.value = []; replayDetFrames.value = []
  manualDataStatus.value = 'none'; manualFusionFrames.value = []; manualSensorFrames.value = []; manualLocFrames.value = []
  manualFusionCount.value = 0; manualSensorCount.value = 0; manualLocCount.value = 0
  manualHasFusion.value = false; manualHasSensor.value = false; manualHasLoc.value = false
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
      switch (msg.type) {
        case 'load_started':
          viewerRef.value?.resetScene(); _meshLayers = []
          break
        case 'load_progress':
          if (msg.rebuild?.mesh) {
            _meshLayers.push(msg.rebuild.mesh)
            const merged = viewerRef.value?._mergeLayers(_meshLayers)
            if (merged) viewerRef.value?.addMesh(merged)
            if (msg.rebuild.camera_trail) viewerRef.value?.updateTrail(msg.rebuild.camera_trail)
          }
          break
        case 'load_complete':
          break
        case 'rebuild_complete':
          if (msg.data?.mesh) {
            if (msg.layered) {
              _meshLayers.push(msg.data.mesh)
            } else {
              _meshLayers = [msg.data.mesh]
            }
            const merged = viewerRef.value?._mergeLayers(_meshLayers)
            if (merged) viewerRef.value?.addMesh(merged)
            viewerRef.value?.updateTrail(msg.data.camera_trail)
            meshStats.frames = msg.data.total_frames || 0
            crackList.value = msg.data.cracks || []
            viewerRef.value?.addCracks(msg.data.cracks || [])
            doSave('fusion', msg.data)
            log(`重建完成 mesh=${meshStats.frames}`, 'success')
          }
          break
      }
    } catch { /* ignore */ }
  }
  backendWs.onerror = () => { backendConnected.value = false }
  backendWs.onclose = () => {
    backendConnected.value = false
    if (wsDisposed) return
    if (wsReconnectTimer) clearTimeout(wsReconnectTimer)
    wsReconnectTimer = setTimeout(connectBackendWs, 3000)
  }
}

// ── 被动模式状态轮询 ──
async function passivePoll() {
  if (!running.value) return
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
  wsDisposed = false
  connectBackendWs()
})

onUnmounted(() => {
  wsDisposed = true
  if (wsReconnectTimer) { clearTimeout(wsReconnectTimer); wsReconnectTimer = null }
  if (backendWs) {
    backendWs.onclose = null
    backendWs.close()
  }
  if (pollTimer) clearInterval(pollTimer)
  stopAllTimers()
})
</script>
