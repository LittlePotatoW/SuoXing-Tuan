<!-- ============================================================ -->
<!-- frontend/src/components/three/PointCloudView.vue              -->
<!-- 点云灰度深度图 — Canvas 2D 百分位灰度映射                   -->
<!-- ============================================================ -->
<template>
  <div ref="containerRef" class="pc-container">
    <canvas ref="canvasRef" />
    <div class="pc-info">
      <div>点数: {{ pointCount.toLocaleString() }}</div>
      <div>Z: {{ zNear.toFixed(2) }} ~ {{ zFar.toFixed(2) }}</div>
    </div>
    <div class="pc-bar">
      <span class="pc-bar-label">近</span>
      <div class="pc-bar-gradient" />
      <span class="pc-bar-label">远</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const containerRef = ref<HTMLElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const pointCount = ref(0)
const zNear = ref(0)
const zFar = ref(0)

let disposed = false
let resizeObs: ResizeObserver | null = null
let lastPoints: number[] = []

onMounted(() => {
  resizeObs = new ResizeObserver(() => {
    syncSize()
    if (lastPoints.length > 0) drawGrayscale(lastPoints)
  })
  if (containerRef.value) resizeObs.observe(containerRef.value)
})

onUnmounted(() => {
  disposed = true
  resizeObs?.disconnect()
})

function syncSize(): void {
  const canvas = canvasRef.value
  const container = containerRef.value
  if (!canvas || !container) return
  const dpr = window.devicePixelRatio || 1
  const w = Math.round(container.clientWidth * dpr)
  const h = Math.round(container.clientHeight * dpr)
  if (canvas.width !== w || canvas.height !== h) {
    canvas.width = w
    canvas.height = h
  }
}

// 百分位灰度渲染
function drawGrayscale(flatArr: number[]): void {
  const canvas = canvasRef.value
  if (!canvas || flatArr.length < 3) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const dpr = window.devicePixelRatio || 1
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

  const W = Math.round(canvas.width / dpr)
  const H = Math.round(canvas.height / dpr)
  const N = flatArr.length / 3
  const pad = 4

  // 收集 Z 值 + XY 范围
  const zArr = new Float64Array(N)
  let xMin = Infinity, xMax = -Infinity
  let yMin = Infinity, yMax = -Infinity
  for (let i = 0, j = 0; i < flatArr.length; i += 3, j++) {
    const x = flatArr[i]
    const y = flatArr[i + 1]
    if (x < xMin) xMin = x; if (x > xMax) xMax = x
    if (y < yMin) yMin = y; if (y > yMax) yMax = y
    zArr[j] = flatArr[i + 2]
  }

  const sorted = zArr.slice().sort((a, b) => a - b)
  const p2 = sorted[Math.floor(N * 0.02)]
  const p98 = sorted[Math.floor(N * 0.98)]
  zNear.value = p2
  zFar.value = p98
  pointCount.value = N

  const xSpan = xMax - xMin || 1
  const ySpan = yMax - yMin || 1
  const zSpan = p98 - p2 || 1
  const scale = Math.min((W - pad * 2) / xSpan, (H - pad * 2) / ySpan)
  const ox = (W - xSpan * scale) / 2
  const oy = (H - ySpan * scale) / 2

  ctx.fillStyle = '#000'
  ctx.fillRect(0, 0, W, H)

  const imageData = ctx.createImageData(W, H)
  const buf = imageData.data

  for (let i = 0; i < flatArr.length; i += 3) {
    const px = Math.round((flatArr[i] - xMin) * scale + ox)
    const py = Math.round((flatArr[i + 1] - yMin) * scale + oy)
    const t = (flatArr[i + 2] - p2) / zSpan
    const g = 255 - Math.round(Math.max(0, Math.min(1, t)) * 255)

    if (px >= 0 && px < W && py >= 0 && py < H) {
      const idx = (py * W + px) * 4
      buf[idx] = buf[idx + 1] = buf[idx + 2] = g
      buf[idx + 3] = 255
    }
  }
  ctx.putImageData(imageData, 0, 0)
}

function update(flatArr: number[]): void {
  if (disposed || !flatArr || flatArr.length < 3) return
  lastPoints = flatArr
  drawGrayscale(flatArr)
}

function reset(): void {
  lastPoints = []
  pointCount.value = 0
  const canvas = canvasRef.value
  if (canvas) {
    const ctx = canvas.getContext('2d')
    if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height)
  }
}

defineExpose({ update, reset })
</script>

<style scoped>
.pc-container {
  width: 100%; height: 100%; position: relative; background: #1a1a1a;
}
canvas { display: block; width: 100%; height: 100%; }
.pc-info {
  position: absolute; top: 6px; left: 6px;
  background: rgba(0,0,0,0.7); padding: 2px 8px;
  font-size: 10px; color: #aaa; border-radius: 3px;
  pointer-events: none; line-height: 1.5;
}
.pc-bar {
  position: absolute; right: 8px; top: 8px; bottom: 8px;
  width: 18px; display: flex; flex-direction: column; align-items: center;
}
.pc-bar-label { font-size: 8px; color: #aaa; }
.pc-bar-gradient {
  flex: 1; width: 10px;
  background: linear-gradient(to bottom, #fff, #000);
  border: 1px solid #444; border-radius: 3px;
}
</style>
