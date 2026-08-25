package com.aivideotool.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.aivideotool.app.data.ApiClient
import com.aivideotool.app.data.TaskDto
import com.aivideotool.app.data.TokenManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.HttpException

@Composable
fun TaskListScreen(
    apiClient: ApiClient,
    tokenManager: TokenManager,
    onLogout: () -> Unit,
) {
    var tasks by remember { mutableStateOf<List<TaskDto>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(Unit) {
        loading = true
        error = null
        try {
            tasks = withContext(Dispatchers.IO) { apiClient.taskApi.listTasks() }
        } catch (e: HttpException) {
            error = if (e.code() == 401) "登录已失效，请重新登录" else "加载失败：${e.code()}"
        } catch (e: Exception) {
            error = "网络错误：${e.message}"
        } finally {
            loading = false
        }
    }

    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("任务中心", style = MaterialTheme.typography.headlineSmall)
            Button(onClick = onLogout) {
                Text("退出登录")
            }
        }

        when {
            loading -> {
                CircularProgressIndicator(modifier = Modifier.padding(top = 32.dp))
            }
            error != null -> {
                Text(
                    text = error ?: "",
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.padding(top = 32.dp),
                )
            }
            tasks.isEmpty() -> {
                Text(
                    text = "暂无任务",
                    modifier = Modifier.padding(top = 32.dp),
                )
            }
            else -> {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(tasks, key = { it.uid }) { task ->
                        TaskCard(task)
                    }
                }
            }
        }
    }
}

@Composable
private fun TaskCard(task: TaskDto) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(
                text = task.prompt,
                style = MaterialTheme.typography.bodyLarge,
                maxLines = 2,
            )
            Text(
                text = "状态：${task.status}",
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.padding(top = 4.dp),
            )
            Text(
                text = "UID：${task.uid}",
                style = MaterialTheme.typography.bodySmall,
            )
        }
    }
}
