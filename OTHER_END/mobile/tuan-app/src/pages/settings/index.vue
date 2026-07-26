<template>
  <view class="page">
    <!-- 导航栏 -->
    <view class="nav-bar" :style="{ paddingTop: statusBarH + 'px' }">
      <view class="nav-inner" :style="{ height: navH + 'px', paddingRight: navPad + 'px' }">
        <view class="nav-left" @click="goBack">
          <text class="back-icon">‹</text>
        </view>
        <text class="nav-title">设置</text>
        <view class="nav-spacer" />
      </view>
    </view>

    <view class="body-wrap" :style="{ paddingTop: navTotalH + 'px' }">
    <scroll-view class="content" scroll-y enhanced :show-scrollbar="false">
      <!-- 账号与安全 -->
      <view class="section">
        <text class="section-title">账号与安全</text>
        <view class="card">
          <view class="item" @click="goPage('个人资料')">
            <text class="item-label">个人资料</text>
            <AppIcon name="chevron-right" :size="22" color="#D1D5DB" />
          </view>
          <view class="item" @click="goPage('修改密码')">
            <text class="item-label">修改密码</text>
            <AppIcon name="chevron-right" :size="22" color="#D1D5DB" />
          </view>
          <view class="item item-last" @click="goPage('账号绑定')">
            <text class="item-label">账号绑定</text>
            <text class="item-hint">手机号 {{ maskedPhone }}</text>
            <AppIcon name="chevron-right" :size="22" color="#D1D5DB" />
          </view>
        </view>
      </view>

      <!-- 通知设置 -->
      <view class="section">
        <text class="section-title">通知设置</text>
        <view class="card">
          <view class="item">
            <text class="item-label">消息通知</text>
            <switch :checked="settings.notifyMaster" color="#3B82F6" @change="toggleNotify('notifyMaster')" />
          </view>
          <view class="item">
            <text class="item-label">任务提醒</text>
            <switch :checked="settings.taskRemind" color="#3B82F6" @change="toggleNotify('taskRemind')" />
          </view>
          <view class="item">
            <text class="item-label">团队邀请</text>
            <switch :checked="settings.teamInvite" color="#3B82F6" @change="toggleNotify('teamInvite')" />
          </view>
          <view class="item">
            <text class="item-label">告警推送</text>
            <switch :checked="settings.alertPush" color="#3B82F6" @change="toggleNotify('alertPush')" />
          </view>
          <view class="item item-last">
            <text class="item-label">系统公告</text>
            <switch :checked="settings.systemNotice" color="#3B82F6" @change="toggleNotify('systemNotice')" />
          </view>
        </view>
      </view>

      <!-- 通用设置 -->
      <view class="section">
        <text class="section-title">通用设置</text>
        <view class="card">
          <view class="item" @click="goPage('语言切换')">
            <text class="item-label">语言切换</text>
            <text class="item-hint">简体中文</text>
            <AppIcon name="chevron-right" :size="22" color="#D1D5DB" />
          </view>
          <view class="item" @click="clearCache">
            <text class="item-label">缓存清理</text>
            <text class="item-hint">{{ cacheSize }}</text>
            <AppIcon name="chevron-right" :size="22" color="#D1D5DB" />
          </view>
          <view class="item item-last">
            <text class="item-label">深色模式</text>
            <switch :checked="settings.darkMode" color="#3B82F6" @change="toggleNotify('darkMode')" />
          </view>
        </view>
      </view>

      <!-- 关于 -->
      <view class="section">
        <text class="section-title">关于</text>
        <view class="card">
          <view class="item" @click="checkUpdate">
            <text class="item-label">版本号</text>
            <text class="item-hint">v1.0.0</text>
          </view>
          <view class="item" @click="checkUpdate">
            <text class="item-label">检查更新</text>
            <text class="item-badge">最新</text>
            <AppIcon name="chevron-right" :size="22" color="#D1D5DB" />
          </view>
          <view class="item" @click="goPage('用户协议')">
            <text class="item-label">用户协议</text>
            <AppIcon name="chevron-right" :size="22" color="#D1D5DB" />
          </view>
          <view class="item item-last" @click="goPage('隐私政策')">
            <text class="item-label">隐私政策</text>
            <AppIcon name="chevron-right" :size="22" color="#D1D5DB" />
          </view>
        </view>
      </view>

      <!-- 退出登录 -->
      <view class="logout-card" @click="handleLogout">
        <AppIcon name="log-out" :size="36" color="#EF4444" />
        <text class="logout-text">退出登录</text>
      </view>

      <view class="bottom-spacer" />
    </scroll-view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import { useAuth } from '@/utils/auth'
import { useNavBar } from '@/composables/useNavBar'

const { currentPhone } = useAuth()

const maskedPhone = computed(() => {
  const p = currentPhone.value
  if (!p || p.length < 7) return '未绑定'
  return p.slice(0, 3) + '****' + p.slice(-4)
})

const { statusBarH, navH, navPad, navTotalH } = useNavBar()
const cacheSize = ref('2.3 MB')

interface Settings {
  notifyMaster: boolean; taskRemind: boolean; teamInvite: boolean;
  alertPush: boolean; systemNotice: boolean; darkMode: boolean;
}
const settings = reactive<Settings>({
  notifyMaster: true, taskRemind: true, teamInvite: true,
  alertPush: true, systemNotice: true, darkMode: false,
})

function toggleNotify(key: keyof Settings) {
  settings[key] = !settings[key]
  uni.setStorageSync('app_settings', { ...settings })
}

function goPage(name: string) {
  const routes: Record<string, string> = {
    '个人资料': '/pages/profile/edit',
    '修改密码': '/pages/password/change',
    '账号绑定': '/pages/settings/index',
    '语言切换': '/pages/settings/index',
    '用户协议': '/pages/settings/index',
    '隐私政策': '/pages/settings/index',
  }
  const url = routes[name]
  if (url) {
    uni.navigateTo({ url })
  } else {
    uni.showToast({ title: `${name} 开发中`, icon: 'none', duration: 1200 })
  }
}
function clearCache() {
  cacheSize.value = '0 KB'
  uni.showToast({ title: '缓存已清理', icon: 'success', duration: 1200 })
}
function checkUpdate() {
  uni.showToast({ title: '已是最新版本', icon: 'success', duration: 1200 })
}
function handleLogout() {
  uni.showModal({
    title: '退出确认', content: '确认退出登录？',
    confirmText: '退出', confirmColor: '#EF4444', cancelText: '取消',
    success(res) { if (res.confirm) { auth.logout() } },
  })
}
function goBack() { uni.navigateBack() }

onMounted(() => {
  const saved = uni.getStorageSync('app_settings')
  if (saved) Object.assign(settings, saved)
})
</script>

<style lang="scss" scoped>
/* ===== 引用全局设计 Token (uni.scss) ===== */

.page { min-height: 100vh; background: $uni-bg-color-grey; }
.nav-bar { position:fixed; top:0; left:0; right:0; z-index:100; background:$uni-bg-color-grey; }
.nav-inner { display:flex; align-items:center; padding-left:40rpx; }
.nav-left { width:72rpx; height:72rpx; border-radius:50%; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.back-icon { font-size:56rpx; color:$uni-text-color; font-weight:300; line-height:1; margin-top:-4rpx; }
.nav-title { font-size:40rpx; font-weight:700; color:$uni-text-color; margin-left:16rpx; }
.nav-spacer { width:72rpx; flex-shrink:0; }

.body-wrap { min-height:100vh; }
.content { height:calc(100vh - 160rpx); padding:20rpx 36rpx 0; }

.section { margin-bottom: 48rpx; }
.section-title { font-size: 28rpx; color: $uni-text-color-tertiary; font-weight: 400; padding: 0 8rpx 16rpx; display: block; }
.card { background: $uni-bg-color; border-radius: $uni-border-radius-lg; overflow: hidden; box-shadow: $uni-shadow-weak; }
.item { display: flex; align-items: center; padding: 32rpx; gap: 16rpx; border-bottom: 1rpx solid $uni-border-color-light; }
.item:active { background: #FAFAFB; }
.item-last { border-bottom: 0; }
.item-label { flex: 1; font-size: 32rpx; font-weight: 400; color: $uni-text-color; }
.item-hint { font-size: 28rpx; font-weight: 400; color: $uni-text-color-tertiary; }
.item-badge { font-size: 24rpx; font-weight: 400; color: #10B981; background: #ECFDF5; padding: 4rpx 16rpx; border-radius: 20rpx; }

.logout-card { display: flex; align-items: center; justify-content: center; gap: 16rpx; padding: 32rpx; background: $uni-bg-color; border-radius: $uni-border-radius-lg; box-shadow: $uni-shadow-weak; }
.logout-card:active { background: #FEF2F2; }
.logout-text { font-size: 32rpx; font-weight: 400; color: $uni-color-error; }

.bottom-spacer { height: 60rpx; }
</style>
