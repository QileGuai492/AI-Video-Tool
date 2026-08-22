# AI 视频生成工具（个人创作者版）

> 一个低成本、高质量、可定制化的 AI 视频生成工作台。
> 通过多 Agent 协作和云端 API 组合，实现文生视频、图生视频、角色一致性、自动配音/配乐、视频拼接与后处理增强，最终输出可直接发布到抖音/B站/YouTube 的 1 分钟左右短视频。

## 项目约定（长期记忆）

- 开发者配置与 AI 协作约定已写入 [CLAUDE.md](CLAUDE.md)，包括语言规范、提交规范、安全提醒、开发日志要求等。
- 项目上下文入口见 [CONTEXT.md](CONTEXT.md)。
- 请 AI 辅助工具在开始开发前先阅读 `CLAUDE.md` 与 `CONTEXT.md`。

## 文档导航

本文档库按软件工程原则拆分，每份文档只负责一个关注点，避免重复维护。

| 文档 | 内容 | 主要读者 |
| --- | --- | --- |
| [docs/01-产品愿景.md](docs/01-产品愿景.md) | 产品愿景、目标用户、核心场景、目标与非目标 | 产品 / 开发者 |
| [docs/02-需求与用户故事.md](docs/02-需求与用户故事.md) | 功能需求列表（MoSCoW）、用户故事、需求追踪 | 产品 / 开发 / 测试 |
| [docs/03-迭代计划.md](docs/03-迭代计划.md) | Sprint 1~5 迭代计划、交付物 | 项目管理 / 开发 |
| [docs/04-技术架构.md](docs/04-技术架构.md) | 技术选型、系统架构、核心流程、Agent 划分 | 架构 / 开发 |
| [docs/05-数据模型.md](docs/05-数据模型.md) | 核心数据表、字段说明、关系 | 后端 / 数据库 |
| [docs/06-接口设计.md](docs/06-接口设计.md) | API 接口、示例、任务状态机 | 前后端 / 联调 |
| [docs/07-成本控制.md](docs/07-成本控制.md) | 成本估算与控制策略 | 产品 / 开发 |
| [docs/08-风险与依赖.md](docs/08-风险与依赖.md) | 风险矩阵、依赖与应对措施 | 全员 |
| [docs/09-验收标准与完成定义.md](docs/09-验收标准与完成定义.md) | Demo 验收标准、完成定义 | 测试 / 验收 |
| [docs/10-行动清单.md](docs/10-行动清单.md) | 立即开始行动清单、环境准备 | 开发 |
| [docs/11-非功能需求.md](docs/11-非功能需求.md) | 性能、可用性、安全、数据保留等质量属性 | 架构 / 开发 / 测试 |
| [docs/12-任务与错误处理.md](docs/12-任务与错误处理.md) | 任务生命周期、重试、幂等、超时、取消、错误码 | 后端 / 运维 |
| [docs/13-测试策略.md](docs/13-测试策略.md) | 测试分层、Mock 策略、覆盖率、CI | 测试 / 开发 |
| [docs/14-安全与密钥管理.md](docs/14-安全与密钥管理.md) | 密钥管理、认证、上传安全、OSS 安全 | 后端 / 运维 |
| [docs/15-本地开发与部署.md](docs/15-本地开发与部署.md) | 本地启动、Docker Compose、部署、备份 | 开发 / 运维 |
| [docs/16-外部服务与Key状态.md](docs/16-外部服务与Key状态.md) | 外部 API 申请进度、Key 状态、替代方案 | 开发 |
| [docs/17-Provider适配层设计.md](docs/17-Provider适配层设计.md) | 统一 Provider 接口、错误映射、重试切换 | 后端 |
| [docs/18-LangGraph状态图设计.md](docs/18-LangGraph状态图设计.md) | 调度 Agent 状态、节点、条件分支 | 后端 |
| [docs/19-角色一致性方案.md](docs/19-角色一致性方案.md) | 角色参考图处理、特征存储、跨会话一致 | 产品 / 开发 |
| [docs/20-前端交互设计.md](docs/20-前端交互设计.md) | 页面结构、用户流程、进度展示 | 前端 / 产品 |
| [docs/21-Prompt与模板管理.md](docs/21-Prompt与模板管理.md) | Prompt 模板、用户模板 Schema、版本管理 | 开发 |
| [docs/22-质量评估标准.md](docs/22-质量评估标准.md) | 质量维度、打分、阈值、重试策略 | 测试 / 开发 |
| [docs/23-用户故事验收标准.md](docs/23-用户故事验收标准.md) | 每条用户故事的可验证验收条件 | 测试 / 验收 |
| [docs/24-Git工作流与代码规范.md](docs/24-Git工作流与代码规范.md) | 分支策略、提交规范、代码规范 | 全员 |
| [docs/25-运维Runbook.md](docs/25-运维Runbook.md) | 服务启停、日志、备份恢复、故障排查 | 运维 / 开发 |
| [docs/26-存储与任务编排抽象.md](docs/26-存储与任务编排抽象.md) | 存储抽象、任务编排抽象、扩展点 | 后端 / 架构 |
| [docs/29-白模视频升级方案.md](docs/29-白模视频升级方案.md) | 白模视频技术升级详细方案 | 产品 / 开发 |
| [docs/30-前端优化方案.md](docs/30-前端优化方案.md) | React + Three.js 前端优化方案 | 前端 / 产品 |
| [logs/开发日志.md](logs/开发日志.md) | 常规开发日志、修复记录、验证结果 | 开发 / 项目管理 |
| [logs/交互日志.md](logs/交互日志.md) | 与 AI 协作解决问题的交互过程记录 | 开发 |

## 当前状态

- **阶段**：Sprint 1~4 核心能力已完成，Sprint 5 功能增强与生产部署加固进行中。
- **技术栈**：FastAPI + SQLAlchemy + Celery + Redis + LangGraph + Streamlit + SiliconFlow + Nginx。
- **已支持**：真实视频生成、TTS、批量生成、模板市场、质量评估、Harness 评测、CI。
- **下一步**：继续完善角色一致性、生产监控告警与正式前端。

## Docker 快速启动

```bash
cp .env.example .env
# 编辑 .env 填入真实配置

docker compose build
docker compose up -d

# 首次部署执行迁移
docker compose exec api alembic upgrade head
```

访问：

- Nginx 入口：http://localhost（反向代理 API / 前端 / 上传）
- 后端 API：http://localhost:8000
- Streamlit 前端：http://localhost:8501
- Flower 监控：http://localhost:5555
- 监控指标：http://localhost:8000/api/v1/metrics

## 评测

项目内置 Harness 评测 Agent，用于评测各 Agent 能力与完整系统：

```bash
# 默认：Mock 隔离模式，可复现、无外部费用
python -m eval_harness

# 加入真实 SiliconFlow 冒烟评测（LLM / 文生图 / TTS / 文生视频）
python -m eval_harness --real

# 加入 LLM-as-Judge 深度质量评测
python -m eval_harness --judge

# 自定义报告路径
python -m eval_harness --report logs/评测报告.md

# 评测结束后清理 .eval_tmp 临时目录
python -m eval_harness --clean
```

评测默认使用 Mock Provider + 本地 SQLite，保证可复现、不产生真实 API 费用。当前默认包含 58 个核心用例，加入 `--real --judge` 后共 63 个。报告输出到：

- `logs/评测报告.md`

## Allure 测试报告

项目已接入 Allure，CI 会自动生成并上传 HTML 报告。

本地生成：

```bash
# 安装依赖
pip install -e ".[dev]"

# 运行测试并收集 Allure 结果
pytest --alluredir=allure-results

# 生成 HTML 报告（需要已安装 Allure Commandline）
python scripts/generate_allure_report.py
```

产物：

- `allure-results/`：测试结果原始数据
- `allure-report/`：HTML 报告

## 文档维护约定

- 每份文档顶部保留 `状态` 和 `最近更新` 字段。
- 需求变更时，先更新 `docs/02-需求与用户故事.md`，再同步影响到的 `docs/03-迭代计划.md`、`docs/06-接口设计.md`。
- 架构决策变更时，在 `docs/04-技术架构.md` 中记录，并建议沉淀到 `docs/adr/`。
- 所有文档、代码注释、提交信息统一使用中文；代码标识符保持英文命名。
