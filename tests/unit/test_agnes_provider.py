"""Agnes Provider 单元测试。"""

import httpx
import pytest

from app.providers.agnes import (
    AgnesImageProvider,
    AgnesLLMProvider,
    AgnesVideoProvider,
)
from app.providers.base import (
    ImageGenerationRequest,
    LLMRequest,
    VideoGenerationRequest,
    VideoTaskHandle,
)


class FakeResponse:
    """模拟 httpx.Response。"""

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        """模拟无异常。"""

    def json(self) -> dict:
        """返回模拟 JSON。"""
        return self._payload


def test_agnes_llm_complete(monkeypatch) -> None:
    """Agnes LLM 应从 chat/completions 响应中提取文本。"""
    provider = AgnesLLMProvider()
    provider.api_key = "test-key"

    def fake_post(url, headers=None, json=None, timeout=None):
        assert "/chat/completions" in url
        return FakeResponse({"choices": [{"message": {"content": "优化后的提示词"}}]})

    monkeypatch.setattr(httpx, "post", fake_post)

    result = provider.complete(LLMRequest(system_prompt="system", user_prompt="一只猫"))
    assert result.text == "优化后的提示词"
    assert result.provider == "agnes"


def test_agnes_image_generate(monkeypatch) -> None:
    """Agnes 文生图应从响应中提取图片 URL。"""
    provider = AgnesImageProvider()
    provider.api_key = "test-key"

    def fake_post(url, headers=None, json=None, timeout=None):
        assert "/images/generations" in url
        return FakeResponse({"data": [{"url": "https://agnes.example.com/image.png"}]})

    monkeypatch.setattr(httpx, "post", fake_post)

    result = provider.generate_image(ImageGenerationRequest(prompt="一只猫", aspect_ratio="16:9"))
    assert result.image_url == "https://agnes.example.com/image.png"
    assert result.provider == "agnes"


def test_agnes_video_submit_and_query(monkeypatch) -> None:
    """Agnes 视频提交应返回任务 ID，查询应返回视频 URL。"""
    provider = AgnesVideoProvider()
    provider.api_key = "test-key"
    captured: dict = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        assert "/videos" in url
        captured["json"] = json
        return FakeResponse({"id": "task-123"})

    def fake_get(url, headers=None, timeout=None):
        assert "/videos/task-123" in url
        return FakeResponse(
            {
                "status": "completed",
                "metadata": {"url": "https://agnes.example.com/video.mp4"},
            }
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(httpx, "get", fake_get)

    handle = provider.submit_video_task(
        VideoGenerationRequest(prompt="一只猫", first_frame_url="https://example.com/frame.png")
    )
    assert handle.external_task_id == "task-123"
    assert captured["json"]["image"] == "https://example.com/frame.png"

    status = provider.query_video_task(VideoTaskHandle(provider="agnes", external_task_id="task-123"))
    assert status.state == "succeeded"
    assert status.video_url == "https://agnes.example.com/video.mp4"


def test_agnes_video_submit_error_contains_response_body(monkeypatch) -> None:
    """Agnes 视频接口 4xx 时应把响应体带进异常，便于定位。"""
    provider = AgnesVideoProvider()
    provider.api_key = "test-key"

    def fake_post(url, headers=None, json=None, timeout=None):
        request = httpx.Request("POST", url)
        response = httpx.Response(400, text='{"error":"image url invalid"}', request=request)
        response.raise_for_status()
        return response

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(RuntimeError, match="Agnes 视频接口返回 400"):
        provider.submit_video_task(
            VideoGenerationRequest(prompt="一只猫", first_frame_url="https://example.com/frame.png")
        )
