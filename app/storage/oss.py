"""阿里云 OSS 存储实现。

依赖 oss2 SDK，配置项从环境变量读取。
"""

import uuid
from urllib.parse import quote

from app.core.config import get_settings


class OSSStorageProvider:
    """阿里云 OSS 存储实现。"""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.oss_access_key_id or not settings.oss_access_key_secret:
            raise RuntimeError("OSS 存储需要配置 OSS_ACCESS_KEY_ID 和 OSS_ACCESS_KEY_SECRET")

        import oss2  # 延迟导入，避免本地开发未安装时影响其他功能

        self._bucket = oss2.Bucket(
            oss2.Auth(settings.oss_access_key_id, settings.oss_access_key_secret),
            settings.oss_endpoint or "",
            settings.oss_bucket or "",
        )
        self._public_base_url = settings.oss_public_base_url

    def upload(self, content: bytes, suffix: str, folder: str = "files") -> str:
        """上传文件到 OSS，返回对象 key。"""
        filename = f"{uuid.uuid4().hex}.{suffix}"
        key = f"{folder}/{filename}"
        self._bucket.put_object(key, content)
        return key

    def get_url(self, key: str) -> str:
        """返回 OSS 访问 URL。

        配置了公共基础域名时直接拼接，否则生成签名 URL。
        """
        if self._public_base_url:
            return f"{self._public_base_url.rstrip('/')}/{quote(key)}"
        return self._bucket.sign_url("GET", key, 3600)
