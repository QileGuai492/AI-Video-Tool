"""轨迹录制、黄金轨迹对比与工具调用正确性。

这是 Evaluation Harness 区别于普通测试的核心能力：
- 轨迹（Trajectory）：记录 Agent 完成任务时的每一步动作、参数、结果、成本与耗时。
- 黄金轨迹（Golden Trajectory）：与人工标注的理想动作序列做相似度对比。
- 工具调用正确性（Tool-Use Correctness）：校验关键动作是否按预期调用且参数正确。
"""

import difflib
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TrajectoryStep:
    """轨迹中的单步记录。"""

    agent: str
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    result: str = ""
    ok: bool = True
    cost: float = 0.0
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "action": self.action,
            "params": self.params,
            "result": self.result,
            "ok": self.ok,
            "cost": self.cost,
            "latency_ms": self.latency_ms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrajectoryStep":
        return cls(
            agent=str(data.get("agent", "")),
            action=str(data.get("action", "")),
            params=data.get("params") or {},
            result=str(data.get("result", "")),
            ok=bool(data.get("ok", True)),
            cost=float(data.get("cost", 0.0)),
            latency_ms=float(data.get("latency_ms", 0.0)),
        )


@dataclass
class Trajectory:
    """一次任务完整轨迹。"""

    task_id: str
    steps: list[TrajectoryStep] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "steps": [step.to_dict() for step in self.steps],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Trajectory":
        return cls(
            task_id=str(data.get("task_id", "")),
            steps=[TrajectoryStep.from_dict(item) for item in data.get("steps", [])],
        )

    def signature(self) -> list[str]:
        """动作签名序列，用于黄金轨迹对比。"""
        return [f"{step.agent}:{step.action}" for step in self.steps]


def trajectory_similarity(actual: Trajectory, golden: Trajectory) -> float:
    """计算实际轨迹与黄金轨迹的动作序列相似度（0~1）。"""
    if not golden.signature():
        return 0.0
    return difflib.SequenceMatcher(None, actual.signature(), golden.signature()).ratio()


def validate_tool_use(
    trajectory: Trajectory,
    expected_calls: list[dict[str, Any]],
) -> tuple[bool, float, list[str]]:
    """校验轨迹是否包含预期工具调用且参数正确。

    expected_calls 示例：
    [
        {"agent": "llm", "action": "complete", "params_contains": {"system_prompt": "短视频导演"}},
        {"agent": "video", "action": "submit_video_task", "params_contains": {"duration": 5}},
    ]
    """
    issues: list[str] = []
    matched = 0
    for expected in expected_calls:
        agent = expected.get("agent")
        action = expected.get("action")
        params_contains = expected.get("params_contains") or {}
        found = False
        for step in trajectory.steps:
            if step.agent != agent or step.action != action:
                continue
            params_ok = all(
                step.params.get(key) == value for key, value in params_contains.items()
            )
            if params_ok:
                found = True
                break
        if found:
            matched += 1
        else:
            issues.append(f"缺少预期调用 {agent}.{action} 或参数不匹配: {params_contains}")

    if not expected_calls:
        score = 1.0
    else:
        score = matched / len(expected_calls)
    return (score == 1.0, score, issues)


def format_trajectory(trajectory: Trajectory) -> list[str]:
    """把轨迹格式化为人类可读的行列表。"""
    lines = [f"任务 {trajectory.task_id} 轨迹："]
    for index, step in enumerate(trajectory.steps, start=1):
        status = "ok" if step.ok else "fail"
        lines.append(
            f"{index}. [{status}] {step.agent}.{step.action} "
            f"cost={step.cost:.4f} latency={step.latency_ms:.1f}ms "
            f"params={step.params} result={step.result}"
        )
    return lines
