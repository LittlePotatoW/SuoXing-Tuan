<template>
  <view class="login-page">
    <!-- 背景渐变 -->
    <view class="bg-gradient" />

    <!-- 插图（卡片上方偏左，与卡片左侧对齐） -->
    <image class="login-illus" src="/static/login-illustration.png" mode="widthFix" />

    <!-- 中央白色卡片 -->
    <view class="login-card">
      <!-- 账号输入框 -->
      <input
        v-model="phone"
        type="number"
        maxlength="11"
        :placeholder="isRegister ? '请输入手机号' : '请输入账号'"
        class="login-input"
      />

      <!-- 密码输入框 -->
      <input
        v-model="password"
        password
        :placeholder="isRegister ? '请设置密码（至少6位）' : '请输入密码'"
        class="login-input"
      />

      <!-- 确认密码（仅注册模式） -->
      <input
        v-if="isRegister"
        v-model="confirmPassword"
        password
        placeholder="请再次输入密码"
        class="login-input"
      />

      <text v-if="errorMessage" class="error-text">{{ errorMessage }}</text>

      <!-- 登录 / 注册按钮 -->
      <template v-if="!isRegister">
        <button
          :disabled="!canSubmit"
          :loading="isLoading"
          class="btn-login"
          @click="handleLogin"
        >
          <image class="login-btn-icon" src="/static/phone-icon.png" mode="aspectFit" />
          {{ isLoading ? '登录中...' : '登录' }}
        </button>

        <!-- #ifdef MP-WEIXIN -->
        <button class="btn-wechat" @click="handleWechatLogin">
          <image class="wechat-btn-icon" src="/static/wechat-icon.png" mode="aspectFit" />
          微信登录
        </button>
        <!-- #endif -->
      </template>

      <template v-if="isRegister">
        <button
          :disabled="!canRegister"
          :loading="isLoading"
          class="btn-login"
          @click="handleRegister"
        >
          {{ isLoading ? '注册中...' : '注册' }}
        </button>

        <view class="back-to-login" @click="toggleMode">
          <text class="back-text">← 返回登录</text>
        </view>
      </template>

      <!-- 底部链接 -->
      <view class="card-footer" v-if="!isRegister">
        <text class="footer-link" @click="toggleMode">忘记密码</text>
        <text class="footer-divider">|</text>
        <text class="footer-link" @click="toggleMode">注册账号</text>
      </view>
    </view>

    <!-- 协议提示 -->
    <text class="agreement-text">登录即表示同意《用户协议》和《隐私政策》</text>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAuth } from '@/utils/auth'

const phone = ref('')
const password = ref('')
const confirmPassword = ref('')
const errorMessage = ref('')
const isRegister = ref(false)

const { isLoading, login, register } = useAuth()

const canSubmit = computed(
  () => phone.value.trim() !== '' && password.value.trim() !== '' && !isLoading.value,
)

const canRegister = computed(
  () => phone.value.trim() !== '' && password.value.trim() !== '' && confirmPassword.value.trim() !== '' && !isLoading.value,
)

function toggleMode() {
  isRegister.value = !isRegister.value
  errorMessage.value = ''
  phone.value = ''
  password.value = ''
  confirmPassword.value = ''
}

async function handleLogin() {
  errorMessage.value = ''

  if (!phone.value.trim()) {
    errorMessage.value = '请输入账号'
    return
  }
  if (!password.value) {
    errorMessage.value = '请输入密码'
    return
  }

  const result = await login(phone.value.trim(), password.value)

  if (result.success) {
    uni.showToast({ title: '登录成功', icon: 'success', duration: 1500 })
    setTimeout(() => uni.reLaunch({ url: '/pages/index/index' }), 500)
  } else {
    errorMessage.value = result.message
  }
}

async function handleRegister() {
  errorMessage.value = ''

  if (!phone.value.trim() || phone.value.trim().length < 11) {
    errorMessage.value = '请输入正确的11位手机号'
    return
  }
  if (!password.value || password.value.length < 6) {
    errorMessage.value = '密码至少需要6位'
    return
  }
  if (password.value !== confirmPassword.value) {
    errorMessage.value = '两次输入的密码不一致'
    return
  }

  const result = await register(phone.value.trim(), password.value)

  if (result.success) {
    uni.showToast({ title: '注册成功，请登录', icon: 'success', duration: 2000 })
    toggleMode()
  } else {
    errorMessage.value = result.message
  }
}

// #ifdef MP-WEIXIN
async function handleWechatLogin() {
  try {
    const loginRes = await new Promise<UniApp.LoginRes>((resolve, reject) => {
      uni.login({ provider: 'weixin', success: resolve, fail: reject })
    })
    if (!loginRes.code) {
      uni.showToast({ title: '微信授权失败', icon: 'none' })
      return
    }

    let nickName = '微信用户'
    let avatarUrl = ''
    try {
      const profileRes = await new Promise<UniApp.GetUserProfileRes>((resolve, reject) => {
        uni.getUserProfile({ desc: '用于完善个人资料', success: resolve, fail: reject })
      })
      nickName = profileRes.userInfo?.nickName || nickName
      avatarUrl = profileRes.userInfo?.avatarUrl || ''
    } catch { /* user declined profile */ }

    const mockOpenId = 'wx_' + loginRes.code.slice(0, 8)
    const { getStorage, setStorage } = await import('@/utils/storage')
    const wxUsers = getStorage<Array<{ openId: string; phone: string; nickName: string }>>('wx_users') || []
    let wxUser = wxUsers.find((u) => u.openId === mockOpenId)

    if (!wxUser) {
      const mockPhone = 'wx' + loginRes.code.slice(0, 9)
      wxUser = { openId: mockOpenId, phone: mockPhone, nickName }
      wxUsers.push(wxUser)
      setStorage('wx_users', wxUsers)
      const { registerUser } = await import('@/utils/userStore')
      registerUser(mockPhone, 'wx_login_' + mockOpenId.slice(-6))
    }

    const auth = useAuth()
    const result = await auth.login(wxUser.phone, 'wx_login_' + mockOpenId.slice(-6))
    if (result.success) {
      const { saveProfile, getProfile } = await import('@/utils/profileStore')
      const profile = getProfile()
      profile.nickname = nickName
      if (avatarUrl) profile.avatar = avatarUrl
      saveProfile(profile)
      uni.showToast({ title: '微信登录成功', icon: 'success', duration: 1500 })
      setTimeout(() => uni.reLaunch({ url: '/pages/index/index' }), 500)
    } else {
      uni.showToast({ title: result.message || '登录失败', icon: 'none' })
    }
  } catch (e: any) {
    console.error('微信登录失败:', e)
    uni.showToast({ title: e.errMsg || '微信登录失败', icon: 'none', duration: 2000 })
  }
}
// #endif
</script>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 0 48rpx;
  position: relative;
}

/* 插图 — 带浮动动画 */
.login-illus {
  width: 420rpx;
  align-self: flex-start;
  margin-bottom: 32rpx;
  margin-left: -10rpx;
  position: relative;
  z-index: 1;
  animation: float 4s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-12rpx); }
}

/* 背景渐变 — 缓慢呼吸 */
.bg-gradient {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: linear-gradient(160deg,
    #E8F4FD 0%,
    #F5F7FA 20%,
    #FFF8F0 50%,
    #E8F8F5 75%,
    #E0F7FA 100%
  );
  background-size: 200% 200%;
  animation: bgShift 8s ease-in-out infinite alternate;
  z-index: 0;
}

@keyframes bgShift {
  0% { background-position: 0% 0%; }
  100% { background-position: 100% 100%; }
}

/* 中央白色卡片 — 入场动画 */
.login-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 640rpx;
  background: #FFFFFF;
  border-radius: 32rpx;
  padding: 56rpx 44rpx 48rpx;
  box-shadow: 0 16rpx 48rpx rgba(0, 0, 0, 0.06);
  animation: cardIn 0.6s ease-out;
}

@keyframes cardIn {
  from {
    opacity: 0;
    transform: translateY(40rpx);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 输入框 */
.login-input {
  width: 100%;
  height: 96rpx;
  padding: 0 28rpx;
  border: 1rpx solid #E0E0E0;
  border-radius: 16rpx;
  font-size: 30rpx;
  font-weight: 400;
  color: #111111;
  background: #FAFAFA;
  box-sizing: border-box;
  margin-bottom: 24rpx;
  transition: border-color 0.25s, box-shadow 0.25s;
}

.login-input:focus {
  border-color: #000000;
  box-shadow: 0 0 0 4rpx rgba(0, 0, 0, 0.06);
}

.login-input::placeholder {
  color: #B0B0B0;
}

.error-text {
  display: block;
  font-size: 24rpx;
  font-weight: 400;
  color: #DA1E28;
  margin-bottom: 16rpx;
}

/* 登录按钮 */
.btn-login {
  width: 100%;
  height: 100rpx;
  border-radius: 50rpx;
  background: #000000;
  color: #FFFFFF;
  font-size: 30rpx;
  font-weight: 400;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 24rpx;
  position: relative;
  transition: transform 0.15s, opacity 0.2s;

  &:active {
    transform: scale(0.97);
    opacity: 0.9;
  }

  &[disabled] {
    opacity: 0.35;
  }
}

.login-btn-icon {
  position: absolute;
  left: 32rpx;
  top: 50%;
  transform: translateY(-50%);
  width: 44rpx;
  height: 44rpx;
}

/* 微信登录按钮 */
.btn-wechat {
  width: 100%;
  height: 100rpx;
  border-radius: 50rpx;
  background: #E0F7FA;
  color: #004D40;
  font-size: 30rpx;
  font-weight: 400;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 24rpx;
  position: relative;
  transition: transform 0.15s, opacity 0.2s;

  &:active {
    transform: scale(0.97);
    opacity: 0.85;
  }
}

.wechat-btn-icon {
  position: absolute;
  left: 32rpx;
  top: 50%;
  transform: translateY(-50%);
  width: 44rpx;
  height: 44rpx;
}

/* 底部链接 */
.card-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16rpx;
  margin-top: 48rpx;
}

.footer-link {
  font-size: 24rpx;
  font-weight: 400;
  color: #999999;
}

.back-to-login {
  text-align: center;
  margin-top: 24rpx;
}

.back-text {
  font-size: 24rpx;
  font-weight: 400;
  color: #999999;
}

.footer-divider {
  font-size: 24rpx;
  color: #CCCCCC;
}

/* 协议提示 */
.agreement-text {
  position: relative;
  z-index: 1;
  margin-top: 28rpx;
  font-size: 22rpx;
  font-weight: 400;
  color: #AAAAAA;
  text-align: center;
}
</style>
