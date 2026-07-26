<template>
  <view class="control-page">
    <!-- ===== 顶部导航栏 ===== -->
    <view class="control-header">
      <view class="back-btn" @click="goBack">
        <text class="back-icon">‹</text>
      </view>
      <text class="page-title">远程遥控</text>
      <view class="header-spacer" />
    </view>

    <!-- ===== 摄像头画面区 ===== -->
    <view class="camera-panel">
      <view class="camera-feed">
        <image class="feed-image" src="/static/camera-feed.jpg" mode="aspectFill" />

        <!-- 浮层标签 -->
        <view class="camera-overlay">
          <view class="overlay-top">
            <view class="tag tag-battery">
              <AppIcon name="battery" :size="20" color="#7BC8A4" />
              <text>{{ batteryLevel }}%</text>
            </view>
            <view class="tag tag-live">
              <view class="live-dot" />
              <text>Live</text>
            </view>
          </view>

          <view class="overlay-top-right">
            <view class="tag tag-quality">
              <text>1080p · 30fps</text>
            </view>
          </view>

          <view class="overlay-bottom">
            <text class="tag-time">{{ currentTime }}</text>
            <view class="tag tag-latency">
              <text>{{ signalStrength }}</text>
            </view>
          </view>
        </view>

        <!-- 底部状态行 -->
        <view class="camera-status-row">
          <view class="cs-item">
            <view class="cs-dot cs-dot-online" />
            <text>在线</text>
          </view>
          <text class="cs-sep">|</text>
          <view class="cs-item">
            <text>延迟 42ms</text>
          </view>
          <text class="cs-sep">|</text>
          <view class="cs-item">
            <text>手动控制</text>
          </view>
          <text class="cs-sep">|</text>
          <view class="cs-item">
            <text>信号强</text>
          </view>
        </view>
      </view>

      <view v-if="flashVisible" class="camera-flash" />
    </view>

    <!-- ===== 截图 / 关闭按钮 ===== -->
    <view class="action-row">
      <view class="action-btn capture-btn" @click="captureFrame">
        <AppIcon name="camera" :size="32" color="#FFFFFF" />
        <text>截图</text>
      </view>
      <view class="action-btn close-btn" @click="stopCamera">
        <AppIcon name="stop-circle" :size="32" color="#D5564D" />
        <text>关闭设备</text>
      </view>
    </view>

    <!-- ===== 虚拟摇杆 + 独立急停 ===== -->
    <view class="joystick-panel">
      <!-- 摇杆底座 -->
      <view
        class="joystick-base"
        @touchstart.prevent="onJoystickStart"
        @touchmove.prevent="onJoystickMove"
        @touchend.prevent="onJoystickEnd"
      >
        <view class="js-cross-v" />
        <view class="js-cross-h" />
        <text class="js-dir js-dir-n">前</text>
        <text class="js-dir js-dir-s">后</text>
        <text class="js-dir js-dir-w">左</text>
        <text class="js-dir js-dir-e">右</text>

        <view
          class="joystick-thumb"
          :class="{ active: isDragging }"
          :style="thumbStyle"
        >
          <view class="thumb-dot" />
        </view>
      </view>

      <!-- 急停扇环（Canvas 仅覆盖左上弧段区） -->
      <canvas
        class="estop-canvas"
        canvas-id="estopCanvas"
        :style="{ width: arcW + 'px', height: arcH + 'px' }"
        @click="emergencyStop"
      />

      <view class="speed-indicator">
        <text class="speed-num">{{ currentSpeed.toFixed(1) }}</text>
        <text class="speed-unit">m/s</text>
      </view>
    </view>

    <!-- ===== 底部状态栏 ===== -->
    <view class="status-footer">
      <view class="sf-item">
        <AppIcon name="gauge" :size="28" color="#7BC8A4" />
        <text class="sf-label">速度</text>
        <text class="sf-val">{{ currentSpeed }} m/s</text>
      </view>
      <view class="sf-item">
        <AppIcon name="shield" :size="28" color="#7BC8A4" />
        <text class="sf-label">安全状态</text>
        <text class="sf-val">正常</text>
      </view>
      <view class="sf-item">
        <AppIcon name="radio" :size="28" color="#7BC8A4" />
        <text class="sf-label">机器人</text>
        <text class="sf-val">已连接</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, getCurrentInstance } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import { robotState } from '@/utils/robotStore'
import { simSetDirection } from '@/utils/robotSimulator'
import { sendCommand } from '@/utils/robotSocket'

// ===== 状态（绑定 robotStore） =====
const batteryLevel = computed(() => Math.round(robotState.battery))
const signalStrength = computed(() => robotState.signal)
const currentSpeed = computed(() => +robotState.controlSpeed.toFixed(2))
const flashVisible = ref(false)

// ===== 虚拟摇杆 =====
const isDragging = ref(false)
const thumbOffset = ref({ x: 0, y: 0 }) // px
const joystickMaxR = ref(90) // 摇杆最大拖拽半径 px
let baseCenter = { x: 0, y: 0 } // 底座圆心屏幕坐标
let pxRatio = 1 // rpx→px 换算比
const arcW = ref(140)  // canvas 宽 px，右下角=摇杆圆心
const arcH = ref(140)  // canvas 高 px

const thumbStyle = computed(() => {
  const { x, y } = thumbOffset.value
  return `transform: translate(${x}px, ${y}px)`
})

/** 触摸开始 — 记录底座中心位置 */
function onJoystickStart(e: any) {
  const touch = e.touches[0]
  const query = uni.createSelectorQuery()
  query.select('.joystick-base').boundingClientRect((rect: any) => {
    if (!rect) return
    baseCenter = { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 }
    joystickMaxR.value = rect.width / 2 - 32
    isDragging.value = true
    moveThumb(touch.clientX, touch.clientY)
  }).exec()
}

/** 触摸移动 — 更新摇杆位置 */
function onJoystickMove(e: any) {
  if (!isDragging.value) return
  const touch = e.touches[0]
  moveThumb(touch.clientX, touch.clientY)
}

/** 触摸结束 — 摇杆回中 */
function onJoystickEnd() {
  isDragging.value = false
  thumbOffset.value = { x: 0, y: 0 }
  // 停止机器人
  robotState.controlDirection = ''
  if (robotState.connected && robotState.mode === 'realtime') {
    sendCommand('stop')
  } else {
    simSetDirection('stop')
  }
}

/** 根据触摸坐标计算摇杆偏移 + 方向 */
function moveThumb(touchX: number, touchY: number) {
  let dx = touchX - baseCenter.x
  let dy = touchY - baseCenter.y
  const dist = Math.sqrt(dx * dx + dy * dy)
  const maxR = joystickMaxR.value

  // 限制在最大半径内
  if (dist > maxR) {
    dx = (dx / dist) * maxR
    dy = (dy / dist) * maxR
  }

  thumbOffset.value = { x: dx, y: dy }

  // 将偏移转为方向和速度
  if (dist < 8) {
    // 死区：太靠近中心视为停止
    robotState.controlDirection = ''
    simSetDirection('')
    return
  }

  const power = Math.min(dist / maxR, 1)
  const speedMs = 0.5 + power * 2.5

  // 角度 → 方向
  const angle = Math.atan2(dy, dx) * (180 / Math.PI) // -180 ~ 180, 0=右
  let dir: string

  if (angle > -22.5 && angle <= 22.5) {
    dir = 'right'
  } else if (angle > 22.5 && angle <= 67.5) {
    dir = 'backward_right'
  } else if (angle > 67.5 && angle <= 112.5) {
    dir = 'backward'
  } else if (angle > 112.5 && angle <= 157.5) {
    dir = 'backward_left'
  } else if (angle > -67.5 && angle <= -22.5) {
    dir = 'forward_right'
  } else if (angle > -112.5 && angle <= -67.5) {
    dir = 'forward'
  } else if (angle > -157.5 && angle <= -112.5) {
    dir = 'forward_left'
  } else {
    dir = 'left'
  }

  robotState.controlDirection = dir
  robotState.controlSpeed = +speedMs.toFixed(2)
  // 路由：连接服务器则发 WebSocket，否则本地模拟
  if (robotState.connected && robotState.mode === 'realtime') {
    sendCommand(dir)
  } else {
    simSetDirection(dir)
  }
}

// ===== 当前时间 =====
const currentTime = ref('')
let timeTimer: ReturnType<typeof setInterval> | null = null

function updateTime() {
  const now = new Date()
  const h = String(now.getHours()).padStart(2, '0')
  const m = String(now.getMinutes()).padStart(2, '0')
  const s = String(now.getSeconds()).padStart(2, '0')
  currentTime.value = `${h}:${m}:${s}`
}

onMounted(() => {
  updateTime()
  timeTimer = setInterval(updateTime, 1000)
  const sys = uni.getSystemInfoSync()
  pxRatio = sys.windowWidth / 750
  arcW.value = Math.round(320 * pxRatio)
  arcH.value = Math.round(320 * pxRatio)
  setTimeout(drawEstop, 300)
})

/** Canvas 绘制急停扇环（旧 API） */
function drawEstop() {
  // #ifdef MP-WEIXIN
  const instance = getCurrentInstance()
  const ctx = uni.createCanvasContext('estopCanvas', instance?.proxy as any)
  if (!ctx) return
  const cx = arcW.value
  const cy = arcH.value
  const outerR = 295 * pxRatio
  const innerR = 240 * pxRatio
  const startA = Math.PI * 1.05  // ~189°
  const endA   = Math.PI * 1.45  // ~261°

  ctx.beginPath()
  ctx.arc(cx, cy, outerR, startA, endA, false)
  ctx.arc(cx, cy, innerR, endA, startA, true)
  ctx.closePath()
  // 填充
  ctx.setFillStyle('rgba(190,50,50,0.55)')
  ctx.fill()
  // 外描边
  ctx.setStrokeStyle('rgba(230,90,90,0.75)')
  ctx.setLineWidth(2.5 * pxRatio)
  ctx.stroke()
  // 内弧描边（更亮）
  ctx.beginPath()
  ctx.arc(cx, cy, innerR, startA, endA, false)
  ctx.setStrokeStyle('rgba(240,120,120,0.6)')
  ctx.setLineWidth(1.5 * pxRatio)
  ctx.stroke()
  // 文字绘制在弧段中点
  const midR = (outerR + innerR) / 2
  const midA = (startA + endA) / 2
  const tx = cx + midR * Math.cos(midA)
  const ty = cy + midR * Math.sin(midA)
  ctx.setFontSize(13)
  ctx.setFillStyle('rgba(255,235,230,0.95)')
  ctx.setTextAlign('center')
  ctx.setTextBaseline('middle')
  ctx.fillText('急停', tx, ty)
  ctx.draw()
  // #endif
}

onUnmounted(() => {
  if (timeTimer) clearInterval(timeTimer)
})

// ===== 操作 =====
function goBack() {
  uni.navigateBack()
}

function captureFrame() {
  flashVisible.value = true
  setTimeout(() => {
    flashVisible.value = false
  }, 200)
  uni.showToast({ title: '画面已截图保存', icon: 'success', duration: 1200 })
}

function stopCamera() {
  uni.showModal({
    title: '关闭摄像头',
    content: '确定要关闭实时画面吗？',
    confirmText: '关闭',
    cancelText: '取消',
    confirmColor: '#EF4444',
    success(res) {
      if (res.confirm) {
        uni.navigateBack()
      }
    },
  })
}

function emergencyStop() {
  if (robotState.controlDirection || robotState.controlSpeed > 0) {
    robotState.controlDirection = ''
    if (robotState.connected && robotState.mode === 'realtime') {
      sendCommand('stop')
    } else {
      simSetDirection('stop')
    }
    isDragging.value = false
    thumbOffset.value = { x: 0, y: 0 }
    uni.vibrateShort({ type: 'heavy' })
    uni.showToast({ title: '紧急停止', icon: 'none', duration: 1000 })
  } else {
    uni.showToast({ title: '已就绪', icon: 'none', duration: 800 })
  }
}

</script>

<style lang="scss" scoped>
/* ===== 深色工业控制台 Token ===== */
$bg-deep: #070B12;
$bg-mid: #0D1522;
$bg-surface: rgba(255, 255, 255, 0.04);
$bg-glass: rgba(255, 255, 255, 0.07);
$bg-glass-hover: rgba(255, 255, 255, 0.12);

$text-primary: #F5F7FB;
$text-secondary: rgba(255, 255, 255, 0.6);
$text-muted: rgba(255, 255, 255, 0.35);

$border-weak: rgba(180, 195, 220, 0.12);
$border-mid: rgba(180, 195, 220, 0.2);
$border-glow: rgba(120, 160, 255, 0.5);

$brand-blue: #4F6FB8;
$brand-blue-light: #5B7FD0;
$danger-red: #D5564D;
$danger-glow: rgba(213, 86, 77, 0.35);
$accent-mint: #7BC8A4;

$radius-sm: 12rpx;
$radius-md: 18rpx;
$radius-lg: 28rpx;
$radius-xl: 36rpx;
$radius-full: 999px;

/* ===== 页面容器 ===== */
.control-page {
  min-height: 100vh;
  background: radial-gradient(circle at 50% 0%, #172033 0%, #0B111C 45%, #070B12 100%);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-family: 'PingFang SC', 'SF Pro Display', Inter, system-ui, -apple-system, sans-serif;
}

/* ===== 顶部导航 ===== */
.control-header {
  display: flex;
  align-items: center;
  padding: calc(var(--status-bar-height) + 16rpx) 32rpx 16rpx;
  flex-shrink: 0;
}

.back-btn {
  width: 88rpx;
  height: 88rpx;
  border-radius: $radius-full;
  background: $bg-glass;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  &:active {
    background: $bg-glass-hover;
  }
}

.back-icon {
  font-size: 56rpx;
  color: $text-primary;
  font-weight: 200;
  line-height: 1;
  margin-top: -4rpx;
}

.page-title {
  flex: 1;
  text-align: center;
  font-size: 36rpx;
  font-weight: 700;
  color: $text-primary;
  letter-spacing: 2rpx;
}

.header-spacer {
  width: 88rpx;
  flex-shrink: 0;
}

/* ===== 摄像头画面 ===== */
.camera-panel {
  flex-shrink: 0;
  margin: 12rpx 28rpx 0;
  position: relative;
}

.camera-feed {
  position: relative;
  height: 540rpx;
  border-radius: $radius-lg;
  overflow: hidden;
  border: 1rpx solid rgba(140, 160, 190, 0.24);
}

.feed-image {
  position: absolute;
  top: 0; right: 0; bottom: 0; left: 0;
  width: 100%;
  height: 100%;
}

/* -- 浮层标签 -- */
.camera-overlay {
  position: absolute;
  top: 0; right: 0; bottom: 0; left: 0;
  padding: 20rpx 24rpx;
  pointer-events: none;
}

.overlay-top {
  display: flex;
  gap: 16rpx;
}

.overlay-top-right {
  position: absolute;
  top: 20rpx;
  right: 24rpx;
}

.overlay-bottom {
  position: absolute;
  bottom: 60rpx;
  left: 24rpx;
  right: 24rpx;
  display: flex;
  justify-content: space-between;
}

.tag {
  display: flex;
  align-items: center;
  gap: 8rpx;
  padding: 8rpx 18rpx;
  border-radius: 20rpx;
  background: rgba(0, 0, 0, 0.55);
  font-size: 22rpx;
  font-weight: 600;
  color: $text-primary;
}

.tag-battery {
  color: $accent-mint;
}

.live-dot {
  width: 12rpx;
  height: 12rpx;
  border-radius: 50%;
  background: #EF4444;
  box-shadow: 0 0 10rpx rgba(239, 68, 68, 0.6);
  animation: livePulse 1.2s ease-in-out infinite;
}

@keyframes livePulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.tag-time {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.8);
  font-weight: 600;
  padding: 8rpx 18rpx;
  border-radius: 20rpx;
  background: rgba(0, 0, 0, 0.55);
}

/* -- 底部状态行 -- */
.camera-status-row {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16rpx;
  padding: 14rpx 24rpx;
  background: rgba(0, 0, 0, 0.5);
}

.cs-item {
  display: flex;
  align-items: center;
  gap: 8rpx;
  font-size: 22rpx;
  color: $text-secondary;
}

.cs-dot {
  width: 10rpx;
  height: 10rpx;
  border-radius: 50%;
}

.cs-dot-online {
  background: $accent-mint;
  box-shadow: 0 0 8rpx rgba(123, 200, 164, 0.5);
}

.cs-sep {
  color: rgba(255, 255, 255, 0.15);
  font-size: 20rpx;
}

/* 拍照闪光 */
.camera-flash {
  position: absolute;
  top: 0; right: 0; bottom: 0; left: 0;
  background: rgba(255, 255, 255, 0.85);
  z-index: 50;
  pointer-events: none;
  border-radius: $radius-lg;
  animation: flashAnim 0.2s ease-out;
}

@keyframes flashAnim {
  from { opacity: 1; }
  to { opacity: 0; }
}

/* ===== 截图 / 关闭按钮 ===== */
.action-row {
  display: flex;
  gap: 24rpx;
  padding: 24rpx 28rpx 20rpx;
  flex-shrink: 0;
}

.action-btn {
  flex: 1;
  height: 88rpx;
  border-radius: $radius-md;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14rpx;
  font-size: 30rpx;
  font-weight: 400;

  &:active {
    opacity: 0.85;
    transform: scale(0.97);
  }
}

.capture-btn {
  background: #355291;
  color: #FFFFFF;
  box-shadow: 0 12rpx 28rpx rgba(53, 82, 145, 0.35);
}

.close-btn {
  background: $bg-glass;
  border: 1rpx solid rgba(255, 255, 255, 0.14);
  color: #D5564D;
}

/* ===== 虚拟摇杆 + 独立急停 ===== */
.joystick-panel {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8rpx 0 16rpx;
  min-height: 0;
}

/* 急停 — Canvas 扇环 */
.estop-canvas {
  position: absolute;
  right: 50%;
  bottom: 50%;
  z-index: 20;
}

/* 摇杆底座 */
.joystick-base {
  position: relative;
  width: 440rpx;
  height: 440rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.02);
  border: 2rpx solid rgba(201, 201, 202, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
}

.js-cross-v {
  position: absolute;
  top: 8%; left: 50%;
  width: 1rpx; height: 84%;
  background: rgba(201, 201, 202, 0.15);
  transform: translateX(-50%);
}

.js-cross-h {
  position: absolute;
  left: 8%; top: 50%;
  width: 84%; height: 1rpx;
  background: rgba(201, 201, 202, 0.15);
  transform: translateY(-50%);
}

.js-dir {
  position: absolute;
  font-size: 22rpx;
  color: rgba(201, 201, 202, 0.35);
  font-weight: 400;
}

.js-dir-n { top: 20rpx; left: 50%; transform: translateX(-50%); }
.js-dir-s { bottom: 20rpx; left: 50%; transform: translateX(-50%); }
.js-dir-w { left: 20rpx; top: 50%; transform: translateY(-50%); }
.js-dir-e { right: 20rpx; top: 50%; transform: translateY(-50%); }

/* 摇杆拖拽头 */
.joystick-thumb {
  position: absolute;
  top: 50%; left: 50%;
  width: 120rpx;
  height: 120rpx;
  margin-left: -60rpx;
  margin-top: -60rpx;
  border-radius: 50%;
  background: rgba(90, 125, 205, 0.12);
  border: 2rpx solid rgba(120, 160, 255, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.15s, box-shadow 0.15s;
  z-index: 5;

  &.active {
    background: rgba(90, 125, 205, 0.25);
    border-color: rgba(120, 160, 255, 0.6);
    box-shadow: 0 0 40rpx rgba(85, 125, 220, 0.35);
  }
}

.thumb-dot {
  width: 40rpx;
  height: 40rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.45);
}

/* 速度指示 */
.speed-indicator {
  position: absolute;
  bottom: 20rpx;
  right: 50%;
  transform: translateX(calc(50% + 220rpx));
  display: flex;
  align-items: baseline;
  gap: 6rpx;
}

.speed-num {
  font-size: 44rpx;
  font-weight: 400;
  color: $accent-mint;
  line-height: 1;
}

.speed-unit {
  font-size: 22rpx;
  font-weight: 400;
  color: rgba(255, 255, 255, 0.3);
}

/* ===== 底部状态栏 ===== */
.status-footer {
  display: flex;
  align-items: center;
  gap: 4rpx;
  margin: 0 28rpx;
  margin-bottom: calc(env(safe-area-inset-bottom) + 12rpx);
  padding: 16rpx 8rpx;
  border-radius: $radius-md;
  background: rgba(255, 255, 255, 0.045);
  border: 1rpx solid rgba(255, 255, 255, 0.1);
  flex-shrink: 0;
}

.sf-item {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6rpx;
  overflow: hidden;
}

.sf-label {
  font-size: 20rpx;
  color: $text-muted;
  white-space: nowrap;
  flex-shrink: 0;
}

.sf-val {
  font-size: 22rpx;
  font-weight: 400;
  color: $text-primary;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
