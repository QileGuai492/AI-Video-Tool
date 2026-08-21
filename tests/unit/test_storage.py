"""存储抽象单元测试。"""

from app.storage import LocalStorageProvider, get_storage_provider, storage
from app.storage.local import UPLOAD_DIR


def test_local_storage_upload_and_get_url() -> None:
    """本地存储应保存文件并返回可访问 URL。"""
    provider = LocalStorageProvider()
    key = provider.upload(content=b"hello", suffix="txt", folder="test")
    assert key.startswith("test/")
    assert (UPLOAD_DIR / key).exists()
    assert provider.get_url(key) == f"/uploads/{key}"


def test_storage_factory_returns_local_by_default() -> None:
    """默认配置下应返回本地存储实例。"""
    assert isinstance(storage, LocalStorageProvider)
    assert isinstance(get_storage_provider(), LocalStorageProvider)
