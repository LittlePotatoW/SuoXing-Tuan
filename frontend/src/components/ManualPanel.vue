<!-- ============================================================ -->
<!-- frontend/src/components/ManualPanel.vue                               -->
<!-- 手动模式 — 多源加载 (fusion/原始) + 一键渲染                                -->
<!-- ============================================================ -->

<template>
  <div style="font-size:11px;color:#ccc">
    <div style="font-weight:bold;margin-bottom:6px;color:#4FC3F7">手动模式</div>
    <div style="display:flex;gap:4px;margin-bottom:6px">
      <input
        :value="folderName"
        @input="$emit('update:folderName', ($event.target as HTMLInputElement).value)"
        placeholder="文件夹名 (如 03)"
        style="flex:1;background:#1a1a1a;color:#ccc;border:1px solid #555;padding:3px 6px;font-size:10px"
      />
      <button @click="$emit('load')"
        style="background:#1976D2;color:#fff;border:none;padding:3px 10px;font-size:10px;cursor:pointer;border-radius:3px;white-space:nowrap">
        加载
      </button>
    </div>

    <!-- 数据源概览 -->
    <div v-if="dataStatus === 'full' || dataStatus === 'error'" style="font-size:10px;margin-bottom:6px;color:#888">
      <span v-if="!hasFusion && !canRawRebuild" style="color:#f44336">无可用数据</span>
      <span v-else>
        数据: <span v-if="hasFusion" style="color:#4FC3F7">fusion {{ fusionCount }}</span>
        <span v-if="hasFusion && canRawRebuild">, </span>
        <span v-if="canRawRebuild || sensorCount+locCount>0">sensor {{ sensorCount }} loc {{ locCount }}</span>
      </span>
    </div>
    <div v-if="dataStatus === 'loading'" style="font-size:10px;color:#ccc">加载中...</div>

    <!-- 回放模式选择 -->
    <div v-if="dataStatus === 'full'" style="margin-bottom:6px">
      <div v-if="hasFusion" style="margin-bottom:2px">
        <label style="cursor:pointer">
          <input type="radio" :value="'fusion'" :checked="replayMode === 'fusion'"
            @change="$emit('update:replayMode', 'fusion')" />
          融合数据回放 ({{ fusionCount }}帧)
        </label>
      </div>
      <div v-if="canRawRebuild" style="margin-bottom:2px">
        <label style="cursor:pointer">
          <input type="radio" :value="'raw'" :checked="replayMode === 'raw'"
            @change="$emit('update:replayMode', 'raw')" />
          原始数据重建 (sensor{{ sensorCount }}+loc{{ locCount }})
        </label>
      </div>
      <!-- 匀速直线: raw 模式可用; sensor+straightLine 可绕过缺 loc -->
      <div v-if="replayMode === 'raw'" style="margin-left:16px;margin-top:2px">
        <label style="cursor:pointer;font-size:10px;color:#ffa726">
          <input type="checkbox" :checked="straightLineOn"
            @change="$emit('update:straightLineOn', ($event.target as HTMLInputElement).checked)" />
          匀速直线 (忽略真实 loc)
        </label>
      </div>
    </div>

    <!-- 播放控制 -->
    <template v-if="dataStatus === 'full'">
      <div style="display:flex;gap:4px;margin-bottom:4px">
        <button v-if="!playing" @click="$emit('play')"
          style="background:#388E3C;color:#fff;border:none;padding:2px 10px;font-size:10px;cursor:pointer;border-radius:3px">▶ 播放</button>
        <button v-else @click="$emit('pause')"
          style="background:#E65100;color:#fff;border:none;padding:2px 10px;font-size:10px;cursor:pointer;border-radius:3px">⏸ 暂停</button>
        <button @click="$emit('stop')"
          style="background:#555;color:#fff;border:none;padding:2px 10px;font-size:10px;cursor:pointer;border-radius:3px">⏹ 停止</button>
        <button @click="$emit('renderAll')"
          style="background:#7B1FA2;color:#fff;border:none;padding:2px 10px;font-size:10px;cursor:pointer;border-radius:3px;white-space:nowrap">⚡ 一键渲染</button>
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
  dataStatus: 'none' | 'loading' | 'full' | 'error'
  replayMode: 'fusion' | 'raw'
  hasFusion: boolean
  canRawRebuild: boolean
  fusionCount: number
  sensorCount: number
  locCount: number
  straightLineOn: boolean
  playing: boolean
  current: number
  total: number
}>()

defineEmits<{
  'update:folderName': [v: string]
  'update:replayMode': [v: 'fusion' | 'raw']
  'update:straightLineOn': [v: boolean]
  load: []
  play: []
  pause: []
  stop: []
  renderAll: []
}>()
</script>
