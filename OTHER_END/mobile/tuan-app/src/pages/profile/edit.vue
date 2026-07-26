<template>
  <view class="page">
    <!-- Avatar -->
    <view class="avatar-section">
      <view class="avatar-wrapper" @click="handleChangeAvatar">
        <image
          v-if="form.avatar"
          :src="form.avatar"
          class="avatar-img"
          mode="aspectFill"
        />
        <view v-else class="avatar-placeholder">
          <AppIcon name="user" :size="56" color="#111111" />
        </view>
        <view class="avatar-camera">
          <AppIcon name="camera" :size="24" color="#FFFFFF" />
        </view>
      </view>
      <text class="avatar-hint">点击更换头像</text>
    </view>

    <!-- Form -->
    <view class="form-card">
      <view class="form-item">
        <text class="form-label">昵称</text>
        <input
          v-model="form.nickname"
          class="form-input"
          placeholder="请输入昵称"
          maxlength="12"
        />
      </view>

      <view class="form-item">
        <text class="form-label">手机号</text>
        <text class="form-value-readonly">{{ maskedPhone }}</text>
      </view>

      <view class="form-item" @click="showGenderPicker = true">
        <text class="form-label">性别</text>
        <view class="status-display">
          <text class="status-label">{{ form.gender || '不公开' }}</text>
          <text class="picker-arrow">›</text>
        </view>
      </view>

      <view class="form-item">
        <text class="form-label">简介</text>
        <view class="intro-row">
          <input
            v-model="form.intro"
            class="form-input"
            placeholder="一句话介绍自己"
            maxlength="30"
          />
          <text class="char-count">{{ form.intro.length }}/30</text>
        </view>
      </view>

      <view class="form-item" @click="showStatusPicker = true">
        <text class="form-label">状态</text>
        <view class="status-display">
          <view
            class="status-dot"
            :style="{ background: currentStatus.color }"
          />
          <text class="status-label">{{ currentStatus.label }}</text>
          <text class="picker-arrow">›</text>
        </view>
      </view>
    </view>

    <!-- Gender Picker -->
    <view
      v-if="showGenderPicker"
      class="picker-mask"
      @click="showGenderPicker = false"
    >
      <view class="picker-card" @click.stop>
        <text class="picker-title">选择性别</text>
        <view
          v-for="opt in GENDER_OPTIONS"
          :key="opt"
          class="picker-option"
          :class="{ selected: form.gender === opt }"
          @click="selectGender(opt)"
        >
          <text class="option-label">{{ opt }}</text>
          <AppIcon v-if="form.gender === opt" name="check" :size="32" color="#466CAC" />
        </view>
        <view class="picker-cancel" @click="showGenderPicker = false">
          <text>取消</text>
        </view>
      </view>
    </view>

    <!-- Save -->
    <view class="save-area">
      <button class="save-btn" @click="handleSave">
        保存
      </button>
    </view>

    <!-- Status Picker -->
    <view
      v-if="showStatusPicker"
      class="picker-mask"
      @click="showStatusPicker = false"
    >
      <view class="picker-card" @click.stop>
        <text class="picker-title">选择状态</text>
        <view
          v-for="opt in STATUS_OPTIONS"
          :key="opt.value"
          class="picker-option"
          :class="{ selected: form.status === opt.value }"
          @click="selectStatus(opt.value)"
        >
          <view class="option-dot" :style="{ background: opt.color }" />
          <text class="option-label">{{ opt.label }}</text>
          <AppIcon v-if="form.status === opt.value" name="check" :size="32" color="#466CAC" />
        </view>
        <view class="picker-cancel" @click="showStatusPicker = false">
          <text>取消</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import AppIcon from '@/components/AppIcon.vue'
import { useAuth } from '@/utils/auth'
import {
  getProfile,
  saveProfile,
  getStatusInfo,
  STATUS_OPTIONS,
  type ProfileData,
} from '@/utils/profileStore'

const GENDER_OPTIONS = ['男', '女', '不公开']

const { currentPhone } = useAuth()

const maskedPhone = computed(() => {
  const p = currentPhone.value
  if (!p || p.length < 7) return '未绑定'
  return p.slice(0, 3) + '****' + p.slice(-4)
})

const form = reactive<ProfileData & { gender: string }>({
  ...getProfile(),
  gender: getProfile().gender || '不公开',
})
const showStatusPicker = ref(false)
const showGenderPicker = ref(false)

onLoad(() => {
  const saved = getProfile()
  Object.assign(form, { gender: '不公开', ...saved })
})

const currentStatus = computed(() => getStatusInfo(form.status))

function selectStatus(val: ProfileData['status']) {
  form.status = val
  showStatusPicker.value = false
}

function selectGender(val: string) {
  form.gender = val
  showGenderPicker.value = false
}

function handleChangeAvatar() {
  uni.chooseImage({
    count: 1,
    sizeType: ['compressed'],
    sourceType: ['album', 'camera'],
    success(res) {
      persistAvatar(res.tempFilePaths[0])
    },
    fail(err) {
      console.log('chooseImage failed:', err)
      if (err.errMsg?.includes('auth deny') || err.errMsg?.includes('cancel')) {
        // 用户拒绝或取消，静默处理
      } else {
        uni.showToast({ title: '选择图片失败，请重试', icon: 'none', duration: 1500 })
      }
    },
  })
}

/** 将临时图片持久化到本地存储，解决微信小程序 tempFilePath 过期问题 */
function persistAvatar(tempPath: string) {
  // 先清理旧头像文件，避免重复堆积
  if (form.avatar) {
    uni.getFileSystemManager().unlink({ filePath: form.avatar })
  }

  uni.saveFile({
    tempFilePath: tempPath,
    success(res) {
      form.avatar = res.savedFilePath
    },
    fail() {
      // saveFile 失败时（如 app-plus 平台不支持），直接用 tempPath
      // app-plus 上路径本身是持久的，不会过期
      form.avatar = tempPath
    },
  })
}

function handleSave() {
  const nickname = form.nickname.trim()
  const intro = form.intro.trim()

  if (!nickname || !intro) {
    uni.showToast({ title: '昵称和简介不能为空', icon: 'none', duration: 1500 })
    return
  }

  saveProfile({
    avatar: form.avatar,
    nickname,
    intro,
    status: form.status,
    gender: form.gender,
  } as ProfileData & { gender: string })

  uni.showToast({ title: '保存成功', icon: 'success', duration: 1200 })
  setTimeout(() => {
    uni.navigateBack()
  }, 800)
}
</script>

<style lang="scss" scoped>
.page {
  min-height: 100vh;
  background: #F7F7F7;
}

/* ===== 头像 ===== */
.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 60rpx;
}

.avatar-wrapper {
  width: 160rpx;
  height: 160rpx;
  border-radius: 50%;
  position: relative;
}

.avatar-img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: #F1F1F1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-camera {
  position: absolute;
  bottom: 4rpx;
  right: 4rpx;
  width: 48rpx;
  height: 48rpx;
  border-radius: 50%;
  background: #171717;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.25);
  border: 4rpx solid #FFFFFF;
}

.avatar-hint {
  font-size: 24rpx;
  color: #8E8E8E;
  margin-top: 18rpx;
}

/* ===== 表单 ===== */
.form-card {
  margin: 48rpx 48rpx 0;
  background: #FFFFFF;
  border-radius: 44rpx;
  overflow: hidden;
  border: 1rpx solid #E8E8E8;
  box-shadow: 0 8rpx 24rpx rgba(0, 0, 0, 0.06);
}

.form-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28rpx 36rpx;
  border-bottom: 1rpx solid #E8E8E8;
  min-height: 88rpx;
  box-sizing: border-box;
}

.form-item:last-child {
  border-bottom: none;
}

.form-label {
  font-size: 28rpx;
  font-weight: 600;
  color: #111111;
  flex-shrink: 0;
  margin-right: 24rpx;
}

.form-input {
  flex: 1;
  font-size: 28rpx;
  text-align: right;
  color: #111111;
  padding: 0;
}

.form-value-readonly {
  font-size: 28rpx;
  color: $uni-text-color-tertiary;
}

.intro-row {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.intro-row .form-input {
  flex: 1;
}

.char-count {
  font-size: 22rpx;
  color: #B5B5B5;
  flex-shrink: 0;
}

/* ===== 状态 ===== */
.status-display {
  display: flex;
  align-items: center;
  gap: 10rpx;
}

.status-dot {
  width: 14rpx;
  height: 14rpx;
  border-radius: 50%;
}

.status-label {
  font-size: 28rpx;
  color: #111111;
}

.picker-arrow {
  font-size: 40rpx;
  color: #DADADA;
  margin-left: 8rpx;
}

/* ===== 保存 ===== */
.save-area {
  padding: 48rpx 48rpx 0;
}

.save-btn {
  width: 100%;
  height: 104rpx;
  line-height: 104rpx;
  background: #171717;
  color: #FFFFFF;
  border-radius: 36rpx;
  font-size: 32rpx;
  font-weight: 600;
  border: none;
  box-shadow: 0 8rpx 24rpx rgba(0, 0, 0, 0.15);
}

.save-btn:active {
  opacity: 0.88;
}

/* ===== 状态选择器 ===== */
.picker-mask {
  position: fixed;
  top: 0; right: 0; bottom: 0; left: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  z-index: 1000;
}

.picker-card {
  width: 100%;
  background: #FFFFFF;
  border-radius: 60rpx 60rpx 0 0;
  padding: 36rpx 48rpx calc(40rpx + env(safe-area-inset-bottom));
}

.picker-title {
  display: block;
  font-size: 32rpx;
  font-weight: 700;
  color: #111111;
  text-align: center;
  margin-bottom: 24rpx;
}

.picker-option {
  display: flex;
  align-items: center;
  padding: 24rpx 24rpx;
  border-radius: 28rpx;
  gap: 16rpx;
}

.picker-option:active {
  background: #F7F7F7;
}

.picker-option.selected {
  background: #F1F1F1;
}

.option-dot {
  width: 20rpx;
  height: 20rpx;
  border-radius: 50%;
}

.option-label {
  flex: 1;
  font-size: 30rpx;
  color: #111111;
  font-weight: 500;
}


.picker-cancel {
  margin-top: 16rpx;
  padding: 24rpx;
  text-align: center;
  border-radius: 36rpx;
  background: #F1F1F1;
}

.picker-cancel:active {
  background: #E5E5E5;
}

.picker-cancel text {
  font-size: 28rpx;
  color: #5F5F5F;
}
</style>
