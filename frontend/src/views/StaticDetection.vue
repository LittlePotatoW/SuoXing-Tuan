<!-- ============================================================ -->
<!-- frontend/src/views/StaticDetection.vue                         -->
<!-- 界面五：静态检测 — 拖拽上传 + 检测结果                      -->
<!-- ============================================================ -->
<template>
  <div class="page">
    <div class="top-bar">
      <button class="btn" @click="detected = !detected">检测</button>
    </div>
    <div class="result-layout">
      <div class="image-panel">
        <div class="panel-title">上传图像</div>
        <div class="img-box">
          <FileDropZone placeholder="拖拽图片到此处 或 点击上传" />
        </div>
      </div>

      <div class="result-panel">
        <div class="panel-title">检测结果</div>
        <table v-if="detected" class="defect-table">
          <thead><tr><th>ID</th><th>类型</th><th>置信度</th><th>位置</th></tr></thead>
          <tbody>
            <tr v-for="d in mockResults" :key="d.id">
              <td>{{ d.id }}</td><td>{{ d.type }}</td><td>{{ d.conf }}</td><td>{{ d.pos }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-msg">点击"检测"查看结果</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import FileDropZone from '@/components/common/FileDropZone.vue'

const detected = ref(false)

const mockResults = [
  { id: 1, type: '裂缝', conf: 0.93, pos: '10.5, 2.1, -3.0' },
  { id: 2, type: '渗水', conf: 0.87, pos: '12.1, 1.8, -2.5' },
]
</script>

<style scoped>
.page { height: 100%; }
.result-layout { display: flex; gap: 12px; height: 100%; }
.image-panel { flex: 1; border: 1px solid #ddd; border-radius: 6px; display: flex; flex-direction: column; }
.result-panel { width: 300px; border: 1px solid #ddd; border-radius: 6px; overflow: auto; }
.panel-title { padding: 8px 12px; font-size: 13px; color: #666; border-bottom: 1px solid #eee; background: #fafafa; }
.img-box { flex: 1; display: flex; align-items: center; justify-content: center; }
.img-placeholder { color: #aaa; font-size: 13px; }
.top-bar { display: flex; align-items: center; gap: 8px; padding: 8px 0; margin-bottom: 12px; }
.btn { padding: 5px 16px; background: #3a7bd5; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn.outline { background: #fff; color: #3a7bd5; border: 1px solid #3a7bd5; }
.btn:hover { opacity: 0.9; }
.defect-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.defect-table th { background: #f5f5f5; padding: 6px; text-align: left; border-bottom: 2px solid #ddd; }
.defect-table td { padding: 5px 6px; border-bottom: 1px solid #eee; }
.empty-msg { padding: 20px; text-align: center; color: #aaa; font-size: 13px; }
</style>
