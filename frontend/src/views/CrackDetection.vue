<!-- ============================================================ -->
<!-- frontend/src/views/CrackDetection.vue                           -->
<!-- 裂缝检测页面 — 图片上传 + YOLO 推理 + 检测结果展示               -->
<!-- ============================================================ -->

<template>
  <div style="display: flex; flex-direction: column; height: 100%">
    <!-- 顶部操作栏 -->
    <div style="display: flex; gap: 16px; padding: 8px 12px; align-items: center; flex-wrap: wrap">
      <button :disabled="!canInfer" @click="onInfer">推理</button>
      <span v-if="inferring" style="color: #888">推理中...</span>
      <span v-if="error" style="color: #e74c3c; font-weight: bold">{{ error }}</span>
    </div>

    <hr style="margin: 0; border-color: #333" />

    <!-- 主体 -->
    <div style="display: flex; flex: 1; overflow: hidden">
      <DragDropZone
        :connected="connected"
        :imageSrc="imageSrc"
        :detections="detections"
        @fileDropped="onFileDropped"
      />
      <div style="width: 280px; min-width: 240px">
        <ResultPanel
          :imageLoaded="!!imageSrc"
          :detections="detections"
          :inferring="inferring"
          :inferenceTimeMs="inferenceTimeMs"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { runInference } from '../services/apiClient'
import DragDropZone from '../components/DragDropZone.vue'
import ResultPanel from '../components/ResultPanel.vue'

defineProps<{ connected: boolean }>()

const imageSrc = ref<string | null>(null)
const selectedFile = ref<File | null>(null)
const detections = ref<{ class_name: string; confidence: number; bbox: number[] }[]>([])
const inferenceTimeMs = ref(0)
const inferring = ref(false)
const error = ref('')

const canInfer = computed(() => !inferring.value && !!selectedFile.value)

function onFileDropped(file: File) {
  selectedFile.value = file
  if (imageSrc.value) URL.revokeObjectURL(imageSrc.value)
  imageSrc.value = URL.createObjectURL(file)
  detections.value = []
  error.value = ''
}

async function onInfer() {
  if (!selectedFile.value) return
  error.value = ''
  inferring.value = true
  try {
    const result = await runInference(selectedFile.value)
    detections.value = result.detections
    inferenceTimeMs.value = result.inference_time_ms
  } catch (e) {
    error.value = '推理失败: ' + (e as Error).message
  } finally {
    inferring.value = false
  }
}
</script>
