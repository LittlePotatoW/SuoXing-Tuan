<template>
  <view class="page">
    <!-- 导航栏 -->
    <view class="nav-bar" :style="{ paddingTop: statusBarH + 'px' }">
      <view class="nav-inner" :style="{ height: navH + 'px', paddingRight: navPad + 'px' }">
        <view class="nav-left" @click="goBack">
          <text class="back-icon">‹</text>
        </view>
        <text class="nav-title">检测记录</text>
        <view class="nav-spacer" />
      </view>
    </view>

    <view class="body-wrap" :style="{ paddingTop: navTotalH + 'px' }">
    <!-- 顶部统计卡片 -->
    <view class="stats-card">
      <view class="stat">
        <text class="stat-num">{{ stats.total }}</text>
        <text class="stat-label">总检测次数</text>
      </view>
      <view class="stat-divider" />
      <view class="stat">
        <text class="stat-num">{{ stats.issues }}</text>
        <text class="stat-label">总发现问题</text>
      </view>
      <view class="stat-divider" />
      <view class="stat">
        <text class="stat-num">{{ stats.rate }}%</text>
        <text class="stat-label">检出率</text>
      </view>
    </view>

    <!-- 筛选栏 -->
    <view class="filter-row">
      <view class="filter-item" :class="{ active: filterArea }" @click="toggleFilter('area')">
        <text>{{ filterArea || '全部区域' }}</text>
        <text class="filter-arrow">▾</text>
      </view>
      <view class="filter-item" :class="{ active: filterStatus }" @click="toggleFilter('status')">
        <text>{{ statusLabel(filterStatus) || '全部状态' }}</text>
        <text class="filter-arrow">▾</text>
      </view>
      <view class="filter-clear" v-if="filterArea || filterStatus" @click="clearFilters">
        <text>重置</text>
      </view>
    </view>

    <!-- 记录列表 -->
    <scroll-view class="list-scroll" scroll-y enhanced :show-scrollbar="false">
      <view v-if="filteredRecords.length === 0" class="empty">
        <AppIcon name="file-text" :size="64" color="#D1D5DB" />
        <text class="empty-text">暂无检测记录</text>
      </view>

      <view v-for="rec in filteredRecords" :key="rec.id" class="rec-card" @click="openDetail(rec)">
        <view class="rec-header">
          <text class="rec-date">{{ rec.date }}</text>
          <view class="rec-badge" :class="rec.issuesCount > 0 ? 'badge-warn' : 'badge-ok'">
            <text>{{ rec.issuesCount > 0 ? `${rec.issuesCount} 项问题` : '正常' }}</text>
          </view>
        </view>
        <view class="rec-body">
          <view class="rec-row">
            <view class="rec-field">
              <text class="rec-label">检测区域</text>
              <text class="rec-val">{{ rec.area }}</text>
            </view>
            <view class="rec-field">
              <text class="rec-label">任务编号</text>
              <text class="rec-val">{{ rec.taskId }}</text>
            </view>
          </view>
          <view class="rec-row">
            <view class="rec-field">
              <text class="rec-label">检测时长</text>
              <text class="rec-val">{{ rec.duration }}</text>
            </view>
            <view class="rec-field">
              <text class="rec-label">操作员</text>
              <text class="rec-val">{{ rec.operator }}</text>
            </view>
          </view>
        </view>
        <view class="rec-footer">
          <text class="rec-status" :class="rec.issuesCount === 0 ? 'text-green' : 'text-red'">
            {{ rec.issuesCount === 0 ? '全部正常' : '发现异常' }}
          </text>
          <AppIcon name="chevron-right" :size="22" color="#D1D5DB" />
        </view>
      </view>

      <view class="bottom-spacer" />
    </scroll-view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import { useNavBar } from '@/composables/useNavBar'

const { statusBarH, navH, navPad, navTotalH } = useNavBar()
const filterArea = ref('')
const filterStatus = ref('')

const stats = { total: 47, issues: 128, rate: 91 }

interface Record {
  id: string; date: string; area: string; taskId: string;
  duration: string; operator: string; issuesCount: number; status: string;
}
const records = ref<Record[]>([
  { id: '1', date: '2026-07-11 14:00', area: '隧道B区', taskId: 'TD-2026-0711-001', duration: '1小时52分', operator: '张伟', issuesCount: 4, status: 'done' },
  { id: '2', date: '2026-07-10 09:30', area: '隧道A区', taskId: 'TD-2026-0710-003', duration: '2小时05分', operator: '李明', issuesCount: 0, status: 'done' },
  { id: '3', date: '2026-07-09 15:00', area: '隧道B区', taskId: 'TD-2026-0709-002', duration: '1小时38分', operator: '张伟', issuesCount: 3, status: 'done' },
  { id: '4', date: '2026-07-08 10:00', area: '隧道C区', taskId: 'TD-2026-0708-005', duration: '2小时12分', operator: '王强', issuesCount: 6, status: 'done' },
  { id: '5', date: '2026-07-07 08:30', area: '隧道A区', taskId: 'TD-2026-0707-001', duration: '1小时45分', operator: '李明', issuesCount: 1, status: 'done' },
])

const filteredRecords = computed(() => {
  return records.value.filter((r) => {
    if (filterArea.value && r.area !== filterArea.value) return false
    if (filterStatus.value === 'normal' && r.issuesCount > 0) return false
    if (filterStatus.value === 'abnormal' && r.issuesCount === 0) return false
    return true
  })
})

const STATUS_LABELS: Record<string, string> = { normal: '正常', abnormal: '异常' }

function toggleFilter(type: string) {
  if (type === 'area') {
    const opts = ['', '隧道A区', '隧道B区', '隧道C区']
    const idx = opts.indexOf(filterArea.value)
    filterArea.value = opts[(idx + 1) % opts.length]
  } else {
    const opts = ['', 'normal', 'abnormal']
    const idx = opts.indexOf(filterStatus.value)
    filterStatus.value = opts[(idx + 1) % opts.length]
  }
}
function statusLabel(key: string): string { return STATUS_LABELS[key] || key }
function clearFilters() { filterArea.value = ''; filterStatus.value = '' }
function openDetail(rec: Record) { uni.showToast({ title: `查看 ${rec.taskId} 详情`, icon: 'none', duration: 1200 }) }
function goBack() { uni.navigateBack() }
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

/* 统计卡片 */
.stats-card {
  display: flex; align-items: center; margin: 20rpx 36rpx; padding: 32rpx 16rpx;
  background: $uni-bg-color; border-radius: $uni-border-radius-lg; box-shadow: $uni-shadow-weak;
}
.stat { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 8rpx; }
.stat-num { font-size: 44rpx; color: $uni-text-color; font-weight: 600; line-height: 1.2; }
.stat-label { font-size: 28rpx; color: $uni-text-color-tertiary; font-weight: 400; }
.stat-divider { width: 1rpx; height: 48rpx; background: $uni-border-color-light; }

/* 筛选栏 */
.filter-row { display: flex; gap: 16rpx; padding: 0 36rpx 16rpx; align-items: center; }
.filter-item {
  display: flex; align-items: center; gap: 8rpx; padding: 14rpx 24rpx;
  border-radius: 40rpx; background: $uni-bg-color; border: 1rpx solid $uni-border-color-light; font-size: 28rpx; color: $uni-text-color-secondary; font-weight: 400;
  &.active { background: $uni-color-brand; border-color: $uni-color-brand; color: #FFF; }
}
.filter-arrow { font-size: 20rpx; }
.filter-clear { font-size: 28rpx; font-weight: 400; color: $uni-color-brand; padding: 14rpx 8rpx; }

/* 列表 */
.body-wrap { min-height:100vh; }
.list-scroll { height:calc(100vh - 340rpx); padding:0 36rpx; }
.empty { display: flex; flex-direction: column; align-items: center; padding: 200rpx 0; gap: 24rpx; }
.empty-text { font-size: 28rpx; color: $uni-text-color-tertiary; font-weight: 400; }

.rec-card {
  background: $uni-bg-color; border-radius: $uni-border-radius-lg; padding: 32rpx 32rpx 24rpx; margin-bottom: 16rpx;
  box-shadow: $uni-shadow-weak;
}
.rec-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20rpx; }
.rec-date { font-size: 32rpx; color: $uni-text-color; font-weight: 600; }
.rec-badge { padding: 8rpx 20rpx; border-radius: 24rpx; font-size: 28rpx; font-weight: 400; }
.badge-warn { background: #FEF2F2; color: $uni-color-error; }
.badge-ok { background: #ECFDF5; color: $uni-color-success; }

.rec-body { margin-bottom: 20rpx; }
.rec-row { display: flex; margin-bottom: 14rpx; }
.rec-field { flex: 1; }
.rec-label { font-size: 28rpx; color: $uni-text-color-tertiary; font-weight: 400; display: block; margin-bottom: 6rpx; }
.rec-val { font-size: 28rpx; color: $uni-text-color; font-weight: 400; }

.rec-footer { display: flex; align-items: center; justify-content: space-between; border-top: 1rpx solid $uni-border-color-light; padding-top: 16rpx; }
.rec-status { font-size: 28rpx; font-weight: 400; }
.text-green { color: $uni-color-success; }
.text-red { color: $uni-color-error; }

.bottom-spacer { height: 48rpx; }
</style>
