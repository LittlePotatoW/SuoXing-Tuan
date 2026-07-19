<!-- ============================================================ -->
<!-- frontend/src/views/DefectDetail.vue                            -->
<!-- 界面四：缺陷详情 — 列表 + 标注图预览                        -->
<!-- ============================================================ -->
<template>
  <div class="page">
    <div class="toolbar">
      <select class="sel" v-model="selectedReport" @focus="fetchReports">
        <option value="">选择 Report...</option>
        <option v-for="r in reports" :key="r" :value="r">{{ r }}</option>
      </select>
    </div>

    <div class="main-row">
      <div class="table-panel">
        <div class="panel-title">缺陷列表 ({{ defects.length }})</div>
        <table class="defect-table">
          <thead><tr><th>ID</th><th>类型</th><th>置信度</th><th>位置 (x, y, z)</th></tr></thead>
          <tbody>
            <tr v-for="d in defects" :key="d.id" @click="selected = d"
              :class="{ selected: selected?.id === d.id }">
              <td>{{ d.id }}</td><td>{{ d.type }}</td><td>{{ d.conf }}</td>
              <td>{{ d.pos }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="preview-panel">
        <div class="panel-title">预览</div>
        <div v-if="selected" class="preview-body">
          <div class="preview-placeholder">（标注图预览）</div>
          <div class="note-row">
            <input v-model="note" class="note-input" placeholder="备注..." />
            <button class="btn sm" @click="saveNote">保存</button>
          </div>
        </div>
        <div v-else class="preview-empty">点击左侧列表查看标注图</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { listReports, loadReport } from '@/api/report'

const selected = ref<any>(null)
const note = ref('')
const selectedReport = ref('')
const reports = ref<string[]>([])
const defects = ref<any[]>([
  { id: 1, type: '裂缝', conf: 0.93, pos: '10.5, 2.1, -3.0' },
  { id: 2, type: '渗水', conf: 0.87, pos: '12.1, 1.8, -2.5' },
  { id: 3, type: '裂缝', conf: 0.76, pos: '14.0, 1.5, -2.0' },
])

async function fetchReports() {
  try {
    const list = await listReports()
    reports.value = list.map((r) => r.filename)
  } catch (e) { console.warn('获取 report 列表失败:', e) }
}

onMounted(() => { fetchReports() })

watch(selectedReport, async (filename) => {
  if (!filename) { defects.value = []; return }
  try {
    const data = await loadReport(filename)
    if (data.defects) {
      defects.value = data.defects.map((d: any) => ({
        id: d.id, type: d.class_name,
        conf: (d.confidence * 100).toFixed(0) + '%',
        pos: (d.center_3d || [0, 0, 0]).join(', '),
      }))
    }
  } catch { /* 加载失败 */ }
})

watch(selected, (d) => {
  note.value = d ? (localStorage.getItem(`defect-note-${d.id}`) ?? '') : ''
})

function saveNote() {
  if (selected.value) {
    localStorage.setItem(`defect-note-${selected.value.id}`, note.value)
  }
}
</script>

<style scoped>
.page { display: flex; flex-direction: column; height: 100%; gap: 0; }
.toolbar { display: flex; gap: 8px; padding: 8px 0; align-items: center; }
.sel { padding: 5px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 13px; min-width: 160px; }
.btn { padding: 5px 14px; background: #3a7bd5; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.btn:hover { background: #2d6ac4; }
.btn.sm { padding: 3px 10px; font-size: 12px; }
.main-row { display: flex; gap: 12px; flex: 1; min-height: 0; }
.table-panel { flex: 1; border: 1px solid #ddd; border-radius: 6px; display: flex; flex-direction: column; overflow: auto; }
.preview-panel { width: 340px; border: 1px solid #ddd; border-radius: 6px; display: flex; flex-direction: column; }
.panel-title { padding: 8px 12px; font-size: 13px; color: #666; border-bottom: 1px solid #eee; background: #fafafa; }
.defect-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.defect-table th { background: #f5f5f5; padding: 7px 8px; text-align: left; border-bottom: 2px solid #ddd; position: sticky; top: 0; }
.defect-table td { padding: 6px 8px; border-bottom: 1px solid #eee; cursor: pointer; }
.defect-table tr:hover { background: #f0f4ff; }
.defect-table tr.selected { background: #dbeafe; }
.preview-body { flex: 1; display: flex; flex-direction: column; }
.preview-placeholder { flex: 1; margin: 8px; background: #f5f5f5; border-radius: 4px; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 13px; }
.preview-empty { flex: 1; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 13px; }
.note-row { display: flex; gap: 6px; padding: 8px; border-top: 1px solid #eee; }
.note-input { flex: 1; padding: 4px 8px; border: 1px solid #ccc; border-radius: 3px; font-size: 12px; }
</style>
