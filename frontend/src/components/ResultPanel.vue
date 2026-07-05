<!-- ============================================================ -->
<!-- frontend/src/components/ResultPanel.vue                         -->
<!-- 检测结果面板 — 表格展示后端返回的缺陷检测结果                     -->
<!-- ============================================================ -->

<template>
  <div style="padding: 12px; overflow-y: auto">
    <h3 style="margin: 0 0 8px 0; font-size: 14px">检测结果</h3>

    <div v-if="detections.length === 0" style="color: #888">
      {{ imageLoaded ? '未检测到缺陷' : '请加载图片' }}
    </div>

    <table v-else style="width: 100%; border-collapse: collapse">
      <thead>
        <tr><th>#</th><th>类别</th><th>置信度</th><th>位置</th></tr>
      </thead>
      <tbody>
        <tr v-for="(d, i) in detections" :key="i">
          <td>{{ i + 1 }}</td>
          <td>
            <span :style="{ background: getColor(d.class_name), color: '#fff', padding: '1px 6px', fontSize: '11px' }">
              {{ d.class_name }}
            </span>
          </td>
          <td>{{ (d.confidence * 100).toFixed(1) }}%</td>
          <td style="font-size: 11px">{{ d.bbox.map((v: number) => Math.round(v)).join(', ') }}</td>
        </tr>
      </tbody>
    </table>

    <div v-if="inferenceTimeMs > 0" style="margin-top: 8px; font-size: 12px; color: #888">
      推理耗时: {{ inferenceTimeMs }}ms
    </div>
  </div>
</template>

<script setup lang="ts">
import { DETECTION_COLORS } from '../constants/colors'

defineProps<{
  imageLoaded: boolean
  detections: { class_name: string; confidence: number; bbox: number[] }[]
  inferenceTimeMs: number
}>()

function getColor(className: string) {
  return DETECTION_COLORS[className] ?? DETECTION_COLORS.default
}
</script>
