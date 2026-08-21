"""Provider 模块统一导出。"""

from app.providers.base import (
    ImageGenerationRequest,
    ImageGenerationResult,
    LLMRequest,
    LLMResult,
    TTSRequest,
    TTSResult,
    VideoGenerationRequest,
    VideoTaskHandle,
    VideoTaskStatus,
)
from app.providers.registry import ProviderRegistry, registry

__all__ = [
    "ImageGenerationRequest",
    "ImageGenerationResult",
    "LLMRequest",
    "LLMResult",
    "ProviderRegistry",
    "TTSRequest",
    "TTSResult",
    "VideoGenerationRequest",
    "VideoTaskHandle",
    "VideoTaskStatus",
    "registry",
]
