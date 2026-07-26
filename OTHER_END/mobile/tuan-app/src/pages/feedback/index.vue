<template>
  <view class="feedback-page">
    <view class="form-section">
      <picker
        mode="selector"
        :range="feedbackTypes"
        :value="typeIndex"
        @change="onTypeChange"
      >
        <view class="form-item picker-item">
          <text class="form-label">反馈类型</text>
          <view class="picker-display">
            <text>{{ feedbackType }}</text>
            <text class="picker-arrow">›</text>
          </view>
        </view>
      </picker>

      <view class="form-item">
        <text class="form-label">联系方式</text>
        <input
          v-model="contact"
          class="form-input"
          placeholder="手机号或邮箱（选填）"
        />
      </view>

      <view class="form-item">
        <text class="form-label">
          反馈内容 <text class="required">*</text>
        </text>
        <textarea
          v-model="feedbackContent"
          class="form-textarea"
          placeholder="请描述您的反馈..."
          :maxlength="500"
        />
        <text class="char-count">{{ feedbackContent.length }}/500</text>
      </view>

      <text v-if="errorMessage" class="error-text">{{ errorMessage }}</text>

      <button
        :loading="isSubmitting"
        :disabled="isSubmitting"
        class="submit-btn"
        @click="handleSubmit"
      >
        {{ isSubmitting ? '提交中...' : '提交反馈' }}
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const feedbackTypes = ['Bug 报告', '功能建议', '通用反馈', '其他']

const contact = ref('')
const feedbackType = ref('Bug 报告')
const feedbackContent = ref('')
const isSubmitting = ref(false)
const errorMessage = ref('')

const typeIndex = computed(() => feedbackTypes.indexOf(feedbackType.value))

function onTypeChange(e: { detail: { value: number } }) {
  const idx = e.detail.value
  feedbackType.value = feedbackTypes[idx]
}

function validate(): boolean {
  if (!feedbackContent.value.trim()) {
    errorMessage.value = '请填写反馈内容'
    return false
  }
  return true
}

async function handleSubmit() {
  errorMessage.value = ''
  if (!validate()) return

  isSubmitting.value = true
  try {
    await new Promise((resolve) => setTimeout(resolve, 600))
    uni.showToast({
      title: '感谢您的反馈！',
      icon: 'success',
      duration: 1500,
    })
    setTimeout(() => {
      uni.navigateBack()
    }, 600)
  } finally {
    isSubmitting.value = false
  }
}
</script>

<style lang="scss" scoped>
.feedback-page {
  min-height: 100vh;
  background: #F7F7F7;
  padding: 0 48rpx;
}

.form-section {
  padding-top: 32rpx;
}

.form-item {
  padding: 32rpx 0;
  border-bottom: 1rpx solid #E8E8E8;
}

.picker-item {
  display: block;
}

.form-label {
  display: block;
  font-size: 28rpx;
  font-weight: 600;
  color: #111111;
  margin-bottom: 16rpx;
}

.required {
  color: #EF4444;
}

.form-input {
  height: 80rpx;
  font-size: 30rpx;
  width: 100%;
  padding: 0;
  color: #111111;
}

.form-input::placeholder {
  color: #B5B5B5;
}

.form-textarea {
  width: 100%;
  height: 240rpx;
  font-size: 30rpx;
  padding: 24rpx;
  border: 1rpx solid #BDBDBD;
  border-radius: 24rpx;
  background: #FFFFFF;
  box-sizing: border-box;
  color: #111111;
}

.picker-display {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 80rpx;
  font-size: 30rpx;
  color: #111111;
}

.picker-arrow {
  font-size: 44rpx;
  color: #DADADA;
  font-weight: 300;
}

.char-count {
  display: block;
  text-align: right;
  font-size: 24rpx;
  color: #8E8E8E;
  margin-top: 10rpx;
}

.error-text {
  display: block;
  color: #EF4444;
  font-size: 26rpx;
  margin-top: 20rpx;
}

.submit-btn {
  width: 100%;
  height: 104rpx;
  line-height: 104rpx;
  background: #171717;
  color: #FFFFFF;
  border-radius: 36rpx;
  font-size: 32rpx;
  font-weight: 600;
  margin-top: 64rpx;
  border: none;

  &[disabled] {
    opacity: 0.3;
  }
}
</style>
