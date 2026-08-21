"""Mock Provider。

本地开发不依赖真实 API Key，返回固定结果，方便联调与测试。
"""

import time
import uuid
from decimal import Decimal

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


class MockImageProvider:
    """模拟文生图 Provider。"""

    name = "mock_image"

    def generate_image(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        """返回固定的模拟图片地址。"""
        return ImageGenerationResult(
            image_url=f"https://mock.local/images/{uuid.uuid4().hex}.png",
            provider=self.name,
            cost=Decimal("0.01"),
            raw_response={"mock": True},
        )


class MockVideoProvider:
    """模拟视频生成 Provider。"""

    name = "mock_video"

    def __init__(self) -> None:
        self._tasks: dict[str, float] = {}

    def submit_video_task(self, request: VideoGenerationRequest) -> VideoTaskHandle:
        """提交任务并记录提交时间。"""
        external_task_id = uuid.uuid4().hex
        self._tasks[external_task_id] = time.time()
        return VideoTaskHandle(provider=self.name, external_task_id=external_task_id)

    def query_video_task(self, handle: VideoTaskHandle) -> VideoTaskStatus:
        """模拟异步生成：5 秒后返回成功。"""
        submitted_at = self._tasks.get(handle.external_task_id, time.time())
        elapsed = time.time() - submitted_at
        if elapsed < 5:
            return VideoTaskStatus(state="processing")
        return VideoTaskStatus(
            state="succeeded",
            video_url=f"https://mock.local/videos/{handle.external_task_id}.mp4",
        )


class MockTTSProvider:
    """模拟 TTS Provider。"""

    name = "mock_tts"

    def synthesize(self, request: TTSRequest) -> TTSResult:
        """返回固定的模拟音频地址。"""
        return TTSResult(
            audio_url=f"https://mock.local/audio/{uuid.uuid4().hex}.mp3",
            provider=self.name,
            cost=Decimal("0.01"),
            raw_response={"mock": True},
        )


class MockLLMProvider:
    """模拟 LLM Provider。"""

    name = "mock_llm"

    def complete(self, request: LLMRequest) -> LLMResult:
        """返回简单扩写结果。"""
        optimized = f"详细视频提示词：{request.user_prompt}（场景、主体、镜头、光线、风格）"
        return LLMResult(
            text=optimized,
            provider=self.name,
            cost=Decimal("0.001"),
            raw_response={"mock": True},
        )
