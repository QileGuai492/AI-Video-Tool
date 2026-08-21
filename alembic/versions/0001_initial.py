"""初始迁移：创建全部业务表。

当前为 Sprint 1 骨架迁移，直接基于 ORM metadata 建表。
后续新增字段应编写增量迁移，不再使用 create_all。
"""

from alembic import op
from app.db.base import Base
from app.models import (  # noqa: F401  确保模型注册到 metadata
    AudioTrack,
    BgmLibrary,
    Character,
    CharacterMultiView,
    GenerationLog,
    Setting,
    TaskConfigSnapshot,
    TaskError,
    TaskRetry,
    Template,
    User,
    VideoSegment,
    VideoTask,
)

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建全部表。"""
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """删除全部表。"""
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
