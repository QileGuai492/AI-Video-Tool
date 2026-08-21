"""存储 Provider 工厂。"""

from app.core.config import get_settings
from app.storage.base import StorageProvider
from app.storage.local import LocalStorageProvider


def get_storage_provider() -> StorageProvider:
    """根据配置返回存储 Provider。"""
    settings = get_settings()
    if settings.storage_backend == "oss":
        from app.storage.oss import OSSStorageProvider

        return OSSStorageProvider()
    return LocalStorageProvider()


# 默认存储实例
storage = get_storage_provider()
