<template>
  <view class="page">
    <!-- 导航栏 -->
    <view class="nav-bar" :style="{ paddingTop: statusBarH + 'px' }">
      <view class="nav-inner" :style="{ height: navH + 'px', paddingRight: navPad + 'px' }">
        <view class="nav-left" @click="goBack">
          <text class="back-icon">‹</text>
        </view>
        <text class="nav-title">团队成员</text>
        <view class="nav-right" @click="showAdd = true">
          <AppIcon name="plus-circle" :size="36" color="#3B82F6" />
        </view>
      </view>
    </view>

    <!-- 统计 -->
    <view class="stats-bar">
      <text class="stats-text">共 {{ members.length }} 人</text>
      <text class="stats-sub">{{ onlineCount }} 人在线</text>
    </view>

    <!-- 成员列表 -->
    <scroll-view class="content" scroll-y enhanced :show-scrollbar="false">
      <!-- 待处理邀请 -->
      <view v-if="invites.length > 0" class="invite-section">
        <text class="section-label">待处理邀请（{{ invites.length }}）</text>
        <view v-for="inv in invites" :key="inv.id" class="member-card invite-card">
          <view class="member-avatar invite-avatar">
            <text class="avatar-initial">{{ inv.name.charAt(0) }}</text>
          </view>
          <view class="member-body">
            <view class="member-top">
              <text class="member-name">{{ inv.name }}</text>
              <text class="tag-pending">等待确认</text>
            </view>
            <view class="member-status">
              <text class="status-text">{{ inv.phone.slice(0,3) }}****{{ inv.phone.slice(-4) }}</text>
            </view>
          </view>
        </view>
      </view>

      <view v-for="m in members" :key="m.id" class="member-card" @click="viewProfile(m)">
        <view class="member-avatar">
          <image v-if="m.avatar" :src="m.avatar" mode="aspectFill" />
          <text v-else class="avatar-initial">{{ m.name.charAt(0) }}</text>
        </view>
        <view class="member-body">
          <view class="member-top">
            <text class="member-name">{{ m.name }}</text>
            <text v-if="m.role === 'owner'" class="tag-owner">负责人</text>
            <text v-else class="tag-member">成员</text>
          </view>
          <view class="member-status">
            <view class="status-dot" :class="'dot-' + m.status" />
            <text class="status-text">{{ getStatusText(m.status) }}</text>
          </view>
        </view>
        <view class="member-more" @click.stop="showActions(m)">
          <AppIcon name="more-horizontal" :size="28" color="#9CA3AF" />
        </view>
      </view>
      <view class="bottom-spacer" />
    </scroll-view>

    <!-- 添加成员弹窗 -->
    <view v-if="showAdd" class="modal-overlay" @click="showAdd = false">
      <view class="modal-card" @click.stop>
        <text class="modal-title">添加成员</text>
        <input v-model="newPhone" type="number" maxlength="11" placeholder="请输入成员手机号" class="modal-input" />
        <view class="modal-actions">
          <view class="btn btn-cancel" @click="showAdd = false"><text>取消</text></view>
          <view class="btn btn-confirm" @click="addMember"><text>确认添加</text></view>
        </view>
      </view>
    </view>

    <!-- 更多操作弹窗 -->
    <view v-if="actionTarget" class="modal-overlay" @click="actionTarget = null">
      <view class="action-sheet" @click.stop>
        <view class="sheet-item" @click="viewProfile(actionTarget)">
          <AppIcon name="user" :size="28" color="#6B7280" />
          <text>查看资料</text>
        </view>
        <view v-if="isOwner" class="sheet-item sheet-danger" @click="removeMember(actionTarget)">
          <AppIcon name="trash" :size="28" color="#EF4444" />
          <text class="danger-text">移除成员</text>
        </view>
        <view class="sheet-cancel" @click="actionTarget = null">
          <text>取消</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import AppIcon from '@/components/AppIcon.vue'
import {
  getTeamMembers, saveTeamMembers, getPendingInvitations,
  getStatusText, inviteMemberByPhone, type TeamMember, type TeamInvitation,
} from '@/utils/profileStore'
import { useNavBar } from '@/composables/useNavBar'

const { statusBarH, navH, navPad } = useNavBar()
const showAdd = ref(false); const newPhone = ref(''); const actionTarget = ref<TeamMember|null>(null)
const isOwner = ref(true)

const members = ref<TeamMember[]>(getTeamMembers())
const invites = ref<TeamInvitation[]>(getPendingInvitations())
const onlineCount = computed(() => members.value.filter((m) => m.status === 'online').length)

function reloadData() {
  members.value = getTeamMembers() as TeamMember[]
  invites.value = getPendingInvitations()
}

onShow(() => reloadData())

function addMember() {
  if (!newPhone.value.trim() || newPhone.value.trim().length < 11) {
    uni.showToast({ title: '请输入正确的手机号', icon: 'none', duration: 1500 }); return
  }
  const result = inviteMemberByPhone(newPhone.value.trim())
  if (result.success) {
    showAdd.value = false; newPhone.value = ''
    reloadData()
  }
  uni.showToast({ title: result.message, icon: result.success ? 'success' : 'none', duration: 2000 })
}
function viewProfile(m: TeamMember) { uni.showToast({ title: `${m.name} 的资料`, icon: 'none', duration: 1200 }) }
function showActions(m: TeamMember) { actionTarget.value = m }
function removeMember(m: TeamMember) {
  uni.showModal({
    title: '移除成员', content: `确认移除 ${m.name} 吗？`, confirmText: '移除', confirmColor: '#EF4444',
    success(res) {
      if (res.confirm) {
        const updated = members.value.filter((x) => x.id !== m.id)
        members.value = updated
        saveTeamMembers(updated)
        actionTarget.value = null
      }
    },
  })
}
function goBack() { uni.navigateBack() }
</script>

<style lang="scss" scoped>
/* ===== 引用全局设计 Token (uni.scss) ===== */

.page { min-height: 100vh; background: $uni-bg-color-grey; display: flex; flex-direction: column; }
.nav-bar { flex-shrink: 0; }
.nav-inner { display:flex; align-items:center; padding-left:40rpx; }
.nav-left { width:72rpx; height:72rpx; border-radius:50%; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.back-icon { font-size:56rpx; color:$uni-text-color; font-weight:300; line-height:1; margin-top:-4rpx; }
.nav-title { font-size:36rpx; font-weight:500; color:$uni-text-color; margin-left:12rpx; }
.nav-right { margin-left:auto; width:72rpx; height:72rpx; display:flex; align-items:center; justify-content:center; flex-shrink:0; }

.stats-bar { display: flex; align-items: baseline; gap: 16rpx; padding: 20rpx 44rpx 16rpx; }
.stats-text { font-size: 28rpx; color: $uni-text-color; }
.stats-sub { font-size: 24rpx; color: $uni-text-color-tertiary; }

.content { flex: 1; padding: 0 36rpx; }

.member-card { display: flex; align-items: center; gap: 20rpx; padding: 24rpx 28rpx; background: $uni-bg-color; border-radius: 24rpx; margin-bottom: 14rpx; box-shadow: 0 4rpx 16rpx rgba(0,0,0,0.03); }
.member-avatar { width: 72rpx; height: 72rpx; border-radius: 50%; overflow: hidden; flex-shrink: 0; background: linear-gradient(135deg, #EEF0FF, #DCD8FF); display: flex; align-items: center; justify-content: center; }
.member-avatar image { width: 100%; height: 100%; }
.avatar-initial { font-size: 32rpx; color: #202332; }
.member-body { flex: 1; min-width: 0; }
.member-top { display: flex; align-items: center; gap: 12rpx; margin-bottom: 8rpx; }
.member-name { font-size: 28rpx; color: $uni-text-color; }
.tag-owner { font-size: 20rpx; color: #5B68C8; background: #EEF1FF; padding: 4rpx 14rpx; border-radius: 16rpx; }
.tag-member { font-size: 20rpx; color: $uni-text-color-tertiary; background: $uni-border-color-light; padding: 4rpx 14rpx; border-radius: 16rpx; }
.member-status { display: flex; align-items: center; gap: 8rpx; }
.status-dot { width: 12rpx; height: 12rpx; border-radius: 50%; }
.dot-online { background: $uni-color-accent-mint; }
.dot-offline { background: #B8BDC8; }
.dot-busy { background: $uni-color-accent-orange; }
.status-text { font-size: 22rpx; color: $uni-text-color-secondary; }
.member-more { width: 56rpx; height: 56rpx; display: flex; align-items: center; justify-content: center; flex-shrink: 0; border-radius: 50%; }
.member-more:active { background: $uni-border-color-light; }

.bottom-spacer { height: 48rpx; }

/* 邀请区 */
.invite-section { margin-bottom: 24rpx; }
.section-label { display: block; font-size: 24rpx; color: $uni-text-color-tertiary; font-weight: 400; padding: 0 8rpx 12rpx; }
.invite-card { opacity: 0.75; }
.invite-avatar { background: linear-gradient(135deg, #FFF7ED, #FFEDD5); }
.tag-pending { font-size: 20rpx; color: #C2410C; background: #FFF7ED; padding: 4rpx 14rpx; border-radius: 16rpx; }

/* 弹窗 */
.modal-overlay { position: fixed; top: 0; right: 0; bottom: 0; left: 0; background: rgba(0,0,0,0.45); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 0 48rpx; }
.modal-card { width: 100%; max-width: 600rpx; background: #FFF; border-radius: 32rpx; padding: 40rpx 36rpx; }
.modal-title { display: block; font-size: 32rpx; color: $uni-text-color; text-align: center; margin-bottom: 32rpx; font-weight: 500; }
.modal-input { width: 100%; height: 88rpx; padding: 0 24rpx; border: 1rpx solid #D1D5DB; border-radius: 20rpx; font-size: 28rpx; color: $uni-text-color; background: $uni-bg-color-grey; box-sizing: border-box; margin-bottom: 28rpx; }
.modal-actions { display: flex; gap: 20rpx; }
.btn { flex: 1; height: 88rpx; border-radius: 24rpx; display: flex; align-items: center; justify-content: center; font-size: 28rpx; font-weight: 500; }
.btn-cancel { background: $uni-border-color-light; color: $uni-text-color-secondary; }
.btn-confirm { background: $uni-color-brand; color: #FFF; }

/* 操作面板 */
.action-sheet { width: 100%; max-width: 600rpx; background: #FFF; border-radius: 32rpx; padding: 16rpx; }
.sheet-item { display: flex; align-items: center; gap: 20rpx; padding: 28rpx 24rpx; border-radius: 20rpx; font-size: 28rpx; color: $uni-text-color; }
.sheet-item:active { background: $uni-bg-color-grey; }
.sheet-danger:active { background: #FEF2F2; }
.danger-text { color: $uni-color-error; }
.sheet-cancel { padding: 24rpx; text-align: center; font-size: 28rpx; color: $uni-text-color-secondary; border-top: 1rpx solid $uni-border-color-light; margin-top: 8rpx; }
</style>
