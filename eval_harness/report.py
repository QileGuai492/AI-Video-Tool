"""评测报告生成器。"""

from collections.abc import Iterable
from datetime import datetime

from eval_harness.models import EvalResult, EvalSummary

PRINCIPLES = """本评测遵循 Agent Harness 评测的核心原则：

1. **可复现性（Reproducibility）**：固定使用 Mock Provider、本地 SQLite 与本地存储，任何机器重复运行应得到一致结论。
2. **隔离性（Isolation）**：每个用例独立注册用户/创建任务，不依赖外部 API 与共享状态。
3. **指标驱动（Metrics-driven）**：除通过/失败外，记录耗时、成本、输出长度、状态码等量化指标。
4. **可追踪性（Traceability）**：每个用例记录检查项、输入输出摘要与执行轨迹，失败可定位到具体环节。
5. **任务特定（Task-specific）**：按 Agent 职责拆分用例，而不是只做端到端黑盒测试。
6. **可回归（Regression-ready）**：评测命令可重复执行，后续接入 CI 后可作为回归门禁。
7. **人工可读报告（Human-readable report）**：最终输出 Markdown 报告，方便评审与改进。"""


def _status_icon(status: str) -> str:
    return {"pass": "✅", "fail": "❌", "error": "💥", "skipped": "⏭️"}.get(status, "❓")


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _stats_table(title: str, stats: dict[str, dict[str, float]]) -> str:
    lines = [
        f"### {title}",
        "",
        "| 对象 | 总数 | 通过 | 失败 | 异常 | 跳过 | 通过率 | 平均分 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, item in stats.items():
        lines.append(
            f"| {name} | {item['total']:.0f} | {item['passed']:.0f} | {item['failed']:.0f} "
            f"| {item['errored']:.0f} | {item['skipped']:.0f} | {_pct(item['pass_rate'])} | {item['avg_score']:.2f} |"
        )
    return "\n".join(lines)


def generate_markdown(
    results: Iterable[EvalResult],
    summary: EvalSummary,
    mode: str = "Mock 隔离模式",
) -> str:
    """生成 Markdown 格式评测报告。"""
    results = list(results)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "# 项目评测报告",
        "",
        f"> 生成时间：{now}",
        f"> 评测模式：{mode}",
        "> 评测范围：Agent 能力 + 完整系统 E2E",
        "",
        "## 一、评测原则",
        "",
        PRINCIPLES,
        "",
        "### 参考来源",
        "",
        "- [Agent Eval Harness: How to Evaluate AI Agents, Not Just Models](https://futureagi.com/blog/agent-eval-harness/)",
        "- [reaatech/agent-eval-harness](https://github.com/reaatech/agent-eval-harness)",
        "- [如何评价一个 Agent Harness：效率、稳定性和可控性](https://developer.aliyun.com/article/1740732)",
        "- [Agent Harness 评测：如何测试生产级 AI Agent](https://qubittool.com/zh/blog/agent-harness-evaluation-guide)",
        "- [EleutherAI LM Evaluation Harness](https://github.com/sam-paech/lm-evaluation-harness)",
        "",
        "## 二、执行摘要",
        "",
        "| 指标 | 数值 |",
        "| --- | ---: |",
        f"| 用例总数 | {summary.total} |",
        f"| 通过 | {summary.passed} |",
        f"| 失败 | {summary.failed} |",
        f"| 异常 | {summary.errored} |",
        f"| 跳过 | {summary.skipped} |",
        f"| 通过率 | {_pct(summary.pass_rate)} |",
        f"| 平均得分 | {summary.avg_score:.2f} / 1.00 |",
        f"| 总耗时 | {summary.total_duration_ms:.0f} ms |",
        "",
        _stats_table("按分类统计", summary.by_category),
        "",
        _stats_table("按评测对象统计", summary.by_target),
        "",
        "## 三、用例明细",
        "",
        "| ID | 分类 | 对象 | 用例 | 结果 | 得分 | 耗时(ms) | 说明 |",
        "| --- | --- | --- | --- | --- | ---: | ---: | --- |",
    ]

    for result in results:
        case = result.case
        lines.append(
            f"| {case.id} | {case.category} | {case.target} | {case.name} "
            f"| {_status_icon(result.outcome.status)} {result.outcome.status} "
            f"| {result.outcome.score:.2f} | {result.duration_ms:.0f} "
            f"| {result.outcome.details.replace('|', '/')[:80]} |"
        )

    lines.extend(["", "## 四、失败与异常详情", ""])
    failures = [r for r in results if r.outcome.status in {"fail", "error"}]
    if not failures:
        lines.append("无失败用例。")
    else:
        for result in failures:
            lines.extend(
                [
                    f"### {result.case.id} - {result.case.name}",
                    "",
                    f"- 状态：{result.outcome.status}",
                    f"- 得分：{result.outcome.score:.2f}",
                    f"- 说明：{result.outcome.details}",
                ]
            )
            if result.outcome.trace:
                lines.append("- 轨迹：")
                lines.extend(f"  - {item}" for item in result.outcome.trace)
            lines.append("")

    lines.extend(
        [
            "## 五、结论与建议",
            "",
            f"当前在 {mode} 下共执行 {summary.total} 个用例，通过率 {_pct(summary.pass_rate)}，"
            f"平均得分 {summary.avg_score:.2f}。",
            "",
            "建议：",
            "1. 将本评测命令接入 CI，作为每次提交的回归门禁。",
            "2. 对失败/异常用例优先修复，再补充对应的单元测试。",
            "3. 在真实 API Key 可用时，增加 `--real` 冒烟评测，但不要纳入默认回归门禁。",
            "4. 后续可扩展 LLM-as-Judge、轨迹相似度、成本预算等更细粒度指标。",
        ]
    )

    return "\n".join(lines)
