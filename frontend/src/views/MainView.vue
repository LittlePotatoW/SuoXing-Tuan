<!-- ============================================================ -->
<!-- frontend/src/views/MainView.vue                                -->
<!-- 界面一：主界面 — 实时图像 + 位置信息                        -->
<!-- ============================================================ -->
<template>
  <div class="page">
    <div class="image-row">
      <div class="panel">
        <div class="panel-title">RGB 实时图像</div>
        <div class="img-placeholder">等待数据...</div>
      </div>
      <div class="panel">
        <div class="panel-title">深度图预览</div>
        <div class="img-placeholder">等待数据...</div>
      </div>
    </div>

    <div class="data-bar">
      <span>位置: X={{ pos.x.toFixed(2) }}  Y={{ pos.y.toFixed(2) }}  H={{ pos.heading.toFixed(1) }}°</span>
      <span class="sep">|</span>
      <span>速度: {{ speed.toFixed(1) }} m/s</span>
      <span class="sep">|</span>
      <span>转向: {{ steering.toFixed(1) }}°</span>
    </div>

    <div class="map-placeholder">
      <span>地图 — GPS 数据接入后显示</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { usePolling } from '@/composables/usePolling'
import { getPosition } from '@/api/vehicle'
import { useVehicleStore } from '@/stores/vehicle'

const vehicle = useVehicleStore()
const pos = ref({ x: 0, y: 0, heading: 0 })
const speed = computed(() => vehicle.speed)
const steering = computed(() => vehicle.steeringAngle)

const { start } = usePolling(async () => {
  try {
    const p = await getPosition()
    pos.value = { x: p.x, y: p.y, heading: p.heading }
    vehicle.updatePosition({ timestamp: p.timestamp, x: p.x, y: p.y, heading: p.heading })
  } catch { /* backend unreachable */ }
}, 1000)

onMounted(() => { start() })
</script>

<style scoped>
.page { display: flex; flex-direction: column; height: 100%; gap: 12px; }
.image-row { display: flex; gap: 12px; flex: 1; min-height: 0; }
.panel { flex: 1; border: 1px solid #ddd; border-radius: 6px; display: flex; flex-direction: column; }
.panel-title { padding: 8px 12px; font-size: 13px; color: #666; border-bottom: 1px solid #eee; background: #fafafa; }
.img-placeholder { flex: 1; display: flex; align-items: center; justify-content: center; color: #aaa; font-size: 14px; }
.data-bar { display: flex; gap: 16px; padding: 8px 12px; background: #f9f9f9; border-radius: 4px; font-size: 14px; color: #333; }
.sep { color: #ccc; }
.map-placeholder { height: 200px; border: 1px dashed #ccc; border-radius: 6px; display: flex; align-items: center; justify-content: center; color: #999; font-size: 13px; }
</style>
