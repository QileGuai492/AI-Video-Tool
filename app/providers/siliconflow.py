"""硅基流动（SiliconFlow）Provider。

SiliconFlow 提供 OpenAI 兼容接口，可用于大模型对话、文生图、视频生成和 TTS。
当前实现：
- LLM：/chat/completions
- 文生图：/images/generations
- 视频生成：/video/submit + /video/status
- TTS：/audio/speech（如平台支持）

具体模型以官网 https://cloud.siliconflow.cn/models 为准。
"""

import base64
from decimal import Decimal

import httpx

from app.core.config import get_settings
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
from app.storage import storage


class SiliconFlowLLMProvider:
    """SiliconFlow 大模型 Provider（OpenAI 兼容）。"""

    name = "siliconflow"

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.siliconflow_api_key or ""
        self.base_url = settings.siliconflow_base_url.rstrip("/")
        self.model = settings.siliconflow_llm_model

    def complete(self, request: LLMRequest) -> LLMResult:
        """调用 SiliconFlow Chat Completions 接口。"""
        if not self.api_key:
            raise RuntimeError("未配置 SILICONFLOW_API_KEY")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }

        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        text = data["choices"][0]["message"]["content"]

        return LLMResult(
            text=text,
            provider=self.name,
            cost=Decimal("0"),
            raw_response=data,
        )


class SiliconFlowImageProvider:
    """SiliconFlow 文生图 Provider（OpenAI 兼容）。"""

    name = "siliconflow"

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.siliconflow_api_key or ""
        self.base_url = settings.siliconflow_base_url.rstrip("/")
        self.model = settings.siliconflow_image_model

    def generate_image(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        """调用 SiliconFlow Images Generations 接口。"""
        if not self.api_key:
            raise RuntimeError("未配置 SILICONFLOW_API_KEY")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "prompt": request.prompt,
            "image_size": self._resolve_size(request.aspect_ratio),
            "batch_size": 1,
        }

        response = httpx.post(
            f"{self.base_url}/images/generations",
            headers=headers,
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        image_item = data["data"][0]
        image_url = image_item.get("url")
        if not image_url:
            raise RuntimeError("SiliconFlow 文生图响应中未包含图片 URL")

        return ImageGenerationResult(
            image_url=image_url,
            provider=self.name,
            cost=Decimal("0"),
            raw_response=data,
        )

    def _resolve_size(self, aspect_ratio: str) -> str:
        """将比例映射为 SiliconFlow 支持的尺寸。"""
        return {
            "16:9": "1280x720",
            "9:16": "720x1280",
            "1:1": "1024x1024",
        }.get(aspect_ratio, "1024x1024")


class SiliconFlowVideoProvider:
    """SiliconFlow 视频生成 Provider。

    文档：https://docs.siliconflow.cn/cn/api-reference/videos/videos_submit
    """

    name = "siliconflow"

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.siliconflow_api_key or ""
        self.base_url = settings.siliconflow_base_url.rstrip("/")
        self.model = settings.siliconflow_video_model

    def submit_video_task(self, request: VideoGenerationRequest) -> VideoTaskHandle:
        """提交视频生成任务。"""
        if not self.api_key:
            raise RuntimeError("未配置 SILICONFLOW_API_KEY")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        image_url = request.first_frame_url or (
            request.reference_image_urls[0] if request.reference_image_urls else None
        )
        model = self.model
        image_data: str | None = None
        if image_url:
            model = "Wan-AI/Wan2.2-I2V-A14B"
            # 使用 base64 数据 URI 传递图片，避免 SiliconFlow 无法访问带签名参数的临时 URL
            image_data = self._load_image_as_data_uri(image_url)

        payload = {
            "model": model,
            "prompt": request.prompt,
            "negative_prompt": "",
            "duration": request.duration,
            "image_size": self._resolve_size(request.aspect_ratio),
        }
        if image_data:
            payload["image"] = image_data

        response = httpx.post(
            f"{self.base_url}/video/submit",
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        external_task_id = str(data.get("request_id") or data.get("requestId") or data.get("id"))

        return VideoTaskHandle(provider=self.name, external_task_id=external_task_id)

    def _load_image_as_data_uri(self, image_url: str) -> str:
        """下载图片并转换为 base64 数据 URI。

        SiliconFlow 的图生视频接口接受 data URI 或公开图片 URL；实测其服务端
        无法稳定访问带签名参数的临时 URL，因此统一先下载再以 base64 提交。
        """
        response = httpx.get(image_url, timeout=120, follow_redirects=True)
        response.raise_for_status()
        mime = response.headers.get("content-type", "image/png").split(";")[0].strip()
        if not mime.startswith("image/"):
            mime = "image/png"
        encoded = base64.b64encode(response.content).decode("ascii")
        return f"data:{mime};base64,{encoded}"

    def query_video_task(self, handle: VideoTaskHandle) -> VideoTaskStatus:
        """查询视频任务状态。"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        response = httpx.post(
            f"{self.base_url}/video/status",
            headers=headers,
            json={"requestId": handle.external_task_id},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        status = str(data.get("status") or data.get("state") or "processing").lower()
        if any(word in status for word in ("succeed", "success", "completed", "done")):
            results = data.get("results") or []
            video_url = data.get("video_url") or data.get("url")
            if isinstance(results, dict):
                videos = results.get("videos") or []
                if videos:
                    first = videos[0]
                    video_url = video_url or first.get("url") or first.get("video_url")
            elif isinstance(results, list):
                if results:
                    first = results[0]
                    video_url = video_url or first.get("url") or first.get("video_url")
            return VideoTaskStatus(state="succeeded", video_url=video_url)
        if any(word in status for word in ("fail", "error", "cancel")):
            return VideoTaskStatus(
                state="failed",
                error_code="API_SERVER_ERROR",
                error_message=data.get("reason") or "SiliconFlow 视频生成失败",
            )
        return VideoTaskStatus(state="processing")

    def _resolve_size(self, aspect_ratio: str) -> str:
        """将比例映射为 SiliconFlow 支持的尺寸。"""
        return {
            "16:9": "1280x720",
            "9:16": "720x1280",
            "1:1": "1024x1024",
        }.get(aspect_ratio, "1024x1024")


class SiliconFlowTTSProvider:
    """SiliconFlow TTS Provider（OpenAI 兼容 /audio/speech）。"""

    name = "siliconflow"

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.siliconflow_api_key or ""
        self.base_url = settings.siliconflow_base_url.rstrip("/")
        self.model = "FunAudioLLM/CosyVoice2-0.5B"

    _VOICE_ALIASES = {
        "female_01": "claire",
        "female_02": "diana",
        "male_01": "alex",
        "male_02": "benjamin",
    }

    def synthesize(self, request: TTSRequest) -> TTSResult:
        """调用 SiliconFlow 语音合成接口。"""
        if not self.api_key:
            raise RuntimeError("未配置 SILICONFLOW_API_KEY")

        # 兼容业务层的通用音色名，映射为平台预置音色
        voice = self._VOICE_ALIASES.get(request.voice_id, request.voice_id)
        if ":" not in voice:
            voice = f"{self.model}:{voice}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": request.text,
            "voice": voice,
            "response_format": "mp3",
            "speed": request.speed,
        }

        response = httpx.post(
            f"{self.base_url}/audio/speech",
            headers=headers,
            json=payload,
            timeout=120,
        )
        response.raise_for_status()

        # 如果返回 JSON 且包含 URL，直接使用
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            data = response.json()
            audio_url = data.get("url") or data.get("audio_url")
            if not audio_url:
                raise RuntimeError("SiliconFlow TTS 响应中未包含音频 URL")
            return TTSResult(audio_url=audio_url, provider=self.name, cost=Decimal("0"), raw_response=data)

        # 否则按音频二进制保存到存储层
        key = storage.upload(content=response.content, suffix="mp3", folder="audio")
        audio_url = storage.get_url(key)
        return TTSResult(audio_url=audio_url, provider=self.name, cost=Decimal("0"), raw_response={})
