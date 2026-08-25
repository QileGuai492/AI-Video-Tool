package com.aivideotool.app.data

import android.content.Context
import android.content.SharedPreferences

/** 本地 Token 管理，使用 SharedPreferences 持久化。 */
class TokenManager(context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("ai_video_tool", Context.MODE_PRIVATE)

    var token: String?
        get() = prefs.getString(KEY_TOKEN, null)
        set(value) {
            prefs.edit().putString(KEY_TOKEN, value).apply()
        }

    fun clear() {
        prefs.edit().remove(KEY_TOKEN).apply()
    }

    private companion object {
        const val KEY_TOKEN = "access_token"
    }
}
