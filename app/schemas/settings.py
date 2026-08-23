"""用户设置 Schema。"""

from pydantic import BaseModel, Field


class SettingsRead(BaseModel):
    """用户设置响应。"""

    default_aspect_ratio: str | None = None
    default_quality: str | None = None
    default_model: str | None = None
    cost_limit: float | None = None

    model_config = {"from_attributes": True}


class SettingsUpdate(BaseModel):
    """用户设置更新请求。"""

    default_aspect_ratio: str | None = Field(default=None, pattern="^(16:9|9:16|1:1)$")
    default_quality: str | None = Field(default=None, pattern="^(fast|standard|high)$")
    default_model: str | None = Field(default=None, max_length=128)
    cost_limit: float | None = Field(default=None, ge=0, le=100000)
