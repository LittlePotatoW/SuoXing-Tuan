<!-- ============================================================ -->
<!-- frontend/src/views/MainView.vue                                -->
<!-- 界面一：主界面 — 实时图像 + 位置信息                        -->
<!-- ============================================================ -->
<template>
  <div class="page">
    <div class="image-row">
      <!-- RGB 面板 -->
      <div class="panel" :class="{ active: showRGB }" @click="showRGB = !showRGB">
        <div class="panel-title">RGB 实时图像 {{ showRGB ? '●' : '○' }}</div>
        <div v-if="showRGB && rgbSrc" class="img-wrap">
          <img :src="rgbSrc" class="img-full" />
        </div>
        <div v-else class="img-placeholder">点击开始</div>
      </div>

      <!-- 深度图面板 -->
      <div class="panel" :class="{ active: showDepth }" @click="showDepth = !showDepth">
        <div class="panel-title">深度图预览 {{ showDepth ? '●' : '○' }}</div>
        <canvas v-if="showDepth" ref="depthCanvas" class="img-full" />
        <div v-else class="img-placeholder">点击开始</div>
      </div>
    </div>

    <div class="data-bar">
      <span>位置: X={{ pos.x.toFixed(2) }}  Y={{ pos.y.toFixed(2) }}  H={{ pos.heading.toFixed(1) }}°</span>
      <span class="sep">|</span>
      <span>速度: {{ speed.toFixed(1) }} m/s</span>
      <span class="sep">|</span>
      <span>转向: {{ steering.toFixed(1) }}°</span>
    </div>

    <div class="map-placeholder">
      <span>地图 — GPS 数据接入后显示</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'
import { usePolling } from '@/composables/usePolling'
import { getPosition } from '@/api/vehicle'
import { useVehicleStore } from '@/stores/vehicle'
import { useLatestFrame } from '@/composables/useConnection'

const vehicle = useVehicleStore()
const latestFrame = useLatestFrame()
const pos = ref({ x: 0, y: 0, heading: 0 })
const speed = computed(() => vehicle.speed)
const steering = computed(() => vehicle.steeringAngle)

const showRGB = ref(false)
const showDepth = ref(false)
const rgbSrc = ref('')
const depthCanvas = ref<HTMLCanvasElement | null>(null)
let lastRGBA = 0
let lastDepthA = 0

const { start } = usePolling(async () => {
  try {
    const p = await getPosition()
    pos.value = { x: p.x, y: p.y, heading: p.heading }
    vehicle.updatePosition({ timestamp: p.timestamp, x: p.x, y: p.y, heading: p.heading })
  } catch { /* backend unreachable */ }
}, 1000)

onMounted(() => { start() })

// 最新帧到达时更新显示
watch(latestFrame, (f) => {
  if (!f) return

  // RGB: 跳帧 ~15fps
  if (showRGB.value && f.image) {
    const now = performance.now()
    if (now - lastRGBA > 66) {
      lastRGBA = now
      rgbSrc.value = `data:image/jpeg;base64,${f.image}`
    }
  }

  // 深度: 16-bit PNG → 灰度拉伸 → Canvas
  if (showDepth.value && f.depth_map && depthCanvas.value) {
    const now = performance.now()
    if (now - lastDepthA > 66) {
      lastDepthA = now
      renderDepth(f.depth_map, depthCanvas.value)
    }
  }
})

// 开关关闭时清空
watch(showRGB, (v) => { if (!v) rgbSrc.value = '' })
watch(showDepth, (v) => { if (!v) clearDepthCanvas() })
onUnmounted(() => { rgbSrc.value = ''; clearDepthCanvas() })

function clearDepthCanvas() {
  if (depthCanvas.value) {
    const ctx = depthCanvas.value.getContext('2d')
    if (ctx) ctx.clearRect(0, 0, depthCanvas.value.width, depthCanvas.value.height)
  }
}

async function renderDepth(b64: string, canvas: HTMLCanvasElement) {
  try {
    const img = await b64ToImage(b64)
    canvas.width = img.width
    canvas.height = img.height
    const ctx = canvas.getContext('2d')!
    ctx.drawImage(img, 0, 0)
    // Canvas 自动转 8-bit，已是可见灰度
  } catch { /* ignore */ }
}

function b64ToImage(b64: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = `data:image/png;base64,${b64}`
  })
}
</script>

<style scoped>
.page { display: flex; flex-direction: column; height: 100%; gap: 12px; }
.image-row { display: flex; gap: 12px; flex: 1; min-height: 0; }
.panel { flex: 1; border: 1px solid #ddd; border-radius: 6px; display: flex; flex-direction: column; cursor: pointer; overflow: hidden; }
.panel.active { border-color: #3a7bd5; }
.panel-title { padding: 8px 12px; font-size: 13px; color: #666; border-bottom: 1px solid #eee; background: #fafafa; flex-shrink: 0; }
.img-placeholder { flex: 1; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 14px; }
.img-wrap { flex: 1; display: flex; align-items: center; justify-content: center; background: #000; }
.img-full { width: 100%; height: 100%; object-fit: contain; }
.data-bar { display: flex; gap: 16px; padding: 8px 12px; background: #f9f9f9; border-radius: 4px; font-size: 14px; color: #333; }
.sep { color: #ccc; }
.map-placeholder { height: 200px; border: 1px dashed #ccc; border-radius: 6px; display: flex; align-items: center; justify-content: center; color: #999; font-size: 13px; }
</style>
