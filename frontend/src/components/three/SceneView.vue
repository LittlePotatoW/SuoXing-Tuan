<!-- ============================================================ -->
<!-- frontend/src/components/three/SceneView.vue                   -->
<!-- Three.js 3D 场景 Vue 壳：挂载画布 + 对外暴露方法             -->
<!-- ============================================================ -->
<template>
  <div ref="containerRef" class="scene-container">
    <canvas ref="canvasRef" />
    <div class="stats-overlay" v-if="pointCount > 0">
      点数: {{ pointCount.toLocaleString() }} | 缺陷: {{ crackCount }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { SceneManager } from '@/services/renderer/three-scene'
import { addToScene, type MeshData } from '@/services/renderer/point-cloud'
import { addCracks, resetCrackCache } from '@/services/renderer/annotations'
import type { DetectionItem } from '@/types/api'

const containerRef = ref<HTMLElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const pointCount = ref(0)
const crackCount = ref(0)

let sceneMgr: SceneManager | null = null
let resizeObs: ResizeObserver | null = null

onMounted(() => {
  const canvas = canvasRef.value
  const container = containerRef.value
  if (!canvas || !container) return

  canvas.width = container.clientWidth
  canvas.height = container.clientHeight

  sceneMgr = new SceneManager(canvas)

  resizeObs = new ResizeObserver(() => {
    if (!containerRef.value || !sceneMgr) return
    const w = containerRef.value.clientWidth
    const h = containerRef.value.clientHeight
    canvas.width = w
    canvas.height = h
    sceneMgr.resize(w, h)
  })
  resizeObs.observe(container)
})

onUnmounted(() => {
  resizeObs?.disconnect()
  sceneMgr?.dispose()
  sceneMgr = null
})

function updateMesh(data: MeshData): void {
  if (!sceneMgr) return
  console.log('[SceneView] updateMesh called, verts:', data.vertex_count, 'faces:', data.face_count)
  addToScene(data, sceneMgr)
  pointCount.value = data.vertex_count
}

function updateCracks(cracks: DetectionItem[]): void {
  if (!sceneMgr) return
  try {
    addCracks(cracks, sceneMgr)
  } catch (e) { console.warn('addCracks failed:', e) }

  crackCount.value = cracks.length
}

function resetScene(): void {
  sceneMgr?.resetScene()
  resetCrackCache()
  pointCount.value = 0
  crackCount.value = 0
}

defineExpose({ updateMesh, updateCracks, resetScene })
</script>

<style scoped>
.scene-container {
  width: 100%; height: 100%; position: relative; overflow: hidden;
}
canvas { display: block; }
.stats-overlay {
  position: absolute; top: 8px; right: 8px;
  background: rgba(0,0,0,0.7); padding: 4px 10px;
  font-size: 12px; color: #ccc; border-radius: 4px;
  pointer-events: none;
}
</style>
