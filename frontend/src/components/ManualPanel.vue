<!-- ============================================================ -->
<!-- frontend/src/components/ManualPanel.vue                               -->
<!-- 手动模式 — 从本地 data_captures/ 文件夹加载保存的数据                  -->
<!-- ============================================================ -->

<template>
  <div style="font-size:11px;color:#ccc">
    <div style="font-weight:bold;margin-bottom:6px;color:#4FC3F7">手动模式</div>
    <div style="display:flex;gap:4px;margin-bottom:6px">
      <input
        :value="folderName"
        @input="$emit('update:folderName', ($event.target as HTMLInputElement).value)"
        placeholder="文件夹名 (如 session_01)"
        style="flex:1;background:#1a1a1a;color:#ccc;border:1px solid #555;padding:3px 6px;font-size:10px"
      />
      <button @click="$emit('load')"
        style="background:#1976D2;color:#fff;border:none;padding:3px 10px;font-size:10px;cursor:pointer;border-radius:3px;white-space:nowrap">
        加载
      </button>
    </div>

    <!-- 加载状态 -->
    <div v-if="dataStatus" :style="{fontSize:'10px',marginBottom:'6px',color: dataStatus === 'error' ? '#f44336' : dataStatus === 'fusion_only' ? '#ffa726' : '#4CAF50'}">
      <template v-if="dataStatus === 'full'">数据完整: Loc={{ locCount }} Det={{ detCount }} (将通过后端融合)</template>
      <template v-else-if="dataStatus === 'fusion_only'">仅有 Fusion 数据: {{ fusionCount }} 条 (跳过融合直接渲染)</template>
      <template v-else-if="dataStatus === 'error'">数据缺失: 需要 (Loc+Det) 或 Fusion 数据</template>
      <template v-else-if="dataStatus === 'loading'">加载中...</template>
    </div>

    <!-- 播放控制 (数据加载成功后可见) -->
    <template v-if="dataStatus === 'full' || dataStatus === 'fusion_only'">
      <div style="display:flex;gap:4px;margin-bottom:4px">
        <button v-if="!playing" @click="$emit('play')" style="background:#388E3C;color:#fff;border:none;padding:2px 10px;font-size:10px;cursor:pointer;border-radius:3px">▶ 播放</button>
        <button v-else @click="$emit('pause')" style="background:#E65100;color:#fff;border:none;padding:2px 10px;font-size:10px;cursor:pointer;border-radius:3px">⏸ 暂停</button>
        <button @click="$emit('stop')" style="background:#555;color:#fff;border:none;padding:2px 10px;font-size:10px;cursor:pointer;border-radius:3px">⏹ 停止</button>
      </div>
      <div style="font-size:10px;color:#888">
        进度: {{ current }} / {{ total }}
        <div style="background:#333;height:4px;border-radius:2px;margin-top:2px">
          <div :style="{background:'#4FC3F7',height:'100%',width:total>0?(current/total*100)+'%':'0%',borderRadius:'2px'}"></div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  folderName: string
  dataStatus: 'none' | 'loading' | 'full' | 'fusion_only' | 'error'
  locCount: number
  detCount: number
  fusionCount: number
  playing: boolean
  current: number
  total: number
}>()

defineEmits<{
  'update:folderName': [v: string]
  load: []
  play: []
  pause: []
  stop: []
}>()
</script>
