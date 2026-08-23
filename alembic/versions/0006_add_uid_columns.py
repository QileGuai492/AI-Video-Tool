"""为用户和任务增加公开 UID（幂等）。"""

from alembic import op

revision = "0006_add_uid_columns"
down_revision = "0005_add_image_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """增加 users.uid 与 video_tasks.uid，并为已有行回填。"""
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS uid VARCHAR(32)")
    op.execute(
        """
        UPDATE users
        SET uid = substr(replace(gen_random_uuid()::text, '-', ''), 1, 32)
        WHERE uid IS NULL OR uid = ''
        """
    )
    op.execute("ALTER TABLE users ALTER COLUMN uid SET NOT NULL")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_uid ON users (uid)")

    op.execute("ALTER TABLE video_tasks ADD COLUMN IF NOT EXISTS uid VARCHAR(32)")
    op.execute(
        """
        UPDATE video_tasks
        SET uid = substr(replace(gen_random_uuid()::text, '-', ''), 1, 32)
        WHERE uid IS NULL OR uid = ''
        """
    )
    op.execute("ALTER TABLE video_tasks ALTER COLUMN uid SET NOT NULL")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_video_tasks_uid ON video_tasks (uid)")


def downgrade() -> None:
    """删除 UID 字段与索引。"""
    op.execute("DROP INDEX IF EXISTS ix_video_tasks_uid")
    op.execute("ALTER TABLE video_tasks DROP COLUMN IF EXISTS uid")
    op.execute("DROP INDEX IF EXISTS ix_users_uid")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS uid")
