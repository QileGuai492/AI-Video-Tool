"""通用 Schema。"""

from pydantic import BaseModel


class MessageResponse(BaseModel):
    """通用消息响应。"""

    message: str
