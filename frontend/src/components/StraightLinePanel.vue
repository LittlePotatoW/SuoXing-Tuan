<!-- ============================================================ -->
<!-- frontend/src/components/StraightLinePanel.vue                         -->
<!-- 匀速直线模式 — 忽略 loc 数据，用匀速推算 car_position                  -->
<!-- ============================================================ -->

<template>
  <div style="margin-bottom:10px">
    <label style="display:flex;align-items:center;gap:6px;font-size:11px;color:#ffa726;cursor:pointer;margin-bottom:4px">
      <input type="checkbox" :checked="on" @change="$emit('update:on', ($event.target as HTMLInputElement).checked)" />
      <span style="font-weight:bold">匀速直线</span>
    </label>
    <div v-if="on" style="display:flex;align-items:center;gap:6px">
      <span style="font-size:10px;color:#888">速度:</span>
      <input
        type="number" step="0.1" min="0.1" max="5"
        :value="speed"
        @input="$emit('update:speed', +($event.target as HTMLInputElement).value)"
        style="width:55px;background:#1a1a1a;color:#ffa726;border:1px solid #555;padding:2px 4px;font-size:11px"
      />
      <span style="font-size:10px;color:#888">m/s</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  on: boolean
  speed: number
}>()

defineEmits<{
  'update:on': [v: boolean]
  'update:speed': [v: number]
}>()
</script>
