<template>
  <view class="page">
    <!-- 导航栏 -->
    <view class="nav-bar" :style="{ paddingTop: statusBarH + 'px' }">
      <view class="nav-inner" :style="{ height: navH + 'px', paddingRight: navPad + 'px' }">
        <view class="nav-left" @click="goBack">
          <text class="back-icon">‹</text>
        </view>
        <text class="nav-title">修改密码</text>
        <view class="nav-spacer" />
      </view>
    </view>

    <view class="body-wrap" :style="{ paddingTop: navTotalH + 'px' }">
      <!-- ===== 步骤一：手机号验证 ===== -->
      <template v-if="step === 1">
        <view class="section">
          <text class="section-title">验证身份</text>
          <view class="card">
            <!-- 脱敏手机号 -->
            <view class="phone-row">
              <text class="phone-label">当前绑定手机号</text>
              <text class="phone-value">{{ maskedPhone }}</text>
            </view>

            <!-- 验证码 -->
            <view class="sms-row">
              <input
                v-model="smsCode"
                type="number"
                maxlength="6"
                placeholder="请输入6位验证码"
                class="sms-input"
              />
              <view
                class="sms-btn"
                :class="{ counting: countdown > 0 }"
                @click="handleSendSms"
              >
                <text>{{ smsBtnText }}</text>
              </view>
            </view>

            <!-- 演示模式提示 -->
            <view class="demo-hint">
              <text>💡 验证码会以弹窗方式展示，模拟真实短信发送</text>
            </view>
          </view>
        </view>

        <view class="btn-area">
          <button
            class="btn-primary"
            :disabled="smsCode.length < 6"
            @click="handleVerifyCode"
          >
            下一步
          </button>
        </view>
      </template>

      <!-- ===== 步骤二：设置新密码 ===== -->
      <template v-if="step === 2">
        <view class="section">
          <text class="section-title">设置新密码</text>
          <view class="card">
            <!-- 新密码 -->
            <view class="pw-item">
              <text class="pw-label">新密码</text>
              <view class="pw-input-row">
                <input
                  v-model="newPassword"
                  :password="!showNewPw"
                  placeholder="请输入新密码（至少8位）"
                  class="pw-input"
                  maxlength="32"
                  @input="checkStrength"
                />
                <view class="eye-btn" @click="showNewPw = !showNewPw">
                  <text class="eye-icon">{{ showNewPw ? '👁' : '👁‍🗨' }}</text>
                </view>
              </view>
            </view>

            <!-- 密码强度 -->
            <view v-if="newPassword" class="strength-row">
              <view class="strength-bar-track">
                <view
                  class="strength-bar-fill"
                  :style="{ width: strengthPercent + '%', background: strengthColor }"
                />
              </view>
              <text class="strength-text" :style="{ color: strengthColor }">
                {{ strengthLabel }}
              </text>
            </view>

            <!-- 确认密码 -->
            <view class="pw-item">
              <text class="pw-label">确认密码</text>
              <view class="pw-input-row">
                <input
                  v-model="confirmPassword"
                  :password="!showConfirmPw"
                  placeholder="请再次输入新密码"
                  class="pw-input"
                  maxlength="32"
                />
                <view class="eye-btn" @click="showConfirmPw = !showConfirmPw">
                  <text class="eye-icon">{{ showConfirmPw ? '👁' : '👁‍🗨' }}</text>
                </view>
              </view>
            </view>
            <text v-if="confirmPassword && newPassword !== confirmPassword" class="mismatch-hint">
              两次密码输入不一致
            </text>
          </view>
        </view>

        <view class="btn-area">
          <button
            class="btn-primary"
            :disabled="!canSubmitNewPw"
            @click="submitNewPassword"
          >
            确认修改
          </button>
        </view>
      </template>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import { useAuth } from '@/utils/auth'
import { getStorage, setStorage } from '@/utils/storage'
import { sendSms, verifySms, clearSmsCache } from '@/utils/smsService'
import { useNavBar } from '@/composables/useNavBar'

const { currentPhone } = useAuth()
const { statusBarH, navH, navPad, navTotalH } = useNavBar()

// ---- 步骤 ----
const step = ref(1)

// ---- 手机号 ----
const maskedPhone = computed(() => {
  const p = currentPhone.value
  if (!p || p.length < 7) return '未绑定'
  return p.slice(0, 3) + '****' + p.slice(-4)
})

// ---- 步骤一：验证码 ----
const smsCode = ref('')
const countdown = ref(0)
let countdownTimer: ReturnType<typeof setInterval> | null = null

const smsBtnText = computed(() => {
  if (countdown.value > 0) return `${countdown.value}s`
  return '获取验证码'
})

async function handleSendSms() {
  if (countdown.value > 0) return

  const phone = currentPhone.value
  if (!phone || phone.length < 11) {
    uni.showToast({ title: '手机号无效，请重新登录', icon: 'none', duration: 1500 })
    return
  }

  // 调用 SMS 服务发送验证码（当前为模拟实现，弹窗展示验证码）
  const result = await sendSms(phone)

  if (result.success) {
    // 60秒倒计时
    countdown.value = 60
    countdownTimer = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) {
        if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null }
      }
    }, 1000)
  } else {
    uni.showToast({ title: result.message, icon: 'none', duration: 2000 })
  }
}

function handleVerifyCode() {
  const phone = currentPhone.value

  // 前端基础校验
  if (smsCode.value.length < 6) {
    uni.showToast({ title: '请输入6位验证码', icon: 'none', duration: 1200 })
    return
  }

  // 调用 SMS 服务校验
  const result = verifySms(phone, smsCode.value)
  if (!result.success) {
    uni.showToast({ title: result.message, icon: 'none', duration: 2000 })
    return
  }

  step.value = 2
}

// ---- 步骤二：设置密码 ----
const newPassword = ref('')
const confirmPassword = ref('')
const showNewPw = ref(false)
const showConfirmPw = ref(false)

const strengthLabel = ref('')
const strengthPercent = ref(0)
const strengthColor = ref('#DA1E28')

const canSubmitNewPw = computed(() => {
  return (
    newPassword.value.length >= 8 &&
    newPassword.value === confirmPassword.value &&
    strengthLabel.value !== '弱'
  )
})

function checkStrength(): void {
  const pw = newPassword.value
  if (!pw) {
    strengthLabel.value = ''
    strengthPercent.value = 0
    strengthColor.value = '#DA1E28'
    return
  }

  const hasNum = /\d/.test(pw)
  const hasLetter = /[a-zA-Z]/.test(pw)
  const hasSpecial = /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]/.test(pw)

  const len = pw.length

  if ((hasNum && !hasLetter && !hasSpecial) || (!hasNum && hasLetter && !hasSpecial)) {
    // 纯数字或纯字母
    if (len < 8) {
      strengthLabel.value = '弱'
      strengthPercent.value = 25
      strengthColor.value = '#DA1E28'
    } else {
      strengthLabel.value = '中'
      strengthPercent.value = 50
      strengthColor.value = '#F2994A'
    }
  } else if (hasNum && hasLetter && !hasSpecial) {
    // 数字+字母
    if (len >= 10) {
      strengthLabel.value = '强'
      strengthPercent.value = 75
      strengthColor.value = '#24A148'
    } else {
      strengthLabel.value = '中'
      strengthPercent.value = 55
      strengthColor.value = '#F2994A'
    }
  } else if (hasNum && hasLetter && hasSpecial && len >= 10) {
    // 数字+字母+特殊字符, 长度 ≥ 10
    strengthLabel.value = '强'
    strengthPercent.value = 100
    strengthColor.value = '#24A148'
  } else {
    strengthLabel.value = '弱'
    strengthPercent.value = 30
    strengthColor.value = '#DA1E28'
  }
}

function submitNewPassword() {
  if (newPassword.value.length < 8) {
    uni.showToast({ title: '新密码至少需要8位', icon: 'none', duration: 1500 })
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    uni.showToast({ title: '两次密码输入不一致', icon: 'none', duration: 1500 })
    return
  }

  // 更新本地存储的密码（预留 API 调用位置）
  // TODO: 后续对接后端时替换为 API 调用
  const users = getStorage<Array<{ phone: string; password: string }>>('registered_users') || []
  const idx = users.findIndex((u) => u.phone === currentPhone.value)
  if (idx >= 0) {
    users[idx].password = newPassword.value
    setStorage('registered_users', users)
  }

  uni.showToast({ title: '密码修改成功', icon: 'success', duration: 1500 })
  setTimeout(() => {
    uni.navigateBack()
  }, 1200)
}

// ---- 公共 ----
function goBack() {
  if (countdownTimer) clearInterval(countdownTimer)
  clearSmsCache()
  uni.navigateBack()
}

onUnmounted(() => {
  if (countdownTimer) clearInterval(countdownTimer)
  clearSmsCache()
})
</script>

<style lang="scss" scoped>
/* ===== 引用全局设计 Token ===== */

.page { min-height: 100vh; background: $uni-bg-color-grey; }

/* 导航栏 */
.nav-bar { position:fixed; top:0; left:0; right:0; z-index:100; background:$uni-bg-color-grey; }
.nav-inner { display:flex; align-items:center; padding-left:40rpx; }
.nav-left { width:72rpx; height:72rpx; border-radius:50%; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.back-icon { font-size:56rpx; color:$uni-text-color; font-weight:300; line-height:1; margin-top:-4rpx; }
.nav-title { font-size:40rpx; font-weight:700; color:$uni-text-color; margin-left:16rpx; }
.nav-spacer { width:72rpx; flex-shrink:0; }

.body-wrap { min-height:100vh; }

.section { margin-bottom: 48rpx; padding: 20rpx 36rpx 0; }
.section-title { font-size: 28rpx; color: $uni-text-color-tertiary; font-weight: 400; padding: 0 8rpx 16rpx; display: block; }

/* 卡片 */
.card { background: $uni-bg-color; border-radius: $uni-border-radius-lg; overflow: hidden; box-shadow: $uni-shadow-weak; }

/* 手机号行 */
.phone-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 32rpx;
  border-bottom: 1rpx solid $uni-border-color-light;
}
.phone-label { font-size: 28rpx; color: $uni-text-color; }
.phone-value { font-size: 28rpx; color: $uni-text-color-tertiary; }

/* 验证码 */
.sms-row {
  display: flex;
  align-items: center;
  padding: 24rpx 32rpx;
  gap: 20rpx;
}
.sms-input {
  flex: 1;
  height: 88rpx;
  background: $uni-bg-color-module;
  border-radius: $uni-border-radius-base;
  padding: 0 24rpx;
  font-size: 28rpx;
  color: $uni-text-color;
}
.sms-btn {
  flex-shrink: 0;
  height: 88rpx;
  padding: 0 28rpx;
  border-radius: $uni-border-radius-base;
  background: #466CAC;
  display: flex;
  align-items: center;
  justify-content: center;
}
.sms-btn text { font-size: 26rpx; color: #FFFFFF; font-weight: 500; }
.sms-btn.counting { background: #B5B5B5; }

.demo-hint {
  padding: 0 32rpx 24rpx;
  text { font-size: 22rpx; color: $uni-color-accent-orange; }
}

/* 按钮区 */
.btn-area { padding: 0 36rpx; }
.btn-primary {
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
.btn-primary[disabled] { background: #DADADA; color: #B5B5B5; }
.btn-primary:active { opacity: 0.88; }

/* 密码输入 */
.pw-item {
  padding: 28rpx 32rpx;
  border-bottom: 1rpx solid $uni-border-color-light;
}
.pw-item:last-child { border-bottom: none; }
.pw-label { font-size: 28rpx; font-weight: 600; color: $uni-text-color; margin-bottom: 16rpx; display: block; }

.pw-input-row {
  display: flex;
  align-items: center;
  background: $uni-bg-color-module;
  border-radius: $uni-border-radius-base;
  overflow: hidden;
}
.pw-input {
  flex: 1;
  height: 88rpx;
  padding: 0 24rpx;
  font-size: 28rpx;
  color: $uni-text-color;
}
.eye-btn {
  width: 80rpx;
  height: 88rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.eye-icon { font-size: 32rpx; }

/* 密码强度 */
.strength-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 12rpx 32rpx 20rpx;
}
.strength-bar-track {
  flex: 1;
  height: 8rpx;
  background: $uni-bg-color-module;
  border-radius: 4rpx;
  overflow: hidden;
}
.strength-bar-fill {
  height: 100%;
  border-radius: 4rpx;
  transition: width 0.3s ease, background 0.3s ease;
}
.strength-text { font-size: 24rpx; font-weight: 500; flex-shrink: 0; }

.mismatch-hint {
  display: block;
  font-size: 24rpx;
  color: $uni-color-error;
  padding: 0 32rpx 20rpx;
}
</style>
