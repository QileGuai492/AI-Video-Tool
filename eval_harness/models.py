"""评测数据模型。"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol


class EvalContext(Protocol):
    """评测运行上下文。"""

    def db_session(self):
        """创建一个数据库会话。"""
        ...

    @property
    def client(self):
        """返回 FastAPI TestClient。"""
        ...


@dataclass
class EvalOutcome:
    """单个评测用例的结果。"""

    status: str  # pass / fail / error / skipped
    score: float = 0.0
    metrics: dict[str, float] = field(default_factory=dict)
    details: str = ""
    trace: list[str] = field(default_factory=list)


@dataclass
class EvalCase:
    """评测用例定义。"""

    id: str
    name: str
    category: str  # agent / system
    target: str  # 被评测对象，如 prompt_agent / api
    description: str
    fn: Callable[["EvalContext"], EvalOutcome]
    weight: float = 1.0
    required: bool = True
    latency_budget_ms: float | None = None
    cost_budget: float | None = None


@dataclass
class EvalResult:
    """用例执行结果（含耗时）。"""

    case: EvalCase
    outcome: EvalOutcome
    duration_ms: float


@dataclass
class EvalSummary:
    """评测汇总。"""

    total: int = 0
    passed: int = 0
    failed: int = 0
    errored: int = 0
    skipped: int = 0
    pass_rate: float = 0.0
    avg_score: float = 0.0
    total_duration_ms: float = 0.0
    by_category: dict[str, dict[str, float]] = field(default_factory=dict)
    by_target: dict[str, dict[str, float]] = field(default_factory=dict)

    @property
    def completed(self) -> int:
        """已完成（非 skipped）的用例数。"""
        return self.passed + self.failed + self.errored
