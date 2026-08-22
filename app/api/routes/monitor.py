"""基础监控指标接口。"""

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import GenerationLog, User, VideoTask

router = APIRouter(prefix="/metrics", tags=["监控"])


@router.get("")
def get_metrics(db: Session = Depends(get_db)) -> dict:
    """返回基础运行指标。"""
    task_status_rows = (
        db.query(VideoTask.status, func.count(VideoTask.id))
        .group_by(VideoTask.status)
        .all()
    )
    user_count = db.query(func.count(User.id)).scalar() or 0
    task_count = db.query(func.count(VideoTask.id)).scalar() or 0
    generation_log_count = db.query(func.count(GenerationLog.id)).scalar() or 0

    return {
        "app": "ai-video-tool",
        "users": user_count,
        "tasks": {
            "total": task_count,
            "by_status": {status: count for status, count in task_status_rows},
        },
        "generation_logs": generation_log_count,
        "status": "ok",
    }


@router.get("/prometheus", response_class=PlainTextResponse)
def get_prometheus_metrics(db: Session = Depends(get_db)) -> str:
    """返回 Prometheus 文本格式指标。"""
    task_status_rows = (
        db.query(VideoTask.status, func.count(VideoTask.id))
        .group_by(VideoTask.status)
        .all()
    )
    user_count = db.query(func.count(User.id)).scalar() or 0
    task_count = db.query(func.count(VideoTask.id)).scalar() or 0
    generation_log_count = db.query(func.count(GenerationLog.id)).scalar() or 0

    lines = [
        "# HELP ai_video_users 用户总数",
        "# TYPE ai_video_users gauge",
        f"ai_video_users {user_count}",
        "# HELP ai_video_tasks_total 任务总数",
        "# TYPE ai_video_tasks_total gauge",
        f"ai_video_tasks_total {task_count}",
        "# HELP ai_video_generation_logs_total 生成日志总数",
        "# TYPE ai_video_generation_logs_total gauge",
        f"ai_video_generation_logs_total {generation_log_count}",
    ]
    for status, count in task_status_rows:
        lines.append(f'ai_video_tasks{{status="{status}"}} {count}')
    return "\n".join(lines) + "\n"
