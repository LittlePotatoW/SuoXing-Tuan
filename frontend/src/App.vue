<!-- ============================================================ -->
<!-- frontend/src/App.vue                                            -->
<!-- 根组件 — 布局 + 全局状态，委托子组件展示                          -->
<!-- ============================================================ -->

<template>
  <div style="display: flex; flex-direction: column; height: 100vh; font-family: monospace; font-size: 13px">

    <!-- 顶部工具栏 -->
    <div style="display: flex; gap: 16px; padding: 8px 12px; align-items: center; flex-wrap: wrap">
      <ConnectionBar :connected="connected" @connect="onConnect" @disconnect="onDisconnect" />
      <span>|</span>
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
import { setHost, healthCheck, runInference } from './services/apiClient'
import ConnectionBar from './components/ConnectionBar.vue'
import DragDropZone from './components/DragDropZone.vue'
import ResultPanel from './components/ResultPanel.vue'

const connected = ref(false)
const imageSrc = ref<string | null>(null)
const selectedFile = ref<File | null>(null)
const detections = ref<{ class_name: string; confidence: number; bbox: number[] }[]>([])
const inferenceTimeMs = ref(0)
const inferring = ref(false)
const error = ref('')

const canInfer = computed(() => connected.value && !!selectedFile.value && !inferring.value)

async function onConnect(host: string, port: number) {
  error.value = ''
  setHost(host, port)
  try {
    await healthCheck()
    connected.value = true
  } catch (e) {
    error.value = '连接失败: ' + (e as Error).message
  }
}

function onDisconnect() {
  connected.value = false
  detections.value = []
  error.value = ''
}

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
