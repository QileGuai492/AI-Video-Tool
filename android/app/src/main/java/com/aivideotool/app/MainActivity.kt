package com.aivideotool.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import com.aivideotool.app.data.ApiClient
import com.aivideotool.app.data.ServerConfig
import com.aivideotool.app.data.TokenManager
import com.aivideotool.app.ui.LoginScreen
import com.aivideotool.app.ui.TaskListScreen

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    AppRoot()
                }
            }
        }
    }
}

@Composable
fun AppRoot() {
    val context = LocalContext.current.applicationContext
    val tokenManager = remember { TokenManager(context) }
    val serverConfig = remember { ServerConfig(context) }
    var apiBaseUrl by remember { mutableStateOf(serverConfig.apiBaseUrl) }
    val apiClient = remember(apiBaseUrl) { ApiClient(tokenManager, apiBaseUrl) }
    var loggedIn by remember { mutableStateOf(tokenManager.token != null) }

    if (loggedIn) {
        TaskListScreen(
            apiClient = apiClient,
            tokenManager = tokenManager,
            onLogout = {
                tokenManager.clear()
                loggedIn = false
            },
        )
    } else {
        LoginScreen(
            apiClient = apiClient,
            tokenManager = tokenManager,
            serverConfig = serverConfig,
            onServerChanged = { newUrl ->
                serverConfig.apiBaseUrl = newUrl
                apiBaseUrl = serverConfig.apiBaseUrl
            },
            onLoggedIn = { loggedIn = true },
        )
    }
}
