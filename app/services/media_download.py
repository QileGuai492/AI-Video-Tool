"""媒体下载服务。

将外部生成的视频/音频下载到本地存储，避免临时 URL 过期。
"""

import httpx

from app.storage import storage


def download_and_store_video(video_url: str, timeout: int = 120) -> str | None:
    """下载视频并保存到存储层，返回可访问 URL；失败返回 None。"""
    try:
        response = httpx.get(video_url, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
        key = storage.upload(content=response.content, suffix="mp4", folder="videos")
        return storage.get_url(key)
    except Exception:  # noqa: BLE001
        return None
