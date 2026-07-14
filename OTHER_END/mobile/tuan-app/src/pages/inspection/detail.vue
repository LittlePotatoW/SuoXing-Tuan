<template>
  <view class="page">
    <scroll-view
      class="content"
      scroll-y
      enhanced
      :show-scrollbar="false"
    >
      <view
        v-for="branch in branches"
        :key="branch.key"
        class="branch-card"
      >
        <view class="branch-card-header" @click="toggleBranch(branch.key)">
          <view class="branch-title-row">
            <AppIcon :name="branch.icon" :size="36" color="#111111" />
            <text class="branch-name">{{ branch.name }}</text>
            <view
              v-if="branch.issues.length > 0"
              class="branch-badge"
            >
              <text>{{ branch.issues.length }}</text>
            </view>
          </view>
          <text class="collapse-arrow" :class="{ expanded: isExpanded(branch.key) }">
            ›
          </text>
        </view>

        <view v-if="isExpanded(branch.key)" class="branch-body">
          <view
            v-for="issue in branch.issues"
            :key="issue.id"
            class="issue-card"
          >
            <view class="issue-header">
              <view class="issue-dot" :style="{ background: getRiskColor(issue.risk) }" />
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
              <view class="issue-delete" @click.stop="handleDelete(issue)">
                <AppIcon name="trash" :size="28" color="#EF4444" />
              </view>
            </view>

            <view class="issue-meta">
              <view class="meta-item">
                <AppIcon name="map-pin" :size="26" color="#8E8E8E" />
                <text class="meta-text">{{ issue.location }}</text>
              </view>
              <view class="meta-item map-link" @click="viewOnMap(issue)">
                <AppIcon name="map" :size="26" color="#8E8E8E" />
                <text class="meta-link-text">查看位置</text>
              </view>
            </view>
          </view>

          <view v-if="branch.issues.length === 0" class="no-issues">
            <AppIcon name="check" :size="36" color="#7BC8A4" />
            <text class="no-issues-text">未发现问题</text>
          </view>
        </view>
      </view>

      <view style="height: 20rpx" />
    </scroll-view>

    <!-- 缺陷位置详情弹窗 -->
    <view v-if="showMapModal" class="modal-mask" @click="showMapModal = false">
      <view class="map-modal-card" @click.stop>
        <text class="map-modal-title">缺陷位置详情</text>

        <!-- 地图占位区 -->
        <view class="map-placeholder">
          <AppIcon name="map-pin" :size="64" color="#466CAC" />
          <text class="map-placeholder-loc">{{ selectedIssue?.location }}</text>
        </view>

        <!-- 缺陷信息卡片 -->
        <view class="defect-info-card">
          <view class="defect-dot" />
          <view class="defect-text">
            <text class="defect-label">问题描述</text>
            <text class="defect-title">{{ selectedIssue?.title }}</text>
          </view>
        </view>

        <view class="map-modal-close" @click="showMapModal = false">
          <text>关闭</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import AppIcon from '@/components/AppIcon.vue'
import {
  getIssuesByDate,
  formatDateFull,
  deleteIssue,
  BRANCHES,
  RISK_CONFIG,
  STATUS_CONFIG,
  type InspectionIssue,
  type RiskLevel,
  type IssueStatus,
} from '@/utils/inspectionStore'

const date = ref('')
const dateFull = ref('')
const branches = ref<Array<{ key: string; name: string; icon: string; issues: InspectionIssue[] }>>([])
const expandedBranches = reactive<Set<string>>(new Set())
const showMapModal = ref(false)
const selectedIssue = ref<InspectionIssue | null>(null)

onLoad((options: Record<string, string>) => {
  date.value = options?.date || ''
  dateFull.value = formatDateFull(date.value)

  uni.setNavigationBarTitle({
    title: dateFull.value + ' 巡检详情',
  })

  branches.value = getIssuesByDate(date.value)

  for (const b of branches.value) {
    if (b.issues.length > 0) {
      expandedBranches.add(b.key)
    }
  }
})

function isExpanded(key: string) {
  return expandedBranches.has(key)
}

function toggleBranch(key: string) {
  if (expandedBranches.has(key)) {
    expandedBranches.delete(key)
  } else {
    expandedBranches.add(key)
  }
}

function viewOnMap(issue: InspectionIssue) {
  selectedIssue.value = issue
  showMapModal.value = true
}

function getRiskColor(risk: RiskLevel): string {
  return RISK_CONFIG[risk]?.color || '#8E8E8E'
}
function getStatusConfig(status: IssueStatus) {
  return STATUS_CONFIG[status] || STATUS_CONFIG.normal
}

function handleDelete(issue: InspectionIssue) {
  uni.showModal({
    title: '删除确认',
    content: `确定要删除「${issue.title}」吗？`,
    confirmText: '删除',
    confirmColor: '#EF4444',
    cancelText: '取消',
    success(res) {
      if (res.confirm) {
        deleteIssue(issue.id)
        // 重新加载数据
        branches.value = getIssuesByDate(date.value)
        uni.showToast({ title: '已删除', icon: 'success', duration: 1200 })
      }
    },
  })
}
</script>

<style lang="scss" scoped>
/* ===== 引用全局设计 Token (uni.scss) ===== */
.page {
  min-height: 100vh;
  background: $uni-bg-color-grey;
  display: flex;
  flex-direction: column;
}

.content {
  flex: 1;
  padding: 20rpx 40rpx;
}

/* ===== 分支卡片 ===== */
.branch-card {
  background: $uni-bg-color;
  border-radius: 44rpx;
  margin-bottom: 24rpx;
  overflow: hidden;
  border: 1rpx solid $uni-border-color-light;
  box-shadow: 0 8rpx 24rpx rgba(0, 0, 0, 0.06);
}

.branch-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28rpx 32rpx;
}

.branch-card-header:active {
  background: #FAFAFA;
}

.branch-title-row {
  display: flex;
  align-items: center;
  gap: 14rpx;
  flex: 1;
  min-width: 0;
}

.branch-name {
  font-size: 32rpx;
  font-weight: 500;
  color: $uni-text-color;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.branch-badge {
  background: $uni-color-accent-orange;
  padding: 6rpx 16rpx;
  border-radius: 32rpx;
  flex-shrink: 0;
}

.branch-badge text {
  font-size: 22rpx;
  font-weight: 400;
  color: $uni-bg-color;
}

.collapse-arrow {
  font-size: 44rpx;
  color: $uni-border-color;
  font-weight: 300;
  flex-shrink: 0;
  transition: transform 0.25s;
}

.collapse-arrow.expanded {
  transform: rotate(90deg);
}

.branch-body {
  padding: 0 32rpx 24rpx;
}

/* ===== 问题卡片 ===== */
.issue-card {
  background: $uni-bg-color-grey;
  border-radius: 24rpx;
  padding: 20rpx 24rpx;
  margin-bottom: 14rpx;
  overflow: hidden;
}

.issue-card:last-child {
  margin-bottom: 0;
}

.issue-header {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-bottom: 14rpx;
}

.issue-dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  flex-shrink: 0;
}

.issue-title {
  flex: 1;
  min-width: 0;
  font-size: 28rpx;
  font-weight: 400;
  color: $uni-text-color;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

.issue-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 10rpx;
  min-width: 0;
}

.meta-text {
  font-size: 24rpx;
  color: $uni-text-color-tertiary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.map-link {
  padding: 12rpx 24rpx;
  border-radius: 44rpx;
  background: $uni-bg-color-module;
  flex-shrink: 0;
  gap: 12rpx;
}

.map-link:active {
  background: #E5E5E5;
}

.meta-link-text {
  font-size: 24rpx;
  color: $uni-color-brand;
  font-weight: 500;
}

/* ===== 无问题 ===== */
.no-issues {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10rpx;
  padding: 28rpx 0;
}

.no-issues-text {
  font-size: 26rpx;
  color: $uni-text-color-tertiary;
}

/* ===== 缺陷位置详情弹窗 ===== */
.modal-mask {
  position: fixed;
  top: 0; right: 0; bottom: 0; left: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 48rpx;
}

.map-modal-card {
  width: 100%;
  max-width: 600rpx;
  background: $uni-bg-color;
  border-radius: 44rpx;
  padding: 40rpx 36rpx 32rpx;
}

.map-modal-title {
  display: block;
  font-size: 34rpx;
  font-weight: 500;
  color: $uni-text-color;
  text-align: center;
  margin-bottom: 32rpx;
}

/* 地图占位区 */
.map-placeholder {
  background: $uni-bg-cool;
  border-radius: 28rpx;
  padding: 56rpx 24rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20rpx;
  margin-bottom: 24rpx;
}

.map-placeholder-loc {
  font-size: 28rpx;
  color: $uni-text-color;
  font-weight: 500;
  text-align: center;
}

/* 缺陷信息卡片 */
.defect-info-card {
  background: #FFF5F5;
  border: 1rpx solid #FECACA;
  border-radius: 22rpx;
  padding: 24rpx 28rpx;
  display: flex;
  align-items: flex-start;
  gap: 16rpx;
  margin-bottom: 28rpx;
}

.defect-dot {
  width: 16rpx;
  height: 16rpx;
  border-radius: 50%;
  background: $uni-color-error;
  flex-shrink: 0;
  margin-top: 6rpx;
}

.defect-text {
  flex: 1;
  min-width: 0;
}

.defect-label {
  display: block;
  font-size: 22rpx;
  color: $uni-color-error;
  font-weight: 600;
  margin-bottom: 6rpx;
}

.defect-title {
  display: block;
  font-size: 28rpx;
  color: $uni-text-color;
  font-weight: 500;
  line-height: 38rpx;
  word-break: break-all;
}

/* 关闭按钮 */
.map-modal-close {
  height: 88rpx;
  border-radius: 36rpx;
  background: $uni-bg-color-module;
  display: flex;
  align-items: center;
  justify-content: center;
}

.map-modal-close:active {
  background: #E5E5E5;
}

.map-modal-close text {
  font-size: 28rpx;
  color: $uni-text-color-secondary;
  font-weight: 500;
}
</style>
