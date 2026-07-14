<template>
  <view class="page">
    <!-- 导航栏 -->
    <view class="nav-bar" :style="{ paddingTop: statusBarH + 'px' }">
      <view class="nav-inner" :style="{ height: navH + 'px', paddingRight: navPad + 'px' }">
        <view class="nav-left" @click="goBack">
          <text class="back-icon">‹</text>
        </view>
        <text class="nav-title">任务详情</text>
        <view class="nav-spacer" />
      </view>
    </view>

    <view class="body-wrap" :style="{ paddingTop: navTotalH + 'px' }">
    <scroll-view class="content" scroll-y enhanced :show-scrollbar="false">
      <!-- 状态标签 + 任务名 -->
      <view class="status-bar">
        <view class="status-badge" :class="'badge-' + currentTask.status">
          <text>{{ getStatusLabel(currentTask.status) }}</text>
        </view>
      </view>

      <!-- 基本信息卡片 -->
      <view class="card info-card">
        <text class="card-title">基本信息</text>
        <view class="info-row">
          <text class="info-label">任务编号</text>
          <text class="info-val">{{ currentTask.id }}</text>
        </view>
        <view class="info-row">
          <text class="info-label">任务名称</text>
          <text class="info-val">{{ currentTask.name }}</text>
        </view>
        <view class="info-row">
          <text class="info-label">负责区域</text>
          <text class="info-val">{{ currentTask.area }}</text>
        </view>
        <view class="info-row">
          <text class="info-label">计划时间</text>
          <text class="info-val">{{ currentTask.planStart }} — {{ currentTask.planEnd }}</text>
        </view>
      </view>

      <!-- 执行进度卡片 -->
      <view class="card progress-card">
        <text class="card-title">执行进度</text>
        <view class="progress-header">
          <text class="progress-pct">{{ currentTask.progress }}%</text>
          <text class="progress-sub">已完成</text>
        </view>
        <view class="progress-track">
          <view class="progress-fill" :style="{ width: currentTask.progress + '%' }" />
        </view>
        <view class="progress-dist">
          <view class="dist-item">
            <text class="dist-label">已巡检距离</text>
            <text class="dist-val">{{ currentTask.doneDist }} km</text>
          </view>
          <view class="dist-item">
            <text class="dist-label">总距离</text>
            <text class="dist-val">{{ currentTask.totalDist }} km</text>
          </view>
        </view>
      </view>

      <!-- 小车状态卡片 -->
      <view class="card robot-card">
        <text class="card-title">小车状态</text>
        <view class="robot-grid">
          <view class="rb-item">
            <text class="rb-label">当前位置</text>
            <text class="rb-val">{{ currentTask.robotPos }}</text>
          </view>
          <view class="rb-item">
            <text class="rb-label">电量</text>
            <text class="rb-val">{{ currentTask.robotBattery }}%</text>
          </view>
          <view class="rb-item">
            <text class="rb-label">速度</text>
            <text class="rb-val">{{ currentTask.robotSpeed }} m/s</text>
          </view>
          <view class="rb-item">
            <text class="rb-label">状态</text>
            <text class="rb-val rb-online">{{ currentTask.robotStatus }}</text>
          </view>
        </view>
      </view>

      <!-- 关联问题列表 -->
      <view class="card issues-card">
        <text class="card-title">关联问题</text>
        <view v-if="currentTask.issues.length === 0" class="no-issues">
          <AppIcon name="check" :size="36" color="#9CA3AF" />
          <text class="no-text">暂无发现问题</text>
        </view>
        <view v-for="iss in currentTask.issues" :key="iss.id" class="issue-item" @click="goInspection(iss)">
          <view class="issue-dot" :style="{ background: iss.riskColor }" />
          <view class="issue-body">
            <text class="issue-title">{{ iss.title }}</text>
            <text class="issue-loc">{{ iss.location }}</text>
          </view>
          <AppIcon name="chevron-right" :size="22" color="#D1D5DB" />
        </view>
      </view>

      <view class="bottom-spacer" />
    </scroll-view>
    </view>

    <!-- 底部操作栏 -->
    <view class="action-bar">
      <view v-if="currentTask.status === 'pending'" class="action-btn btn-start" @click="startTask">
        <text>开始执行</text>
      </view>
      <template v-if="currentTask.status === 'running'">
        <view class="action-btn btn-pause" @click="pauseTask">
          <text>暂停</text>
        </view>
        <view class="action-btn btn-end" @click="endTask">
          <text>结束任务</text>
        </view>
      </template>
      <view v-if="currentTask.status === 'done'" class="action-btn btn-report" @click="viewReport">
        <AppIcon name="file-text" :size="28" color="#FFF" />
        <text>查看报告</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import AppIcon from '@/components/AppIcon.vue'
import { currentTask, getStatusLabel } from '@/utils/taskStore'
import { useNavBar } from '@/composables/useNavBar'

const { statusBarH, navH, navPad, navTotalH } = useNavBar()

function goBack() { uni.navigateBack() }
function startTask() { currentTask.status = 'running'; uni.showToast({ title: '任务已开始', icon: 'success', duration: 1200 }) }
function pauseTask() { uni.showToast({ title: '任务已暂停', icon: 'none', duration: 1200 }) }
function endTask() { currentTask.status = 'done'; uni.showToast({ title: '任务已结束', icon: 'success', duration: 1200 }) }
function viewReport() { uni.showToast({ title: '查看报告中...', icon: 'none', duration: 1200 }) }
function goInspection(iss: { date: string }) { uni.showToast({ title: `跳转 ${iss.date} 巡检记录`, icon: 'none', duration: 1200 }) }
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

.body-wrap { min-height:100vh; padding-bottom:140rpx; }
.content { height:calc(100vh - 260rpx); padding:20rpx 36rpx 0; }

/* 状态栏 */
.status-bar { display: flex; justify-content: center; margin-bottom: 24rpx; }
.status-badge { padding: 10rpx 32rpx; border-radius: 40rpx; font-size: 28rpx; font-weight: 400; }
.badge-pending { background: #FFF7ED; color: #C2410C; }
.badge-running { background: #EFF6FF; color: #1D4ED8; }
.badge-done { background: #ECFDF5; color: #047857; }
.badge-cancelled { background: #F3F4F6; color: #6B7280; }

/* 卡片通用 */
.card { background: $uni-bg-color; border-radius: $uni-border-radius-lg; padding: 32rpx; margin-bottom: 20rpx; box-shadow: $uni-shadow-weak; }
.card-title { font-size: 32rpx; font-weight: 600; color: $uni-text-color; display: block; margin-bottom: 20rpx; }

/* 基本信息 */
.info-row { display: flex; justify-content: space-between; align-items: center; padding: 14rpx 0; border-bottom: 1rpx solid $uni-border-color-light; }
.info-row:last-child { border-bottom: 0; }
.info-label { font-size: 28rpx; color: $uni-text-color-secondary; font-weight: 400; }
.info-val { font-size: 28rpx; color: $uni-text-color; text-align: right; font-weight: 400; }

/* 进度 */
.progress-header { display: flex; align-items: baseline; gap: 12rpx; margin-bottom: 16rpx; }
.progress-pct { font-size: 52rpx; color: $uni-color-brand; font-weight: 600; line-height: 1.1; }
.progress-sub { font-size: 28rpx; color: $uni-text-color-secondary; font-weight: 400; }
.progress-track { height: 12rpx; border-radius: 6rpx; background: $uni-border-color-light; overflow: hidden; margin-bottom: 20rpx; }
.progress-fill { height: 100%; border-radius: 6rpx; background: $uni-color-brand; transition: width 0.4s; }
.progress-dist { display: flex; gap: 48rpx; }
.dist-label { font-size: 28rpx; color: $uni-text-color-tertiary; font-weight: 400; display: block; margin-bottom: 6rpx; }
.dist-val { font-size: 28rpx; font-weight: 600; color: $uni-text-color; }

/* 小车状态 */
.robot-grid { display: flex; flex-wrap: wrap; }
.rb-item { width: 50%; padding: 14rpx 0; }
.rb-label { font-size: 28rpx; color: $uni-text-color-tertiary; font-weight: 400; display: block; margin-bottom: 6rpx; }
.rb-val { font-size: 28rpx; font-weight: 600; color: $uni-text-color; }
.rb-online { color: $uni-color-accent-mint; }

/* 关联问题 */
.no-issues { display: flex; align-items: center; justify-content: center; gap: 12rpx; padding: 32rpx 0; }
.no-text { font-size: 28rpx; color: $uni-text-color-tertiary; font-weight: 400; }
.issue-item { display: flex; align-items: center; gap: 16rpx; padding: 18rpx 0; border-bottom: 1rpx solid $uni-border-color-light; }
.issue-item:last-child { border-bottom: 0; }
.issue-dot { width: 14rpx; height: 14rpx; border-radius: 50%; flex-shrink: 0; }
.issue-body { flex: 1; min-width: 0; }
.issue-title { font-size: 28rpx; font-weight: 400; color: $uni-text-color; display: block; margin-bottom: 6rpx; }
.issue-loc { font-size: 28rpx; font-weight: 400; color: $uni-text-color-tertiary; }

.bottom-spacer { height: 160rpx; }

/* 底部操作栏 */
.action-bar { position:fixed; bottom:0; left:0; right:0; display:flex; gap:20rpx; padding:20rpx 36rpx; padding-bottom:calc(env(safe-area-inset-bottom) + 20rpx); background:$uni-bg-color; border-top:1rpx solid $uni-border-color-light; z-index:100; }
.action-btn { flex: 1; height: 88rpx; border-radius: $uni-border-radius-base; display: flex; align-items: center; justify-content: center; gap: 12rpx; font-size: 32rpx; font-weight: 600; }
.btn-start { background: $uni-color-brand; color: $uni-bg-color; }
.btn-pause { background: #FFF7ED; color: #C2410C; border: 1rpx solid #FED7AA; font-weight: 400; }
.btn-end { background: #FEF2F2; color: #DC2626; border: 1rpx solid #FECACA; font-weight: 400; }
.btn-report { background: $uni-color-brand; color: $uni-bg-color; }
</style>
