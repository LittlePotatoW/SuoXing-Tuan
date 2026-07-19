<!-- ============================================================ -->
<!-- frontend/src/views/RealtimeModeling.vue                        -->
<!-- 界面二：实时建模 — 3D场景 + 缺陷列表                        -->
<!-- ============================================================ -->
<template>
  <div class="page">
    <div class="top-bar">
      <button v-if="!modeling" class="start-btn" @click="modeling = true">开始建模</button>
      <button v-else class="stop-btn" @click="stopModeling">停止建模</button>

      <span v-if="dataActive && !modeling" class="active-tip">● 数据源活跃</span>

      <label class="toggle"><input type="checkbox" v-model="yoloOn" :disabled="modeling" /> YOLO检测</label>
      <label class="toggle"><input type="checkbox" v-model="saveSession" :disabled="modeling" /> 保存Session</label>
      <label class="toggle"><input type="checkbox" v-model="saveReport" :disabled="modeling" /> 保存Report</label>
      <input class="task-input" v-model="taskName" placeholder="任务名" :disabled="modeling" />
      <span class="spacer"></span>
      <span class="frame-count">帧: {{ modeling ? frameCount : 0 }}/{{ frameThreshold }}</span>
    </div>

    <div class="main-row">
      <div class="scene-panel">
        <div class="panel-title">3D 场景 (点云 + 检测标注)</div>
        <div class="scene-placeholder">Three.js 场景 — 待渲染引擎实现</div>
      </div>

      <div class="defect-panel">
        <div class="panel-title">缺陷列表</div>
        <table class="defect-table">
          <thead><tr><th>ID</th><th>类型</th><th>置信度</th><th>位置</th></tr></thead>
          <tbody>
            <tr v-for="d in mockDefects" :key="d.id" @click="selected = d"
              :class="{ selected: selected?.id === d.id }">
              <td>{{ d.id }}</td><td>{{ d.type }}</td><td>{{ d.conf }}</td>
              <td>{{ d.pos }}</td>
            </tr>
            <tr v-if="!mockDefects.length"><td colspan="4" class="empty">暂无缺陷</td></tr>
          </tbody>
        </table>
        <div v-if="selected" class="preview-mini">
          <div class="preview-title">缺陷 #{{ selected.id }} 标注图</div>
          <div class="preview-placeholder">（标注图预览区）</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const modeling = ref(false)
const dataActive = ref(true)   // 模拟: 3s内有数据源
const yoloOn = ref(true)
const saveSession = ref(false)
const saveReport = ref(false)
const taskName = ref('')
const frameCount = ref(12)

function stopModeling() {
  modeling.value = false
  frameCount.value = 0
}
const frameThreshold = ref(30)
const selected = ref<any>(null)

const mockDefects = [
  { id: 1, type: '裂缝', conf: 0.93, pos: '10.5, 2.1' },
  { id: 2, type: '渗水', conf: 0.87, pos: '12.1, 1.8' },
]
</script>

<style scoped>
.page { display: flex; flex-direction: column; height: 100%; }
.main-row { display: flex; gap: 12px; flex: 1; min-height: 0; }
.scene-panel { flex: 1; border: 1px solid #ddd; border-radius: 6px; display: flex; flex-direction: column; }
.defect-panel { width: 280px; border: 1px solid #ddd; border-radius: 6px; display: flex; flex-direction: column; overflow: auto; }
.panel-title { padding: 8px 12px; font-size: 13px; color: #666; border-bottom: 1px solid #eee; background: #fafafa; }
.scene-placeholder { flex: 1; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 14px; }
.defect-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.defect-table th { background: #f5f5f5; padding: 6px; text-align: left; border-bottom: 2px solid #ddd; }
.defect-table td { padding: 5px 6px; border-bottom: 1px solid #eee; cursor: pointer; }
.defect-table tr:hover { background: #f0f4ff; }
.defect-table tr.selected { background: #dbeafe; }
.empty { color: #aaa; text-align: center; }
.preview-mini { padding: 8px; border-top: 1px solid #eee; }
.preview-title { font-size: 12px; color: #666; margin-bottom: 4px; }
.preview-placeholder { height: 100px; background: #f5f5f5; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 12px; border-radius: 4px; }
.top-bar { display: flex; align-items: center; gap: 16px; padding: 8px 12px; background: #f9f9f9; border-bottom: 1px solid #eee; font-size: 13px; margin-bottom: 12px; }
.toggle { cursor: pointer; display: flex; align-items: center; gap: 4px; }
.task-input { width: 120px; padding: 3px 6px; border: 1px solid #ccc; border-radius: 3px; font-size: 12px; }
.frame-count { color: #888; }
.start-btn { padding: 5px 20px; background: #27ae60; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.start-btn:hover { background: #219a52; }
.stop-btn { padding: 5px 20px; background: #e74c3c; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.stop-btn:hover { background: #c0392b; }
.active-tip { color: #27ae60; font-size: 12px; }
.spacer { flex: 1; }
</style>
