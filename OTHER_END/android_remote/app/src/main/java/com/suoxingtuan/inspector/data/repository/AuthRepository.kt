package com.suoxingtuan.inspector.data.repository

import com.suoxingtuan.inspector.data.local.Preferences
import com.suoxingtuan.inspector.data.model.AuthResult
import com.suoxingtuan.inspector.data.model.StoredUser
import kotlinx.coroutines.delay
import kotlin.random.Random

/**
 * Auth repository — login, register, logout, token management.
 * Mirrors tuan-app auth.ts + userStore.ts logic.
 */
object AuthRepository {
    private const val USERS_KEY = "registered_users"
    private const val TOKEN_KEY = "auth_token"

    // ---- Token management ----

    fun getToken(): String? = Preferences.getString(TOKEN_KEY)
    fun setToken(token: String) = Preferences.setString(TOKEN_KEY, token)
    fun removeToken() = Preferences.remove(TOKEN_KEY)

    fun getPhoneFromToken(): String {
        val t = getToken() ?: return ""
        val parts = t.split("-")
        return if (parts.size >= 2) parts[1] else ""
    }

    // ---- User storage ----

    fun getUsers(): List<StoredUser> = Preferences.getObject<List<StoredUser>>(USERS_KEY) ?: emptyList()
    private fun saveUsers(users: List<StoredUser>) = Preferences.setObject(USERS_KEY, users)

    // ---- Auth operations ----

    suspend fun login(phone: String, password: String): AuthResult {
        delay(400 + Random.nextLong(400))
        val result = verifyLogin(phone, password)
        if (result.success) {
            val loginToken = "token-$phone-${System.currentTimeMillis()}"
            setToken(loginToken)
        }
        return result
    }

    suspend fun register(phone: String, password: String): AuthResult {
        delay(400 + Random.nextLong(400))
        return registerUser(phone, password)
    }

    fun logout() = removeToken()

    fun checkAuth(): Boolean {
        val stored = getToken()
        return stored != null
    }

    // ---- Internal ----

    private fun verifyLogin(phone: String, password: String): AuthResult {
        if (phone.isBlank() || password.isBlank()) return AuthResult(false, "请输入手机号和密码")
        val users = getUsers()
        val user = users.find { it.phone == phone }
            ?: return AuthResult(false, "该手机号未注册，请先注册")
        if (user.password != password) return AuthResult(false, "密码错误，请重试")
        return AuthResult(true, "登录成功")
    }

    private fun registerUser(phone: String, password: String): AuthResult {
        if (phone.length < 11) return AuthResult(false, "请输入正确的11位手机号")
        if (password.length < 6) return AuthResult(false, "密码至少需要6位")
        val users = getUsers().toMutableList()
        if (users.any { it.phone == phone }) return AuthResult(false, "该手机号已注册，请直接登录")
        users.add(StoredUser(phone, password, "用户${phone.takeLast(4)}", java.time.Instant.now().toString()))
        saveUsers(users)
        return AuthResult(true, "注册成功，请登录")
    }
}
