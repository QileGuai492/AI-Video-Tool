"""本地文件存储实现。

文件保存到 uploads 目录，URL 为 /uploads/...。
生产环境建议切换为 OSS 或其他对象存储。
"""

import uuid
from pathlib import Path

# 上传根目录
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


class LocalStorageProvider:
    """本地磁盘存储实现。"""

    def upload(self, content: bytes, suffix: str, folder: str = "files") -> str:
        """保存文件到本地 uploads 目录，返回文件 key。"""
        filename = f"{uuid.uuid4().hex}.{suffix}"
        key = f"{folder}/{filename}"
        target = UPLOAD_DIR / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return key

    def get_url(self, key: str) -> str:
        """返回本地可访问 URL。"""
        return f"/uploads/{key}"
