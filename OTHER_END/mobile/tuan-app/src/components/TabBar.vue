<template>
  <view class="tab-bar">
    <view
      v-for="item in tabs"
      :key="item.key"
      class="tab-item"
      :class="{ active: current === item.key }"
      @click="switchTab(item.key)"
    >
      <AppIcon
        :name="item.icon"
        :size="44"
        :color="current === item.key ? '#466CAC' : '#9AA2AD'"
      />
      <text class="tab-label" :class="{ active: current === item.key }">
        {{ item.label }}
      </text>
    </view>
  </view>
</template>

<script setup lang="ts">
import AppIcon from '@/components/AppIcon.vue'

const props = defineProps<{
  current: string
}>()

const emit = defineEmits<{
  change: [key: string]
}>()

const tabs = [
  { key: 'inspection', label: '巡检', icon: 'clipboard' },
  { key: 'home', label: '首页', icon: 'home' },
  { key: 'profile', label: '我的', icon: 'user' },
]

function switchTab(key: string) {
  if (key === props.current) return
  emit('change', key)
}
</script>

<style lang="scss" scoped>
$brand-blue: #466CAC;
$bg-glass: rgba(255, 255, 255, 0.95);

.tab-bar {
  position: fixed;
  bottom: 0;
  left: 12rpx;
  right: 12rpx;
  z-index: 999;
  display: flex;
  height: 126rpx;
  padding-top: 16rpx;
  padding-bottom: env(safe-area-inset-bottom);
  background: $bg-glass;
  border-radius: 34rpx 34rpx 0 0;
  box-shadow: 0 -8rpx 32rpx rgba(37, 48, 68, 0.06);
  border: 1rpx solid #EEF1F4;
}

.tab-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  gap: 4rpx;
  padding-top: 4rpx;
  transition: color 0.2s ease;
}

.tab-label {
  font-size: 20rpx;
  font-weight: 500;
  color: #8E8E8E;
  transition: color 0.2s ease;
  line-height: 24rpx;

  &.active {
    color: #111111;
  }
}

</style>
