<!-- ============================================================ -->
<!-- frontend/src/components/SaveModePanel.vue                             -->
<!-- 保存模式 — 开启后将数据写入 data_captures/ 文件夹                      -->
<!-- ============================================================ -->

<template>
  <div style="margin-bottom:10px">
    <label style="display:flex;align-items:center;gap:6px;font-size:11px;color:#ccc;cursor:pointer;margin-bottom:6px">
      <input type="checkbox" :checked="saveOn" @change="$emit('update:saveOn', ($event.target as HTMLInputElement).checked)" />
      <span style="font-weight:bold">保存模式</span>
      <span v-if="saveOn" style="color:#4CAF50;font-size:10px">ON</span>
    </label>
    <template v-if="saveOn">
      <input
        :value="saveName"
        @input="$emit('update:saveName', ($event.target as HTMLInputElement).value)"
        placeholder="保存名称 (如 session_01)"
        style="width:100%;background:#1a1a1a;color:#ccc;border:1px solid #555;padding:3px 6px;font-size:10px;margin-bottom:4px"
      />
      <div style="display:flex;gap:10px;font-size:10px;color:#888">
        <label style="cursor:pointer"><input type="checkbox" :checked="saveLoc" @change="$emit('update:saveLoc', ($event.target as HTMLInputElement).checked)" /> Loc</label>
        <label style="cursor:pointer"><input type="checkbox" :checked="saveDet" @change="$emit('update:saveDet', ($event.target as HTMLInputElement).checked)" /> Det</label>
        <label style="cursor:pointer"><input type="checkbox" :checked="saveFusion" @change="$emit('update:saveFusion', ($event.target as HTMLInputElement).checked)" /> Fusion</label>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  saveOn: boolean
  saveName: string
  saveLoc: boolean
  saveDet: boolean
  saveFusion: boolean
}>()

defineEmits<{
  'update:saveOn': [v: boolean]
  'update:saveName': [v: string]
  'update:saveLoc': [v: boolean]
  'update:saveDet': [v: boolean]
  'update:saveFusion': [v: boolean]
}>()
</script>
