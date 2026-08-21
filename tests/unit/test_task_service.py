"""任务服务纯函数单元测试。"""

from app.services.task_service import calculate_segment_count, estimate_cost


def test_calculate_segment_count() -> None:
    """分段数量按 5 秒向上取整。"""
    assert calculate_segment_count(5) == 1
    assert calculate_segment_count(60) == 12
    assert calculate_segment_count(1) == 1


def test_estimate_cost_quality() -> None:
    """不同质量档位成本不同。"""
    fast_cost = estimate_cost(60, quality="fast")
    standard_cost = estimate_cost(60, quality="standard")
    high_cost = estimate_cost(60, quality="high")
    assert fast_cost < standard_cost < high_cost
