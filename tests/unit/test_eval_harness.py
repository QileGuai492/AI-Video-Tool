"""评测框架单元测试。"""

from eval_harness.models import EvalCase, EvalContext, EvalOutcome
from eval_harness.report import generate_markdown
from eval_harness.runner import run_cases


class FakeContext:
    """最小评测上下文。"""

    @property
    def client(self):
        return None

    def db_session(self):
        return None


def _pass_case() -> EvalCase:
    return EvalCase(
        id="test.pass",
        name="通过用例",
        category="agent",
        target="test_agent",
        description="应通过",
        fn=lambda ctx: EvalOutcome(status="pass", score=1.0, details="ok"),
    )


def _fail_case() -> EvalCase:
    return EvalCase(
        id="test.fail",
        name="失败用例",
        category="system",
        target="test_api",
        description="应失败",
        fn=lambda ctx: EvalOutcome(status="fail", score=0.0, details="bad"),
    )


def _error_case() -> EvalCase:
    def run(ctx: EvalContext) -> EvalOutcome:
        raise RuntimeError("boom")

    return EvalCase(
        id="test.error",
        name="异常用例",
        category="system",
        target="test_api",
        description="应异常",
        fn=run,
    )


def test_runner_summarize_counts_status() -> None:
    """运行器应正确统计通过/失败/异常。"""
    ctx = FakeContext()
    results, summary = run_cases([_pass_case(), _fail_case(), _error_case()], ctx)

    assert summary.total == 3
    assert summary.passed == 1
    assert summary.failed == 1
    assert summary.errored == 1
    assert summary.pass_rate == 1 / 3
    assert 0.0 <= summary.avg_score <= 1.0
    assert len(results) == 3


def test_summarize_by_category_and_target() -> None:
    """汇总应按分类与目标聚合。"""
    ctx = FakeContext()
    results, summary = run_cases([_pass_case(), _fail_case(), _error_case()], ctx)

    assert "agent" in summary.by_category
    assert "system" in summary.by_category
    assert "test_agent" in summary.by_target
    assert "test_api" in summary.by_target


def test_latency_budget_turns_pass_into_fail() -> None:
    """超出延迟预算的用例应被判为失败。"""
    case = EvalCase(
        id="test.budget",
        name="预算用例",
        category="agent",
        target="test_agent",
        description="应超时",
        latency_budget_ms=100,
        fn=lambda ctx: EvalOutcome(status="pass", score=1.0, metrics={"耗时_ms": 200}, details="慢"),
    )
    ctx = FakeContext()
    result, _ = run_cases([case], ctx)
    assert result[0].outcome.status == "fail"
    assert "超预算" in result[0].outcome.details


def test_generate_markdown_contains_summary_and_details() -> None:
    """报告应包含摘要、明细与失败详情。"""
    ctx = FakeContext()
    results, summary = run_cases([_pass_case(), _fail_case()], ctx)
    markdown = generate_markdown(results, summary)

    assert "# 项目评测报告" in markdown
    assert "test.pass" in markdown
    assert "test.fail" in markdown
    assert "失败与异常详情" in markdown
    assert "通过率" in markdown
