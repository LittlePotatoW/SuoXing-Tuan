<template>
  <view class="page-container">
    <!-- 自定义导航栏 -->
    <view class="custom-nav" :style="{ paddingTop: statusBarHeight + 'px' }">
      <view class="nav-inner" :style="{ height: navContentHeight + 'px', paddingRight: navRightPad + 'px' }">
        <text class="nav-date">{{ todayFull }}</text>
        <view class="nav-action" @click="openAddModal">
          <AppIcon name="plus-circle" :size="28" color="#FFFFFF" />
          <text class="action-text">添加</text>
        </view>
      </view>
    </view>

    <!-- 搜索栏 -->
    <view class="search-bar">
      <view class="search-box">
        <AppIcon name="search" :size="32" color="#8E8E8E" />
        <input
          v-model="searchText"
          class="search-input"
          placeholder="搜索问题或位置..."
          placeholder-style="color:#B5B5B5"
        />
        <view v-if="searchText" class="search-clear" @click="clearSearch">
          <text class="clear-icon">✕</text>
        </view>
      </view>
    </view>

    <!-- 内容滚动区 -->
    <scroll-view
      class="content-scroll"
      scroll-y
      :style="{ height: listHeight + 'px' }"
      :enhanced="true"
      :show-scrollbar="false"
    >
      <view v-if="filteredGroups.length === 0" class="empty-state">
        <view class="empty-icon-wrapper">
          <AppIcon name="clipboard" :size="56" color="#8E8E8E" />
        </view>
        <text class="empty-title">{{ searchText ? '未找到匹配记录' : '暂无巡检记录' }}</text>
        <text class="empty-desc">{{ searchText ? '换个关键词试试' : '点击右上角「添加」创建第一条记录' }}</text>
      </view>

      <view
        v-for="group in filteredGroups"
        :key="group.date"
        class="date-card"
      >
        <!-- 日期头部 -->
        <view class="card-header" @click="goToDetail(group.date)">
          <text class="card-date">{{ formatDateShort(group.date) }}</text>
          <view class="card-badge">
            <text class="badge-text">{{ group.issues.length }} 项问题</text>
          </view>
          <AppIcon name="chevron-right" :size="28" color="#DADADA" />
        </view>

        <!-- 分支 & 问题列表 -->
        <view class="card-body">
          <view
            v-for="branch in getBranchesForGroup(group)"
            :key="branch.key"
            class="branch-block"
          >
            <!-- 分支标题 -->
            <view class="branch-row">
              <AppIcon :name="branch.icon" :size="32" color="#466CAC" />
              <text class="branch-name">{{ branch.name }}</text>
              <view class="branch-count">
                <text class="count-num">{{ branch.issues.length }}</text>
              </view>
            </view>

            <!-- 问题条目 -->
            <view class="issues">
              <view
                v-for="issue in branch.issues"
                :key="issue.id"
                class="issue-row"
              >
                <view class="issue-dot" :style="{ background: getRiskColor(issue.risk) }" />
                <view class="issue-body">
                  <view class="issue-top">
                    <text class="issue-title">{{ issue.title }}</text>
                    <view
                      class="issue-tag"
                      :style="{ background: getStatusConfig(issue.status).bg }"
                    >
                      <text
                        class="tag-text"
                        :style="{ color: getStatusConfig(issue.status).color }"
                      >{{ getStatusConfig(issue.status).label }}</text>
                    </view>
                  </view>
                  <view class="issue-loc">
                    <AppIcon name="map-pin" :size="22" color="#8E8E8E" />
                    <text class="loc-text">{{ issue.location }}</text>
                  </view>
                </view>
                <view class="issue-delete" @click.stop="handleDelete(issue)">
                  <AppIcon name="trash" :size="28" color="#EF4444" />
                </view>
              </view>
            </view>
          </view>
        </view>
      </view>

      <view class="list-bottom-spacer" />
    </scroll-view>

    <!-- 添加弹窗 -->
    <view v-if="showModal" class="modal-overlay" @click="showModal = false">
      <view class="modal-content" @click.stop>
        <text class="modal-title">添加巡检记录</text>

        <view class="form-field">
          <text class="field-label">日期</text>
          <picker
            mode="date"
            :value="form.date"
            :end="todayStr"
            @change="onDateChange"
          >
            <view class="field-picker">
              <text>{{ form.date || todayStr }}</text>
              <text class="picker-arrow">›</text>
            </view>
          </picker>
        </view>

        <view class="form-field">
          <text class="field-label">分支</text>
          <picker
            mode="selector"
            :range="branchNames"
            :value="branchIndex"
            @change="onBranchChange"
          >
            <view class="field-picker">
              <text>{{ branchNames[branchIndex] }}</text>
              <text class="picker-arrow">›</text>
            </view>
          </picker>
        </view>

        <view class="form-field">
          <text class="field-label">问题描述</text>
          <input
            v-model="form.title"
            class="field-input"
            placeholder="填写问题描述"
            maxlength="50"
          />
        </view>

        <view class="form-field">
          <text class="field-label">位置</text>
          <input
            v-model="form.location"
            class="field-input"
            placeholder="填写位置，如 K12+350"
            maxlength="30"
          />
        </view>

        <view class="form-row">
          <view class="form-field form-half">
            <text class="field-label">风险等级</text>
            <picker
              mode="selector"
              :range="riskLabels"
              :value="riskIndex"
              @change="onRiskChange"
            >
              <view class="field-picker">
                <view class="picker-preview">
                  <view class="mini-dot" :style="{ background: riskColors[riskIndex] }" />
                  <text>{{ riskLabels[riskIndex] }}</text>
                </view>
                <text class="picker-arrow">›</text>
              </view>
            </picker>
          </view>
          <view class="form-field form-half">
            <text class="field-label">状态</text>
            <picker
              mode="selector"
              :range="statusLabels"
              :value="statusIndex"
              @change="onStatusChange"
            >
              <view class="field-picker">
                <text>{{ statusLabels[statusIndex] }}</text>
                <text class="picker-arrow">›</text>
              </view>
            </picker>
          </view>
        </view>

        <view class="modal-actions">
          <view class="modal-btn modal-btn-cancel" @click="showModal = false">
            <text>取消</text>
          </view>
          <view class="modal-btn modal-btn-submit" @click="handleAddIssue">
            <text>确认添加</text>
          </view>
        </view>
      </view>
    </view>

    <TabBar current="inspection" @change="onTabChange" />
  </view>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import TabBar from '@/components/TabBar.vue'
import AppIcon from '@/components/AppIcon.vue'
import {
  getDateGroups,
  formatDateShort,
  formatDateFull,
  getTodayStr,
  addIssue,
  deleteIssue,
  BRANCHES,
  RISK_CONFIG,
  STATUS_CONFIG,
  type DateGroup,
  type RiskLevel,
  type IssueStatus,
} from '@/utils/inspectionStore'

const todayStr = getTodayStr()
const todayFull = computed(() => formatDateFull(todayStr))

const dateGroups = ref<DateGroup[]>([])
const listHeight = ref(500)
const statusBarHeight = ref(0)
const navContentHeight = ref(44)
const navRightPad = ref(100)
const searchText = ref('')

function refreshData() {
  dateGroups.value = getDateGroups()
}

const filteredGroups = computed(() => {
  if (!searchText.value.trim()) return dateGroups.value
  const kw = searchText.value.trim().toLowerCase()
  return dateGroups.value
    .map((g) => ({
      ...g,
      issues: g.issues.filter(
        (i) =>
          i.title.toLowerCase().includes(kw) ||
          i.location.toLowerCase().includes(kw),
      ),
    }))
    .filter((g) => g.issues.length > 0)
})

function clearSearch() {
  searchText.value = ''
}

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

  // windowHeight 已排除状态栏，不再重复减
  const searchBarH = 104  // 搜索栏区域高度 (rpx/2)
  const tabBarH = 76      // 底部导航栏高度 (152rpx/2)
  listHeight.value = windowHeight - navContentHeight.value - searchBarH - tabBarH
  refreshData()
})

onShow(() => {
  refreshData()
})

function getBranchesForGroup(group: DateGroup) {
  return BRANCHES.map((b) => ({
    ...b,
    issues: group.issues.filter((i) => i.branch === b.key),
  })).filter((b) => b.issues.length > 0)
}

function goToDetail(date: string) {
  uni.navigateTo({ url: `/pages/inspection/detail?date=${date}` })
}

function onTabChange(key: string) {
  if (key === 'home') {
    uni.redirectTo({ url: '/pages/index/index' })
  } else if (key === 'profile') {
    uni.redirectTo({ url: '/pages/profile/index' })
  }
}

// ---- 风险 & 状态 ----
function getRiskColor(risk: RiskLevel): string {
  return RISK_CONFIG[risk]?.color || '#8E8E8E'
}
function getStatusConfig(status: IssueStatus) {
  return STATUS_CONFIG[status] || STATUS_CONFIG.normal
}

const riskKeys: RiskLevel[] = ['high', 'medium', 'normal']
const riskLabels = riskKeys.map((k) => RISK_CONFIG[k].label)
const riskColors = riskKeys.map((k) => RISK_CONFIG[k].color)
const statusKeys: IssueStatus[] = ['pending', 'reviewed', 'high_risk', 'normal']
const statusLabels = statusKeys.map((k) => STATUS_CONFIG[k].label)

// ---- 弹窗 ----
const showModal = ref(false)
const branchNames = BRANCHES.map((b) => b.name)
const branchIndex = ref(0)
const riskIndex = ref(0)
const statusIndex = ref(0)

const form = reactive({
  date: todayStr,
  title: '',
  location: '',
})

function openAddModal() {
  form.date = todayStr
  form.title = ''
  form.location = ''
  branchIndex.value = 0
  riskIndex.value = 0
  statusIndex.value = 0
  showModal.value = true
}

function onDateChange(e: { detail: { value: string } }) {
  form.date = e.detail.value
}

function onBranchChange(e: { detail: { value: number } }) {
  branchIndex.value = e.detail.value
}

function onRiskChange(e: { detail: { value: number } }) {
  riskIndex.value = e.detail.value
}

function onStatusChange(e: { detail: { value: number } }) {
  statusIndex.value = e.detail.value
}

function handleAddIssue() {
  if (!form.title.trim()) {
    uni.showToast({ title: '请输入问题描述', icon: 'none', duration: 1500 })
    return
  }
  if (!form.location.trim()) {
    uni.showToast({ title: '请输入位置', icon: 'none', duration: 1500 })
    return
  }

  addIssue({
    branch: BRANCHES[branchIndex.value].key,
    title: form.title.trim(),
    location: form.location.trim(),
    date: form.date,
    risk: riskKeys[riskIndex.value],
    status: statusKeys[statusIndex.value],
  })

  showModal.value = false
  refreshData()
  uni.showToast({ title: '记录已添加', icon: 'success', duration: 1500 })
}

// ---- 删除 ----
function handleDelete(issue: { id: string; title: string }) {
  uni.showModal({
    title: '删除确认',
    content: `确定要删除「${issue.title}」吗？`,
    confirmText: '删除',
    confirmColor: '#EF4444',
    cancelText: '取消',
    success(res) {
      if (res.confirm) {
        deleteIssue(issue.id)
        refreshData()
        uni.showToast({ title: '已删除', icon: 'success', duration: 1200 })
      }
    },
  })
}
</script>

<style lang="scss" scoped>
/* ===== 引用全局设计 Token (uni.scss) ===== */

.page-container {
  min-height: 100vh;
  background: $uni-bg-color-grey;
  padding-bottom: calc(120rpx + env(safe-area-inset-bottom));
}

/* ===== 自定义导航栏 ===== */
.custom-nav {
  /* padding-top 由 JS 动态设置 */
}

.nav-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-left: 48rpx;
  /* height 和 padding-right 由 JS 动态设置 */
}

.nav-date {
  font-size: 34rpx;
  font-weight: 600;
  color: $uni-text-color;
  line-height: 1.2;
}

.nav-action {
  display: flex;
  align-items: center;
  gap: 10rpx;
  padding: 14rpx 28rpx;
  border-radius: 44rpx;
  background: $uni-color-brand;
  box-shadow: 0 4rpx 16rpx rgba(70, 108, 172, 0.25);
  flex-shrink: 0;

  &:active {
    opacity: 0.9;
  }
}

.action-text {
  font-size: 26rpx;
  font-weight: 400;
  color: #FFFFFF;
}

/* ===== 搜索栏 ===== */
.search-bar {
  padding: 16rpx 40rpx 8rpx;
}

.search-box {
  display: flex;
  align-items: center;
  height: 80rpx;
  padding: 0 28rpx;
  background: $uni-bg-color;
  border-radius: 44rpx;
  border: 1rpx solid $uni-border-color-light;
  gap: 16rpx;
}

.search-input {
  flex: 1;
  height: 100%;
  font-size: 28rpx;
  color: $uni-text-color;
}

.search-clear {
  width: 40rpx;
  height: 40rpx;
  border-radius: 50%;
  background: $uni-bg-color-module;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  &:active {
    background: #E5E5E5;
  }
}

.clear-icon {
  font-size: 22rpx;
  color: $uni-text-color-tertiary;
  font-weight: 600;
}

/* ===== 滚动区 ===== */
.content-scroll {
  padding: 0 40rpx;
}

/* ===== 空状态 ===== */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 160rpx 48rpx;
  gap: 16rpx;
}

.empty-icon-wrapper {
  width: 120rpx;
  height: 120rpx;
  border-radius: 50%;
  background: $uni-bg-color-module;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16rpx;
}

.empty-title {
  font-size: 32rpx;
  font-weight: 600;
  color: $uni-text-color-secondary;
}

.empty-desc {
  font-size: 26rpx;
  color: $uni-text-color-tertiary;
  text-align: center;
}

/* ===== 日期卡片 ===== */
.date-card {
  background: $uni-bg-color;
  border-radius: 44rpx;
  margin-bottom: 24rpx;
  border: 1rpx solid $uni-border-color-light;
  box-shadow: 0 8rpx 24rpx rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  padding: 28rpx 32rpx;
  gap: 16rpx;

  &:active {
    background: #FAFAFA;
  }
}

.card-date {
  font-size: 34rpx;
  font-weight: 600;
  color: $uni-text-color;
  flex-shrink: 0;
}

.card-badge {
  padding: 8rpx 20rpx;
  border-radius: 32rpx;
  background: $uni-color-accent-orange;
  flex-shrink: 0;
}

.badge-text {
  font-size: 22rpx;
  font-weight: 400;
  color: #FFFFFF;
}

.card-body {
  border-top: 1rpx solid $uni-border-color-light;
  padding: 20rpx 32rpx 24rpx;
}

/* ===== 分支块 ===== */
.branch-block {
  margin-bottom: 20rpx;

  &:last-child {
    margin-bottom: 0;
  }
}

.branch-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 14rpx;
}

.branch-name {
  font-size: 28rpx;
  font-weight: 600;
  color: $uni-text-color;
}

.branch-count {
  margin-left: auto;
  min-width: 44rpx;
  height: 44rpx;
  border-radius: 50%;
  background: $uni-bg-color-module;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.count-num {
  font-size: 24rpx;
  font-weight: 600;
  color: $uni-text-color-secondary;
}

/* ===== 问题列表 ===== */
.issues {
  padding-left: 4rpx;
}

.issue-row {
  display: flex;
  align-items: flex-start;
  padding: 18rpx 0;
  gap: 14rpx;
  border-bottom: 1rpx solid #F5F5F5;

  &:last-child {
    border-bottom: 0;
    padding-bottom: 0;
  }
}

.issue-dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 6rpx;
}

.issue-body {
  flex: 1;
  min-width: 0;
}

.issue-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12rpx;
  margin-bottom: 8rpx;
}

.issue-title {
  font-size: 28rpx;
  color: $uni-text-color;
  font-weight: 500;
  line-height: 38rpx;
  flex: 1;
  min-width: 0;
}

/* 状态标签 */
.issue-tag {
  padding: 6rpx 16rpx;
  border-radius: 20rpx;
  flex-shrink: 0;
}

.tag-text {
  font-size: 20rpx;
  font-weight: 400;
  line-height: 28rpx;
}

.issue-loc {
  display: flex;
  align-items: center;
  gap: 8rpx;
}

.loc-text {
  font-size: 24rpx;
  color: $uni-text-color-tertiary;
}

/* 删除按钮 */
.issue-delete {
  width: 48rpx;
  height: 48rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  &:active {
    background: #FFF5F5;
  }
}

.list-bottom-spacer {
  height: 32rpx;
}

/* ===== 表单行 ===== */
.form-row {
  display: flex;
  gap: 20rpx;
}

.form-half {
  flex: 1;
  min-width: 0;
}

.picker-preview {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.mini-dot {
  width: 18rpx;
  height: 18rpx;
  border-radius: 50%;
  flex-shrink: 0;
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
  max-width: 640rpx;
  background: #FFFFFF;
  border-radius: 44rpx;
  padding: 44rpx 36rpx;
}

.modal-title {
  display: block;
  font-size: 36rpx;
  font-weight: 600;
  color: $uni-text-color;
  text-align: center;
  margin-bottom: 40rpx;
}

.form-field {
  margin-bottom: 24rpx;
}

.field-label {
  display: block;
  font-size: 26rpx;
  font-weight: 600;
  color: $uni-text-color-secondary;
  margin-bottom: 12rpx;
}

.field-picker {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 96rpx;
  padding: 0 28rpx;
  border: 1rpx solid #BDBDBD;
  border-radius: 24rpx;
  font-size: 28rpx;
  color: $uni-text-color;
  background: #FFFFFF;
}

.picker-arrow {
  font-size: 36rpx;
  color: #DADADA;
}

.field-input {
  width: 100%;
  height: 96rpx;
  padding: 0 28rpx;
  border: 1rpx solid #BDBDBD;
  border-radius: 24rpx;
  font-size: 28rpx;
  color: $uni-text-color;
  background: #FFFFFF;
  box-sizing: border-box;
}

.modal-actions {
  display: flex;
  gap: 20rpx;
  margin-top: 20rpx;
}

.modal-btn {
  flex: 1;
  height: 96rpx;
  border-radius: 36rpx;
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
  color: #FFFFFF;
}
</style>
