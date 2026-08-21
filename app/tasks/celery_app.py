"""Celery 应用实例。"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "ai_video_tool",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # 本地开发不依赖 Redis，直接同步执行任务
    task_always_eager=settings.app_env == "local",
)

# 确保 Worker 启动时注册视频生成任务
from app.tasks import video_tasks  # noqa: E402,F401
