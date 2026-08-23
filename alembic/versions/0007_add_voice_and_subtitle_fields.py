"""为 video_tasks 增加配音与字幕开关字段（幂等）。"""

from alembic import op

revision = "0007_add_voice_and_subtitle_fields"
down_revision = "0006_add_uid_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """增加 voice_id 与 with_subtitle 字段。"""
    op.execute("ALTER TABLE video_tasks ADD COLUMN IF NOT EXISTS voice_id VARCHAR(64)")
    op.execute("ALTER TABLE video_tasks ADD COLUMN IF NOT EXISTS with_subtitle BOOLEAN NOT NULL DEFAULT true")


def downgrade() -> None:
    """删除配音与字幕开关字段。"""
    op.execute("ALTER TABLE video_tasks DROP COLUMN IF EXISTS with_subtitle")
    op.execute("ALTER TABLE video_tasks DROP COLUMN IF EXISTS voice_id")
