<!-- ============================================================ -->
<!-- frontend/src/views/ReplayModeling.vue                          -->
<!-- 界面三：回放建模 — 选 session → 全速重建                    -->
<!-- ============================================================ -->
<template>
  <div class="page">
    <div class="toolbar">
      <select class="sel" v-model="selectedSession" @focus="fetchSessions">
        <option value="">选择 Session...</option>
        <option v-for="s in sessions" :key="s" :value="s">{{ s }}</option>
      </select>
      <button class="btn" :disabled="!selectedSession || replaying" @click="startReplay">
        {{ replaying ? '回放中...' : '开始回放重建' }}
      </button>
    </div>

    <div class="main-row">
      <div class="scene-panel">
        <div class="panel-title">3D 场景 (重建结果)</div>
        <SceneView ref="sceneRef" />
      </div>

      <div class="defect-panel">
        <div class="panel-title">缺陷列表 ({{ defects.length }})</div>
        <table class="defect-table">
          <thead><tr><th>ID</th><th>类型</th><th>置信度</th><th>位置</th></tr></thead>
          <tbody>
            <tr v-for="d in defects" :key="d.id" @click="selected = d"
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

    <div v-if="replaying" class="progress-bar">
      <div class="progress-label">已发送: {{ sentFrames }}/{{ totalFrames }} 帧</div>
      <div class="progress-track"><div class="progress-fill" :style="{ width: (totalFrames ? (sentFrames / totalFrames) * 100 : 0) + '%' }"></div></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import SceneView from '@/components/three/SceneView.vue'
import { resetReconstruction } from '@/api/reconstruction'
import { resetEstimator, postTelemetry, postFrame } from '@/api/vehicle'
import { loadSession } from '@/services/data-loader/local-loader'
import type { Session } from '@/services/data-loader/local-loader'
import { listSessions } from '@/api/session'
import { useReconstructionWS, type MeshData } from '@/composables/useReconstructionWS'
import { reconDefaults } from '@/config/defaults'
import type { DetectionItem } from '@/types/api'

const sceneRef = ref<InstanceType<typeof SceneView> | null>(null)
const sessions = ref<string[]>([])
const selectedSession = ref('')
const replaying = ref(false)
const sentFrames = ref(0)
const totalFrames = ref(0)
const selected = ref<DetectionItem | null>(null)
const defects = ref<DetectionItem[]>([])

// WebSocket 驱动重建结果接收
const onMeshData = (data: MeshData) => {
  sceneRef.value?.updateMesh(data)
}
const onCracks = (cracks: DetectionItem[]) => {
  defects.value = cracks
  sceneRef.value?.updateCracks(cracks)
}
const { connect: wsConnect, disconnect: wsDisconnect } =
  useReconstructionWS(onMeshData, onCracks)

async function fetchSessions() {
  try {
    const list = await listSessions()
    sessions.value = list.map((s) => s.name)
  } catch (e) { console.warn('获取 session 列表失败:', e) }
}

onMounted(() => { fetchSessions() })

async function startReplay() {
  if (!selectedSession.value) return

  let session: Session
  try {
    session = await loadSession(selectedSession.value)
  } catch {
    return
  }

  replaying.value = true
  sentFrames.value = 0
  totalFrames.value = session.frames.length
  defects.value = []
  selected.value = null

  try {
    await resetReconstruction({
      mode: reconDefaults.mode, frame_threshold: reconDefaults.frame_threshold, voxel_size: reconDefaults.voxel_size,
    })
    await resetEstimator({ mode: 'bicycle' })
  } catch (e) { console.warn('reset reconstruction failed:', e) }

  // 先连 WebSocket 再发数据，避免漏掉早期的 rebuild_complete
  wsConnect()

  for (const t of session.telemetryList) {
    try { await postTelemetry(t) } catch { /* ignore */ }
  }

  for (const fi of session.frames) {
    try {
      const frame = await session.readFrame(fi.id)
      await postFrame(frame)
      sentFrames.value++
    } catch { /* ignore */ }
  }
}

</script>

<style scoped>
.page { display: flex; flex-direction: column; height: 100%; gap: 0; }
.toolbar { display: flex; gap: 10px; padding: 8px 0; align-items: center; }
.sel { padding: 5px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; min-width: 160px; }
.btn { padding: 5px 16px; background: #3a7bd5; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn:disabled { background: #aaa; cursor: default; }
.main-row { display: flex; gap: 12px; flex: 1; min-height: 0; }
.scene-panel { flex: 1; border: 1px solid #ddd; border-radius: 6px; display: flex; flex-direction: column; overflow: hidden; }
.defect-panel { width: 280px; border: 1px solid #ddd; border-radius: 6px; display: flex; flex-direction: column; overflow: auto; }
.panel-title { padding: 8px 12px; font-size: 13px; color: #666; border-bottom: 1px solid #eee; background: #fafafa; flex-shrink: 0; }
.defect-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.defect-table th { background: #f5f5f5; padding: 6px; text-align: left; border-bottom: 2px solid #ddd; }
.defect-table td { padding: 5px 6px; border-bottom: 1px solid #eee; cursor: pointer; }
.defect-table tr:hover { background: #f0f4ff; }
.defect-table tr.selected { background: #dbeafe; }
.empty { color: #aaa; text-align: center; font-size: 12px; padding: 10px; }
.preview-mini { padding: 8px; border-top: 1px solid #eee; }
.preview-title { font-size: 12px; color: #666; margin-bottom: 4px; }
.preview-placeholder { height: 100px; background: #f5f5f5; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 12px; border-radius: 4px; }
.progress-bar { padding: 10px 0; }
.progress-label { font-size: 12px; color: #666; margin-bottom: 4px; }
.progress-track { height: 6px; background: #eee; border-radius: 3px; }
.progress-fill { height: 100%; background: #3a7bd5; border-radius: 3px; transition: width 0.3s; }
</style>
