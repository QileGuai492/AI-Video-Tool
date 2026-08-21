"""Provider 抽象层。

核心业务只依赖这里的抽象接口，不直接依赖具体厂商 SDK。
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol


@dataclass
class ImageGenerationRequest:
    """文生图请求。"""

    prompt: str
    reference_image_urls: list[str] = field(default_factory=list)
    aspect_ratio: str = "16:9"
    quality: str = "standard"


@dataclass
class ImageGenerationResult:
    """文生图结果。"""

    image_url: str
    provider: str
    cost: Decimal
    raw_response: dict = field(default_factory=dict)


@dataclass
class VideoGenerationRequest:
    """视频生成请求。"""

    prompt: str
    first_frame_url: str | None = None
    reference_image_urls: list[str] = field(default_factory=list)
    duration: int = 5
    aspect_ratio: str = "16:9"
    resolution: str = "720p"
    model: str | None = None


@dataclass
class VideoTaskHandle:
    """视频任务句柄，用于轮询。"""

    provider: str
    external_task_id: str


@dataclass
class VideoTaskStatus:
    """视频任务状态。"""

    state: str  # pending / processing / succeeded / failed
    video_url: str | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass
class TTSRequest:
    """TTS 请求。"""

    text: str
    voice_id: str = "female_01"
    speed: float = 1.0


@dataclass
class TTSResult:
    """TTS 结果。"""

    audio_url: str
    provider: str
    cost: Decimal
    raw_response: dict = field(default_factory=dict)


@dataclass
class LLMRequest:
    """LLM 请求。"""

    system_prompt: str
    user_prompt: str
    temperature: float = 0.7
    max_tokens: int = 2000


@dataclass
class LLMResult:
    """LLM 结果。"""

    text: str
    provider: str
    cost: Decimal
    raw_response: dict = field(default_factory=dict)


class ImageProvider(Protocol):
    """文生图 Provider 协议。"""

    def generate_image(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        """生成图片。"""
        ...


class VideoProvider(Protocol):
    """视频生成 Provider 协议。"""

    def submit_video_task(self, request: VideoGenerationRequest) -> VideoTaskHandle:
        """提交视频生成任务。"""
        ...

    def query_video_task(self, handle: VideoTaskHandle) -> VideoTaskStatus:
        """查询视频任务状态。"""
        ...


class TTSProvider(Protocol):
    """TTS Provider 协议。"""

    def synthesize(self, request: TTSRequest) -> TTSResult:
        """合成语音。"""
        ...


class LLMProvider(Protocol):
    """LLM Provider 协议。"""

    def complete(self, request: LLMRequest) -> LLMResult:
        """调用大模型。"""
        ...
