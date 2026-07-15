<!-- ============================================================ -->
<!-- frontend/src/components/ConnectionBar.vue                        -->
<!-- 后端连接栏 — 输入 IP:端口，连接/断开后端                           -->
<!-- ============================================================ -->

<template>
  <div style="display: flex; gap: 8px; align-items: center">
    <label>后端: <input v-model="localHost" placeholder="192.168.1.100" style="width: 120px" :disabled="connected" /></label>
    <label>端口: <input v-model.number="localPort" placeholder="8000" style="width: 60px" :disabled="connected" /></label>
    <button v-if="!connected" @click="handleConnect">连接</button>
    <button v-else @click="$emit('disconnect')">断开</button>
    <span :style="{ color: connected ? STATUS_ONLINE : STATUS_OFFLINE, fontWeight: 'bold', marginLeft: '8px' }">
      {{ connected ? '已连接' : '未连接' }}
    </span>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { STATUS_ONLINE, STATUS_OFFLINE } from '../constants/colors'

defineProps<{ connected: boolean }>()
const emit = defineEmits<{
  connect: [host: string, port: number]
  disconnect: []
}>()

const localHost = ref('localhost')
const localPort = ref(8000)

function handleConnect() {
  if (isNaN(localPort.value)) return
  emit('connect', localHost.value, localPort.value)
}
</script>
