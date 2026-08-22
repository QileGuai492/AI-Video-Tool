"""Agnes AI Provider（免费全模态 API）。

文档：
- https://github.com/kangarooking/agnes-free-model-skills
- https://apihub.agnes-ai.com
"""

from decimal import Decimal

import httpx

from app.core.config import get_settings
from app.providers.base import (
    ImageGenerationRequest,
    ImageGenerationResult,
    LLMRequest,
    LLMResult,
    VideoGenerationRequest,
    VideoTaskHandle,
    VideoTaskStatus,
)


class AgnesLLMProvider:
    """Agnes 文本生成 Provider。"""

    name = "agnes"

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.agnes_api_key or ""
        self.base_url = settings.agnes_base_url.rstrip("/")
        self.model = settings.agnes_llm_model

    def complete(self, request: LLMRequest) -> LLMResult:
        """调用 Agnes Chat Completions。"""
        if not self.api_key:
            raise RuntimeError("未配置 AGNES_API_KEY")

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
            timeout=120,
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


class AgnesImageProvider:
    """Agnes 文生图 Provider。"""

    name = "agnes"

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.agnes_api_key or ""
        self.base_url = settings.agnes_base_url.rstrip("/")
        self.public_base_url = settings.public_base_url.rstrip("/")
        self.model = settings.agnes_image_model

    def generate_image(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        """调用 Agnes Images Generations。"""
        if not self.api_key:
            raise RuntimeError("未配置 AGNES_API_KEY")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict = {
            "model": self.model,
            "prompt": request.prompt,
            "size": self._resolve_size(request.aspect_ratio),
        }
        if request.reference_image_urls:
            payload["extra_body"] = {
                "image": [self._to_public_url(url) for url in request.reference_image_urls],
                "response_format": "url",
            }

        response = httpx.post(
            f"{self.base_url}/images/generations",
            headers=headers,
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()
        image_url = data["data"][0]["url"]
        return ImageGenerationResult(
            image_url=image_url,
            provider=self.name,
            cost=Decimal("0"),
            raw_response=data,
        )

    def _to_public_url(self, url: str) -> str:
        """将本地相对 URL 转为公网可访问 URL。"""
        if url.startswith("/"):
            return f"{self.public_base_url}{url}"
        return url

    def _resolve_size(self, aspect_ratio: str) -> str:
        return {
            "16:9": "1280x720",
            "9:16": "720x1280",
            "1:1": "1024x1024",
        }.get(aspect_ratio, "1024x1024")


class AgnesVideoProvider:
    """Agnes 视频生成 Provider（异步任务）。"""

    name = "agnes"

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.agnes_api_key or ""
        self.base_url = settings.agnes_base_url.rstrip("/")
        self.public_base_url = settings.public_base_url.rstrip("/")
        self.model = settings.agnes_video_model

    def submit_video_task(self, request: VideoGenerationRequest) -> VideoTaskHandle:
        """创建视频生成任务。"""
        if not self.api_key:
            raise RuntimeError("未配置 AGNES_API_KEY")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        width, height = self._resolve_size(request.aspect_ratio)
        payload: dict = {
            "model": self.model,
            "prompt": request.prompt,
            "width": width,
            "height": height,
            "num_frames": 81,
            "frame_rate": 24,
        }
        image_url = request.first_frame_url or (
            request.reference_image_urls[0] if request.reference_image_urls else None
        )
        if image_url:
            payload["image"] = self._to_public_url(image_url)

        response = httpx.post(
            f"{self.base_url}/videos",
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        external_task_id = str(data.get("id") or data.get("task_id") or data.get("request_id"))
        return VideoTaskHandle(provider=self.name, external_task_id=external_task_id)

    def query_video_task(self, handle: VideoTaskHandle) -> VideoTaskStatus:
        """查询视频生成状态。"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        response = httpx.get(
            f"{self.base_url}/videos/{handle.external_task_id}",
            headers=headers,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        status = str(data.get("status") or "queued").lower()
        if status in {"completed", "succeeded", "success"}:
            return VideoTaskStatus(
                state="succeeded",
                video_url=data.get("video_url") or data.get("url"),
            )
        if status in {"failed", "error", "cancelled"}:
            return VideoTaskStatus(
                state="failed",
                error_code="API_SERVER_ERROR",
                error_message=data.get("error") or "Agnes 视频生成失败",
            )
        return VideoTaskStatus(state="processing")

    def _to_public_url(self, url: str) -> str:
        """将本地相对 URL 转为公网可访问 URL。"""
        if url.startswith("/"):
            return f"{self.public_base_url}{url}"
        return url

    def _resolve_size(self, aspect_ratio: str) -> tuple[int, int]:
        return {
            "16:9": (1280, 720),
            "9:16": (720, 1280),
            "1:1": (1024, 1024),
        }.get(aspect_ratio, (1024, 768))
