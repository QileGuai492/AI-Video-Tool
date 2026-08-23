"""质量评估服务单元测试。"""

from decimal import Decimal

from app.providers.base import LLMResult
from app.services.quality_service import evaluate_video, evaluate_video_with_vlm


def test_evaluate_video_with_url() -> None:
    """有视频 URL 时质量应通过。"""
    report = evaluate_video("https://example.com/video.mp4", threshold=7.5)
    assert report.passed is True
    assert report.score >= 7.5


def test_evaluate_video_without_url() -> None:
    """没有视频 URL 时质量应不通过。"""
    report = evaluate_video(None, threshold=7.5)
    assert report.passed is False
    assert report.score == 0.0


def test_evaluate_video_dimensions() -> None:
    """质量评估应返回多维度分数。"""
    report = evaluate_video("https://example.com/video.mp4", threshold=7.5, duration=5)
    assert report.dimensions is not None
    assert set(report.dimensions) == {"url", "file", "duration"}
    assert report.score == 8.0


class FakeLLMProvider:
    """模拟返回分数的 LLM Provider。"""

    name = "fake_vlm"

    def complete(self, request):
        return LLMResult(
            text="8.5",
            provider=self.name,
            cost=Decimal("0"),
            raw_response={"choices": [{"message": {"content": "8.5"}}]},
        )


def test_evaluate_video_with_vlm_scores_frame(monkeypatch) -> None:
    """启用 VLM 时应提取首帧并综合评分。"""
    monkeypatch.setattr(
        "app.services.quality_service._extract_first_frame",
        lambda video_url: "https://example.com/frame.jpg",
    )
    fake_provider = FakeLLMProvider()
    monkeypatch.setattr(
        "app.services.quality_service.registry.get_llm_provider",
        lambda: fake_provider,
    )

    report = evaluate_video_with_vlm("https://example.com/video.mp4", threshold=7.5, duration=5)

    assert report.dimensions is not None
    assert "vlm" in report.dimensions
    assert report.dimensions["vlm"] == 8.5
    assert report.passed is True


def test_evaluate_video_with_vlm_falls_back_without_frame(monkeypatch) -> None:
    """无法提取首帧时应回退到启发式结果。"""
    monkeypatch.setattr(
        "app.services.quality_service._extract_first_frame",
        lambda video_url: None,
    )

    report = evaluate_video_with_vlm("https://example.com/video.mp4", threshold=7.5, duration=5)

    assert report.dimensions is not None
    assert "vlm" not in report.dimensions
    assert report.score == 8.0
