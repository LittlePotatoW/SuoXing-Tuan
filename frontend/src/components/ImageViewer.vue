<!-- ============================================================ -->
<!-- frontend/src/components/ImageViewer.vue                         -->
<!-- 图像显示 — Canvas 渲染图像 + 检测框叠加，纯展示                  -->
<!-- ============================================================ -->

<template>
  <canvas ref="canvasRef" style="max-width: 100%; max-height: 100%" />
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { DETECTION_COLORS } from '../constants/colors'

const props = defineProps<{
  imageSrc: string
  detections: { class_name: string; confidence: number; bbox: number[] }[]
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)

function getColor(className: string) {
  return DETECTION_COLORS[className] ?? DETECTION_COLORS.default
}

function draw() {
  const canvas = canvasRef.value
  if (!canvas) return
  const img = new Image()
  img.onload = () => {
    canvas.width = img.naturalWidth
    canvas.height = img.naturalHeight
    const ctx = canvas.getContext('2d')!
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
      ctx.fillStyle = color
      ctx.fillRect(x1, y1 - 20, tw + 8, 20)
      ctx.fillStyle = '#fff'
      ctx.fillText(label, x1 + 4, y1 - 6)
    }
  }
  img.src = props.imageSrc
}

onMounted(draw)
watch(() => [props.imageSrc, props.detections], draw, { deep: true })
</script>
