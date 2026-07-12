<!-- ============================================================ -->
<!-- frontend/src/views/ReconstructionView.vue                         -->
<!-- 3D 重建页 — 场景加载 + 3D 查看器                                  -->
<!-- ============================================================ -->

<template>
  <div style="display: flex; flex-direction: column; height: 100%">
    <!-- 控制栏 -->
    <div style="display: flex; gap: 12px; padding: 8px 12px; align-items: center; flex-wrap: wrap; border-bottom: 1px solid #333">
      <label style="color: #888; font-size: 12px">场景路径:</label>
      <input v-model="scenePath" placeholder="data/test_scene" style="width: 180px; background: #2a2a2a; color: #ccc; border: 1px solid #555; padding: 3px 6px; font-size: 12px" />
      <button @click="loadScene" :disabled="loading">加载</button>
      <button @click="sendControl('pause')" :disabled="!loaded">暂停</button>
      <button @click="sendControl('resume')" :disabled="!loaded">继续</button>
      <button @click="sendControl('stop')" :disabled="!loaded">停止</button>
      <span style="font-size: 12px; color: #888; margin-left: 8px">
        帧: {{ currentFrame }} / {{ totalFrames }}
      </span>
    </div>

    <!-- 3D 查看器 -->
    <div style="flex: 1; position: relative">
      <ReconstructionViewer ref="viewerRef" />
      <!-- 统计面板 -->
      <div style="position: absolute; top: 8px; right: 8px; background: rgba(0,0,0,0.7); padding: 8px 12px; font-size: 12px; color: #ccc; border-radius: 4px">
        <div>帧数: {{ stats.total_frames }}</div>
        <div>点数: {{ stats.total_points?.toLocaleString() }}</div>
        <div>顶点: {{ stats.vertex_count?.toLocaleString() }}</div>
        <div>三角面: {{ stats.face_count?.toLocaleString() }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onUnmounted } from 'vue'
import ReconstructionViewer from '../components/ReconstructionViewer.vue'
import { getBaseUrl } from '../services/apiClient'

const viewerRef = ref<InstanceType<typeof ReconstructionViewer> | null>(null)
const scenePath = ref('test_data/test_scene')
const loading = ref(false)
const loaded = ref(false)
const currentFrame = ref(0)
const totalFrames = ref(0)
const stats = reactive({ total_frames: 0, total_points: 0, vertex_count: 0, face_count: 0 })
const error = ref('')

let ws: WebSocket | null = null

function wsUrl() {
  const base = getBaseUrl().replace('http', 'ws')
  return `${base}/api/reconstruction/ws`
}

async function loadScene() {
  loading.value = true
  const base = getBaseUrl()

  // 先清空场景（不等 WS 消息，避免时序问题）
  viewerRef.value?.resetScene()

  // 关闭旧 WebSocket 并创建新连接
  if (ws) { ws.onmessage = null; ws.onerror = null; ws.onclose = null; ws.close() }
  ws = new WebSocket(wsUrl())
  ws.onerror = () => { error.value = 'WebSocket 连接失败，请检查后端是否启动' }
  ws.onclose = () => { error.value = 'WebSocket 已断开' }
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data)
    if (!msg || !msg.type) return
    switch (msg.type) {
      case 'load_started':
        totalFrames.value = msg.total_frames ?? 0
        break
      case 'load_progress':
        currentFrame.value = msg.current_frame ?? 0
        totalFrames.value = msg.total_frames ?? 0
        if (msg.rebuild) {
          stats.total_frames = msg.rebuild.total_frames ?? 0
          stats.total_points = msg.rebuild.total_points ?? 0
          stats.vertex_count = msg.rebuild.mesh?.vertex_count || 0
          stats.face_count = msg.rebuild.mesh?.face_count || 0
          if (msg.rebuild.mesh) viewerRef.value?.addMesh(msg.rebuild.mesh)
          if (msg.rebuild.camera_trail) viewerRef.value?.updateTrail(msg.rebuild.camera_trail)
        }
        break
      case 'rebuild_complete':
        const d = msg.data
        if (d) {
          stats.total_frames = d.total_frames ?? 0
          stats.total_points = d.total_points ?? 0
          stats.vertex_count = d.mesh?.vertex_count || 0
          stats.face_count = d.mesh?.face_count || 0
          if (d.mesh) viewerRef.value?.addMesh(d.mesh)
          if (d.camera_trail) viewerRef.value?.updateTrail(d.camera_trail)
        }
        break
      case 'load_complete':
        loading.value = false
        break
    }
  }

  try {
    const res = await fetch(`${base}/api/reconstruction/load`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scene_path: scenePath.value, interval: 0.05 }),
    })
    if (res.ok) {
      loaded.value = true
    }
  } catch (e) {
    loading.value = false
    alert('加载失败: ' + (e as Error).message)
  }
}

async function sendControl(action: string) {
  if (action === 'stop') { loaded.value = false; currentFrame.value = 0 }
  const base = getBaseUrl()
  await fetch(`${base}/api/reconstruction/control`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action }),
  })
}

onUnmounted(() => {
  if (ws) { ws.onmessage = null; ws.close(); ws = null }
})
</script>
