"""SiliconFlow Provider 单元测试。"""

import httpx

from app.providers.base import (
    ImageGenerationRequest,
    LLMRequest,
    TTSRequest,
    VideoGenerationRequest,
    VideoTaskHandle,
)
from app.providers.siliconflow import (
    SiliconFlowImageProvider,
    SiliconFlowLLMProvider,
    SiliconFlowTTSProvider,
    SiliconFlowVideoProvider,
)


class FakeResponse:
    """模拟 httpx.Response。"""

    headers = {"content-type": "application/json"}

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        """模拟无异常。"""

    def json(self) -> dict:
        """返回模拟 JSON。"""
        return self._payload


class FakeDownloadResponse:
    """模拟图片下载响应。"""

    content = b"fake-image-bytes"
    headers = {"content-type": "image/png"}

    def raise_for_status(self) -> None:
        """模拟无异常。"""


def test_siliconflow_llm_complete(monkeypatch) -> None:
    """LLM 应从 chat/completions 响应中提取文本。"""
    provider = SiliconFlowLLMProvider()
    provider.api_key = "test-key"

    def fake_post(url, headers=None, json=None, timeout=None):
        assert "/chat/completions" in url
        return FakeResponse({"choices": [{"message": {"content": "优化后的提示词"}}]})

    monkeypatch.setattr(httpx, "post", fake_post)

    result = provider.complete(
        LLMRequest(system_prompt="system", user_prompt="一只猫")
    )
    assert result.text == "优化后的提示词"
    assert result.provider == "siliconflow"


def test_siliconflow_image_generate(monkeypatch) -> None:
    """文生图应从 images/generations 响应中提取 URL。"""
    provider = SiliconFlowImageProvider()
    provider.api_key = "test-key"

    def fake_post(url, headers=None, json=None, timeout=None):
        assert "/images/generations" in url
        return FakeResponse({"data": [{"url": "https://example.com/image.png"}]})

    monkeypatch.setattr(httpx, "post", fake_post)

    result = provider.generate_image(
        ImageGenerationRequest(prompt="一只猫", aspect_ratio="16:9")
    )
    assert result.image_url == "https://example.com/image.png"
    assert result.provider == "siliconflow"


def test_siliconflow_video_submit(monkeypatch) -> None:
    """视频提交应从响应中提取 request_id。"""
    provider = SiliconFlowVideoProvider()
    provider.api_key = "test-key"

    def fake_post(url, headers=None, json=None, timeout=None):
        assert "/video/submit" in url
        return FakeResponse({"request_id": "abc123"})

    monkeypatch.setattr(httpx, "post", fake_post)

    handle = provider.submit_video_task(
        VideoGenerationRequest(prompt="一只猫", duration=5, aspect_ratio="16:9")
    )
    assert handle.external_task_id == "abc123"


def test_siliconflow_video_submit_with_image_uses_data_uri(monkeypatch) -> None:
    """图生视频提交时，应将图片转换为 base64 数据 URI。"""
    provider = SiliconFlowVideoProvider()
    provider.api_key = "test-key"
    captured: dict = {}

    def fake_get(url, timeout=None, follow_redirects=None):
        assert url == "https://example.com/first-frame.png"
        return FakeDownloadResponse()

    def fake_post(url, headers=None, json=None, timeout=None):
        assert "/video/submit" in url
        captured["json"] = json
        return FakeResponse({"request_id": "abc123"})

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(httpx, "post", fake_post)

    handle = provider.submit_video_task(
        VideoGenerationRequest(
            prompt="一只猫",
            first_frame_url="https://example.com/first-frame.png",
            duration=5,
            aspect_ratio="16:9",
        )
    )
    assert handle.external_task_id == "abc123"
    assert captured["json"]["model"] == "Wan-AI/Wan2.2-I2V-A14B"
    assert captured["json"]["image"].startswith("data:image/png;base64,")


def test_siliconflow_video_query_with_results_object(monkeypatch) -> None:
    """视频查询应从 results.videos 对象中提取视频 URL。"""
    provider = SiliconFlowVideoProvider()
    provider.api_key = "test-key"

    def fake_post(url, headers=None, json=None, timeout=None):
        assert "/video/status" in url
        return FakeResponse(
            {
                "status": "Succeed",
                "results": {
                    "videos": [{"url": "https://example.com/video.mp4"}],
                    "timings": {"inference": 12},
                    "seed": 1,
                },
            }
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    status = provider.query_video_task(
        VideoTaskHandle(provider="siliconflow", external_task_id="abc123")
    )
    assert status.state == "succeeded"
    assert status.video_url == "https://example.com/video.mp4"


def test_siliconflow_video_query_with_results_list(monkeypatch) -> None:
    """兼容旧版 results 数组结构。"""
    provider = SiliconFlowVideoProvider()
    provider.api_key = "test-key"

    def fake_post(url, headers=None, json=None, timeout=None):
        assert "/video/status" in url
        return FakeResponse(
            {
                "status": "Succeed",
                "results": [{"url": "https://example.com/video.mp4"}],
            }
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    status = provider.query_video_task(
        VideoTaskHandle(provider="siliconflow", external_task_id="abc123")
    )
    assert status.state == "succeeded"
    assert status.video_url == "https://example.com/video.mp4"


def test_siliconflow_tts_maps_voice_alias(monkeypatch) -> None:
    """TTS 应将业务音色名映射为平台预置音色。"""
    provider = SiliconFlowTTSProvider()
    provider.api_key = "test-key"
    captured: dict = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        assert "/audio/speech" in url
        captured["json"] = json
        return FakeResponse({"url": "https://example.com/audio.mp3"})

    monkeypatch.setattr(httpx, "post", fake_post)

    result = provider.synthesize(TTSRequest(text="你好", voice_id="female_01"))
    assert result.audio_url == "https://example.com/audio.mp3"
    assert captured["json"]["voice"] == "FunAudioLLM/CosyVoice2-0.5B:claire"
