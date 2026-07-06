<!-- ============================================================ -->
<!-- frontend/src/components/ImageViewer.vue                         -->
<!-- 图像显示 — Canvas 渲染图像 + 检测框叠加                          -->
<!-- ============================================================ -->

<template>
  <canvas ref="canvasRef" style="max-width: 100%; max-height: 100%" />
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { DETECTION_COLORS } from '../constants/colors'

const props = defineProps<{
  imageSrc: string
  detections: { class_name: string; confidence: number; bbox: number[] }[]
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
let rafId = 0
let currentSrc = ''

function getColor(className: string) {
  return DETECTION_COLORS[className] ?? DETECTION_COLORS.default
}

function draw() {
  const canvas = canvasRef.value
  if (!canvas) return

  const img = new Image()
  const src = props.imageSrc
  currentSrc = src

  img.onload = () => {
    if (props.imageSrc !== currentSrc) return  // 防竞态

    const dpr = window.devicePixelRatio || 1
    canvas.width = img.naturalWidth * dpr
    canvas.height = img.naturalHeight * dpr
    canvas.style.width = img.naturalWidth + 'px'
    canvas.style.height = img.naturalHeight + 'px'

    const ctx = canvas.getContext('2d')!
    ctx.scale(dpr, dpr)
    ctx.drawImage(img, 0, 0)

    for (const d of props.detections) {
      const color = getColor(d.class_name)
      const [x1, y1, x2, y2] = d.bbox

      ctx.strokeStyle = color
      ctx.lineWidth = 2
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1)

      const label = `${d.class_name} ${(d.confidence * 100).toFixed(0)}%`
      ctx.font = '14px monospace'
      const tw = ctx.measureText(label).width
      const labelH = 20
      const labelY = y1 < labelH ? y1 + labelH : y1  // 顶部溢出时画在框内

      ctx.fillStyle = color
      ctx.fillRect(x1, labelY - labelH, tw + 8, labelH)
      ctx.fillStyle = '#fff'
      ctx.fillText(label, x1 + 4, labelY - 6)
    }
  }

  img.onerror = () => {
    console.warn('ImageViewer: failed to load image')
  }

  img.src = src
}

onMounted(draw)

watch(() => [props.imageSrc, props.detections], () => {
  cancelAnimationFrame(rafId)
  rafId = requestAnimationFrame(draw)
})

onUnmounted(() => cancelAnimationFrame(rafId))
</script>
