"""音频相关 Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class AudioGenerateRequest(BaseModel):
    """生成音频请求。"""

    task_id: int | None = None
    type: str = Field(default="tts", pattern="^(tts|bgm)$")
    text: str | None = None
    voice_id: str | None = None
    bgm_id: int | None = None
    tags: list[str] | None = None


class AudioTrackRead(BaseModel):
    """音频记录响应。"""

    id: int
    task_id: int | None = None
    type: str
    source_url: str
    text_content: str | None = None
    voice_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
