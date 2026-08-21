"""新增 video_tasks.audio_url 与 subtitle_url 字段。"""

from alembic import op

revision = "0003_add_audio_subtitle_urls"
down_revision = "0002_add_character_id_to_video_tasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """添加音频与字幕 URL 字段（幂等）。"""
    op.execute(
        "ALTER TABLE video_tasks ADD COLUMN IF NOT EXISTS audio_url VARCHAR(512)"
    )
    op.execute(
        "ALTER TABLE video_tasks ADD COLUMN IF NOT EXISTS subtitle_url VARCHAR(512)"
    )


def downgrade() -> None:
    """删除音频与字幕 URL 字段。"""
    op.execute("ALTER TABLE video_tasks DROP COLUMN IF EXISTS subtitle_url")
    op.execute("ALTER TABLE video_tasks DROP COLUMN IF EXISTS audio_url")
