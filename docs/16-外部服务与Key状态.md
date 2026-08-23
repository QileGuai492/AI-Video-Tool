# 16 - 外部服务与 Key 状态

> 状态：已更新  
> 最近更新：2026-08-23  
> 所属文档库：[README](../README.md)

## 1. 用途

记录所有外部服务的申请进度、Key 状态、额度和替代方案，避免开发到一半才发现某个 API 不可用。

## 2. 服务状态总表

| 服务 | 用途 | 申请状态 | Key 状态 | 免费额度 | 预估成本 | 替代方案 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MiniMax 海螺 | 视频生成 / TTS | 未申请 | 未配置 | 待确认 | 见成本文档 | 火山、可灵 | 优先申请 |
| 通义万相 | 文生图 | 未申请 | 未配置 | 待确认 | ¥0.1~0.5/张 | Flux、SD | 阿里云账号 |
| Claude API | 提示词优化 / 台词 | 未申请 | 未配置 | 待确认 | 按 token | GPT-4o-mini、Qwen、SiliconFlow | 需要海外支付方式 |
| SiliconFlow（硅基流动） | 大模型 / 文生图 / 视频生成 / TTS | 已配置 | 已配置 | 待确认 | 按量 | Agnes、Claude、通义万相、MiniMax | OpenAI 兼容，已接入 LLM/文生图/视频/TTS；TTS 当前 402，已由 Edge TTS 替代 |
| Agnes AI | 大模型 / 文生图 / 视频生成 | 已注册 | 已配置 | 声称免费 | 免费 | SiliconFlow、MiniMax | 已接入 Provider，白模端到端验证通过 |
| Edge TTS（Microsoft） | TTS 语音合成 | 无需申请 | 无需 Key | 免费 | 免费 | SiliconFlow、MiniMax | 基于 edge-tts，已接入默认真实 TTS Provider |
| 阿里云 OSS | 文件存储 | 未申请 | 未配置 | 有免费额度 | 按量 | 本地磁盘、其他对象存储 | 已有服务器可顺便开通 |
| 阿里云 PostgreSQL | 数据库 | 未申请 | 未配置 | 无 | 按量 | 本地 Docker PostgreSQL | 也可先用 SQLite |
| Redis | 队列 / 缓存 | 无需申请 | 本地 Docker | 免费 | 免费 | 无 | 本地开发即可 |
| Whisper | 语音识别 | 开源免费 | 无需 Key | 免费 | 免费 | 直接用 TTS 文本生成字幕 | 本地或云端部署 |
| FFmpeg / MoviePy | 后处理 | 开源免费 | 无需 Key | 免费 | 免费 | 云端转码服务 | 本地安装 |

## 3. 填写说明

- **申请状态**：未申请 / 申请中 / 已通过 / 被拒绝。
- **Key 状态**：未配置 / 已配置 / 已轮换 / 已失效。
- **免费额度**：填写每月免费次数 / 金额。
- **备注**：记录联系人、控制台链接、申请注意事项。

## 4. 环境变量清单

所有 Key 统一放入 `.env`，不提交 Git：

```dotenv
MINIMAX_API_KEY=
TONGYI_API_KEY=
CLAUDE_API_KEY=
AGNES_API_KEY=
OSS_ACCESS_KEY_ID=
OSS_ACCESS_KEY_SECRET=
OSS_BUCKET=
OSS_ENDPOINT=
```

## 5. 申请优先级

1. **MiniMax**：Sprint 1 视频生成依赖，优先申请。
2. **通义万相**：Sprint 1 文生图依赖。
3. **Claude API**：提示词优化依赖。
4. **阿里云 OSS**：Sprint 1 文件保存依赖。
5. **可灵 / 火山**：Sprint 2+ 多模型备用。

## 6. 风险提示

- 如果 MiniMax 个人申请被拒，Sprint 1 可先用通义万相 + 可灵/火山或开源模型替代。
- 如果 Claude API 申请困难，可用 GPT-4o-mini 或国内大模型 API 替代。
- 所有 Key 建议使用子账号 / 最小权限，避免泄露后造成大额损失。
