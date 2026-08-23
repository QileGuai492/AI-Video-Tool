"""任务编排抽象单元测试。"""

import pytest

from app.orchestration import SimpleTaskOrchestrator, get_orchestrator, orchestrator
from app.orchestration import simple as simple_module
from app.providers.base import VideoTaskHandle, VideoTaskStatus


def test_orchestrator_factory_returns_simple() -> None:
    """当前默认编排器应为 SimpleTaskOrchestrator。"""
    assert isinstance(orchestrator, SimpleTaskOrchestrator)
    assert isinstance(get_orchestrator(), SimpleTaskOrchestrator)


def test_infer_voice_by_prompt_keywords() -> None:
    """应根据文案关键词推断默认配音音色。"""
    orchestrator = SimpleTaskOrchestrator()
    assert orchestrator._infer_voice("蜘蛛侠举起手接住蝴蝶") == "male_01"
    assert orchestrator._infer_voice("她站在海边") == "female_01"
    assert orchestrator._infer_voice("一个普通场景") == "female_01"


def test_wait_for_real_video_returns_remote_url_when_download_fails(monkeypatch) -> None:
    """真实视频下载失败时，应回退到原始远程 URL。"""
    class FakeProvider:
        name = "siliconflow"

        def query_video_task(self, handle):
            return VideoTaskStatus(
                state="succeeded",
                video_url="https://example.com/video.mp4",
            )

    monkeypatch.setattr(simple_module, "download_and_store_video", lambda url: None)

    result = SimpleTaskOrchestrator()._wait_for_real_video(
        FakeProvider(),
        VideoTaskHandle(provider="siliconflow", external_task_id="abc"),
        max_attempts=1,
    )
    assert result == "https://example.com/video.mp4"


def test_wait_for_real_video_raises_on_failed() -> None:
    """真实视频失败时不应回退占位视频，而应抛出异常。"""
    class FakeProvider:
        name = "siliconflow"

        def query_video_task(self, handle):
            return VideoTaskStatus(
                state="failed",
                error_code="API_SERVER_ERROR",
                error_message="生成失败",
            )

    with pytest.raises(RuntimeError, match="生成失败"):
        SimpleTaskOrchestrator()._wait_for_real_video(
            FakeProvider(),
            VideoTaskHandle(provider="siliconflow", external_task_id="abc"),
            max_attempts=1,
        )
