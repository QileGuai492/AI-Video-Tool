# 18 - LangGraph 状态图设计

> 状态：已实现骨架（可通过 `ORCHESTRATOR_BACKEND=langgraph` 启用）  
> 最近更新：2026-01-01  
> 所属文档库：[README](../README.md)

## 1. 目的

定义调度 Agent 的 State、节点、边和条件分支，作为 Sprint 4 重构和后续开发的实现蓝图。

## 2. State 数据结构

```python
@dataclass
class GenerationState:
    # 用户输入
    user_id: str
    task_id: str
    prompt: str
    image_url: str | None = None
    character_id: str | None = None
    duration: int = 60
    aspect_ratio: str = "16:9"
    quality: str = "standard"
    model: str | None = None

    # 中间结果
    optimized_prompt: str | None = None
    first_frame_url: str | None = None
    segment_urls: list[str] = field(default_factory=list)
    audio_url: str | None = None
    subtitle_url: str | None = None
    final_video_url: str | None = None

    # 质量与成本
    quality_score: float | None = None
    total_cost: Decimal = Decimal("0")
    retry_count: int = 0

    # 控制
    current_stage: str = "pending"
    error_code: str | None = None
    error_message: str | None = None
```

## 3. 节点

| 节点 | 输入 | 输出 | 说明 |
| --- | --- | --- | --- |
| `prompt_agent` | `prompt` | `optimized_prompt` | 调用 LLM 优化提示词 |
| `image_agent` | `optimized_prompt`, `character_id` | `first_frame_url` | 生成首帧 |
| `video_gen_agent` | `optimized_prompt`, `first_frame_url` | `segment_urls` | 生成多个片段 |
| `audio_agent` | `optimized_prompt`, `segment_urls` | `audio_url` | TTS + BGM |
| `subtitle_agent` | `audio_url`, `optimized_prompt` | `subtitle_url` | 生成字幕 |
| `post_process_agent` | `segment_urls`, `audio_url`, `subtitle_url` | `final_video_url` | 拼接、叠加字幕 |
| `quality_check_agent` | `final_video_url` | `quality_score` | 质量打分 |
| `cost_agent` | 全状态 | `total_cost` | 汇总成本 |

## 4. 图结构

```text
START
  ↓
prompt_agent
  ↓
image_agent
  ↓
video_gen_agent
  ↓
audio_agent
  ↓
subtitle_agent
  ↓
post_process_agent
  ↓
quality_check_agent
  ├── score >= threshold ──→ cost_agent ──→ END
  └── score < threshold ──→ retry / fallback
                              ├── retry_count < max ──→ video_gen_agent（或 post_process_agent）
                              └── retry_count >= max ──→ failed ──→ END
```

## 5. 条件分支

### 5.1 质量回退

```python
def should_retry(state: GenerationState) -> str:
    if state.quality_score is None:
        return "quality_check"
    if state.quality_score >= QUALITY_THRESHOLD:
        return "cost"
    if state.retry_count < MAX_RETRY:
        return "retry"
    return "failed"
```

### 5.2 异常分支

- 任意节点抛出可重试错误 → 进入 `retry`。
- 不可重试错误 → 直接 `failed`。
- 用户取消 → `cancelled`。

## 6. 节点失败处理

- 每个节点包一层统一错误捕获：

```python
def run_node(state: GenerationState, node_func):
    try:
        return node_func(state)
    except RetryableError as exc:
        state.retry_count += 1
        state.error_code = exc.code
        return state
    except FatalError as exc:
        state.error_code = exc.code
        return state
```

## 7. 并行化（后续优化）

- `video_gen_agent` 内部可并行生成多个片段。
- `audio_agent` 和 `subtitle_agent` 可在片段生成后并行。
- 并行时注意：每个片段单独记录 `video_segments`，统一汇总成本。

## 8. 与任务状态机的映射

| LangGraph 节点 | 任务状态 |
| --- | --- |
| prompt_agent | `optimizing_prompt` |
| image_agent | `generating_first_frame` |
| video_gen_agent | `generating_video` |
| audio_agent | `generating_audio` |
| subtitle_agent | `generating_subtitle` |
| post_process_agent | `post_processing` |
| quality_check_agent | `quality_check` |
| cost_agent | `completed` |
