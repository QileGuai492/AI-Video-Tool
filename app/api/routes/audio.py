"""音频生成接口。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User, VideoTask
from app.schemas.audio import AudioGenerateRequest, AudioTrackRead
from app.services.audio_service import generate_bgm_audio, generate_tts_audio

router = APIRouter(prefix="/generate", tags=["音频"])


@router.post("/audio", response_model=AudioTrackRead)
def generate_audio(
    payload: AudioGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """生成 TTS 配音或 BGM。"""
    if payload.task_id is not None:
        task = db.query(VideoTask).filter(
            VideoTask.id == payload.task_id,
            VideoTask.user_id == current_user.id,
        ).first()
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    if payload.type == "tts":
        if not payload.text:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TTS 需要提供文本")
        return generate_tts_audio(
            db=db,
            user_id=current_user.id,
            task_id=payload.task_id,
            text=payload.text,
            voice_id=payload.voice_id or "female_01",
        )

    return generate_bgm_audio(
        db=db,
        user_id=current_user.id,
        task_id=payload.task_id,
        bgm_id=payload.bgm_id,
    )
