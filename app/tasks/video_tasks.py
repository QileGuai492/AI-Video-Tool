"""视频生成 Celery 任务。

Celery 任务只负责调度入口，具体流水线由 TaskOrchestrator 执行。
当前使用 SimpleTaskOrchestrator，后续可替换为 LangGraph 编排器。
支持失败自动重试。
"""

from app.orchestration import orchestrator
from app.tasks.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="tasks.process_video_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
)
def process_video_task(self, task_id: int) -> None:
    """执行视频生成流水线。"""
    orchestrator.run(task_id)
