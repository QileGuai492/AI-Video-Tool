"""字幕服务单元测试。"""

from app.services.subtitle_service import _split_text, build_srt_content


def test_build_srt_content() -> None:
    """SRT 内容应包含序号、时间轴和文本。"""
    content = build_srt_content("测试字幕")
    assert content.startswith("1\n")
    assert "00:00:00,000 --> 00:00:05,000" in content
    assert "测试字幕" in content


def test_split_text_by_punctuation() -> None:
    """长文本应按标点拆成多条字幕。"""
    chunks = _split_text("第一句。第二句！第三句？")
    assert len(chunks) >= 2
    assert all(chunk for chunk in chunks)


def test_build_srt_content_multiple_cues() -> None:
    """多段字幕应生成多个时间轴。"""
    content = build_srt_content("第一句。第二句。第三句。", duration=6.0)
    assert content.count("\n\n") >= 2
    assert "00:00:02,000 --> 00:00:04,000" in content
