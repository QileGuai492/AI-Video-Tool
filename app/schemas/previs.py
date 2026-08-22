"""白模预演相关 Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class PrevisTemplateCreate(BaseModel):
    """创建白模模板请求。"""

    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    thumbnail_url: str | None = None
    scene_json: dict = Field(default_factory=dict)
    category: str | None = None


class PrevisTemplateRead(BaseModel):
    """白模模板信息。"""

    id: int
    user_id: int | None
    name: str
    description: str | None
    thumbnail_url: str | None
    scene_json: dict
    category: str | None
    is_builtin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PrevisProjectCreate(BaseModel):
    """创建白模项目请求。"""

    title: str = Field(default="未命名白模项目", max_length=128)
    template_id: int | None = None
    mode: str = Field(default="manual", pattern="^(template|auto|manual)$")
    scene_json: dict = Field(default_factory=dict)
    camera_script: dict | None = None
    mapping_rules: dict | None = None


class PrevisProjectUpdate(BaseModel):
    """更新白模项目请求。"""

    title: str | None = None
    scene_json: dict | None = None
    camera_script: dict | None = None
    mapping_rules: dict | None = None
    previs_video_url: str | None = None
    status: str | None = Field(default=None, pattern="^(draft|rendering|ready|failed)$")


class PrevisProjectRead(BaseModel):
    """白模项目信息。"""

    id: int
    user_id: int
    template_id: int | None
    title: str
    mode: str
    scene_json: dict
    camera_script: dict | None
    mapping_rules: dict | None
    previs_video_url: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
