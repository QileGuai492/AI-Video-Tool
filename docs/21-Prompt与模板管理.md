# 21 - Prompt 与模板管理

> 状态：待评审  
> 最近更新：2026-01-01  
> 所属文档库：[README](../README.md)

## 1. 目标

统一管理提示词模板和用户模板，保证：

- 提示词可复用、可版本化。
- 用户模板结构清晰，可安全序列化。
- 后续可做模板推荐和数据分析。

## 2. Prompt 模板

### 2.1 系统提示词模板

用于 PromptAgent 优化用户输入，建议放在独立配置或数据库中。

示例：

```text
你是一个短视频导演。请把用户的创意扩写为适合 AI 视频生成的详细提示词。
要求：
- 包含场景、主体、动作、镜头、光线、风格、氛围。
- 输出 JSON 格式：
  {
    "optimized_prompt": "...",
    "style": "...",
    "negative_prompt": "...",
    "suggested_duration": 5,
    "suggested_aspect_ratio": "16:9"
  }
```

### 2.2 变量占位

推荐使用 `{variable}` 占位：

```text
在{scene}中，{subject}正在{action}，光线{lighting}，风格{style}。
```

### 2.3 版本管理

- 模板表增加 `version` 字段。
- 修改模板时创建新版本，不覆盖旧版本。
- 任务保存使用的模板版本快照，便于复现。

## 3. 用户模板（templates）

### 3.1 `config_json` 结构

建议 JSON Schema：

```json
{
  "name": "雨天猫咪",
  "config": {
    "prompt": "一只猫在雨天奔跑",
    "duration": 60,
    "aspect_ratio": "16:9",
    "quality": "standard",
    "model": "minimax",
    "character_id": null,
    "tts": {
      "enabled": true,
      "voice_id": "female_01"
    },
    "bgm": {
      "enabled": true,
      "source": "auto"
    },
    "subtitle": {
      "enabled": true
    }
  }
}
```

### 3.2 校验规则

- `duration` 必须是 5~120 秒。
- `aspect_ratio` 必须是 `16:9` / `9:16` / `1:1`。
- `quality` 必须是 `fast` / `standard` / `high`。
- `character_id` 必须属于当前用户。

## 4. 默认模板

建议内置几个默认模板：

| 模板 | 适用场景 |
| --- | --- |
| 通用口播 | 9:16，TTS + 字幕 |
| 猫咪 / 动物 | 1:1，BGM 轻快 |
| 风景大片 | 16:9，高质量 |
| 产品展示 | 1:1，TTS + BGM |

## 5. 数据表建议

`templates` 表补充：

- `version`
- `is_builtin`
- `updated_at`

可选新增：

- `prompt_templates`：系统提示词模板库。
