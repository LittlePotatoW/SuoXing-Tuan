<!-- ============================================================ -->
<!-- frontend/src/views/StaticDetection.vue                         -->
<!-- 界面五：静态检测 — 拖拽上传 + 推理标注图                    -->
<!-- ============================================================ -->
<template>
  <div class="page">
    <div class="top-bar">
      <button v-if="!imageBase64" class="btn" disabled>请先上传图片</button>
      <button v-else-if="!detected" class="btn" :disabled="detecting" @click="runDetection">
        {{ detecting ? '检测中...' : '开始检测' }}
      </button>
      <button v-else class="btn" @click="runDetection" :disabled="detecting">
        {{ detecting ? '检测中...' : '重新检测' }}
      </button>
      <span v-if="detected" class="count-tip">共 {{ results.length }} 个缺陷</span>
    </div>
    <div class="result-layout">
      <div class="image-panel">
        <div class="panel-title">{{ detected ? '推理标注图' : '上传图像' }}</div>
        <div class="img-box">
          <FileDropZone v-if="!previewUrl" placeholder="拖拽图片到此处 或 点击上传" @file-selected="onFileSelected" />
          <img v-else :src="displayImage" class="preview-img" @click="triggerUpload" title="点击更换图片" />
          <input ref="fileInput" type="file" accept="image/*" class="hidden-input" @change="onFileInputChange" />
        </div>
      </div>

      <div class="result-panel">
        <div class="panel-title">检测结果</div>
        <table v-if="results.length" class="defect-table">
          <thead><tr><th>ID</th><th>类型</th><th>置信度</th><th>位置 (x, y, z)</th></tr></thead>
          <tbody>
            <tr v-for="d in results" :key="d.id">
              <td>{{ d.id }}</td>
              <td>{{ d.class_name }}</td>
              <td>{{ (d.confidence * 100).toFixed(0) }}%</td>
              <td>{{ (d.center_3d?.map(v => v.toFixed(2)).join(', ') ?? '-') }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-msg">{{ detected ? '未检测到缺陷' : '上传图片后点击"开始检测"' }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import FileDropZone from '@/components/common/FileDropZone.vue'
import { fileToBase64 } from '@/services/pack-unpack/parse'
import { postDetectionImage, getDetectionResultAnnotated } from '@/api/detection'
import type { DetectionItem } from '@/types/api'

const imageBase64 = ref('')
const previewUrl = ref('')         // 原始图片 blob URL
const annotatedB64 = ref('')       // 标注图 base64
const detecting = ref(false)
const detected = ref(false)
const results = ref<DetectionItem[]>([])
const fileInput = ref<HTMLInputElement | null>(null)

const displayImage = computed(() => {
  if (annotatedB64.value) return 'data:image/jpeg;base64,' + annotatedB64.value
  return previewUrl.value
})

function triggerUpload() {
  fileInput.value?.click()
}

function onFileInputChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) onFileSelected(file)
  input.value = ''  // 允许重复选同一文件
}

async function onFileSelected(file: File) {
  previewUrl.value = URL.createObjectURL(file)
  imageBase64.value = await fileToBase64(file)
  detected.value = false
  annotatedB64.value = ''
  results.value = []
}

async function runDetection() {
  if (!imageBase64.value) return
  detecting.value = true
  try {
    // 1. 提交图片进行检测
    const res = await postDetectionImage({ image: imageBase64.value })
    results.value = res.detections
    detected.value = true

    // 2. 获取后端 YOLO 画好框的标注图
    try {
      const anno = await getDetectionResultAnnotated()
      if (anno.annotated_image) {
        annotatedB64.value = anno.annotated_image
      }
    } catch { /* 标注图获取失败，保留原图 */ }
  } catch { /* backend unreachable */ }
  detecting.value = false
}
</script>

<style scoped>
.page { height: 100%; display: flex; flex-direction: column; }
.result-layout { display: flex; gap: 12px; flex: 1; min-height: 0; }
.image-panel { flex: 1; border: 1px solid #ddd; border-radius: 6px; display: flex; flex-direction: column; }
.result-panel { width: 300px; border: 1px solid #ddd; border-radius: 6px; overflow: auto; display: flex; flex-direction: column; }
.panel-title { padding: 8px 12px; font-size: 13px; color: #666; border-bottom: 1px solid #eee; background: #fafafa; }
.img-box { flex: 1; display: flex; align-items: center; justify-content: center; padding: 12px; overflow: auto; }
.preview-img { max-width: 100%; max-height: 100%; object-fit: contain; border-radius: 4px; cursor: pointer; }
.preview-img:hover { opacity: 0.85; }
.hidden-input { display: none; }
.top-bar { display: flex; align-items: center; gap: 12px; padding: 8px 0; margin-bottom: 12px; }
.btn { padding: 5px 16px; background: #3a7bd5; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn:disabled { background: #aaa; cursor: default; }
.btn:hover:not(:disabled) { opacity: 0.9; }
.count-tip { font-size: 13px; color: #666; }
.defect-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.defect-table th { background: #f5f5f5; padding: 6px; text-align: left; border-bottom: 2px solid #ddd; position: sticky; top: 0; }
.defect-table td { padding: 5px 6px; border-bottom: 1px solid #eee; }
.empty-msg { flex: 1; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 13px; padding: 20px; }
</style>
