"""为 video_tasks 增加台词文本字段（幂等）。"""

from alembic import op

revision = "0009_add_speech_text"
down_revision = "0008_add_character_mappings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """增加 speech_text 字段。"""
    op.execute("ALTER TABLE video_tasks ADD COLUMN IF NOT EXISTS speech_text TEXT")


def downgrade() -> None:
    """删除台词文本字段。"""
    op.execute("ALTER TABLE video_tasks DROP COLUMN IF EXISTS speech_text")
