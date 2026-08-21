"""基础监控指标接口。"""

from fastapi import APIRouter, Depends
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
