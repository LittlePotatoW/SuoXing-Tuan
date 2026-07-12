<!-- ============================================================ -->
<!-- frontend/src/components/ReplayPanel.vue                               -->
<!-- 回放模式 — 从 TranspondServer 按范围拉取历史数据播放                   -->
<!-- ============================================================ -->

<template>
  <div style="font-size:11px;color:#ccc">
    <div style="font-weight:bold;margin-bottom:6px;color:#4FC3F7">回放设置</div>

    <!-- 服务器地址 -->
    <input
      :value="relayUrl"
      @input="$emit('update:relayUrl', ($event.target as HTMLInputElement).value)"
      placeholder="http://x.x.x.x:8001"
      style="width:100%;background:#1a1a1a;color:#ccc;border:1px solid #555;padding:3px 6px;font-size:10px;margin-bottom:6px"
    />

    <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px">
      <button @click="doTest" style="background:#555;color:#fff;border:none;padding:2px 8px;font-size:10px;cursor:pointer;border-radius:3px">连接测试</button>
      <span v-if="testResult !== null" style="font-size:10px" :style="{color: testResult ? '#4CAF50' : '#f44336'}">{{ testResult ? '✓ 可达' : '✗ 不可达' }}</span>
      <span style="color:#888;font-size:10px;margin-left:8px">超时</span>
      <input type="number" min="5" max="300" :value="timeout" @input="$emit('update:timeout', +($event.target as HTMLInputElement).value)"
        style="width:45px;background:#1a1a1a;color:#ccc;border:1px solid #555;padding:2px 4px;font-size:10px" />
      <span style="color:#888;font-size:10px">秒</span>
    </div>

    <!-- 范围类型选择 -->
    <div style="display:flex;gap:12px;margin-bottom:6px">
      <label style="cursor:pointer;font-size:10px">
        <input type="radio" :checked="rangeType === 'frames'" @change="$emit('update:rangeType', 'frames')" /> 按帧数
      </label>
      <label style="cursor:pointer;font-size:10px">
        <input type="radio" :checked="rangeType === 'time'" @change="$emit('update:rangeType', 'time')" /> 按时间
      </label>
    </div>

    <!-- 帧数范围 -->
    <template v-if="rangeType === 'frames'">
      <div style="display:flex;align-items:center;gap:4px;margin-bottom:4px">
        <span style="color:#888;font-size:10px">最近</span>
        <input type="number" min="1" :value="startN" @input="$emit('update:startN', +($event.target as HTMLInputElement).value)"
          style="width:50px;background:#1a1a1a;color:#ccc;border:1px solid #555;padding:2px 4px;font-size:10px" />
        <span style="color:#888;font-size:10px">份 到 最近</span>
        <input type="number" min="0" :value="endN" @input="$emit('update:endN', +($event.target as HTMLInputElement).value)"
          style="width:50px;background:#1a1a1a;color:#ccc;border:1px solid #555;padding:2px 4px;font-size:10px" />
        <span style="color:#888;font-size:10px">份</span>
      </div>
      <div style="font-size:9px;color:#666;margin-bottom:4px">(endN=0 表示到现在)</div>
    </template>

    <!-- 时间范围 -->
    <template v-else>
      <div style="display:flex;align-items:center;gap:4px;margin-bottom:4px">
        <input type="number" min="0" :value="startMin" @input="$emit('update:startMin', +($event.target as HTMLInputElement).value)"
          style="width:50px;background:#1a1a1a;color:#ccc;border:1px solid #555;padding:2px 4px;font-size:10px" />
        <span style="color:#888;font-size:10px">分钟前 到</span>
        <input type="number" min="0" :value="endMin" @input="$emit('update:endMin', +($event.target as HTMLInputElement).value)"
          style="width:50px;background:#1a1a1a;color:#ccc;border:1px solid #555;padding:2px 4px;font-size:10px" />
        <span style="color:#888;font-size:10px">分钟前</span>
      </div>
      <div style="font-size:9px;color:#666;margin-bottom:4px">(endMin=0 表示到现在)</div>
    </template>

    <!-- 加载/播放按钮 -->
    <button @click="$emit('load')"
      style="background:#1976D2;color:#fff;border:none;padding:3px 12px;font-size:10px;cursor:pointer;border-radius:3px;margin-bottom:4px">
      加载数据
    </button>

    <div v-if="loaded" style="font-size:10px;color:#4CAF50;margin-bottom:6px">
      已拉取: Loc={{ locCount }} Det={{ detCount }}
    </div>

    <!-- 播放控制 (加载后可见) -->
    <template v-if="loaded">
      <div style="display:flex;gap:4px;margin-bottom:4px">
        <button v-if="!playing" @click="$emit('play')" style="background:#388E3C;color:#fff;border:none;padding:2px 10px;font-size:10px;cursor:pointer;border-radius:3px">▶ 播放</button>
        <button v-else @click="$emit('pause')" style="background:#E65100;color:#fff;border:none;padding:2px 10px;font-size:10px;cursor:pointer;border-radius:3px">⏸ 暂停</button>
        <button @click="$emit('stop')" style="background:#555;color:#fff;border:none;padding:2px 10px;font-size:10px;cursor:pointer;border-radius:3px">⏹ 停止</button>
        <button @click="$emit('renderAll')" style="background:#FF6F00;color:#fff;border:none;padding:2px 10px;font-size:10px;cursor:pointer;border-radius:3px">⚡ 一键渲染</button>
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
import { ref } from 'vue'

const props = defineProps<{
  relayUrl: string
  rangeType: 'frames' | 'time'
  startN: number
  endN: number
  startMin: number
  endMin: number
  timeout: number
  loaded: boolean
  locCount: number
  detCount: number
  playing: boolean
  current: number
  total: number
}>()

defineEmits<{
  'update:relayUrl': [v: string]
  'update:rangeType': [v: 'frames' | 'time']
  'update:startN': [v: number]
  'update:endN': [v: number]
  'update:startMin': [v: number]
  'update:endMin': [v: number]
  'update:timeout': [v: number]
  load: []
  play: []
  pause: []
  stop: []
  renderAll: []
}>()

const testResult = ref<boolean | null>(null)

async function doTest() {
  testResult.value = null
  try {
    const r = await fetch(props.relayUrl + '/status', { method: 'GET', signal: AbortSignal.timeout(3000) })
    testResult.value = r.ok
  } catch {
    testResult.value = false
  }
}
</script>
