"""为 video_tasks 增加图生视频字段（幂等）。"""

from alembic import op

revision = "0005_add_image_fields_to_video_tasks"
down_revision = "0004_add_previs_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """增加 image_url 与 reference_image_urls 字段。"""
    op.execute("ALTER TABLE video_tasks ADD COLUMN IF NOT EXISTS image_url VARCHAR(512)")
    op.execute("ALTER TABLE video_tasks ADD COLUMN IF NOT EXISTS reference_image_urls JSON")


def downgrade() -> None:
    """删除图生视频字段。"""
    op.execute("ALTER TABLE video_tasks DROP COLUMN IF EXISTS reference_image_urls")
    op.execute("ALTER TABLE video_tasks DROP COLUMN IF EXISTS image_url")
