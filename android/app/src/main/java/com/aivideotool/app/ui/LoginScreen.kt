package com.aivideotool.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.aivideotool.app.data.ApiClient
import com.aivideotool.app.data.LoginRequest
import com.aivideotool.app.data.RegisterRequest
import com.aivideotool.app.data.ServerConfig
import com.aivideotool.app.data.TokenManager
import kotlinx.coroutines.launch
import retrofit2.HttpException

@Composable
fun LoginScreen(
    apiClient: ApiClient,
    tokenManager: TokenManager,
    serverConfig: ServerConfig,
    onServerChanged: (String) -> Unit,
    onLoggedIn: () -> Unit,
) {
    var isRegister by remember { mutableStateOf(false) }
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var email by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var showServerSettings by remember { mutableStateOf(false) }
    var serverUrl by remember { mutableStateOf(serverConfig.apiBaseUrl) }
    val scope = rememberCoroutineScope()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = "AI 视频工具",
            style = MaterialTheme.typography.headlineMedium,
        )
        Text(
            text = if (isRegister) "注册新账号" else "登录后开始创作",
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.padding(bottom = 24.dp),
        )
        OutlinedTextField(
            value = username,
            onValueChange = { username = it },
            label = { Text("用户名") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        if (isRegister) {
            OutlinedTextField(
                value = email,
                onValueChange = { email = it },
                label = { Text("邮箱（可选）") },
                singleLine = true,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 12.dp),
            )
        }
        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text("密码") },
            singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 12.dp),
        )
        if (error != null) {
            Text(
                text = error ?: "",
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.padding(top = 12.dp),
            )
        }
        Button(
            onClick = {
                scope.launch {
                    loading = true
                    error = null
                    try {
                        val response = if (isRegister) {
                            apiClient.authApi.register(
                                RegisterRequest(
                                    username = username,
                                    password = password,
                                    email = email.ifBlank { null },
                                )
                            )
                        } else {
                            apiClient.authApi.login(LoginRequest(username, password))
                        }
                        tokenManager.token = response.accessToken
                        onLoggedIn()
                    } catch (e: HttpException) {
                        error = when (e.code()) {
                            400 -> "用户名已存在或参数不合法"
                            401 -> "用户名或密码错误"
                            422 -> "密码至少 8 位且包含字母和数字"
                            else -> "请求失败：${e.code()}"
                        }
                    } catch (e: Exception) {
                        error = "网络错误：${e.message}"
                    } finally {
                        loading = false
                    }
                }
            },
            enabled = !loading && username.isNotBlank() && password.isNotBlank(),
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 24.dp),
        ) {
            if (loading) {
                CircularProgressIndicator(modifier = Modifier.padding(end = 8.dp), strokeWidth = 2.dp)
            }
            Text(if (isRegister) "注册并登录" else "登录")
        }
        TextButton(
            onClick = {
                isRegister = !isRegister
                error = null
            },
            modifier = Modifier.padding(top = 8.dp),
        ) {
            Text(if (isRegister) "已有账号？去登录" else "没有账号？去注册")
        }
        TextButton(
            onClick = {
                showServerSettings = !showServerSettings
                serverUrl = serverConfig.apiBaseUrl
            },
        ) {
            Text("服务器设置")
        }
        if (showServerSettings) {
            OutlinedTextField(
                value = serverUrl,
                onValueChange = { serverUrl = it },
                label = { Text("API 地址") },
                singleLine = true,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 8.dp),
            )
            Button(
                onClick = {
                    onServerChanged(serverUrl)
                    showServerSettings = false
                    error = null
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 8.dp),
            ) {
                Text("保存并重试")
            }
        }
    }
}
