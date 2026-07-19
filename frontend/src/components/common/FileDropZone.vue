<!-- ============================================================ -->
<!-- frontend/src/components/common/FileDropZone.vue               -->
<!-- 拖拽上传区：纯 UI，暂不接文件处理逻辑                       -->
<!-- ============================================================ -->
<template>
  <div class="dropzone" :class="{ dragging }"
    @dragover.prevent="dragging = true"
    @dragleave="dragging = false"
    @drop.prevent="dragging = false">
    <div class="icon">📁</div>
    <p>{{ placeholder }}</p>
    <input type="file" accept="image/*" class="file-input" @change="dragging = false" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
defineProps<{ placeholder?: string }>()
const dragging = ref(false)
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
