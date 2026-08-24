"""视频生成接口。"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models import (
    AudioTrack,
    GenerationLog,
    TaskConfigSnapshot,
    TaskError,
    TaskRetry,
    User,
    VideoSegment,
    VideoTask,
)
from app.schemas.task import (
    BatchSubmitResponse,
    GenerateBatchRequest,
    GenerateVideoRequest,
    TaskStatusResponse,
    VideoTaskRead,
)
from app.services.task_service import create_video_task, get_task_status_by_uid
from app.tasks.video_tasks import process_video_task

router = APIRouter(prefix="/generate", tags=["视频生成"])


@router.post("/video", response_model=VideoTaskRead)
def submit_video_task(
    payload: GenerateVideoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VideoTask:
    """提交视频生成任务并进入 Celery 队列。"""
    task = create_video_task(db=db, user_id=current_user.id, request=payload)

    # 提交到 Celery 异步执行
    process_video_task.delay(task.id)

    return task


@router.post("/batch", response_model=BatchSubmitResponse)
def submit_batch_tasks(
    payload: GenerateBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BatchSubmitResponse:
    """批量提交多个视频生成任务。"""
    task_ids: list[int] = []
    task_uids: list[str] = []
    interval = get_settings().video_task_interval_seconds
    for index in range(payload.count):
        single = GenerateVideoRequest(
            prompt=payload.prompt,
            image_url=payload.image_url,
            reference_image_urls=payload.reference_image_urls,
            character_mappings=payload.character_mappings,
            voice_id=payload.voice_id,
            with_subtitle=payload.with_subtitle,
            speech_text=payload.speech_text,
            duration=payload.duration,
            aspect_ratio=payload.aspect_ratio,
            quality=payload.quality,
            model=payload.model,
            character_id=payload.character_id,
            previs_video_url=payload.previs_video_url,
            previs_type=payload.previs_type,
            reference_video_url=payload.reference_video_url,
            previs_project_id=payload.previs_project_id,
            camera_script=payload.camera_script,
        )
        task = create_video_task(db=db, user_id=current_user.id, request=single)
        # 按模型限流错峰提交：第 1 个立即执行，后续每个间隔 interval 秒
        process_video_task.apply_async(args=[task.id], countdown=index * interval)
        task_ids.append(task.id)
        task_uids.append(task.uid)

    return BatchSubmitResponse(
        batch_id=uuid.uuid4().hex,
        task_ids=task_ids,
        task_uids=task_uids,
        count=len(task_ids),
    )


@router.get("/status/{task_uid}", response_model=TaskStatusResponse)
def query_task_status(
    task_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskStatusResponse:
    """查询任务状态（使用公开任务 UID）。"""
    result = get_task_status_by_uid(db=db, task_uid=task_uid, user_id=current_user.id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return result


@router.get("/{task_uid}/download")
def download_video(
    task_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """下载已生成视频（使用公开任务 UID）。"""
    task = db.query(VideoTask).filter(
        VideoTask.uid == task_uid,
        VideoTask.user_id == current_user.id,
    ).first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    if not task.video_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频尚未生成")

    # 本地存储文件
    if task.video_url.startswith("/uploads/"):
        relative_path = task.video_url.removeprefix("/uploads/")
        file_path = Path("uploads") / relative_path
        if not file_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频文件不存在")
        return FileResponse(
            path=file_path,
            media_type="video/mp4",
            filename=f"task_{task.id}.mp4",
        )

    # OSS / 远程 URL 直接重定向
    if task.video_url.startswith(("http://", "https://")):
        return RedirectResponse(url=task.video_url)

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频文件不可用")


@router.post("/{task_uid}/cancel", response_model=VideoTaskRead)
def cancel_task(
    task_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VideoTask:
    """取消任务（当前为简单状态标记，后续补充 Celery revoke）。"""
    task = db.query(VideoTask).filter(
        VideoTask.uid == task_uid,
        VideoTask.user_id == current_user.id,
    ).first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    if task.status in {"completed", "failed", "cancelled"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前状态不可取消")
    task.status = "cancelled"
    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_uid}/retry", response_model=VideoTaskRead)
def retry_task(
    task_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VideoTask:
    """重试失败或已取消任务。"""
    task = db.query(VideoTask).filter(
        VideoTask.uid == task_uid,
        VideoTask.user_id == current_user.id,
    ).first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    if task.status not in {"failed", "cancelled"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只有失败或已取消任务可以重试")
    task.status = "pending"
    db.commit()
    db.refresh(task)
    process_video_task.apply_async(
        args=[task.id],
        countdown=get_settings().video_task_interval_seconds,
    )
    return task


@router.delete("/{task_uid}", response_model=VideoTaskRead)
def delete_task(
    task_uid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VideoTask:
    """删除当前用户的任务及其关联数据。"""
    task = db.query(VideoTask).filter(
        VideoTask.uid == task_uid,
        VideoTask.user_id == current_user.id,
    ).first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    db.query(VideoSegment).filter(VideoSegment.task_id == task.id).delete()
    db.query(AudioTrack).filter(AudioTrack.task_id == task.id).delete()
    db.query(TaskRetry).filter(TaskRetry.task_id == task.id).delete()
    db.query(TaskError).filter(TaskError.task_id == task.id).delete()
    db.query(TaskConfigSnapshot).filter(TaskConfigSnapshot.task_id == task.id).delete()
    db.query(GenerationLog).filter(GenerationLog.task_id == task.id).delete()
    db.delete(task)
    db.commit()
    return task
