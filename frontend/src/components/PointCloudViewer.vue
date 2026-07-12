<!-- ============================================================ -->
<!-- frontend/src/components/PointCloudViewer.vue                    -->
<!-- 点云灰度深度图 — Canvas 2D 渲染，百分位灰度映射                    -->
<!-- ============================================================ -->

<template>
  <div ref="containerRef" style="width: 100%; height: 100%; position: relative; background: #1a1a1a">
    <canvas ref="canvasRef" style="width: 100%; height: 100%" />
    <!-- 叠加信息 -->
    <div style="position:absolute;top:6px;left:6px;background:rgba(0,0,0,0.7);padding:2px 8px;font-size:10px;color:#aaa;border-radius:3px;pointer-events:none;line-height:1.5">
      <div>点数: {{ pointCount.toLocaleString() }}</div>
      <div>Z: {{ zP2.toFixed(2) }} ~ {{ zP98.toFixed(2) }}</div>
    </div>
    <!-- 色阶条 -->
    <div style="position:absolute;right:8px;top:8px;bottom:8px;width:18px;display:flex;flex-direction:column;align-items:center">
      <span style="font-size:8px;color:#aaa;margin-bottom:2px">近</span>
      <div style="flex:1;width:10px;background:linear-gradient(to bottom, #fff, #000);border:1px solid #444;border-radius:3px" />
      <span style="font-size:8px;color:#aaa;margin-top:2px">远</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const containerRef = ref<HTMLElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const pointCount = ref(0)
const zP2 = ref(0)
const zP98 = ref(0)

let disposed = false
let resizeObs: ResizeObserver | null = null

onMounted(() => {
  if (!containerRef.value || !canvasRef.value) return
  syncCanvasSize()

  resizeObs = new ResizeObserver(() => {
    syncCanvasSize()
    if (lastPoints.length > 0) drawGrayscale(lastPoints)
  })
  resizeObs.observe(containerRef.value)
})

onUnmounted(() => {
  disposed = true
  resizeObs?.disconnect()
})

function syncCanvasSize() {
  const canvas = canvasRef.value
  const container = containerRef.value
  if (!canvas || !container) return
  const w = container.clientWidth
  const h = container.clientHeight
  if (canvas.width !== w || canvas.height !== h) {
    canvas.width = w
    canvas.height = h
  }
}

// ── 缓存最近一次点云 ──
let lastPoints: number[] = []

function drawGrayscale(points: number[]) {
  const canvas = canvasRef.value
  if (!canvas || points.length < 3) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const W = canvas.width
  const H = canvas.height
  const N = points.length / 3
  const pad = 4

  // 1. 收集 Z 值 → 计算百分位
  const zArr = new Float64Array(N)
  let xMin = Infinity, xMax = -Infinity
  let yMin = Infinity, yMax = -Infinity
  for (let i = 0, j = 0; i < points.length; i += 3, j++) {
    const x = points[i]
    const y = points[i + 1]
    if (x < xMin) xMin = x
    if (x > xMax) xMax = x
    if (y < yMin) yMin = y
    if (y > yMax) yMax = y
    zArr[j] = points[i + 2]
  }
  const sorted = zArr.slice().sort((a, b) => a - b)
  const p2 = sorted[Math.floor(N * 0.02)]   // 2% 百分位 → 白（近）
  const p98 = sorted[Math.floor(N * 0.98)]  // 98% 百分位 → 黑（远）

  zP2.value = p2
  zP98.value = p98
  pointCount.value = N

  // 2. 缩放（XY 等比）
  const xSpan = xMax - xMin || 1
  const ySpan = yMax - yMin || 1
  const zSpan = p98 - p2 || 1
  const scale = Math.min((W - pad * 2) / xSpan, (H - pad * 2) / ySpan)
  const ox = (W - xSpan * scale) / 2
  const oy = (H - ySpan * scale) / 2

  // 3. 渲染
  ctx.fillStyle = '#000'
  ctx.fillRect(0, 0, W, H)

  const imageData = ctx.createImageData(W, H)
  const buf = imageData.data

  for (let i = 0; i < points.length; i += 3) {
    const px = Math.round((points[i] - xMin) * scale + ox)
    const py = Math.round((points[i + 1] - yMin) * scale + oy)
    // 百分位灰度: p2→白(255), p98→黑(0), 超出范围截断
    const z = points[i + 2]
    const t = (z - p2) / zSpan
    const g = 255 - Math.round(Math.max(0, Math.min(1, t)) * 255)

    if (px >= 0 && px < W && py >= 0 && py < H) {
      const idx = (py * W + px) * 4
      buf[idx] = buf[idx + 1] = buf[idx + 2] = g
      buf[idx + 3] = 255
    }
  }

  ctx.putImageData(imageData, 0, 0)
}

// ── 外部方法 ──

function updatePointCloud(points: number[]) {
  if (disposed || !points || points.length < 3) return
  lastPoints = points
  drawGrayscale(points)
}

function resetView() {
  lastPoints = []
  pointCount.value = 0
  zP2.value = 0
  zP98.value = 0
  const canvas = canvasRef.value
  if (canvas) {
    const ctx = canvas.getContext('2d')
    if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height)
  }
}

defineExpose({ updatePointCloud, resetView })
</script>
