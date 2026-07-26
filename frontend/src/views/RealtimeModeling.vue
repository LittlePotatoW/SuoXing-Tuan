<!-- ============================================================ -->
<!-- frontend/src/views/RealtimeModeling.vue                        -->
<!-- 界面二：实时建模 — 3D场景 + 缺陷列表                        -->
<!-- ============================================================ -->
<template>
  <div class="page">
    <div class="top-bar">
      <button v-if="!modeling" class="start-btn" @click="startModeling">开始建模</button>
      <button v-else class="stop-btn" @click="stopModeling">停止建模</button>

      <span v-if="dataActive && !modeling" class="active-tip">● 数据源活跃</span>

      <label class="toggle"><input type="checkbox" v-model="yoloOn" :disabled="modeling" /> YOLO检测</label>
      <label class="toggle"><input type="checkbox" v-model="saveSession" :disabled="modeling" /> 保存Session</label>
      <label class="toggle"><input type="checkbox" v-model="saveReport" :disabled="modeling" /> 保存Report</label>
      <input class="task-input" v-model="taskName" placeholder="任务名" :disabled="modeling" />
      <span class="spacer"></span>
      <span class="frame-count">帧: --/--（待实现）</span>
    </div>

    <div class="main-row">
      <div class="scene-panel">
        <div class="panel-title">3D 场景 (点云 + 检测标注)</div>
        <SceneView ref="sceneRef" />
      </div>

      <div class="defect-panel">
        <div class="panel-title">缺陷列表 ({{ defects.length }})</div>
        <table class="defect-table">
          <thead><tr><th>ID</th><th>类型</th><th>置信度</th><th>位置</th></tr></thead>
          <tbody>
            <tr v-for="(d, idx) in defects" :key="d.id ?? idx" @click="selected = d"
              :class="{ selected: selected?.id === d.id }">
              <td>{{ d.id }}</td>
              <td>{{ d.class_name }}</td>
              <td>{{ (d.confidence * 100).toFixed(0) }}%</td>
              <td>{{ d.center_3d?.map((v: number) => v.toFixed(2)).join(', ') || '-' }}</td>
            </tr>
            <tr v-if="!defects.length"><td colspan="4" class="empty">暂无缺陷</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'  // watch 已注释
import SceneView from '@/components/three/SceneView.vue'
// import { getReconstructionStatus } from '@/api/reconstruction'  // 轮询已注释
import { useConnectionStore } from '@/stores/connection'
import { setModelingActive, useConnection } from '@/composables/useConnection'
import { startSessionSignal, stopSessionSignal } from '@/api/session'
import { useReconstructionWS, type MeshData } from '@/composables/useReconstructionWS'
import { useModeling } from '@/composables/useModeling'
import type { DetectionItem } from '@/types/api'

const connStore = useConnectionStore()
const { connectAll } = useConnection()

const sceneRef = ref<InstanceType<typeof SceneView> | null>(null)
const dataActive = computed(() => connStore.overall === 'connected')
const yoloOn = ref(true)
const saveSession = ref(false)
const saveReport = ref(false)
const taskName = ref('')
const selected = ref<DetectionItem | null>(null)

// const frameCount = ref(0)
// const frameThreshold = ref(30)
const defects = ref<DetectionItem[]>([])
const pointCloudUrl = ref('')

// let statusTimer: ReturnType<typeof setInterval> | null = null
// let fallbackTimer: ReturnType<typeof setInterval> | null = null

// 统一建模生命周期
const { running: modeling, start, stop, setWs } = useModeling({
  yoloEnabled: yoloOn, saveReport, taskName,
})

// WebSocket 驱动的重建结果接收
const onMeshData = (data: MeshData) => { sceneRef.value?.updateMesh(data) }
const onCracks = (cracks: DetectionItem[]) => {
  for (const c of cracks) {
    if (!_isDup(c, defects.value)) defects.value.push(c)
  }
  sceneRef.value?.updateCracks(defects.value)
}
function _isDup(c: DetectionItem, existing: DetectionItem[]): boolean {
  const c3 = c.center_3d
  if (!c3 || c3.length < 3) return false
  for (const e of existing) {
    const e3 = e.center_3d
    if (!e3 || e3.length < 3) continue
    const dx = c3[0] - e3[0]; const dy = c3[1] - e3[1]; const dz = c3[2] - e3[2]
    if (Math.sqrt(dx * dx + dy * dy + dz * dz) < 0.3) return true
  }
  return false
}
const onTrail = (trail: number[][]) => { sceneRef.value?.updateTrail(trail) }
const onMeta = (meta: { point_cloud_url?: string }) => {
  if (meta.point_cloud_url) pointCloudUrl.value = meta.point_cloud_url
}
const { /* connected: wsConnected, */ connect: wsConnect, disconnect: wsDisconnect } =
  useReconstructionWS(onMeshData, onCracks, onTrail, onMeta)
setWs(wsConnect, wsDisconnect)

// ---------- 轮询已注释（待 WS 推送完善后启用）----------
// watch(wsConnected, (v) => {
//   if (v) {
//     if (fallbackTimer) { clearInterval(fallbackTimer); fallbackTimer = null }
//   } else if (modeling.value) {
//     if (!fallbackTimer) fallbackTimer = setInterval(fallbackPoll, 3000)
//   }
// }, { immediate: true })
//
// async function fallbackPoll() {
//   try {
//     const r = await getReconstructionStatus()
//     frameCount.value = r.frame_count
//     frameThreshold.value = r.frame_threshold
//   } catch { /* ignore */ }
// }
//
// async function pollStatus() {
//   try {
//     const st = await getReconstructionStatus()
//     frameCount.value = st.frame_count
//     frameThreshold.value = st.frame_threshold
//   } catch { /* backend unreachable */ }
// }

async function startModeling() {
  await start()
  if (saveSession.value) {
    try { await startSessionSignal(taskName.value) } catch { /* ignore */ }
  }
  if (connStore.overall !== 'connected') connectAll()
  setModelingActive(true)
  // frameCount.value = 0
  defects.value = []
  pointCloudUrl.value = ''
  selected.value = null
  // statusTimer = setInterval(pollStatus, 2000)
}

async function stopModeling() {
  setModelingActive(false)
  // if (statusTimer) { clearInterval(statusTimer); statusTimer = null }
  // if (fallbackTimer) { clearInterval(fallbackTimer); fallbackTimer = null }
  if (saveSession.value) {
    try { await stopSessionSignal() } catch { /* ignore */ }
  }
  await stop()
}

onUnmounted(() => {
  setModelingActive(false)
  // if (statusTimer) { clearInterval(statusTimer); statusTimer = null }
  // if (fallbackTimer) { clearInterval(fallbackTimer); fallbackTimer = null }
  if (saveSession.value) {
    try { stopSessionSignal() } catch { /* ignore */ }
  }
  stop()
})
</script>

<style scoped>
.page { display: flex; flex-direction: column; height: 100%; }
.main-row { display: flex; gap: 12px; flex: 1; min-height: 0; }
.scene-panel { flex: 1; border: 1px solid #ddd; border-radius: 6px; display: flex; flex-direction: column; overflow: hidden; }
.defect-panel { width: 280px; border: 1px solid #ddd; border-radius: 6px; display: flex; flex-direction: column; overflow: auto; }
.panel-title { padding: 8px 12px; font-size: 13px; color: #666; border-bottom: 1px solid #eee; background: #fafafa; flex-shrink: 0; }
.defect-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.defect-table th { background: #f5f5f5; padding: 6px; text-align: left; border-bottom: 2px solid #ddd; }
.defect-table td { padding: 5px 6px; border-bottom: 1px solid #eee; cursor: pointer; }
.defect-table tr:hover { background: #f0f4ff; }
.defect-table tr.selected { background: #dbeafe; }
.empty { color: #aaa; text-align: center; }
.top-bar { display: flex; align-items: center; gap: 16px; padding: 8px 12px; background: #f9f9f9; border-bottom: 1px solid #eee; font-size: 13px; margin-bottom: 12px; }
.frame-count { color: #888; }
.start-btn { padding: 5px 20px; background: #27ae60; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.start-btn:hover { background: #219a52; }
.stop-btn { padding: 5px 20px; background: #e74c3c; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.stop-btn:hover { background: #c0392b; }
.active-tip { color: #27ae60; font-size: 12px; }
.spacer { flex: 1; }
</style>
