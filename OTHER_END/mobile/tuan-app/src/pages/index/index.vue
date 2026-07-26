<template>
  <view class="page">
    <!-- 自定义导航栏（避开微信右上角胶囊按钮） -->
    <view class="nav-bar" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="nav-inner" :style="{ height: navContentHeight + 'px', paddingRight: navRightPad + 'px' }">
        <view class="nav-header">
          <text class="nav-title">智能巡检</text>
          <text class="nav-sub">巡检机器人管理平台</text>
        </view>
      </view>
    </view>

    <scroll-view
      class="main-scroll"
      :scroll-y="!mapTouching"
      enhanced
      :show-scrollbar="false"
      :style="{ height: scrollHeight + 'px' }"
    >
      <!-- ===== 连接状态条 ===== -->
      <view v-if="connectionLabel" class="conn-bar" :class="'conn-' + robotState.mode">
        <view class="conn-dot" :class="robotState.connected ? 'dot-live' : 'dot-wait'" />
        <text class="conn-text">{{ connectionLabel }}</text>
      </view>

      <!-- ===== 地图卡片 ===== -->
      <view class="map-card" @touchstart="mapTouching = true" @touchend="mapTouching = false">
        <!-- 腾讯地图（微信小程序自动调用） -->
        <map
          id="robotMap"
          class="map-view"
          :latitude="roverGcj.latitude"
          :longitude="roverGcj.longitude"
          :scale="mapScale"
          :markers="mapMarkers"
          :polyline="mapPolyline"
          show-location
          :show-compass="false"
          :show-scale="false"
          :enable-zoom="true"
          :enable-scroll="true"
          :enable-rotate="false"
          @tap="onMapTap"
        />

      </view>

      <!-- ===== 仪表盘（2列网格） ===== -->
      <view class="dashboard">
        <!-- 左侧：巡检车卡片 -->
        <view class="card vehicle-card">
          <view class="card-head">
            <text class="head-title">巡检车 A-03</text>
            <view class="online-badge">
              <view class="online-dot" />
              <text>运行中</text>
            </view>
          </view>

          <!-- 巡检车图 -->
          <view class="rover-stage">
            <image class="rover-img" src="/static/rover.png" mode="aspectFit" />
          </view>

          <view class="vehicle-meta">
            <view class="meta-row">
              <AppIcon name="tool" :size="28" color="#9AA3AD" />
              <text class="meta-text">自动中</text>
            </view>
            <view class="meta-row">
              <AppIcon name="gauge" :size="28" color="#9AA3AD" />
              <text class="meta-text">{{ robotState.controlSpeed.toFixed(1) }} m/s</text>
            </view>
          </view>
        </view>

        <!-- 右侧：设备状态卡片 -->
        <view class="card status-card">
          <view class="card-head">
            <text class="head-title">设备状态</text>
          </view>
          <view class="status-list">
            <view class="status-row">
              <view class="status-icon">
                <AppIcon name="battery" :size="34" color="#88C37B" />
              </view>
              <view class="status-body">
                <text class="status-label">电量状态</text>
                <view class="status-value-row">
                  <text class="status-val" :class="batteryColorClass">{{ batteryLevel }}%</text>
                  <text class="status-tag" :class="batteryTagClass">{{ batteryTag }}</text>
                </view>
              </view>
            </view>

            <view class="status-row">
              <view class="status-icon">
                <AppIcon name="signal" :size="34" color="#5D90DF" />
              </view>
              <view class="status-body">
                <text class="status-label">网络状态</text>
                <view class="status-value-row">
                  <text class="status-val green">强</text>
                  <text class="status-sub">（-65 dBm）</text>
                </view>
              </view>
            </view>

            <view class="status-row">
              <view class="status-icon">
                <AppIcon name="radio" :size="34" color="#7BC8A4" />
              </view>
              <view class="status-body">
                <text class="status-label">环境状态</text>
                <text class="status-val green">良好</text>
              </view>
            </view>

            <view class="status-row">
              <view class="status-icon">
                <AppIcon name="crosshair" :size="34" color="#466CAC" />
              </view>
              <view class="status-body">
                <text class="status-label">行驶里程</text>
                <text class="status-val">{{ robotState.mileage.toFixed(1) }}km</text>
              </view>
            </view>
          </view>
        </view>
      </view>

      <!-- ===== 任务卡片 ===== -->
      <view class="card task-card" @click="goToTask">
        <view class="task-head">
          <view class="task-title">
            <text class="task-label">当前任务</text>
            <text class="task-name">{{ currentTask.name }}</text>
          </view>
          <text class="task-arrow">›</text>
        </view>

        <view class="task-progress">
          <view class="progress-col">
            <text class="progress-label">任务</text>
            <view class="progress-track">
              <view class="progress-fill" :style="{ width: currentTask.progress + '%' }" />
            </view>
            <text class="progress-num">{{ currentTask.progress }}%</text>
          </view>
          <view class="time-col">
            <text class="time-label">预计完成</text>
            <text class="time-val">{{ currentTask.timeRemaining }}</text>
          </view>
        </view>

        <view class="task-next">
          <view class="next-dot">
            <view class="next-pin" />
          </view>
          <text>下一个点位： {{ robotState.nextPoint }}</text>
        </view>
      </view>

      <!-- ===== 进入操控按钮 ===== -->
      <button class="btn-control" @click="enterControl">
        <text>进入遥控 →</text>
      </button>

      <!-- 底部安全间距 -->
      <view class="bottom-spacer" />
    </scroll-view>

    <!-- 底部导航 -->
    <TabBar current="home" @change="onTabChange" />
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, getCurrentInstance } from 'vue'
import TabBar from '@/components/TabBar.vue'
import AppIcon from '@/components/AppIcon.vue'
import { currentTask } from '@/utils/taskStore'
import { robotState } from '@/utils/robotStore'
import { startSimulation, stopSimulation } from '@/utils/robotSimulator'
import { connectRobot, disconnectRobot } from '@/utils/robotSocket'
import { wgs84ToGcj02 } from '@/utils/coordConvert'

const SERVER_HOST = '39.107.253.73:8080'

// ===== 地图数据（WGS-84 → GCJ-02 转换适配腾讯地图） =====
const connectionLabel = computed(() => {
  if (!robotState.connected) return ''
  if (robotState.mode === 'realtime') {
    return robotState.peerId ? `已连接服务器 · ${robotState.peerId}` : '正在连接服务器...'
  }
  return '本地模拟'
})
const mapScale = ref(15)

/** 坐标转换：仅在 realtime 模式（真实 GPS WGS-84）时转为 GCJ-02 */
function toGcj(lat: number, lng: number) {
  if (robotState.mode === 'realtime') {
    // #ifdef MP-WEIXIN
    return wgs84ToGcj02(lat, lng)
    // #endif
  }
  return { latitude: lat, longitude: lng }
}

const roverGcj = computed(() => toGcj(robotState.latitude, robotState.longitude))
const pathGcj = computed(() => robotState.path.map((p) => toGcj(p.latitude, p.longitude)))

const mapMarkers = computed(() => [
  {
    id: 1,
    latitude: roverGcj.value.latitude,
    longitude: roverGcj.value.longitude,
    title: `巡检车 ${robotState.robotId}`,
    width: 28,
    height: 28,
    callout: {
      content: `巡检车 ${robotState.robotId}`,
      fontSize: 12,
      padding: 6,
      display: 'ALWAYS',
    },
  },
  ...pathGcj.value.map((p, i) => ({
    id: i + 2,
    latitude: p.latitude,
    longitude: p.longitude,
    title: `巡检点 K12+${300 + i * 150}`,
    width: 20,
    height: 20,
  })),
])
const mapPolyline = computed(() => [
  {
    points: pathGcj.value,
    color: '#466CAC',
    width: 4,
    dottedLine: false,
  },
])

const batteryLevel = computed(() => robotState.battery)
const batteryTag = computed(() => {
  if (robotState.battery >= 50) return '正常'
  if (robotState.battery >= 20) return '中电'
  return '低电'
})
const batteryTagClass = computed(() => {
  if (robotState.battery >= 50) return 'green'
  if (robotState.battery >= 20) return 'orange'
  return 'red'
})
const batteryColorClass = computed(() => {
  if (robotState.battery >= 50) return 'color-green'
  if (robotState.battery >= 20) return 'color-orange'
  return 'color-red'
})

const statusBarHeight = ref(0)
const navContentHeight = ref(44)
const navRightPad = ref(100)
const scrollHeight = ref(600)

let mapCtx: any = null
const mapTouching = ref(false)

onMounted(() => {
  const sys = uni.getSystemInfoSync()
  const windowHeight = sys.windowHeight || 812
  const windowWidth = sys.windowWidth || 375

  // 状态栏高度
  statusBarHeight.value = sys.statusBarHeight || 20

  // 获取微信胶囊按钮位置（仅在微信小程序环境有效）
  // #ifdef MP-WEIXIN
  try {
    const menuButton = uni.getMenuButtonBoundingClientRect()
    navContentHeight.value = (menuButton.bottom - statusBarHeight.value) + (menuButton.height / 2)
    navRightPad.value = Math.max(windowWidth - menuButton.left + 12, 90)
  } catch (e) {
    navContentHeight.value = 44
    navRightPad.value = 100
  }
  // #endif

  // 滚动区高度
  const navTotalHeight = statusBarHeight.value + navContentHeight.value
  scrollHeight.value = windowHeight - navTotalHeight - 76

  // 尝试连接后端服务器，5秒超时后降级为模拟
  const fallbackTimer = setTimeout(() => {
    if (!robotState.connected) {
      console.log('[App] 服务器无响应，启动本地模拟')
      startSimulation()
    }
  }, 5000)

  connectRobot(SERVER_HOST)

  // 连接成功后取消降级
  const stopFallback = setInterval(() => {
    if (robotState.connected) {
      clearTimeout(fallbackTimer)
      clearInterval(stopFallback)
      console.log('[App] 已连接服务器，模拟器不启动')
    }
  }, 500)

  // 获取地图上下文
  // #ifdef MP-WEIXIN
  const instance = getCurrentInstance()
  mapCtx = uni.createMapContext('robotMap', instance?.proxy as any)
  // #endif
})

onUnmounted(() => {
  stopSimulation()
  disconnectRobot()
})

// 监听位置变化，平滑移动标记
watch(
  () => [robotState.latitude, robotState.longitude],
  () => {
    // #ifdef MP-WEIXIN
    if (mapCtx) {
      mapCtx.translateMarker({
        markerId: 1,
        destination: {
          latitude: robotState.latitude,
          longitude: robotState.longitude,
        },
        duration: 900,
        autoRotate: true,
      })
    }
    // #endif
  },
)

function goToTask() {
  uni.navigateTo({ url: '/pages/task/detail' })
}

function enterControl() {
  uni.navigateTo({ url: '/pages/control/index' })
}

function onMapTap(e: any) {
  console.log('Map tapped:', e.detail)
}

function onTabChange(key: string) {
  if (key === 'inspection') {
    uni.redirectTo({ url: '/pages/inspection/index' })
  } else if (key === 'profile') {
    uni.redirectTo({ url: '/pages/profile/index' })
  }
}
</script>

<style lang="scss" scoped>
/* ===== 引用全局设计 Token (uni.scss) ===== */

/* ===== 页面容器 ===== */
.page {
  min-height: 100vh;
  background: $uni-bg-color-grey;
  font-family: 'PingFang SC', 'SF Pro Display', Inter, system-ui, -apple-system, sans-serif;
  color: $uni-text-color;
  overflow-x: hidden;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

/* ===== 自定义导航栏 ===== */
.nav-bar {
  /* padding-top 由 JS 动态设置 */
}

.nav-inner {
  position: relative;
  display: flex;
  align-items: center;
  padding-left: 48rpx;
  /* height 和 padding-right 由 JS 动态设置 */
}

.nav-header {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}

.nav-title {
  font-size: 40rpx;
  font-weight: 700;
  color: $uni-text-color;
  line-height: 48rpx;
}

.nav-sub {
  font-size: 24rpx;
  font-weight: 400;
  color: $uni-text-color-tertiary;
  line-height: 32rpx;
}


/* ===== 滚动区域 ===== */
.main-scroll {
  /* height 由 JS 动态设置 */
}

/* ===== 连接状态条 ===== */
.conn-bar {
  display: flex;
  align-items: center;
  gap: 12rpx;
  padding: 14rpx 36rpx;
  margin-bottom: 4rpx;
}

.conn-dot {
  width: 14rpx;
  height: 14rpx;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-live {
  background: $uni-color-success;
  box-shadow: 0 0 10rpx rgba(36, 161, 72, 0.5);
  animation: livePulse 1.2s ease-in-out infinite;
}

.dot-wait {
  background: $uni-color-warning;
  animation: livePulse 1.2s ease-in-out infinite;
}

@keyframes livePulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.conn-text {
  font-size: 24rpx;
  font-weight: 400;
  color: $uni-text-color-tertiary;
}

/* ===== 地图卡片 ===== */
.map-card {
  position: relative;
  margin: 0 36rpx;
  height: 680rpx;
  border-radius: $uni-border-radius-lg;
  overflow: hidden;
  background: $uni-bg-cool;
  box-shadow: $uni-shadow-standard;
}

.map-view {
  position: absolute;
  top: 0; right: 0; bottom: 0; left: 0;
  width: 100%;
  height: 100%;
}

/* ===== 仪表盘 2列网格 ===== */
.dashboard {
  display: flex;
  gap: 20rpx;
  margin: 24rpx 36rpx;

  > .card {
    flex: 1;
    min-width: 0;
  }
}

.card {
  background: $uni-bg-color;
  border: 1rpx solid $uni-border-color-light;
  border-radius: $uni-border-radius-lg;
  box-shadow: $uni-shadow-weak;
  overflow: hidden;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4rpx;
}

.head-title {
  font-size: 28rpx;
  font-weight: 600;
  color: $uni-text-color;
}

/* ===== 巡检车卡片 ===== */
.vehicle-card {
  padding: 32rpx;
  display: flex;
  flex-direction: column;
}

.online-badge {
  display: flex;
  align-items: center;
  gap: 6rpx;
  font-size: 24rpx;
  font-weight: 400;
  color: $uni-color-accent-mint;
}

.online-dot {
  width: 12rpx;
  height: 12rpx;
  border-radius: 50%;
  background: $uni-color-accent-mint;
}

/* 巡检车图片 */
.rover-stage {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8rpx 0;
}

.rover-img {
  width: 310rpx;
  height: 224rpx;
}

.vehicle-meta {
  display: flex;
  flex-direction: column;
  gap: 14rpx;
  padding-top: 8rpx;
  border-top: 1rpx solid $uni-border-color-light;
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 14rpx;
}

.meta-text {
  font-size: 28rpx;
  font-weight: 400;
  color: $uni-text-color-secondary;
}

/* ===== 设备状态卡片 ===== */
.status-card {
  padding: 32rpx;
  display: flex;
  flex-direction: column;
}

.status-list {
  display: flex;
  flex-direction: column;
  margin-top: 8rpx;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 16rpx 0;
  border-bottom: 1rpx solid $uni-border-color-light;

  .status-icon {
    flex-shrink: 0;
  }
  .status-body {
    flex: 1;
  }

  &:last-child {
    border-bottom: 0;
    padding-bottom: 0;
  }
}

.status-icon {
  width: 44rpx;
  height: 44rpx;
  border-radius: 50%;
  background: $uni-bg-color-module;
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-body {
  min-width: 0;
  overflow: hidden;
}

.status-label {
  display: block;
  font-size: 28rpx;
  font-weight: 400;
  color: $uni-text-color-tertiary;
  line-height: 32rpx;
}

.status-value-row {
  display: flex;
  align-items: baseline;
  gap: 10rpx;
  margin-top: 4rpx;
}

.status-val {
  font-size: 28rpx;
  font-weight: 600;
  color: $uni-text-color;
  line-height: 34rpx;

  &.green {
    color: #5EA560;
    font-weight: 400;
  }

  &.color-green  { color: $uni-color-success; }
  &.color-orange { color: $uni-color-warning; }
  &.color-red    { color: $uni-color-error; }
}

.status-tag {
  font-size: 28rpx;
  font-weight: 400;
  line-height: 34rpx;

  &.green  { color: $uni-color-success; }
  &.orange { color: $uni-color-warning; }
  &.red    { color: $uni-color-error; }
}

.status-sub {
  font-size: 28rpx;
  font-weight: 400;
  color: $uni-text-color-tertiary;
  white-space: nowrap;
}

/* ===== 任务卡片 ===== */
.task-card {
  margin: 0 36rpx 24rpx;
  padding: 24rpx 24rpx 20rpx;

  &:active {
    background: #FAFAFA;
  }
}

.task-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.task-label {
  display: block;
  font-size: 28rpx;
  font-weight: 400;
  color: $uni-text-color-tertiary;
  line-height: 32rpx;
}

.task-name {
  display: block;
  margin-top: 4rpx;
  font-size: 32rpx;
  font-weight: 600;
  color: $uni-text-color;
  line-height: 40rpx;
}

.task-arrow {
  font-size: 40rpx;
  color: $uni-text-color-tertiary;
  line-height: 30rpx;
}

.task-progress {
  margin-top: 24rpx;
  display: flex;
  gap: 32rpx;
  align-items: flex-end;

  .progress-col {
    flex: 1;
    min-width: 0;
  }
  .time-col {
    width: 140rpx;
    flex-shrink: 0;
  }
}

.progress-label,
.time-label {
  display: block;
  font-size: 28rpx;
  font-weight: 400;
  color: $uni-text-color-tertiary;
  line-height: 32rpx;
}

.progress-track {
  margin-top: 10rpx;
  width: 100%;
  height: 12rpx;
  background: $uni-border-color-light;
  border-radius: 10rpx;
  overflow: hidden;
  display: inline-block;
  vertical-align: middle;
}

.progress-fill {
  height: 100%;
  background: $uni-color-brand;
  border-radius: 10rpx;
  transition: width 0.4s ease;
}

.progress-num {
  margin-left: 12rpx;
  font-size: 28rpx;
  font-weight: 400;
  color: $uni-text-color-secondary;
  vertical-align: middle;
}

.time-val {
  display: block;
  margin-top: 4rpx;
  font-size: 32rpx;
  font-weight: 600;
  color: $uni-text-color;
  line-height: 38rpx;
}

.task-next {
  margin-top: 16rpx;
  border-top: 1rpx solid $uni-border-color-light;
  padding-top: 12rpx;
  display: flex;
  align-items: center;
  gap: 12rpx;
  font-size: 28rpx;
  font-weight: 400;
  color: $uni-text-color-secondary;
}

.next-dot {
  width: 24rpx;
  height: 24rpx;
  border-radius: 50%;
  background: #EDF3FF;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.next-pin {
  width: 10rpx;
  height: 14rpx;
  background: $uni-color-brand;
  border-radius: 10rpx 10rpx 10rpx 0;
  transform: rotate(-45deg);
}

/* ===== 主按钮 ===== */
.btn-control {
  margin: 0 36rpx;
  width: calc(100% - 72rpx);
  height: 104rpx;
  border: none;
  border-radius: $uni-border-radius-base;
  background: $uni-color-brand;
  color: #FFFFFF;
  font-size: 36rpx;
  font-weight: 600;
  font-family: inherit;
  box-shadow: $uni-shadow-standard;
  display: flex;
  align-items: center;
  justify-content: center;

  &:active {
    opacity: 0.9;
    transform: scale(0.98);
  }
}

/* ===== 底部安全间距 ===== */
.bottom-spacer {
  height: 32rpx;
}
</style>
