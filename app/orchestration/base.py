"""任务编排器抽象。

Celery 任务只依赖该接口，后续可用 LangGraph 实现替换 SimpleTaskOrchestrator。
"""

from typing import Protocol


class TaskOrchestrator(Protocol):
    """视频生成任务编排器协议。"""

    def run(self, task_id: int) -> None:
        """执行完整生成流水线。"""
        ...
