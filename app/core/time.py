"""时间工具。"""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """返回无时区信息的 UTC 当前时间，兼容 SQLAlchemy DateTime。"""
    return datetime.now(UTC).replace(tzinfo=None)
