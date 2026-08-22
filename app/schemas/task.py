"""任务相关 Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class GenerateVideoRequest(BaseModel):
    """提交视频生成任务请求。"""

    prompt: str = Field(min_length=1, max_length=2000)
    image_url: str | None = None
    duration: int = Field(default=60, ge=5, le=120)
    aspect_ratio: str = Field(default="16:9", pattern="^(16:9|9:16|1:1)$")
    quality: str = Field(default="standard", pattern="^(fast|standard|high)$")
    model: str | None = None
    character_id: int | None = None
    previs_video_url: str | None = None
    previs_type: str | None = None
    reference_video_url: str | None = None
    previs_project_id: int | None = None


class GenerateBatchRequest(BaseModel):
    """批量提交视频生成任务请求。"""

    prompt: str = Field(min_length=1, max_length=2000)
    count: int = Field(default=2, ge=1, le=5)
    image_url: str | None = None
    duration: int = Field(default=60, ge=5, le=120)
    aspect_ratio: str = Field(default="16:9", pattern="^(16:9|9:16|1:1)$")
    quality: str = Field(default="standard", pattern="^(fast|standard|high)$")
    model: str | None = None
    character_id: int | None = None


class BatchSubmitResponse(BaseModel):
    """批量提交响应。"""

    batch_id: str
    task_ids: list[int]
    count: int


class VideoTaskRead(BaseModel):
    """任务基本信息响应。"""

    id: int
    user_id: int
    prompt: str
    optimized_prompt: str | None = None
    status: str
    video_url: str | None = None
    audio_url: str | None = None
    subtitle_url: str | None = None
    duration: int | None = None
    aspect_ratio: str | None = None
    cost: float | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class TaskStatusResponse(BaseModel):
    """任务状态查询响应。"""

    task_id: int
    status: str
    progress: float
    current_stage: str
    segments_done: int
    segments_total: int
    estimated_cost: float | None = None
