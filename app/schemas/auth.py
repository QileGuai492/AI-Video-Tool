"""认证相关 Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class UserRead(BaseModel):
    """当前用户信息。"""

    id: int
    username: str
    email: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """更新当前用户信息。"""

    email: str | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)


class RegisterRequest(BaseModel):
    """注册请求。"""

    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    email: str | None = None


class LoginRequest(BaseModel):
    """登录请求。"""

    username: str
    password: str


class TokenResponse(BaseModel):
    """登录成功返回的令牌。"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
