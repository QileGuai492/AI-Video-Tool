"""日志配置。

提供统一的结构化日志格式，便于生产环境采集与分析。
"""

import logging
import sys
from datetime import UTC, datetime


class StructuredFormatter(logging.Formatter):
    """输出包含时间、级别、Logger 与消息的结构化日志。"""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(UTC).isoformat()
        return (
            f"timestamp={timestamp} "
            f"level={record.levelname} "
            f"logger={record.name} "
            f"message={record.getMessage()}"
        )


def setup_logging(level: int = logging.INFO) -> None:
    """配置根日志器。"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
