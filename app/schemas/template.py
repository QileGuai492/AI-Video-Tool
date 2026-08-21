"""模板相关 Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class TemplateCreate(BaseModel):
    """保存模板请求。"""

    name: str = Field(min_length=1, max_length=128)
    config_json: dict


class TemplateRead(BaseModel):
    """模板信息响应。"""

    id: int
    user_id: int
    name: str
    config_json: dict
    version: int
    is_builtin: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
