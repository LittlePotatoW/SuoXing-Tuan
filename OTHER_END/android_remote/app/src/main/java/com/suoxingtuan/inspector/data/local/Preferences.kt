package com.suoxingtuan.inspector.data.local

import android.content.Context
import android.content.SharedPreferences
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken

/**
 * Typed SharedPreferences wrapper — replaces uni.storage sync APIs.
 * Usage: Preferences.init(context) once at app start, then use get/set/remove.
 */
object Preferences {
    private lateinit var prefs: SharedPreferences
    @PublishedApi internal val gson = Gson()

    fun init(context: Context) {
        prefs = context.getSharedPreferences("suoxingtuan_prefs", Context.MODE_PRIVATE)
    }

    fun getString(key: String): String? {
        val v = prefs.getString(key, null)
        return if (v.isNullOrEmpty()) null else v
    }

    fun setString(key: String, value: String) = prefs.edit().putString(key, value).apply()
    fun remove(key: String) = prefs.edit().remove(key).apply()

    inline fun <reified T> getObject(key: String): T? {
        val json = getString(key) ?: return null
        return try { gson.fromJson(json, object : TypeToken<T>() {}.type) } catch (_: Exception) { null }
    }

    inline fun <reified T> setObject(key: String, value: T) {
        setString(key, gson.toJson(value))
    }
}
