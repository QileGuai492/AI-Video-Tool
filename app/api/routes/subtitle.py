"""字幕生成接口。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User, VideoTask
from app.schemas.subtitle import SubtitleGenerateRequest, SubtitleRead
from app.services.subtitle_service import generate_subtitle

router = APIRouter(prefix="/generate", tags=["字幕"])


@router.post("/subtitle", response_model=SubtitleRead)
def generate_subtitle_endpoint(
    payload: SubtitleGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubtitleRead:
    """根据文本生成字幕文件。"""
    if payload.task_id is not None:
        task = db.query(VideoTask).filter(
            VideoTask.id == payload.task_id,
            VideoTask.user_id == current_user.id,
        ).first()
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    subtitle_url, content = generate_subtitle(payload.text)
    return SubtitleRead(subtitle_url=subtitle_url, content=content)
