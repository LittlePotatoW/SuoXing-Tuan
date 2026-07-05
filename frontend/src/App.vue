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
      <ModelSelector :connected="connected" @modelLoaded="onModelLoaded" />
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
          :inferenceTimeMs="inferenceTimeMs"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// ============================================================
// App.vue — 持有所有状态，通过 props 下传，通过事件接收
// 不使用 Pinia 等状态管理库
// ============================================================
import { ref } from 'vue'
import { setHost, healthCheck, runInference } from './services/apiClient'
import ConnectionBar from './components/ConnectionBar.vue'
import ModelSelector from './components/ModelSelector.vue'
import DragDropZone from './components/DragDropZone.vue'
import ResultPanel from './components/ResultPanel.vue'

const connected = ref(false)
const imageSrc = ref<string | null>(null)
const detections = ref<{ class_name: string; confidence: number; bbox: number[] }[]>([])
const inferenceTimeMs = ref(0)

async function onConnect(host: string, port: number) {
  setHost(host, port)
  await healthCheck()
  connected.value = true
}

function onDisconnect() {
  connected.value = false
}

function onModelLoaded(_name: string) {
  // 模型已加载到后端，后续推理自动使用
}

async function onFileDropped(file: File) {
  imageSrc.value = URL.createObjectURL(file)

  if (!connected.value) {
    detections.value = []
    return
  }

  const result = await runInference(file)
  detections.value = result.detections
  inferenceTimeMs.value = result.inference_time_ms
}
</script>
