"""OSS 存储接入验证脚本。

用法：
    python scripts/validate_oss.py

未配置 OSS 时输出 SKIP；配置后会上传一个测试文件并尝试访问。
"""

import sys

import httpx

from app.core.config import get_settings
from app.storage.oss import OSSStorageProvider


def main() -> None:
    """执行 OSS 验证。"""
    settings = get_settings()
    if settings.storage_backend != "oss" or not settings.oss_access_key_id:
        print("SKIP: 未启用 OSS 或未配置 OSS_ACCESS_KEY_ID")
        sys.exit(0)

    try:
        provider = OSSStorageProvider()
        key = provider.upload(b"ai-video-tool oss validation", suffix="txt", folder="validation")
        url = provider.get_url(key)
        print(f"UPLOAD_OK key={key}")
        print(f"URL={url}")

        response = httpx.get(url, timeout=30, follow_redirects=True)
        if response.status_code == 200 and b"oss validation" in response.content:
            print("READ_OK")
        else:
            print(f"READ_FAIL status={response.status_code}")
            sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"OSS_VALIDATE_FAILED: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
