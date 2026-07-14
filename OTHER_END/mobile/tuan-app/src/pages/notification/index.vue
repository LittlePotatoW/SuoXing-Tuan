<template>
  <view class="page">
    <view class="nav-bar" :style="{ paddingTop: statusBarH + 'px' }">
      <view class="nav-inner" :style="{ height: navH + 'px', paddingRight: navPad + 'px' }">
        <view class="nav-left" @click="goBack"><text class="back-icon">‹</text></view>
        <text class="nav-title">通知</text>
        <view class="nav-right" @click="markAllRead"><text class="read-all">全部已读</text></view>
      </view>
    </view>

    <view class="body-wrap" :style="{ paddingTop: navTotalH + 'px' }">
      <view class="tab-scroll">
        <view v-for="tab in tabs" :key="tab.key" class="tab-item" :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key">
          <text class="tab-text">{{ tab.label }}</text>
        </view>
      </view>

      <scroll-view class="list-scroll" scroll-y enhanced :show-scrollbar="false">
      <view v-if="filteredList.length === 0" class="empty">
        <AppIcon name="bell" :size="64" color="#D1D5DB" />
        <text class="empty-text">暂无通知</text>
      </view>

      <template v-for="msg in filteredList" :key="msg.id">
        <!-- 团队邀请消息 -->
        <view v-if="msg.type === 'invite'" class="msg-card">
          <view class="msg-left">
            <view class="msg-icon icon-invite">
              <AppIcon name="user-plus" :size="34" color="#8B5CF6" />
            </view>
          </view>
          <view class="msg-body">
            <view class="msg-top">
              <text class="msg-title">{{ msg.title }}</text>
              <view v-if="!msg.read && msg.state === 'pending'" class="unread-dot" />
              <text v-if="msg.state === 'accepted'" class="state-tag state-ok">已接受</text>
              <text v-if="msg.state === 'rejected'" class="state-tag state-no">已拒绝</text>
            </view>
            <text class="msg-desc">{{ msg.desc }}</text>
            <text class="msg-time">{{ msg.time }}</text>
            <view v-if="msg.state === 'pending'" class="invite-actions">
              <view class="invite-btn accept" @click.stop="acceptInvite(msg)"><text>接受</text></view>
              <view class="invite-btn reject" @click.stop="rejectInvite(msg)"><text>拒绝</text></view>
            </view>
          </view>
        </view>

        <!-- 普通消息 -->
        <view v-else class="msg-card" @click="openMsg(msg)">
          <view class="msg-left">
            <view class="msg-icon" :class="'icon-' + msg.type">
              <AppIcon :name="getIcon(msg.type)" :size="34" :color="getIconColor(msg.type)" />
            </view>
          </view>
          <view class="msg-body">
            <view class="msg-top">
              <text class="msg-title">{{ msg.title }}</text>
              <view v-if="!msg.read" class="unread-dot" />
            </view>
            <text class="msg-desc">{{ msg.desc }}</text>
            <text class="msg-time">{{ msg.time }}</text>
          </view>
          <AppIcon name="chevron-right" :size="22" color="#D1D5DB" />
        </view>
      </template>

      <view class="bottom-spacer" />
    </scroll-view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import AppIcon from '@/components/AppIcon.vue'
import { getStorage, setStorage } from '@/utils/storage'
import { useNavBar } from '@/composables/useNavBar'
import { acceptInvitation, rejectInvitation } from '@/utils/profileStore'

const { statusBarH, navH, navPad, navTotalH } = useNavBar()

interface Message {
  id: string; type: 'task' | 'alert' | 'system' | 'invite'
  title: string; desc: string; time: string; read: boolean
  state?: 'pending' | 'accepted' | 'rejected'; linkId?: string
}

const activeTab = ref('all')
const tabs = [
  { key: 'all', label: '全部' },
  { key: 'task', label: '任务通知' },
  { key: 'invite', label: '团队邀请' },
  { key: 'alert', label: '告警提醒' },
  { key: 'system', label: '系统公告' },
]

const messages = ref<Message[]>([
  { id: '1', type: 'task', title: '新巡检任务已派发', desc: '隧道B区巡检任务，计划今日 14:00 执行，请准时前往。', time: '10分钟前', read: false },
  { id: 'i1', type: 'invite', title: '组队邀请', desc: '张伟 邀请您加入 隧道巡检A组', time: '25分钟前', read: false, state: 'pending' },
  { id: '2', type: 'alert', title: '小车电量低于 20%', desc: '巡检车 A-03 电量仅剩 18%，请及时充电以保证下次任务正常执行。', time: '32分钟前', read: false },
  { id: '3', type: 'task', title: '任务执行完成', desc: '隧道B区巡检任务已于 11:45 完成，发现 4 项问题，请查看报告。', time: '1小时前', read: false },
  { id: '4', type: 'system', title: '三维模型已更新', desc: '隧道B区三维重建模型已更新至 v2.3，新增 K12+300 至 K12+500 区段数据。', time: '2小时前', read: true },
  { id: 'i2', type: 'invite', title: '组队邀请', desc: '李明 邀请您加入 设备检修组', time: '昨天', read: true, state: 'accepted' },
  { id: '5', type: 'alert', title: '信号连接异常', desc: '巡检车 A-03 在 K12+420 处信号中断超过 30 秒，已自动切换至本地控制模式。', time: '3小时前', read: true },
  { id: 'i3', type: 'invite', title: '组队邀请', desc: '王强 邀请您加入 应急响应组', time: '2天前', read: true, state: 'rejected' },
])

const filteredList = computed(() => {
  if (activeTab.value === 'all') return messages.value
  return messages.value.filter((m) => m.type === activeTab.value)
})

const MSG_ICONS: Record<string, string> = { task: 'clipboard', alert: 'alert-triangle', system: 'info' }
const MSG_COLORS: Record<string, string> = { task: '#3B82F6', alert: '#EF4444', system: '#8B5CF6' }
function getIcon(type: string): string { return MSG_ICONS[type] || 'bell' }
function getIconColor(type: string): string { return MSG_COLORS[type] || '#6B7280' }

function markAllRead() { messages.value.forEach((m) => { m.read = true }); saveMsgs(); uni.showToast({ title:'已全部标为已读', icon:'success', duration:1200 }) }
function openMsg(msg: Message) {
  msg.read = true
  saveMsgs()
  if (msg.type === 'task') uni.navigateTo({ url:'/pages/task/detail' })
  else if (msg.type === 'alert') uni.navigateTo({ url:'/pages/inspection/index' })
}
const NOTIFY_KEY = 'notify_messages'

function saveMsgs() { setStorage(NOTIFY_KEY, messages.value.map(m => ({ id:m.id, state:m.state, read:m.read }))) }
function acceptInvite(msg: Message) {
  msg.state = 'accepted'; msg.read = true; saveMsgs()
  // 同步团队邀请系统
  if (msg.linkId) acceptInvitation(msg.linkId)
  uni.showToast({ title:'已加入团队', icon:'success', duration:1500 })
}
function rejectInvite(msg: Message) {
  uni.showModal({ title:'确认拒绝', content:'确认拒绝该邀请吗？', confirmText:'拒绝', confirmColor:'#EF4444', cancelText:'取消', success(res) {
    if (res.confirm) {
      msg.state = 'rejected'; msg.read = true; saveMsgs()
      if (msg.linkId) rejectInvitation(msg.linkId)
      uni.showToast({ title:'已拒绝邀请', icon:'none', duration:1200 })
    }
  }})
}
function goBack() { uni.navigateBack() }

function restoreFromStorage(): boolean {
  const saved = getStorage<{id:string,state?:string,read:boolean}[]>(NOTIFY_KEY)
  if (saved && saved.length > 0) {
    saved.forEach(s => { const m = messages.value.find(x => x.id === s.id); if (m) { if (s.state) m.state = s.state as Message['state']; m.read = s.read } })
    return true
  }
  return false
}

onMounted(() => {
  if (!restoreFromStorage()) {
    saveMsgs()
  }
})

onShow(() => {
  restoreFromStorage()
})
</script>

<style lang="scss" scoped>
/* ===== 引用全局设计 Token (uni.scss) ===== */

.page { min-height:100vh; background:$uni-bg-color-grey; }
.nav-bar { position:fixed; top:0; left:0; right:0; z-index:100; background:$uni-bg-color-grey; }
.nav-inner { display:flex; align-items:center; padding-left:40rpx; }
.nav-left { width:72rpx; height:72rpx; border-radius:50%; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.back-icon { font-size:56rpx; color:$uni-text-color; font-weight:300; line-height:1; margin-top:-4rpx; }
.nav-title { font-size:40rpx; font-weight:700; color:$uni-text-color; margin-left:16rpx; }
.nav-right { margin-left:auto; flex-shrink:0; padding:12rpx 0; }
.read-all { font-size:28rpx; font-weight:400; color:$uni-color-brand; }

.tab-scroll { display:flex; gap:8rpx; padding:20rpx 36rpx 16rpx; flex-shrink:0; }
.tab-item { padding:14rpx 24rpx; border-radius:40rpx; background:$uni-bg-color; border:1rpx solid $uni-border-color-light; white-space:nowrap; }
.tab-item.active { background:$uni-color-brand; border-color:$uni-color-brand; .tab-text { color:#FFF; } }
.tab-text { font-size:28rpx; color:$uni-text-color-secondary; font-weight:400; }

.body-wrap { min-height:100vh; }
.list-scroll { height:calc(100vh - 200rpx); padding:0 36rpx; }
.empty { display:flex; flex-direction:column; align-items:center; padding:200rpx 0; gap:24rpx; }
.empty-text { font-size:28rpx; color:$uni-text-color-tertiary; font-weight:400; }

.msg-card { display:flex; align-items:flex-start; gap:20rpx; padding:28rpx; background:$uni-bg-color; border-radius:$uni-border-radius-lg; margin-bottom:16rpx; box-shadow:$uni-shadow-weak; }
.msg-left { flex-shrink:0; }
.msg-icon { width:64rpx; height:64rpx; border-radius:$uni-border-radius-base; display:flex; align-items:center; justify-content:center; }
.icon-task { background:#EFF6FF; } .icon-alert { background:#FEF2F2; } .icon-system { background:#F5F3FF; } .icon-invite { background:#F5F3FF; }
.msg-body { flex:1; min-width:0; }
.msg-top { display:flex; align-items:center; gap:12rpx; margin-bottom:8rpx; }
.msg-title { font-size:32rpx; font-weight:600; color:$uni-text-color; flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.unread-dot { width:14rpx; height:14rpx; border-radius:50%; background:$uni-color-brand; flex-shrink:0; }
.state-tag { font-size:24rpx; font-weight:400; padding:4rpx 14rpx; border-radius:16rpx; flex-shrink:0; }
.state-ok { background:#ECFDF5; color:#059669; }
.state-no { background:#F3F4F6; color:#9CA3AF; }
.msg-desc { font-size:28rpx; font-weight:400; color:$uni-text-color-secondary; line-height:40rpx; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; margin-bottom:10rpx; }
.msg-time { font-size:28rpx; font-weight:400; color:$uni-text-color-tertiary; }

.invite-actions { display:flex; gap:16rpx; margin-top:16rpx; }
.invite-btn { flex:1; height:64rpx; border-radius:20rpx; display:flex; align-items:center; justify-content:center; font-size:28rpx; font-weight:400; }
.invite-btn.accept { background:$uni-color-brand; color:#FFF; }
.invite-btn.reject { background:$uni-border-color-light; color:$uni-text-color-secondary; }

.bottom-spacer { height:48rpx; }
</style>
