"""历史记录接口。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User, VideoTask
from app.schemas.task import VideoTaskRead

router = APIRouter(prefix="/history", tags=["历史记录"])


@router.get("", response_model=list[VideoTaskRead])
def list_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[VideoTask]:
    """分页查询当前用户的历史任务。"""
    query = db.query(VideoTask).filter(VideoTask.user_id == current_user.id)
    if status_filter is not None:
        query = query.filter(VideoTask.status == status_filter)
    return (
        query.order_by(VideoTask.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
