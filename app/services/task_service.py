"""视频任务服务。

负责创建任务、成本估算和状态查询。
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import VideoSegment, VideoTask
from app.schemas.task import GenerateVideoRequest, TaskStatusResponse


def calculate_segment_count(duration: int, segment_seconds: int = 5) -> int:
    """根据目标时长计算片段数量。"""
    return max(1, (duration + segment_seconds - 1) // segment_seconds)


def estimate_cost(duration: int, quality: str = "standard") -> Decimal:
    """粗略估算任务成本。

    当前为 Mock 估算，后续由 Provider 单价表驱动。
    """
    segment_count = calculate_segment_count(duration)
    unit_cost = Decimal("0.50")
    if quality == "high":
        unit_cost = Decimal("2.00")
    elif quality == "fast":
        unit_cost = Decimal("0.30")
    return unit_cost * segment_count


def create_video_task(db: Session, user_id: int, request: GenerateVideoRequest) -> VideoTask:
    """创建视频生成任务并返回。"""
    task = VideoTask(
        user_id=user_id,
        character_id=request.character_id,
        image_url=request.image_url,
        reference_image_urls=request.reference_image_urls,
        prompt=request.prompt,
        status="pending",
        duration=request.duration,
        aspect_ratio=request.aspect_ratio,
        cost=estimate_cost(request.duration, request.quality),
        previs_video_url=request.previs_video_url,
        previs_type=request.previs_type,
        reference_video_url=request.reference_video_url,
        previs_project_id=request.previs_project_id,
        camera_script=request.camera_script,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task_status(db: Session, task_id: int, user_id: int) -> TaskStatusResponse | None:
    """查询任务状态；任务不存在或不属于该用户时返回 None。"""
    task = db.query(VideoTask).filter(VideoTask.id == task_id, VideoTask.user_id == user_id).first()
    if task is None:
        return None

    segments = db.query(VideoSegment).filter(VideoSegment.task_id == task.id).count()
    total_segments = calculate_segment_count(task.duration or 60)

    stage_progress = {
        "pending": 0.0,
        "optimizing_prompt": 0.1,
        "generating_first_frame": 0.2,
        "generating_video": 0.5,
        "generating_audio": 0.6,
        "generating_subtitle": 0.7,
        "post_processing": 0.8,
        "quality_check": 0.9,
        "completed": 1.0,
        "failed": 1.0,
    }

    return TaskStatusResponse(
        task_id=task.id,
        status=task.status,
        progress=stage_progress.get(task.status, 0.0),
        current_stage=task.status,
        segments_done=segments,
        segments_total=total_segments,
        estimated_cost=float(task.cost) if task.cost is not None else None,
    )
