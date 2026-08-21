"""存储 Provider 抽象。

核心业务只依赖该抽象，不直接写本地磁盘或 OSS 代码。
"""

from typing import Protocol


class StorageProvider(Protocol):
    """文件存储 Provider 协议。"""

    def upload(self, content: bytes, suffix: str, folder: str = "files") -> str:
        """上传文件，返回文件 key。"""
        ...

    def get_url(self, key: str) -> str:
        """根据文件 key 返回可访问 URL。"""
        ...
