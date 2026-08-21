"""新增 video_tasks.character_id 字段，用于任务关联角色。"""

from alembic import op

revision = "0002_add_character_id_to_video_tasks"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """添加 character_id 字段和索引（幂等）。"""
    op.execute(
        "ALTER TABLE video_tasks ADD COLUMN IF NOT EXISTS character_id INTEGER"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_video_tasks_character_id ON video_tasks (character_id)"
    )


def downgrade() -> None:
    """删除 character_id 字段和索引。"""
    op.execute("DROP INDEX IF EXISTS ix_video_tasks_character_id")
    op.execute("ALTER TABLE video_tasks DROP COLUMN IF EXISTS character_id")
