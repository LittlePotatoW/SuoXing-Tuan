<script setup lang="ts">
import { onLaunch } from '@dcloudio/uni-app'
import { useAuth } from '@/utils/auth'

const { checkAuth } = useAuth()

onLaunch(() => {
  const isAuthed = checkAuth()
  if (isAuthed) {
    uni.reLaunch({ url: '/pages/index/index' })
  }
})
</script>

<style lang="scss">
/* ===== Tuan App 设计规范全局样式 ===== */

$primary: #171717;
$text-primary: #111111;
$text-secondary: #5F5F5F;
$text-tertiary: #8E8E8E;
$text-placeholder: #B5B5B5;

$bg-page: #F7F7F7;
$bg-card: #FFFFFF;
$bg-module: #F1F1F1;

$border-light: #E8E8E8;

$shadow-weak: 0 4rpx 16rpx rgba(0, 0, 0, 0.04);
$shadow-standard: 0 8rpx 24rpx rgba(0, 0, 0, 0.06);

$radius-md: 18rpx;
$radius-lg: 22rpx;

page {
  margin: 0;
  padding: 0;
  width: 100%;
  background: $bg-page;
  font-family: 'PingFang SC', 'SF Pro Display', Inter, system-ui, -apple-system, sans-serif;
  min-height: 100vh;
  color: $text-primary;
  font-size: 28rpx;
  line-height: 1.5;
  box-sizing: border-box;
}

view, text, scroll-view, image, input, button {
  box-sizing: border-box;
}

/* ===== 全局按钮重置（修复微信小程序按钮默认样式，不覆盖 line-height） ===== */
button {
  padding: 0;
  margin: 0;
  font-family: inherit;

  &::after {
    display: none;
    border: none;
  }
}

.page-container {
  min-height: 100vh;
  padding-bottom: calc(120rpx + env(safe-area-inset-bottom));
  overflow-x: hidden;
  box-sizing: border-box;
}

/* ===== 卡片 ===== */
.card {
  background: $bg-card;
  border-radius: $radius-lg;
  border: 1rpx solid $border-light;
  box-shadow: $shadow-standard;
  padding: 40rpx;
}

/* ===== 按钮 ===== */
.btn-primary {
  height: 104rpx;
  border-radius: $radius-md;
  background: $primary;
  color: #FFFFFF;
  font-size: 32rpx;
  font-weight: 600;
  border: none;
  box-shadow: 0 8rpx 24rpx rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;

  &:active {
    opacity: 0.9;
    transform: scale(0.98);
  }
}

.btn-secondary {
  height: 104rpx;
  border-radius: $radius-md;
  background: $bg-module;
  color: $primary;
  font-size: 30rpx;
  font-weight: 600;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;

  &:active {
    background: #E5E5E5;
  }
}

/* ===== 文字层级 ===== */
.text-title {
  font-size: 68rpx;
  font-weight: 700;
  color: $text-primary;
  line-height: 1.2;
}

.text-heading {
  font-size: 56rpx;
  font-weight: 700;
  color: $text-primary;
  line-height: 1.2;
}

.text-body {
  font-size: 30rpx;
  font-weight: 400;
  color: $text-secondary;
  line-height: 1.6;
}

.text-sm {
  font-size: 26rpx;
  color: $text-tertiary;
}
</style>
