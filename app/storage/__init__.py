"""存储模块统一导出。"""

from app.storage.base import StorageProvider
from app.storage.factory import get_storage_provider, storage
from app.storage.local import LocalStorageProvider
from app.storage.oss import OSSStorageProvider

__all__ = [
    "LocalStorageProvider",
    "OSSStorageProvider",
    "StorageProvider",
    "get_storage_provider",
    "storage",
]
