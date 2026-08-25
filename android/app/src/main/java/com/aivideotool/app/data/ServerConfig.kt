package com.aivideotool.app.data

import android.content.Context
import android.content.SharedPreferences

/** 服务器地址配置，默认指向 Android 模拟器宿主机；真机可改为电脑局域网 IP。 */
class ServerConfig(context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("ai_video_tool", Context.MODE_PRIVATE)

    var apiBaseUrl: String
        get() = prefs.getString(KEY_API_BASE_URL, DEFAULT_API_BASE_URL) ?: DEFAULT_API_BASE_URL
        set(value) {
            prefs.edit().putString(KEY_API_BASE_URL, value.trimEnd('/') + "/").apply()
        }

    private companion object {
        const val KEY_API_BASE_URL = "api_base_url"
        // 10.0.2.2 是 Android 模拟器访问宿主机 localhost 的固定地址
        const val DEFAULT_API_BASE_URL = "http://10.0.2.2:8080/api/v1/"
    }
}
