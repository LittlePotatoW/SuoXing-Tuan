/**
 * SMS 验证码服务
 *
 * 当前阶段使用本地模拟（uni.setStorageSync 存储，弹窗展示验证码）。
 * 后续对接后端时只需替换 sendSms 和 verifySms 两个函数的实现，
 * 其余代码（倒计时、校验流程）无需修改。
 */

const SMS_STORAGE_KEY = 'sms_code'
const CODE_EXPIRE_MS = 5 * 60 * 1000 // 5 分钟有效
const CODE_LENGTH = 6

// ---- 类型 ----

export interface SmsRecord {
  code: string
  expireTime: number // Date.now() + 5 min
  phone: string
}

export interface SmsResult {
  success: boolean
  message: string
}

// ---- 内部工具 ----

function generateCode(): string {
  return String(Math.floor(Math.pow(10, CODE_LENGTH - 1) + Math.random() * 9 * Math.pow(10, CODE_LENGTH - 1)))
}

function saveRecord(record: SmsRecord): void {
  uni.setStorageSync(SMS_STORAGE_KEY, record)
}

function getRecord(): SmsRecord | null {
  return uni.getStorageSync(SMS_STORAGE_KEY) || null
}

function clearRecord(): void {
  uni.removeStorageSync(SMS_STORAGE_KEY)
}

// ---- 公开 API ----

/**
 * 发送验证码。
 * 当前为模拟实现：生成随机码 → 本地存储 → 弹窗展示。
 *
 * TODO: 对接后端时替换为：
 *   const res = await uni.request({ url: 'https://api.xxx.com/sms/send', method: 'POST', data: { phone } })
 */
export async function sendSms(phone: string): Promise<SmsResult> {
  // 校验手机号
  if (!phone || phone.length < 11) {
    return { success: false, message: '手机号无效' }
  }

  // 60s 内重复发送限制（防止刷验证码）
  const existing = getRecord()
  if (existing && existing.phone === phone) {
    const elapsed = Date.now() - (existing.expireTime - CODE_EXPIRE_MS)
    if (elapsed < 60_000) {
      return { success: false, message: `请${Math.ceil((60_000 - elapsed) / 1000)}秒后再试` }
    }
  }

  const code = generateCode()

  // 存储验证码
  saveRecord({
    code,
    expireTime: Date.now() + CODE_EXPIRE_MS,
    phone,
  })

  // 模拟：弹窗展示验证码（开发/演示用，生产环境删除）
  uni.showModal({
    title: '验证码（演示模式）',
    content: `您的验证码是：\n\n${code}\n\n有效期 5 分钟\n（对接真实短信API后将不再弹窗）`,
    showCancel: false,
    confirmText: '知道了',
  })

  console.log(`[SMS] 模拟发送验证码到 ${phone}：${code}`)

  return { success: true, message: '验证码已发送' }
}

/**
 * 校验验证码。
 *
 * TODO: 对接后端时替换为：
 *   const res = await uni.request({ url: 'https://api.xxx.com/sms/verify', method: 'POST', data: { phone, code } })
 */
export function verifySms(phone: string, inputCode: string): SmsResult {
  if (!inputCode || inputCode.length !== CODE_LENGTH) {
    return { success: false, message: '请输入6位验证码' }
  }

  const record = getRecord()
  if (!record) {
    return { success: false, message: '请先获取验证码' }
  }
  if (record.phone !== phone) {
    return { success: false, message: '验证码与手机号不匹配' }
  }
  if (Date.now() > record.expireTime) {
    clearRecord()
    return { success: false, message: '验证码已过期，请重新获取' }
  }
  if (inputCode !== record.code) {
    return { success: false, message: '验证码错误' }
  }

  // 验证通过后清除，防止重复使用
  clearRecord()
  return { success: true, message: '验证通过' }
}

/** 清除验证码缓存（页面卸载时调用） */
export function clearSmsCache(): void {
  clearRecord()
}
