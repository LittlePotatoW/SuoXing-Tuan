<!-- ============================================================ -->
<!-- frontend/src/views/SettingsView.vue                            -->
<!-- 界面六：配置 — 网络/重建/估计                                -->
<!-- ============================================================ -->
<template>
  <div class="page">
    <!-- 网络 -->
    <section class="sec">
      <h2 class="sec-title">网络</h2>
      <div class="row">
        <label class="radio"><input type="radio" v-model="netMode" value="lan" /> 局域网直连</label>
        <label class="radio"><input type="radio" v-model="netMode" value="server" /> 服务器中转</label>
      </div>
      <div class="addr-row">
        <div class="addr-group"><label>遥测源</label> <input class="in" v-model="addr.telemetry" placeholder="IP" /> :<input class="in port" v-model.number="port.telemetry" /></div>
        <div class="addr-group"><label>帧数据源</label> <input class="in" v-model="addr.frame" placeholder="IP" /> :<input class="in port" v-model.number="port.frame" /></div>
        <div class="addr-group"><label>后端API</label> <input class="in" v-model="addr.backend" placeholder="IP" /> :<input class="in port" v-model.number="port.backend" /></div>
      </div>
    </section>

    <!-- 重建 -->
    <section class="sec">
      <div class="sec-header">
        <h2 class="sec-title">重建参数</h2>
        <button class="apply-btn" @click="reconApplied = true">应用</button>
      </div>
      <div class="row">
        <label class="radio"><input type="radio" v-model="reconMode" value="incremental" /> 增量重建</label>
        <label class="radio"><input type="radio" v-model="reconMode" value="full" /> 全量重建</label>
        <span class="field">帧阈值 <input class="in sm" v-model.number="frameThreshold" /></span>
        <span class="field">体素 <input class="in sm" v-model.number="voxelSize" step="0.001" /> m</span>
      </div>
      <p v-if="reconApplied" class="applied-msg">✓ 已应用 (引擎已重启)</p>
    </section>

    <!-- 位置估计 -->
    <section class="sec">
      <div class="sec-header">
        <h2 class="sec-title">位置估计</h2>
        <button class="apply-btn" @click="estimatorApplied = true">应用</button>
      </div>
      <div class="row">
        <label class="radio"><input type="radio" v-model="estMode" value="bicycle" /> 自行车</label>
        <label class="radio"><input type="radio" v-model="estMode" value="constant" /> 匀速直线</label>
        <label class="radio"><input type="radio" v-model="estMode" value="rgbd" /> RGB-D</label>
        <label class="radio"><input type="radio" v-model="estMode" value="fusion" /> 融合</label>
      </div>
      <div class="row" style="margin-top:8px">
        <span class="field" v-if="estMode === 'bicycle' || estMode === 'fusion'">轴距 <input class="in sm" v-model.number="wheelbase" /> m</span>
        <span class="field" v-if="estMode === 'constant'">默认速度 <input class="in sm" v-model.number="constSpeed" /> m/s</span>
        <span class="field" v-if="estMode === 'fusion'">融合权重 <input class="in sm" v-model.number="fusionWeight" step="0.1" /></span>
      </div>
      <p v-if="estimatorApplied" class="applied-msg">✓ 已应用 (引擎已重启)</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const netMode = ref('lan')
const addr = ref({ telemetry: '192.168.1.100', frame: '192.168.1.100', backend: '127.0.0.1' })
const port = ref({ telemetry: 8001, frame: 8002, backend: 8000 })

const reconMode = ref('incremental')
const frameThreshold = ref(30)
const voxelSize = ref(0.01)
const reconApplied = ref(false)

const estMode = ref('bicycle')
const wheelbase = ref(2.0)
const constSpeed = ref(1.0)
const fusionWeight = ref(0.5)
const estimatorApplied = ref(false)
</script>

<style scoped>
.page { padding: 4px 0; }
.sec { margin-bottom: 20px; border: 1px solid #e0e0e0; border-radius: 6px; padding: 14px 16px; }
.sec-header { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.sec-title { font-size: 15px; font-weight: 600; margin: 0; flex: 1; }
.apply-btn { padding: 4px 16px; background: #e74c3c; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 13px; }
.apply-btn:hover { background: #c0392b; }
.row { display: flex; gap: 16px; align-items: center; flex-wrap: wrap; }
.addr-row { display: flex; gap: 24px; margin-top: 8px; }
.addr-group { display: flex; align-items: center; gap: 4px; font-size: 13px; color: #555; }
.radio { display: flex; align-items: center; gap: 4px; font-size: 13px; cursor: pointer; }
.field { display: flex; align-items: center; gap: 4px; font-size: 13px; color: #555; }
.in { padding: 4px 8px; border: 1px solid #ccc; border-radius: 3px; font-size: 13px; width: 120px; }
.in.sm { width: 70px; }
.in.port { width: 55px; }
.applied-msg { margin-top: 6px; color: #27ae60; font-size: 12px; }
</style>
