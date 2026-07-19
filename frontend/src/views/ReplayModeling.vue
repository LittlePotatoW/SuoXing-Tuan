<!-- ============================================================ -->
<!-- frontend/src/views/ReplayModeling.vue                          -->
<!-- 界面三：回放建模 — 选 session → 全速重建                    -->
<!-- ============================================================ -->
<template>
  <div class="page">
    <div class="toolbar">
      <select class="sel" v-model="selectedSession">
        <option value="">选择 Session...</option>
        <option v-for="s in sessions" :key="s" :value="s">{{ s }}</option>
      </select>
      <button class="btn" :disabled="!selectedSession" @click="replaying = true">
        开始回放重建
      </button>
    </div>

    <div class="main-row">
      <div class="scene-panel">
        <div class="panel-title">3D 场景 (重建结果)</div>
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
            <tr v-if="!hasReport"><td colspan="4" class="empty">此 Session 未保存 Report</td></tr>
          </tbody>
        </table>
        <div v-if="selected && hasReport" class="preview-mini">
          <div class="preview-title">#{{ selected.id }} 标注图</div>
          <div class="preview-placeholder">（标注图预览区）</div>
        </div>
      </div>
    </div>

    <div v-if="replaying" class="progress-bar">
      <div class="progress-label">重建进度: {{ progress }}%  耗时: {{ elapsed }}s  帧数: {{ totalFrames }}</div>
      <div class="progress-track"><div class="progress-fill" :style="{ width: progress + '%' }"></div></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const sessions = ['隧道北段_20240718', '隧道南段_20240719', '测试路段_20240720']
const selectedSession = ref('')
const replaying = ref(false)
const progress = ref(100)
const elapsed = ref(2.3)
const totalFrames = ref(1800)
const hasReport = ref(true)
const selected = ref<any>(null)

const mockDefects = [
  { id: 1, type: '裂缝', conf: 0.93, pos: '10.5, 2.1' },
  { id: 2, type: '渗水', conf: 0.87, pos: '12.1, 1.8' },
]
</script>

<style scoped>
.page { display: flex; flex-direction: column; height: 100%; gap: 0; }
.toolbar { display: flex; gap: 10px; padding: 8px 0; align-items: center; }
.sel { padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; }
.btn { padding: 5px 16px; background: #3a7bd5; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn:disabled { background: #aaa; cursor: default; }
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
.empty { color: #aaa; text-align: center; font-size: 12px; padding: 10px; }
.preview-mini { padding: 8px; border-top: 1px solid #eee; }
.preview-title { font-size: 12px; color: #666; margin-bottom: 4px; }
.preview-placeholder { height: 100px; background: #f5f5f5; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 12px; border-radius: 4px; }
.progress-bar { padding: 10px 0; }
.progress-label { font-size: 12px; color: #666; margin-bottom: 4px; }
.progress-track { height: 6px; background: #eee; border-radius: 3px; }
.progress-fill { height: 100%; background: #3a7bd5; border-radius: 3px; transition: width 0.3s; }
</style>
