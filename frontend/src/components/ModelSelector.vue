<!-- ============================================================ -->
<!-- frontend/src/components/ModelSelector.vue                       -->
<!-- 模型选择器 — 选 .pt 文件上传到后端，拔插式换模型                  -->
<!-- ============================================================ -->

<template>
  <div style="display: flex; gap: 8px; align-items: center">
    <button @click="fileInput?.click()" :disabled="!connected">加载 .pt 模型</button>
    <input ref="fileInput" type="file" accept=".pt,.onnx,.engine" @change="onFile" style="display: none" />
    <span :style="{ color: loading ? STATUS_LOADING : modelName ? STATUS_ONLINE : STATUS_IDLE }">
      {{ loading ? '加载中...' : modelName || '未加载模型' }}
    </span>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { STATUS_ONLINE, STATUS_IDLE, STATUS_LOADING } from '../constants/colors'
import { uploadModel } from '../services/apiClient'

defineProps<{ connected: boolean }>()
const emit = defineEmits<{ modelLoaded: [name: string] }>()

const fileInput = ref<HTMLInputElement | null>(null)
const modelName = ref('')
const loading = ref(false)

async function onFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return

  loading.value = true
  try {
    const result = await uploadModel(file)
    modelName.value = result.model_name
    emit('modelLoaded', result.model_name)
  } catch (err) {
    alert('模型加载失败: ' + (err as Error).message)
  } finally {
    loading.value = false
  }
}
</script>
