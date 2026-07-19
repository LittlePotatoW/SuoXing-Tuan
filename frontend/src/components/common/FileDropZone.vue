<!-- ============================================================ -->
<!-- frontend/src/components/common/FileDropZone.vue               -->
<!-- 拖拽上传区：支持 emit file-selected 传出文件对象              -->
<!-- ============================================================ -->
<template>
  <div class="dropzone" :class="{ dragging }"
    @dragover.prevent="dragging = true"
    @dragleave="dragging = false"
    @drop.prevent="onDrop">
    <p>{{ placeholder }}</p>
    <input type="file" accept="image/*" class="file-input" @change="onChange" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ placeholder?: string }>()
const emit = defineEmits<{ 'file-selected': [file: File] }>()

const dragging = ref(false)

function onDrop(e: DragEvent) {
  dragging.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) emit('file-selected', file)
}

function onChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) emit('file-selected', file)
}
</script>

<style scoped>
.dropzone {
  border: 2px dashed #aaa; border-radius: 8px; padding: 40px;
  text-align: center; color: #888; cursor: pointer; position: relative;
  transition: border-color 0.2s;
}
.dropzone.dragging { border-color: #4a90d9; color: #4a90d9; }
.icon { font-size: 36px; margin-bottom: 8px; }
.file-input {
  position: absolute; inset: 0; opacity: 0; cursor: pointer;
}
</style>
