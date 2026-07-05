<!-- ============================================================ -->
<!-- frontend/src/components/DragDropZone.vue                         -->
<!-- 拖拽上传区 — 拖拽/选择图片，发后端推理，展示图像+检测框            -->
<!-- ============================================================ -->

<template>
  <div style="flex: 1; display: flex; flex-direction: column; padding: 12px">
    <div
      :style="{
        flex: 1,
        border: `2px dashed ${dragOver ? DROPZONE_BORDER_HOVER : DROPZONE_BORDER}`,
        background: dragOver ? DROPZONE_BG_HOVER : DROPZONE_BG,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        cursor: 'pointer', minHeight: '300px',
      }"
      @dragover.prevent="dragOver = true"
      @dragleave="dragOver = false"
      @drop.prevent="onDrop"
      @click="fileInput?.click()"
    >
      <input ref="fileInput" type="file" accept="image/*" @change="onFile" style="display: none" />

      <ImageViewer v-if="imageSrc" :imageSrc="imageSrc" :detections="detections" />
      <div v-else style="text-align: center; color: #888">
        <p>拖拽图片到这里，或点击选择文件</p>
        <p v-if="!connected" style="font-size: 12px">(连接后端后自动推理)</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ImageViewer from './ImageViewer.vue'
import { DROPZONE_BG, DROPZONE_BG_HOVER, DROPZONE_BORDER, DROPZONE_BORDER_HOVER } from '../constants/colors'

defineProps<{ connected: boolean; imageSrc: string | null; detections: any[] }>()
const emit = defineEmits<{ fileDropped: [file: File] }>()

const fileInput = ref<HTMLInputElement | null>(null)
const dragOver = ref(false)

function onDrop(e: DragEvent) {
  dragOver.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file && file.type.startsWith('image/')) emit('fileDropped', file)
}

function onFile(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (file) emit('fileDropped', file)
}
</script>
