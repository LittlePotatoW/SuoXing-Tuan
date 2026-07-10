<!-- ============================================================ -->
<!-- frontend/src/components/RelayPanel.vue                                -->
<!-- 中继模式设置 — TranspondServer 连接 + 轮询控制                         -->
<!-- ============================================================ -->

<template>
  <div style="font-size:11px;color:#ccc">
    <div style="font-weight:bold;margin-bottom:6px;color:#4FC3F7">中继设置</div>
    <input
      :value="relayUrl"
      @input="$emit('update:relayUrl', ($event.target as HTMLInputElement).value)"
      placeholder="http://x.x.x.x:8001"
      style="width:100%;background:#1a1a1a;color:#ccc;border:1px solid #555;padding:3px 6px;font-size:10px;margin-bottom:4px"
    />
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px">
      <span style="color:#888">轮询间隔:</span>
      <select
        :value="relayInterval"
        @change="$emit('update:relayInterval', +($event.target as HTMLSelectElement).value)"
        style="background:#1a1a1a;color:#ccc;border:1px solid #555;font-size:10px;padding:2px"
      >
        <option :value="1000">1s</option>
        <option :value="2000">2s</option>
        <option :value="5000">5s</option>
      </select>
    </div>
    <div style="color:#888;font-size:10px">
      状态: <span :style="{color: relayConnected ? '#4CAF50' : '#f44336'}">{{ relayConnected ? '●已连接' : '●未连接' }}</span>
    </div>
    <div v-if="relayConnected && relayCache" style="color:#888;font-size:10px;margin-top:2px">
      缓存: Loc={{ relayCache.location }} Sen={{ relayCache.sensor }}
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  relayUrl: string
  relayInterval: number
  relayConnected: boolean
  relayCache: { location: number; sensor: number } | null
}>()

defineEmits<{
  'update:relayUrl': [v: string]
  'update:relayInterval': [v: number]
}>()
</script>
