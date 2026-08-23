"""为 video_tasks 增加多角色映射字段（幂等）。"""

from alembic import op

revision = "0008_add_character_mappings"
down_revision = "0007_add_voice_subtitle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """增加 character_mappings JSON 字段。"""
    op.execute("ALTER TABLE video_tasks ADD COLUMN IF NOT EXISTS character_mappings JSON")


def downgrade() -> None:
    """删除多角色映射字段。"""
    op.execute("ALTER TABLE video_tasks DROP COLUMN IF EXISTS character_mappings")
