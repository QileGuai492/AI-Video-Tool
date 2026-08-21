"""MiniMax 视频生成 Provider。

调用 MiniMax 海螺视频生成接口，需配置 MINIMAX_API_KEY。
注意：具体请求/轮询字段请以 MiniMax 官方文档为准。
"""

import uuid

import httpx

from app.core.config import get_settings
from app.providers.base import (
    VideoGenerationRequest,
    VideoTaskHandle,
    VideoTaskStatus,
)

SUBMIT_ENDPOINT = "https://api.minimax.chat/v1/video_generation"
QUERY_ENDPOINT = "https://api.minimax.chat/v1/video_generation/query"


class MiniMaxVideoProvider:
    """MiniMax 视频生成 Provider。"""

    name = "minimax"

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.minimax_api_key or ""
        self.model = "video-01"

    def submit_video_task(self, request: VideoGenerationRequest) -> VideoTaskHandle:
        """提交视频生成任务。"""
        if not self.api_key:
            raise RuntimeError("未配置 MINIMAX_API_KEY")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "prompt": request.prompt,
            "first_frame_image": request.first_frame_url,
            "duration": request.duration,
        }

        response = httpx.post(SUBMIT_ENDPOINT, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        external_task_id = str(data.get("task_id") or data.get("id") or uuid.uuid4().hex)

        return VideoTaskHandle(provider=self.name, external_task_id=external_task_id)

    def query_video_task(self, handle: VideoTaskHandle) -> VideoTaskStatus:
        """查询视频任务状态。"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"task_id": handle.external_task_id}

        response = httpx.post(QUERY_ENDPOINT, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        status = data.get("status") or data.get("task_status") or "processing"
        if status in {"SUCCEEDED", "succeeded", "success"}:
            video_url = (
                data.get("video_url")
                or data.get("file_url")
                or data.get("output", {}).get("video_url")
            )
            return VideoTaskStatus(
                state="succeeded",
                video_url=video_url,
            )
        if status in {"FAILED", "failed"}:
            return VideoTaskStatus(
                state="failed",
                error_code="API_SERVER_ERROR",
                error_message="MiniMax 视频生成失败",
            )
        return VideoTaskStatus(state="processing")
