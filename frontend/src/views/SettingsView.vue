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
        <label class="radio"><input type="radio" v-model="netMode" value="direct" /> 本地直连</label>
      </div>
      <div v-if="netMode === 'direct'" class="direct-hint">
        本地直连模式：相机 USB 直连此电脑。需先在本机启动 astra_vehicle_server.py。
        无需遥测数据，位置估计建议使用「匀速直线」模式。
      </div>
      <div class="addr-row">
        <div class="addr-group"><label>遥测源</label> <input class="in" v-model="addr.telemetry" placeholder="IP" /> :<input class="in port" v-model.number="port.telemetry" /></div>
        <div class="addr-group"><label>帧数据源</label> <input class="in" v-model="addr.frame" placeholder="IP" /> :<input class="in port" v-model.number="port.frame" /></div>
        <div class="addr-group"><label>后端API</label> <input class="in" v-model="addr.backend" placeholder="IP" /> :<input class="in port" v-model.number="port.backend" />
          <button class="test-btn" @click="testBackend">{{ testing ? '测试中...' : '测试连接' }}</button>
          <span v-if="testResult !== null" :class="testResult ? 'ok' : 'fail'">{{ testResult ? '✓ 连通' : '✗ 失败' }}</span>
        </div>
      </div>
    </section>

    <!-- 重建 -->
    <section class="sec">
      <div class="sec-header">
        <h2 class="sec-title">重建参数</h2>
        <button class="apply-btn" @click="reconApplied = true">应用</button>
      </div>
      <div class="row">
        <label class="radio"><input type="radio" v-model="reconMethod" value="poisson" /> Poisson</label>
        <label class="radio"><input type="radio" v-model="reconMethod" value="tsdf" /> TSDF</label>
      </div>
      <div class="row" v-if="reconMethod === 'poisson'" style="margin-top:4px">
        <span class="field">帧阈值 <input class="in sm" v-model.number="frameThreshold" /></span>
        <label class="radio"><input type="radio" v-model="reconMode" value="incremental" /> 增量</label>
        <label class="radio"><input type="radio" v-model="reconMode" value="full" /> 全量</label>
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
import { ref, watch, onMounted } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import { reconDefaults, estimationDefaults } from '@/config/defaults'
import { httpClient } from '@/network/http-client'
import { resetEstimator } from '@/api/vehicle'

const settings = useSettingsStore()

// --- 网络参数 ---
// 表单本地副本，初始化时从 store 读（store 数据源是 frontend/config.yaml）
const netMode = ref(settings.mode)
const addr = ref({ telemetry: '', frame: '', backend: '' })
const port = ref({ telemetry: 8001, frame: 8002, backend: 8000 })

syncFormFromStore()

function syncFormFromStore() {
  netMode.value = settings.mode
  addr.value = {
    telemetry: settings.telemetry.host,
    frame: settings.frame.host,
    backend: settings.backend.host,
  }
  port.value = {
    telemetry: settings.telemetry.port,
    frame: settings.frame.port,
    backend: settings.backend.port,
  }
}

const RECON_STORAGE = 'suoxingtuan_recon_config'

function loadReconConfig() {
  try {
    const saved = localStorage.getItem(RECON_STORAGE)
    if (saved) {
      const c = JSON.parse(saved)
      reconMethod.value = c.method || reconDefaults.method
      reconMode.value = c.mode || reconDefaults.mode
      frameThreshold.value = c.frame_threshold ?? reconDefaults.frame_threshold
      return
    }
  } catch {}
  reconMethod.value = reconDefaults.method
  reconMode.value = reconDefaults.mode
  frameThreshold.value = reconDefaults.frame_threshold
}

onMounted(async () => {
  loadReconConfig()
  try {
    const estRes = await httpClient.get('/api/vehicle/estimator/config')
    const cfg = estRes.data
    estMode.value = cfg.mode || estimationDefaults.mode
    wheelbase.value = cfg.wheelbase ?? estimationDefaults.wheelbase
    constSpeed.value = cfg.constant_speed ?? estimationDefaults.constant_speed
  } catch { /* 后端不可达 */ }
})

// 状态栏改了模式 → 表单跟随
watch(() => settings.mode, () => { syncFormFromStore() })

// 用户改了模式 radio → 切 store → 再同步 addr/port 显示
watch(netMode, (v) => {
  settings.switchMode(v)
  syncFormFromStore()
})

// 用户编辑了地址 → 写入 store
watch([addr, port], () => {
  settings.telemetry.host = addr.value.telemetry
  settings.frame.host = addr.value.frame
  settings.backend.host = addr.value.backend
  settings.telemetry.port = port.value.telemetry
  settings.frame.port = port.value.frame
  settings.backend.port = port.value.backend
  settings.applyBackendURL()
}, { deep: true })

// --- 重建参数 — 初始值来自 frontend/config.yaml ---
const reconMethod = ref(reconDefaults.method)
const reconMode = ref(reconDefaults.mode)
const frameThreshold = ref(reconDefaults.frame_threshold)
const reconApplied = ref(false)

watch(reconApplied, (v) => {
  if (!v) return
  localStorage.setItem(RECON_STORAGE, JSON.stringify({
    method: reconMethod.value,
    mode: reconMode.value,
    frame_threshold: frameThreshold.value,
  }))
  reconApplied.value = false
})

// --- 估计参数 — 初始值来自 frontend/config.yaml ---
const estMode = ref(estimationDefaults.mode)
const wheelbase = ref(estimationDefaults.wheelbase)
const constSpeed = ref(estimationDefaults.constant_speed)
const fusionWeight = ref(estimationDefaults.fusion_weight)
const estimatorApplied = ref(false)

watch(estimatorApplied, async (v) => {
  if (!v) return
  try {
    await resetEstimator({
      mode: estMode.value,
      wheelbase: wheelbase.value,
      constant_speed: constSpeed.value,
    })
  } catch { /* 后端不可达 */ }
  estimatorApplied.value = false
})

// --- 测试后端连接 ---
const testing = ref(false)
const testResult = ref<boolean | null>(null)

async function testBackend() {
  testing.value = true; testResult.value = null
  const url = `http://${addr.value.backend}:${port.value.backend}/api/vehicle/position`
  console.log('[testBackend] testing:', url)
  try {
    const resp = await fetch(url, { cache: 'no-cache', signal: AbortSignal.timeout(3000) })
    const ok = resp.ok
    console.log('[testBackend] response:', resp.status, ok)
    testResult.value = ok
  } catch (e) {
    console.warn('[testBackend] failed:', e)
    testResult.value = false
  }
  testing.value = false
}
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
.test-btn { padding: 2px 10px; background: #666; color: #fff; border: none; border-radius: 3px; cursor: pointer; font-size: 11px; white-space: nowrap; }
.test-btn:hover { background: #888; }
.ok { color: #27ae60; font-size: 11px; }
.fail { color: #e74c3c; font-size: 11px; }
.direct-hint { margin: 8px 0 0 0; padding: 8px 12px; background: #fff3cd; border: 1px solid #ffc107; border-radius: 4px; font-size: 12px; color: #856404; }
</style>
