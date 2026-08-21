"""字幕相关 Schema。"""

from pydantic import BaseModel, Field


class SubtitleGenerateRequest(BaseModel):
    """生成字幕请求。"""

    task_id: int | None = None
    text: str = Field(min_length=1, max_length=5000)
    source: str = Field(default="tts_text", max_length=32)


class SubtitleRead(BaseModel):
    """字幕生成结果。"""

    subtitle_url: str
    content: str
