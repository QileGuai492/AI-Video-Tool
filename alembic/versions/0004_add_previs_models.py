"""新增白模预演数据模型（幂等）。"""

from alembic import op

revision = "0004_add_previs_models"
down_revision = "0003_add_audio_subtitle_urls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建白模表并扩展 video_tasks（表/字段均幂等）。"""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS previs_templates (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            name VARCHAR(128) NOT NULL,
            description TEXT,
            thumbnail_url VARCHAR(512),
            scene_json JSON NOT NULL,
            category VARCHAR(64),
            is_builtin BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS previs_projects (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            template_id INTEGER REFERENCES previs_templates(id),
            title VARCHAR(128) NOT NULL DEFAULT '未命名白模项目',
            mode VARCHAR(16) NOT NULL DEFAULT 'manual',
            scene_json JSON NOT NULL,
            camera_script JSON,
            mapping_rules JSON,
            previs_video_url VARCHAR(512),
            status VARCHAR(32) NOT NULL DEFAULT 'draft',
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
        )
        """
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
    op.execute("DROP TABLE IF EXISTS previs_projects")
    op.execute("DROP TABLE IF EXISTS previs_templates")
