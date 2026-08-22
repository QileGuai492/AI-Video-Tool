"""新增白模预演数据模型。"""

from alembic import op
import sqlalchemy as sa

revision = "0004_add_previs_models"
down_revision = "0003_add_audio_subtitle_urls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建白模表并扩展 video_tasks。"""
    op.create_table(
        "previs_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=512), nullable=True),
        sa.Column("scene_json", sa.JSON(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "previs_projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("previs_templates.id"), nullable=True, index=True),
        sa.Column("title", sa.String(length=128), nullable=False, server_default="未命名白模项目"),
        sa.Column("mode", sa.String(length=16), nullable=False, server_default="manual"),
        sa.Column("scene_json", sa.JSON(), nullable=False),
        sa.Column("camera_script", sa.JSON(), nullable=True),
        sa.Column("mapping_rules", sa.JSON(), nullable=True),
        sa.Column("previs_video_url", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    op.execute("ALTER TABLE video_tasks ADD COLUMN IF NOT EXISTS previs_video_url VARCHAR(512)")
    op.execute("ALTER TABLE video_tasks ADD COLUMN IF NOT EXISTS previs_type VARCHAR(16)")
    op.execute("ALTER TABLE video_tasks ADD COLUMN IF NOT EXISTS previs_scene_json JSON")
    op.execute("ALTER TABLE video_tasks ADD COLUMN IF NOT EXISTS storyboard_url VARCHAR(512)")
    op.execute("ALTER TABLE video_tasks ADD COLUMN IF NOT EXISTS camera_script JSON")
    op.execute("ALTER TABLE video_tasks ADD COLUMN IF NOT EXISTS reference_video_url VARCHAR(512)")
    op.execute("ALTER TABLE video_tasks ADD COLUMN IF NOT EXISTS previs_project_id INTEGER")


def downgrade() -> None:
    """删除白模表与 video_tasks 扩展字段。"""
    op.execute("ALTER TABLE video_tasks DROP COLUMN IF EXISTS previs_project_id")
    op.execute("ALTER TABLE video_tasks DROP COLUMN IF EXISTS reference_video_url")
    op.execute("ALTER TABLE video_tasks DROP COLUMN IF EXISTS camera_script")
    op.execute("ALTER TABLE video_tasks DROP COLUMN IF EXISTS storyboard_url")
    op.execute("ALTER TABLE video_tasks DROP COLUMN IF EXISTS previs_scene_json")
    op.execute("ALTER TABLE video_tasks DROP COLUMN IF EXISTS previs_type")
    op.execute("ALTER TABLE video_tasks DROP COLUMN IF EXISTS previs_video_url")
    op.drop_table("previs_projects")
    op.drop_table("previs_templates")
