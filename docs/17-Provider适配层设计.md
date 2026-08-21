# 17 - Provider 适配层设计

> 状态：已实现（Mock + 真实 Provider 骨架）  
> 最近更新：2026-01-01  
> 所属文档库：[README](../README.md)

## 1. 目的

定义外部 API 的统一调用抽象，让核心流程不依赖任何具体厂商，支持多模型切换、重试、限流和错误码映射。

## 2. 设计原则

- 核心业务只依赖抽象接口，不直接 import 厂商 SDK。
- 每个厂商一个 Provider 实现。
- Provider 之间可通过配置切换。
- 所有 Provider 必须统一错误映射、超时、重试。

## 3. 统一接口

### 3.1 文生图

```python
class ImageProvider(Protocol):
    def generate_image(self, request: ImageGenerationRequest) -> ImageGenerationResult: ...
```

`ImageGenerationRequest`：

- `prompt: str`
- `reference_image_urls: list[str] | None`
- `aspect_ratio: str`
- `quality: str`

`ImageGenerationResult`：

- `image_url: str`
- `provider: str`
- `cost: Decimal`
- `raw_response: dict`

### 3.2 视频生成

```python
class VideoProvider(Protocol):
    def submit_video_task(self, request: VideoGenerationRequest) -> VideoTaskHandle: ...
    def query_video_task(self, handle: VideoTaskHandle) -> VideoTaskStatus: ...
```

`VideoGenerationRequest`：

- `prompt: str`
- `first_frame_url: str | None`
- `reference_image_urls: list[str] | None`
- `duration: int`
- `aspect_ratio: str`
- `resolution: str`
- `model: str | None`

`VideoTaskStatus`：

- `state: pending | processing | succeeded | failed`
- `video_url: str | None`
- `error_code: str | None`
- `error_message: str | None`

### 3.3 TTS

```python
class TTSProvider(Protocol):
    def synthesize(self, request: TTSRequest) -> TTSResult: ...
```

`TTSRequest`：

- `text: str`
- `voice_id: str`
- `speed: float`

`TTSResult`：

- `audio_url: str`
- `provider: str`
- `cost: Decimal`

### 3.4 LLM

```python
class LLMProvider(Protocol):
    def complete(self, request: LLMRequest) -> LLMResult: ...
```

`LLMRequest`：

- `system_prompt: str`
- `user_prompt: str`
- `temperature: float`
- `max_tokens: int`

`LLMResult`：

- `text: str`
- `provider: str`
- `cost: Decimal`

## 4. 错误码映射

每个 Provider 必须把厂商错误转换为内部错误码：

| 内部错误码 | 触发场景 |
| --- | --- |
| `API_TIMEOUT` | 请求超时 |
| `API_RATE_LIMITED` | 限流 / 429 |
| `API_SERVER_ERROR` | 5xx |
| `API_QUOTA_EXCEEDED` | 余额不足 / 配额耗尽 |
| `CONTENT_REJECTED` | 内容违规被拒 |
| `INVALID_PARAMETER` | 参数非法 |
| `AUTH_FAILED` | Key 无效 / 无权限 |

## 5. 重试与超时

- 每个 Provider 可配置独立超时。
- 可重试错误使用统一重试装饰器。
- 重试策略：指数退避 + 抖动。

```python
@retry(
    retry_on=(API_TIMEOUT, API_RATE_LIMITED, API_SERVER_ERROR),
    max_attempts=3,
    backoff=30,
)
def call_with_retry(func, *args, **kwargs):
    return func(*args, **kwargs)
```

## 6. 健康检查与自动切换

- 每个 Provider 提供 `health_check()`。
- 连续失败 N 次后标记为不健康。
- 调度 Agent 根据健康状态、成本、风格需求选择 Provider。
- Provider 配置示例：

```yaml
providers:
  video:
    primary: minimax
    fallback: [volcano, kling]
  image:
    primary: tongyi
    fallback: [flux, sd]
```

## 7. 目录结构建议

```text
app/providers/
├── base.py            # 抽象接口与公共类型
├── registry.py        # Provider 注册与选择
├── mock.py            # Mock 实现
├── siliconflow.py     # SiliconFlow（LLM / 文生图）
├── minimax.py         # MiniMax（视频生成）
├── tongyi.py          # 通义万相（文生图）
├── claude.py          # Claude（LLM）
└── errors.py          # 内部错误码
```

当前 SiliconFlow 已实现 LLM、文生图、视频生成与 TTS；视频/语音字段以官方文档为准。

## 8. 注意事项

- 真实调用前先写 Mock Provider，保证本地开发不依赖真实 Key。
- 所有 Provider 的返回必须记录 `generation_logs`。
- 日志中不得打印完整 API Key。
