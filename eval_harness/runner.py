"""评测运行器。"""

import time

from eval_harness.models import EvalCase, EvalContext, EvalOutcome, EvalResult, EvalSummary


def _apply_budgets(case: EvalCase, outcome: EvalOutcome) -> EvalOutcome:
    """按用例预设的延迟/成本预算做门禁判定。"""
    if outcome.status != "pass":
        return outcome

    metrics = outcome.metrics
    latency = metrics.get("耗时_ms", metrics.get("latency_ms", 0.0))
    if case.latency_budget_ms is not None and latency > case.latency_budget_ms:
        outcome.status = "fail"
        outcome.details += f"；耗时超预算 {latency:.0f}ms > {case.latency_budget_ms:.0f}ms"

    cost = metrics.get("成本", metrics.get("cost", 0.0))
    if case.cost_budget is not None and cost > case.cost_budget:
        outcome.status = "fail"
        outcome.details += f"；成本超预算 {cost:.4f} > {case.cost_budget:.4f}"

    return outcome


def run_case(case: EvalCase, ctx: EvalContext) -> EvalResult:
    """执行单个评测用例并记录耗时。"""
    start = time.perf_counter()
    try:
        outcome = _apply_budgets(case, case.fn(ctx))
    except Exception as exc:  # noqa: BLE001
        outcome = EvalOutcome(
            status="error",
            score=0.0,
            details=f"执行异常：{exc}",
            trace=[f"{type(exc).__name__}: {exc}"],
        )
    duration_ms = (time.perf_counter() - start) * 1000
    return EvalResult(case=case, outcome=outcome, duration_ms=duration_ms)


def _category_stats(results: list[EvalResult], key: str) -> dict[str, dict[str, float]]:
    """按分类或目标聚合统计。"""
    groups: dict[str, list[EvalResult]] = {}
    for result in results:
        group = getattr(result.case, key)
        groups.setdefault(group, []).append(result)

    stats: dict[str, dict[str, float]] = {}
    for name, items in groups.items():
        passed = sum(1 for item in items if item.outcome.status == "pass")
        failed = sum(1 for item in items if item.outcome.status == "fail")
        errored = sum(1 for item in items if item.outcome.status == "error")
        skipped = sum(1 for item in items if item.outcome.status == "skipped")
        completed = passed + failed + errored
        score_values = [item.outcome.score for item in items if item.outcome.status != "skipped"]
        avg_score = sum(score_values) / len(score_values) if score_values else 0.0
        stats[name] = {
            "total": float(len(items)),
            "passed": float(passed),
            "failed": float(failed),
            "errored": float(errored),
            "skipped": float(skipped),
            "pass_rate": (passed / completed) if completed else 0.0,
            "avg_score": avg_score,
        }
    return stats


def summarize(results: list[EvalResult]) -> EvalSummary:
    """汇总评测结果。"""
    total = len(results)
    passed = sum(1 for r in results if r.outcome.status == "pass")
    failed = sum(1 for r in results if r.outcome.status == "fail")
    errored = sum(1 for r in results if r.outcome.status == "error")
    skipped = sum(1 for r in results if r.outcome.status == "skipped")
    completed = passed + failed + errored
    score_values = [r.outcome.score for r in results if r.outcome.status != "skipped"]
    avg_score = sum(score_values) / len(score_values) if score_values else 0.0
    total_duration = sum(r.duration_ms for r in results)

    return EvalSummary(
        total=total,
        passed=passed,
        failed=failed,
        errored=errored,
        skipped=skipped,
        pass_rate=(passed / completed) if completed else 0.0,
        avg_score=avg_score,
        total_duration_ms=total_duration,
        by_category=_category_stats(results, "category"),
        by_target=_category_stats(results, "target"),
    )


def run_cases(cases: list[EvalCase], ctx: EvalContext) -> tuple[list[EvalResult], EvalSummary]:
    """运行全部用例并返回结果与汇总。"""
    results = [run_case(case, ctx) for case in cases]
    return results, summarize(results)
