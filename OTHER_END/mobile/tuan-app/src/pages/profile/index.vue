<template>
  <view class="profile-page">
    <!-- 自定义导航栏 -->
    <view class="nav-bar" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="nav-inner" :style="{ height: navContentHeight + 'px', paddingRight: navRightPad + 'px' }">
        <text class="nav-title">我的</text>
      </view>
    </view>

    <scroll-view
      class="content-scroll"
      scroll-y
      enhanced
      :show-scrollbar="false"
      :style="{ height: scrollHeight + 'px' }"
    >
      <!-- ===== 用户信息大卡片 ===== -->
      <view class="user-card">
        <!-- 主体行：头像 + 信息 + 编辑 -->
        <view class="user-main">
          <view class="avatar-wrap" @click="handleChangeAvatar">
            <image
              v-if="profile.avatar"
              :src="profile.avatar"
              class="avatar-img"
              mode="aspectFill"
            />
            <view v-else class="avatar-placeholder">
              <text class="avatar-initial">{{ profile.nickname.charAt(0) }}</text>
            </view>
            <view class="camera-btn">
              <AppIcon name="camera" :size="20" color="#FFFFFF" />
            </view>
          </view>

          <view class="user-info">
            <text class="nickname">{{ profile.nickname }}</text>
            <text class="bio">{{ profile.intro || '隧道检测工程师' }}</text>
            <view class="status-row">
              <view class="status-pill" :class="statusInfo.value">
                <view class="status-dot" />
                <text>{{ statusInfo.label }}</text>
              </view>
              <text class="sync-time">{{ syncTime }} 已同步</text>
            </view>
          </view>

          <view class="edit-arrow" @click="goToEdit">
            <AppIcon name="chevron-right" :size="32" color="#8E8E8E" />
          </view>
        </view>

        <!-- 底部三列数据 -->
        <view class="user-stats">
          <view class="stat-item">
            <view class="stat-icon stat-icon-blue">
              <AppIcon name="clipboard" :size="30" color="#466CAC" />
            </view>
            <view class="stat-body">
              <text class="stat-label">今日任务</text>
              <view class="stat-val-row">
                <text class="stat-val">2</text>
                <text class="stat-unit">个</text>
              </view>
            </view>
          </view>
          <view class="stat-item">
            <view class="stat-icon stat-icon-purple">
              <AppIcon name="map-pin" :size="30" color="#7C5CED" />
            </view>
            <view class="stat-body">
              <text class="stat-label">负责区段</text>
              <text class="stat-val">隧道 B 区</text>
            </view>
          </view>
          <view class="stat-item">
            <view class="stat-icon stat-icon-green">
              <AppIcon name="gauge" :size="30" color="#7BC8A4" />
            </view>
            <view class="stat-body">
              <text class="stat-label">在线时长</text>
              <view class="stat-val-row">
                <text class="stat-val">2</text>
                <text class="stat-unit">h </text>
                <text class="stat-val">36</text>
                <text class="stat-unit">m</text>
              </view>
            </view>
          </view>
        </view>
      </view>

      <!-- ===== 我的团队 ===== -->
      <view class="team-section">
        <view class="team-header" @click="viewTeamList">
          <text class="team-title">我的团队</text>
          <view class="team-count-wrap">
            <text class="team-count">{{ teamMembers.length }} 位成员{{ teamMembers.length > 4 ? '（共' + teamMembers.length + '位）' : '' }}</text>
            <text class="team-arrow">›</text>
          </view>
        </view>

        <view class="team-card">
          <!-- 前2位成员完整展示 -->
          <view
            v-for="(member, index) in teamMembers.slice(0, 2)"
            :key="member.id || index"
            class="team-member"
            hover-class="tap-active"
            @click="editMember(member)"
          >
            <view class="member-avatar">
              <image v-if="member.avatar" :src="member.avatar" mode="aspectFill" />
              <text v-else class="member-initial">{{ getMemberInitial(member.name) }}</text>
            </view>
            <view class="member-info">
              <view class="member-name-row">
                <text class="member-name">{{ member.name }}</text>
                <text v-if="member.role === 'owner'" class="owner-tag">负责人</text>
              </view>
              <view class="member-status-row">
                <view class="status-dot" :class="'status-' + member.status" />
                <text class="member-status-text">{{ getStatusText(member.status) }}</text>
              </view>
            </view>
          </view>

          <!-- 超出2人 → +N 圆形占位 -->
          <view v-if="teamMembers.length > 2" class="member-dot-avatar" style="marginLeft: -20rpx">
            <text class="dot-initial">+{{ teamMembers.length - 2 }}</text>
          </view>

          <view class="team-add-btn" hover-class="tap-active" @click="showAddMember = true">
            <text class="add-icon">+</text>
          </view>
        </view>
      </view>

      <!-- ===== 功能列表 ===== -->
      <view class="menu-card">
        <view class="menu-item" @click="handleMenuClick('检测记录')">
          <view class="menu-icon-wrap menu-icon-blue">
            <AppIcon name="file-text" :size="36" color="#4F73C2" />
          </view>
          <text class="menu-label">检测记录</text>
          <AppIcon name="chevron-right" :size="24" color="#D1D5DB" />
        </view>

        <view class="menu-item" @click="handleMenuClick('通知')">
          <view class="menu-icon-wrap menu-icon-red">
            <AppIcon name="bell" :size="36" color="#F3B616" />
          </view>
          <text class="menu-label">通知</text>
          <view v-if="notifyCount > 0" class="menu-badge">
            <text class="badge-num">{{ notifyCount }}</text>
          </view>
          <AppIcon name="chevron-right" :size="24" color="#D1D5DB" />
        </view>

        <view class="menu-item" @click="handleMenuClick('设置')">
          <view class="menu-icon-wrap menu-icon-gray">
            <AppIcon name="settings" :size="36" color="#5F5F5F" />
          </view>
          <text class="menu-label">设置</text>
          <AppIcon name="chevron-right" :size="24" color="#D1D5DB" />
        </view>

        <view class="menu-item" @click="handleMenuClick('帮助与反馈')">
          <view class="menu-icon-wrap menu-icon-teal">
            <AppIcon name="help-circle" :size="36" color="#14B8A6" />
          </view>
          <text class="menu-label">帮助与反馈</text>
          <AppIcon name="chevron-right" :size="24" color="#D1D5DB" />
        </view>

        <view class="menu-item menu-item-last" @click="handleMenuClick('关于我们')">
          <view class="menu-icon-wrap menu-icon-indigo">
            <AppIcon name="info" :size="36" color="#6366F1" />
          </view>
          <text class="menu-label">关于我们</text>
          <AppIcon name="chevron-right" :size="24" color="#D1D5DB" />
        </view>
      </view>

      <!-- ===== 退出登录 ===== -->
      <view class="logout-card" @click="handleLogout">
        <AppIcon name="log-out" :size="36" color="#EF4444" />
        <text class="logout-text">退出登录</text>
      </view>

      <view class="bottom-spacer" />
    </scroll-view>

    <!-- 添加成员弹窗 -->
    <view v-if="showAddMember" class="modal-overlay" @click="showAddMember = false">
      <view class="modal-content" @click.stop>
        <text class="modal-title">添加团队成员</text>
        <view class="modal-input-wrap">
          <input
            v-model="searchPhone"
            type="number"
            maxlength="11"
            placeholder="请输入成员手机号"
            class="modal-input"
          />
        </view>
        <view class="modal-actions">
          <view class="modal-btn modal-btn-cancel" @click="showAddMember = false">
            <text>取消</text>
          </view>
          <view class="modal-btn modal-btn-submit" @click="handleAddMember">
            <text>确认添加</text>
          </view>
        </view>
      </view>
    </view>

    <TabBar current="profile" @change="onTabChange" />
  </view>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import TabBar from '@/components/TabBar.vue'
import AppIcon from '@/components/AppIcon.vue'
import { useAuth } from '@/utils/auth'
import { getStorage } from '@/utils/storage'
import {
  getProfile,
  saveProfile,
  getStatusInfo,
  getTeamMembers,
  inviteMemberByPhone,
  getStatusText,
  getMemberInitial,
  type ProfileData,
  type TeamMember,
} from '@/utils/profileStore'

interface NotifyMsg { id: string; read: boolean; state?: string }

const { logout } = useAuth()

const profile = reactive<ProfileData>(getProfile())
const statusInfo = reactive(getStatusInfo(profile.status))

// 导航栏动态尺寸
const statusBarHeight = ref(0)
const navContentHeight = ref(44)
const navRightPad = ref(100)
const scrollHeight = ref(600)

const syncTime = ref('15:38')

// 未读通知数 — 与通知页面共享 storage
function getUnreadCount(): number {
  const msgs = getStorage<NotifyMsg[]>('notify_messages') || []
  return msgs.filter((m) => !m.read).length
}
const notifyCount = ref(getUnreadCount())

onMounted(() => {
  const sys = uni.getSystemInfoSync()
  const windowHeight = sys.windowHeight || 812
  const windowWidth = sys.windowWidth || 375

  statusBarHeight.value = sys.statusBarHeight || 20

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

  scrollHeight.value = windowHeight - statusBarHeight.value - navContentHeight.value - 76
})

onShow(() => {
  const updated = getProfile()
  Object.assign(profile, updated)
  Object.assign(statusInfo, getStatusInfo(profile.status))
  notifyCount.value = getUnreadCount()
  // 刷新团队成员列表（可能在其他地方被修改）
  teamMembers.value = getTeamMembers()
})

// 头像
function handleChangeAvatar() {
  uni.chooseImage({
    count: 1,
    sizeType: ['compressed'],
    sourceType: ['album', 'camera'],
    success(res) {
      const tempPath = res.tempFilePaths[0]
      // 清理旧头像
      if (profile.avatar) {
        uni.getFileSystemManager().unlink({ filePath: profile.avatar })
      }
      // 持久化到本地存储，解决微信小程序 tempFilePath 过期问题
      uni.saveFile({
        tempFilePath: tempPath,
        success(result) {
          profile.avatar = result.savedFilePath
          saveProfile({ ...profile })
        },
        fail() {
          // app-plus 上路径本身是持久的
          profile.avatar = tempPath
          saveProfile({ ...profile })
        },
      })
    },
    fail(err) {
      console.log('chooseImage failed:', err)
    },
  })
}

function goToEdit() {
  uni.navigateTo({ url: '/pages/profile/edit' })
}

function onTabChange(key: string) {
  if (key === 'home') {
    uni.redirectTo({ url: '/pages/index/index' })
  } else if (key === 'inspection') {
    uni.redirectTo({ url: '/pages/inspection/index' })
  }
}

// 菜单
function handleMenuClick(label: string) {
  if (label === '检测记录') {
    uni.navigateTo({ url: '/pages/records/index' })
  } else if (label === '通知') {
    uni.navigateTo({ url: '/pages/notification/index' })
  } else if (label === '设置') {
    uni.navigateTo({ url: '/pages/settings/index' })
  } else if (label === '帮助与反馈') {
    uni.navigateTo({ url: '/pages/feedback/index' })
  } else {
    uni.showToast({ title: `${label}开发中`, icon: 'none', duration: 1500 })
  }
}

// 退出确认
function handleLogout() {
  uni.showModal({
    title: '退出确认',
    content: '确认退出登录？',
    confirmText: '退出',
    confirmColor: '#EF4444',
    cancelText: '取消',
    success(res) {
      if (res.confirm) {
        logout()
      }
    },
  })
}

function viewTeamList() {
  uni.navigateTo({ url: '/pages/team/index' })
}

function editMember(member: { name: string }) {
  uni.showToast({ title: `${member.name} 详情开发中`, icon: 'none', duration: 1500 })
}

// 团队
const teamMembers = ref<TeamMember[]>(getTeamMembers())
const showAddMember = ref(false)
const searchPhone = ref('')

function handleAddMember() {
  if (!searchPhone.value.trim()) {
    uni.showToast({ title: '请输入手机号', icon: 'none', duration: 1500 })
    return
  }
  const result = inviteMemberByPhone(searchPhone.value.trim())
  if (result.success) {
    teamMembers.value = getTeamMembers()
    showAddMember.value = false
    searchPhone.value = ''
  }
  uni.showToast({ title: result.message, icon: result.success ? 'success' : 'none', duration: 2000 })
}
</script>

<style lang="scss" scoped>
/* ===== 引用全局设计 Token (uni.scss) ===== */

.profile-page {
  min-height: 100vh;
  background: $uni-bg-color-grey;
  padding-bottom: calc(120rpx + env(safe-area-inset-bottom));
}

/* ===== 导航栏 ===== */
.nav-bar {
  /* padding-top 由 JS 动态设置 */
}
.nav-inner {
  display: flex;
  align-items: center;
  padding-left: 48rpx;
}
.nav-title {
  font-size: 40rpx;
  font-weight: 700;
  color: $uni-text-color;
  line-height: 1.2;
}

/* ===== 内容滚动 ===== */
.content-scroll {
  padding: 32rpx 40rpx 0;
}

/* ===== 用户大卡片 ===== */
.user-card {
  background: $uni-bg-color;
  border-radius: $uni-border-radius-xl;
  padding: 40rpx;
  box-shadow: $uni-shadow-standard;
  margin-bottom: 48rpx;
}

.user-main {
  display: flex;
  align-items: flex-start;
  gap: 28rpx;
}

.avatar-wrap {
  position: relative;
  width: 128rpx;
  height: 128rpx;
  flex-shrink: 0;
}

.avatar-img {
  width: 128rpx;
  height: 128rpx;
  border-radius: 50%;
}

.avatar-placeholder {
  width: 128rpx;
  height: 128rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, #E0E7FF 0%, #C7D2FE 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-initial {
  font-size: 56rpx;
  font-weight: 600;
  color: $uni-color-brand;
}

.camera-btn {
  position: absolute;
  right: -4rpx;
  bottom: -4rpx;
  width: 44rpx;
  height: 44rpx;
  border-radius: 50%;
  background: $uni-color-brand;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 4rpx solid $uni-bg-color;
  box-shadow: 0 4rpx 12rpx rgba(79, 115, 194, 0.3);
}

.user-info {
  flex: 1;
  min-width: 0;
}

.nickname {
  display: block;
  font-size: 36rpx;
  font-weight: 700;
  color: $uni-text-color;
  line-height: 44rpx;
}

.bio {
  display: block;
  font-size: 28rpx;
  font-weight: 400;
  color: $uni-text-color-secondary;
  margin-top: 8rpx;
  line-height: 34rpx;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin-top: 20rpx;
}

.status-pill {
  display: flex;
  align-items: center;
  gap: 8rpx;
  padding: 6rpx 18rpx;
  border-radius: 24rpx;
  font-size: 28rpx;
  font-weight: 400;

  .status-dot {
    width: 12rpx;
    height: 12rpx;
    border-radius: 50%;
  }

  &.online {
    background: $uni-bg-color-module;
    color: $uni-color-accent-mint;
    .status-dot { background: $uni-color-accent-mint; }
  }
  &.busy {
    background: #FFFBEB;
    color: $uni-color-accent-orange;
    .status-dot { background: $uni-color-accent-orange; }
  }
  &.offline {
    background: $uni-bg-color-module;
    color: $uni-text-color-secondary;
    .status-dot { background: $uni-text-color-tertiary; }
  }
}

.sync-time {
  font-size: 28rpx;
  font-weight: 400;
  color: $uni-text-color-tertiary;
}

.edit-arrow {
  width: 60rpx;
  height: 60rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  &:active {
    background: $uni-bg-color-module;
  }
}

/* ===== 用户三列数据 ===== */
.user-stats {
  display: flex;
  margin-top: 36rpx;
  padding-top: 28rpx;
  border-top: 1rpx solid $uni-border-color-light;
}

.stat-item {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 20rpx;
  min-width: 0;
}

.stat-icon {
  width: 60rpx;
  height: 60rpx;
  border-radius: 20rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon-blue {
  background: $uni-bg-color-module;
}
.stat-icon-purple {
  background: $uni-bg-color-module;
}
.stat-icon-green {
  background: $uni-bg-color-module;
}

.stat-body {
  min-width: 0;
}

.stat-label {
  display: block;
  font-size: 28rpx;
  font-weight: 400;
  color: $uni-text-color-secondary;
  line-height: 32rpx;
  margin-bottom: 8rpx;
}

.stat-val-row {
  display: flex;
  align-items: baseline;
}

.stat-val {
  font-size: 28rpx;
  font-weight: 600;
  color: $uni-text-color;
  line-height: 36rpx;
}

.stat-unit {
  font-size: 28rpx;
  font-weight: 400;
  color: $uni-text-color-secondary;
  line-height: 36rpx;
}

/* ===== 我的团队 ===== */
.team-section {
  margin: 0 0 48rpx;
}

.team-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16rpx;
  padding: 0 8rpx;
}

.team-title {
  font-size: 32rpx;
  font-weight: 600;
  color: $uni-text-color;
}

.team-count-wrap {
  display: flex;
  align-items: center;
  gap: 8rpx;
}

.team-count {
  font-size: 28rpx;
  font-weight: 400;
  color: $uni-text-color-tertiary;
}

.team-arrow {
  font-size: 32rpx;
  color: $uni-text-color-tertiary;
}

/* 团队卡片 */
.team-card {
  min-height: 118rpx;
  padding: 32rpx 40rpx;
  border-radius: $uni-border-radius-xl;
  background: $uni-bg-color;
  box-shadow: $uni-shadow-standard;
  display: flex;
  align-items: center;
  gap: 56rpx;
  overflow-x: auto;
}

/* 成员 */
.team-member {
  position: relative;
  display: flex;
  align-items: center;
  min-width: 0;
}

.member-avatar {
  width: 64rpx;
  height: 64rpx;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
  margin-right: 24rpx;
  background: linear-gradient(135deg, #EEF0FF, #DCD8FF);
  display: flex;
  align-items: center;
  justify-content: center;
}

.member-avatar image {
  width: 100%;
  height: 100%;
}

.member-initial {
  font-size: 30rpx;
  font-weight: 500;
  color: #202332;
}

.member-info {
  min-width: 0;
}

.member-name-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
  white-space: nowrap;
}

.member-name {
  font-size: 28rpx;
  font-weight: 600;
  color: #111827;
  max-width: 160rpx;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  flex-shrink: 0;
}

.owner-tag {
  padding: 6rpx 16rpx;
  border-radius: 999rpx;
  background: #EEF1FF;
  color: #5B68C8;
  font-size: 24rpx;
  font-weight: 400;
  line-height: 1.2;
  flex-shrink: 0;
}

.member-status-row {
  margin-top: 8rpx;
  display: flex;
  align-items: center;
  gap: 8rpx;
  white-space: nowrap;
}

.status-dot {
  width: 12rpx;
  height: 12rpx;
  border-radius: 50%;
}

.status-online {
  background: $uni-color-accent-mint;
}

.status-offline {
  background: $uni-text-color-tertiary;
}

.status-busy {
  background: $uni-color-accent-orange;
}

.member-status-text {
  font-size: 28rpx;
  font-weight: 400;
  color: $uni-text-color-tertiary;
}

.member-phone {
  font-size: 24rpx;
  font-weight: 400;
  color: $uni-text-color-tertiary;
  margin-left: 8rpx;
}

.unverified {
  background: #FFF7ED;
  color: #C2410C;
}

/* +N 圆形占位 */
.member-dot-avatar {
  width: 64rpx;
  height: 64rpx;
  border-radius: 50%;
  background: $uni-bg-color-module;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 4rpx solid $uni-bg-color;
}

.dot-initial {
  font-size: 24rpx;
  font-weight: 400;
  color: $uni-text-color-tertiary;
}

/* 添加按钮 */
.team-add-btn {
  width: 64rpx;
  height: 64rpx;
  border-radius: 50%;
  border: 2rpx dashed #C5CAD6;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: #FAFBFF;
}

.add-icon {
  font-size: 36rpx;
  line-height: 1;
  color: $uni-text-color-tertiary;
  font-weight: 300;
}

.tap-active {
  opacity: 0.72;
  transform: scale(0.98);
}

/* ===== 功能菜单 ===== */
.menu-card {
  background: $uni-bg-color;
  border-radius: $uni-border-radius-lg;
  overflow: hidden;
  box-shadow: $uni-shadow-weak;
  margin-bottom: 48rpx;
}

.menu-item {
  display: flex;
  align-items: center;
  padding: 32rpx;
  gap: 24rpx;
  border-bottom: 1rpx solid $uni-border-color-light;

  &:active {
    background: #FAFAFB;
  }
}

.menu-item-last {
  border-bottom: none;
}

.menu-icon-wrap {
  width: 72rpx;
  height: 72rpx;
  border-radius: $uni-border-radius-base;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.menu-icon-blue  { background: $uni-bg-color-module; }
.menu-icon-red   { background: $uni-bg-color-module; }
.menu-icon-gray  { background: $uni-bg-color-module; }
.menu-icon-teal  { background: $uni-bg-color-module; }
.menu-icon-indigo { background: $uni-bg-color-module; }

.menu-label {
  flex: 1;
  font-size: 32rpx;
  font-weight: 400;
  color: $uni-text-color;
}

/* 通知角标 */
.menu-badge {
  min-width: 40rpx;
  height: 40rpx;
  border-radius: 20rpx;
  background: $uni-color-error;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 10rpx;
}

.badge-num {
  font-size: 22rpx;
  font-weight: 500;
  color: $uni-bg-color;
}

/* ===== 退出登录 ===== */
.logout-card {
  background: $uni-bg-color;
  border-radius: $uni-border-radius-lg;
  padding: 32rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16rpx;
  box-shadow: $uni-shadow-weak;

  &:active {
    background: #FEF2F2;
  }
}

.logout-text {
  font-size: 32rpx;
  font-weight: 400;
  color: $uni-color-error;
}

.bottom-spacer {
  height: 60rpx;
}

/* ===== 弹窗 ===== */
.modal-overlay {
  position: fixed;
  top: 0; right: 0; bottom: 0; left: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 0 48rpx;
}

.modal-content {
  width: 100%;
  max-width: 600rpx;
  background: $uni-bg-color;
  border-radius: 40rpx;
  padding: 44rpx 36rpx;
}

.modal-title {
  display: block;
  font-size: 34rpx;
  font-weight: 600;
  color: $uni-text-color;
  text-align: center;
  margin-bottom: 24rpx;
}

.modal-input-wrap {
  margin-bottom: 24rpx;
}

.modal-input {
  width: 100%;
  height: 96rpx;
  padding: 0 28rpx;
  border: 1rpx solid #D1D5DB;
  border-radius: 24rpx;
  font-size: 28rpx;
  color: $uni-text-color;
  background: #F9FAFB;
  box-sizing: border-box;
}

.modal-actions {
  display: flex;
  gap: 20rpx;
}

.modal-btn {
  flex: 1;
  height: 96rpx;
  border-radius: 32rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30rpx;
  font-weight: 600;

  &:active {
    opacity: 0.85;
  }
}

.modal-btn-cancel {
  background: $uni-bg-color-module;
  color: $uni-text-color-secondary;
}

.modal-btn-submit {
  background: $uni-color-brand;
  color: $uni-bg-color;
}
</style>
