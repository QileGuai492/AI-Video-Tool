"""Pydantic Schemas 统一导出。"""

from app.schemas.audio import AudioGenerateRequest, AudioTrackRead
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.character import (
    CharacterCreate,
    CharacterDetailRead,
    CharacterMultiViewCreate,
    CharacterMultiViewRead,
    CharacterRead,
)
from app.schemas.cost import CostItemRead, CostSummaryRead, CostTaskRead
from app.schemas.previs import (
    PrevisProjectCreate,
    PrevisProjectRead,
    PrevisProjectUpdate,
    PrevisTemplateCreate,
    PrevisTemplateRead,
)
from app.schemas.subtitle import SubtitleGenerateRequest, SubtitleRead
from app.schemas.task import (
    GenerateVideoRequest,
    TaskStatusResponse,
    VideoTaskRead,
)
from app.schemas.template import TemplateCreate, TemplateRead

__all__ = [
    "AudioGenerateRequest",
    "AudioTrackRead",
    "CharacterCreate",
    "CharacterDetailRead",
    "CharacterMultiViewCreate",
    "CharacterMultiViewRead",
    "CharacterRead",
    "CostItemRead",
    "CostSummaryRead",
    "CostTaskRead",
    "GenerateVideoRequest",
    "LoginRequest",
    "PrevisProjectCreate",
    "PrevisProjectRead",
    "PrevisProjectUpdate",
    "PrevisTemplateCreate",
    "PrevisTemplateRead",
    "RegisterRequest",
    "SubtitleGenerateRequest",
    "SubtitleRead",
    "TaskStatusResponse",
    "TemplateCreate",
    "TemplateRead",
    "TokenResponse",
    "VideoTaskRead",
]
