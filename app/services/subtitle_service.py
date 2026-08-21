"""字幕服务。"""

from app.storage import storage


def build_srt_content(text: str) -> str:
    """根据文本生成简单 SRT 字幕内容。"""
    return (
        "1\n"
        "00:00:00,000 --> 00:00:05,000\n"
        f"{text}\n"
    )


def generate_subtitle(text: str) -> tuple[str, str]:
    """生成字幕文件并返回 URL 与内容。"""
    content = build_srt_content(text)
    key = storage.upload(
        content=content.encode("utf-8"),
        suffix="srt",
        folder="subtitles",
    )
    return storage.get_url(key), content
