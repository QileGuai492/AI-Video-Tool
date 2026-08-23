"""认证相关 Schema。"""

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


def _validate_password_strength(value: str | None) -> str | None:
    """校验密码强度：至少 8 位，且包含字母和数字。"""
    if value is None:
        return value
    if len(value) < 8:
        raise ValueError("密码至少 8 位")
    if not re.search(r"[A-Za-z]", value):
        raise ValueError("密码必须包含字母")
    if not re.search(r"\d", value):
        raise ValueError("密码必须包含数字")
    return value


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
    password: str | None = Field(default=None, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str | None) -> str | None:
        """密码可选，但填写时必须满足强度要求。"""
        return _validate_password_strength(value)


class RegisterRequest(BaseModel):
    """注册请求。"""

    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    email: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        """注册密码必须满足强度要求。"""
        return _validate_password_strength(value)


class LoginRequest(BaseModel):
    """登录请求。"""

    username: str
    password: str


class TokenResponse(BaseModel):
    """登录成功返回的令牌。"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
