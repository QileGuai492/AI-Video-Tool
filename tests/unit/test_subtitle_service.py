"""字幕服务单元测试。"""

from app.services.subtitle_service import build_srt_content


def test_build_srt_content() -> None:
    """SRT 内容应包含序号、时间轴和文本。"""
    content = build_srt_content("测试字幕")
    assert content.startswith("1\n")
    assert "00:00:00,000 --> 00:00:05,000" in content
    assert "测试字幕" in content
