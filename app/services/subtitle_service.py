"""字幕服务。"""

import re

from app.storage import storage


def _split_text(text: str, max_chars: int = 20) -> list[str]:
    """按标点将长文本拆成适合单条字幕的片段。"""
    parts = [part.strip() for part in re.split(r"(?<=[。！？；])", text) if part.strip()]
    if len(parts) > 1:
        return parts
    if len(text) <= max_chars:
        return [text]
    return [text[index : index + max_chars] for index in range(0, len(text), max_chars)]


def _format_timestamp(seconds: float) -> str:
    """将秒数格式化为 SRT 时间戳。"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def build_srt_content(text: str, duration: float = 5.0) -> str:
    """根据文本生成多段 SRT 字幕内容。"""
    chunks = _split_text(text)
    step = duration / len(chunks)
    entries: list[str] = []
    for index, chunk in enumerate(chunks):
        start = index * step
        end = min(duration, (index + 1) * step)
        entries.append(
            f"{index + 1}\n"
            f"{_format_timestamp(start)} --> {_format_timestamp(end)}\n"
            f"{chunk}\n"
        )
    return "\n".join(entries)


def generate_subtitle(text: str) -> tuple[str, str]:
    """生成字幕文件并返回 URL 与内容。"""
    content = build_srt_content(text)
    key = storage.upload(
        content=content.encode("utf-8"),
        suffix="srt",
        folder="subtitles",
    )
    return storage.get_url(key), content
