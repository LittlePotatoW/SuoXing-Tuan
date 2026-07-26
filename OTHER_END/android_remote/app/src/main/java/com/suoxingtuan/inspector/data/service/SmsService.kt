package com.suoxingtuan.inspector.data.service

import com.suoxingtuan.inspector.data.local.Preferences
import com.suoxingtuan.inspector.data.model.SmsRecord
import com.suoxingtuan.inspector.data.model.SmsResult

/**
 * SMS verification code service — mirrors smsService.ts.
 * Currently uses local simulation; ready to be replaced with real API.
 */
object SmsService {
    private const val KEY = "sms_code"
    private const val EXPIRE_MS = 5 * 60 * 1000L
    private const val CODE_LENGTH = 6

    private fun generateCode(): String {
        val min = Math.pow(10.0, (CODE_LENGTH - 1).toDouble()).toInt()
        val max = Math.pow(10.0, CODE_LENGTH.toDouble()).toInt() - 1
        return (min + (Math.random() * (max - min)).toInt()).toString()
    }

    private fun getRecord(): SmsRecord? = Preferences.getObject<SmsRecord>(KEY)

    private fun saveRecord(record: SmsRecord) = Preferences.setObject(KEY, record)

    fun sendSms(phone: String): SmsResult {
        if (phone.length < 11) return SmsResult(false, "手机号无效")
        val existing = getRecord()
        if (existing != null && existing.phone == phone) {
            val elapsed = System.currentTimeMillis() - (existing.expireTime - EXPIRE_MS)
            if (elapsed < 60_000) return SmsResult(false, "请${Math.ceil((60_000 - elapsed) / 1000.0).toInt()}秒后再试")
        }
        val code = generateCode()
        saveRecord(SmsRecord(code, System.currentTimeMillis() + EXPIRE_MS, phone))
        // In production, replace with real SMS API call
        println("[SMS] 模拟发送验证码到 $phone：$code")
        return SmsResult(true, "验证码已发送（演示：$code）")
    }

    fun verifySms(phone: String, inputCode: String): SmsResult {
        if (inputCode.length != CODE_LENGTH) return SmsResult(false, "请输入6位验证码")
        val record = getRecord() ?: return SmsResult(false, "请先获取验证码")
        if (record.phone != phone) return SmsResult(false, "验证码与手机号不匹配")
        if (System.currentTimeMillis() > record.expireTime) {
            clearCache()
            return SmsResult(false, "验证码已过期，请重新获取")
        }
        if (inputCode != record.code) return SmsResult(false, "验证码错误")
        clearCache()
        return SmsResult(true, "验证通过")
    }

    fun clearCache() = Preferences.remove(KEY)
}
