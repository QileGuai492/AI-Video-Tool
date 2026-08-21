"""角色相关 Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class CharacterCreate(BaseModel):
    """创建角色请求。"""

    name: str = Field(min_length=1, max_length=128)
    reference_image_url: str
    description: str | None = None


class CharacterMultiViewCreate(BaseModel):
    """添加角色多角度参考图请求。"""

    view_name: str = Field(min_length=1, max_length=64)
    image_url: str


class CharacterMultiViewRead(BaseModel):
    """角色多角度参考图响应。"""

    id: int
    character_id: int
    view_name: str
    image_url: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CharacterRead(BaseModel):
    """角色信息响应。"""

    id: int
    user_id: int
    name: str
    reference_image_url: str
    description: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CharacterDetailRead(CharacterRead):
    """角色详情响应，包含多角度参考图。"""

    multi_views: list[CharacterMultiViewRead] = []
