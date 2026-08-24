# Harness 评测方案

> 状态：已具备轨迹录制/黄金轨迹/工具调用正确性/预算/趋势，LLM-as-Judge 仍为可选
> 最近更新：2026-08-24

## 1. 什么是 Harness 评测

**Harness 评测（Evaluation Harness）** 是 LLM / AI Agent 领域的一套评测框架，目标是在可控环境中**衡量 Agent / LLM 的能力、质量、成本、稳定性**，而不是像普通测试那样只判断“代码是否按预期返回”。

它重点关注：

| 维度 | 说明 |
| --- | --- |
| 任务成功率 | Agent 是否真正完成了用户任务 |
| 轨迹质量（Trajectory） | 推理、工具调用顺序、中间步骤是否合理 |
| 工具调用正确性 | 调用了哪些工具、参数是否正确、是否绕弯路 |
| 成本 | 完成任务消耗的 token / API 费用 |
| 延迟 | 端到端耗时、单步耗时 |
| 稳定性 | 同一输入多次运行结果是否一致 |
| LLM-as-Judge | 用大模型对输出质量打分 |
| 黄金轨迹 | 与人工标注的理想轨迹做对比 |
| 预算门禁 | 超过成本 / 延迟上限判失败 |
| 趋势回归 | 多次运行之间质量、成本、耗时是否恶化 |

参考来源：

- [reaatech/agent-eval-harness](https://github.com/reaatech/agent-eval-harness)
- [Agent Eval Harness: How to Evaluate AI Agents, Not Just Models](https://futureagi.com/blog/agent-eval-harness/)
- [AgentGuide: evaluation-harness](https://github.com/adongwanai/AgentGuide/blob/main/resources/agent/evaluation-harness.md)
- [Harness AI Evals](https://www.harness.io/products/ai-evals)

## 2. Harness 评测和普通测试的区别

| 维度 | 普通测试（Test） | Harness 评测（Evaluation Harness） |
| --- | --- | --- |
| 目标 | 验证代码行为符合预期 | 衡量 Agent/LLM 能力、质量、成本、稳定性 |
| 结果 | pass / fail 断言 | 分数、指标、轨迹、趋势、基线对比 |
| 输入 | 固定输入 + 期望输出 | 任务、场景、黄金轨迹、评分规则 |
| 重点 | 边界、异常、回归 | 任务完成率、轨迹合理性、工具调用、成本、延迟 |
| 例子 | pytest、Vitest、接口测试 | ReAct Agent 轨迹回放、LLM-as-Judge、成本预算评测 |

**本项目中的对应关系：**

- `pytest` / `tests/`：普通单元 + 集成测试，验证函数/接口行为。
- `eval_harness/`：Harness 评测，衡量编排 Agent 的完整任务质量。

## 3. 当前实现（改造中）

现有 `eval_harness/` 已具备：

- Mock 隔离环境（本地 SQLite + Mock Provider）
- 用例定义 / 运行器 / 汇总 / Markdown 报告
- 基础延迟与成本预算字段（`latency_budget_ms` / `cost_budget`）
- 简单 LLM-as-Judge（`--judge` 时启用）

计划补充：

- [x] 任务接口 UID 适配
- [x] 新功能用例（角色映射、台词、删除、密码强度等）
- [x] 轨迹录制（Trajectory Recorder）
- [x] 黄金轨迹对比（Golden Trajectory）
- [x] 工具调用正确性检查（Tool-Use Correctness）
- [x] 成本 / 延迟预算门禁用例
- [x] 趋势报告（历史对比）
- [x] LLM-as-Judge 常态化（默认纳入，无真实 Key 时自动跳过）

## 4. 目录结构

```text
eval_harness/
├── __main__.py        # 入口：默认 / --real / --judge / --trend
├── models.py          # EvalCase / EvalOutcome / EvalResult / EvalSummary
├── runner.py          # 执行、预算门禁、汇总
├── context.py         # 隔离环境与运行上下文
├── trajectory.py      # 轨迹录制、黄金轨迹、工具调用正确性（新增）
├── report.py          # Markdown 报告
├── judge.py           # LLM-as-Judge
├── cases_agent.py     # Agent 能力用例
├── cases_system.py    # 系统级 E2E 用例
├── cases_deep.py      # 深度 / LLM-as-Judge 用例
└── cases_real.py      # 真实 API 冒烟用例
```

## 5. 核心数据结构

```python
@dataclass
class TrajectoryStep:
    agent: str          # 哪个 Agent / 模块
    action: str         # 动作名，如 llm_complete / image_generate / video_submit
    params: dict        # 关键入参摘要
    result: str         # 结果摘要
    ok: bool
    cost: float = 0.0
    latency_ms: float = 0.0

@dataclass
class Trajectory:
    task_id: str
    steps: list[TrajectoryStep]
```

评测时通过 `ctx.record_trajectory(...)` 记录步骤，报告输出轨迹明细。

## 6. 评测命令

```bash
# 默认 Mock 隔离评测
python -m eval_harness

# 包含真实 API 冒烟
python -m eval_harness --real

# 包含 LLM-as-Judge
python -m eval_harness --judge

# 输出趋势对比（自动保存历史 JSON）
python -m eval_harness --trend
```

## 7. 验收标准

- [ ] 每个 Agent 关键动作都有轨迹记录
- [ ] 至少一个黄金轨迹对比用例
- [ ] 至少一个工具调用正确性用例
- [ ] 报告包含轨迹明细与趋势摘要
- [ ] 默认 Mock 模式可重复运行且不依赖外部 API
