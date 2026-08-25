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
    val apiClient = remember { ApiClient(tokenManager) }
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
            onLoggedIn = { loggedIn = true },
        )
    }
}
