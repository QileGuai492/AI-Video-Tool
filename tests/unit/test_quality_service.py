"""质量评估服务单元测试。"""

from app.services.quality_service import evaluate_video


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
