"""ORM 实体定义。

所有表结构以 docs/05-数据模型.md 为参考，当前为 Sprint 1 可运行骨架。
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now
from app.db.base import Base


class User(Base):
    """用户表。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uid: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, default=lambda: uuid.uuid4().hex)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    characters: Mapped[list["Character"]] = relationship(back_populates="user")
    video_tasks: Mapped[list["VideoTask"]] = relationship(back_populates="user")
    templates: Mapped[list["Template"]] = relationship(back_populates="user")
    previs_templates: Mapped[list["PrevisTemplate"]] = relationship(back_populates="user")
    previs_projects: Mapped[list["PrevisProject"]] = relationship(back_populates="user")


class Character(Base):
    """角色库。"""

    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    reference_image_url: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    user: Mapped["User"] = relationship(back_populates="characters")
    multi_views: Mapped[list["CharacterMultiView"]] = relationship(back_populates="character")


class CharacterMultiView(Base):
    """角色多角度参考图。"""

    __tablename__ = "characters_multi_view"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), nullable=False, index=True)
    view_name: Mapped[str] = mapped_column(String(64), nullable=False)
    image_url: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    character: Mapped["Character"] = relationship(back_populates="multi_views")


class VideoTask(Base):
    """视频生成任务。"""

    __tablename__ = "video_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uid: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, default=lambda: uuid.uuid4().hex)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    character_id: Mapped[int | None] = mapped_column(ForeignKey("characters.id"), nullable=True, index=True)
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    reference_image_urls: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    character_mappings: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    voice_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    with_subtitle: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    optimized_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True)
    video_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    audio_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    subtitle_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(32), nullable=True)
    aspect_ratio: Mapped[str | None] = mapped_column(String(16), nullable=True)
    cost: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    previs_video_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    previs_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    previs_scene_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    storyboard_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    camera_script: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reference_video_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    previs_project_id: Mapped[int | None] = mapped_column(ForeignKey("previs_projects.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship(back_populates="video_tasks")
    segments: Mapped[list["VideoSegment"]] = relationship(back_populates="task")
    audio_tracks: Mapped[list["AudioTrack"]] = relationship(back_populates="task")
    retries: Mapped[list["TaskRetry"]] = relationship(back_populates="task")
    errors: Mapped[list["TaskError"]] = relationship(back_populates="task")
    config_snapshot: Mapped["TaskConfigSnapshot | None"] = relationship(back_populates="task", uselist=False)
    previs_project: Mapped["PrevisProject | None"] = relationship(back_populates="video_tasks")


class VideoSegment(Base):
    """视频片段。"""

    __tablename__ = "video_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("video_tasks.id"), nullable=False, index=True)
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    video_url: Mapped[str] = mapped_column(String(512), nullable=False)
    prompt_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    task: Mapped["VideoTask"] = relationship(back_populates="segments")


class Template(Base):
    """用户模板。"""

    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user: Mapped["User"] = relationship(back_populates="templates")


class PrevisTemplate(Base):
    """白模预演模板。"""

    __tablename__ = "previs_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    scene_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    user: Mapped["User | None"] = relationship(back_populates="previs_templates")
    projects: Mapped[list["PrevisProject"]] = relationship(back_populates="template")


class PrevisProject(Base):
    """白模预演项目。"""

    __tablename__ = "previs_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    template_id: Mapped[int | None] = mapped_column(ForeignKey("previs_templates.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(128), default="未命名白模项目", nullable=False)
    mode: Mapped[str] = mapped_column(String(16), default="manual", nullable=False)  # template / auto / manual
    scene_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    camera_script: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    mapping_rules: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    previs_video_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user: Mapped["User"] = relationship(back_populates="previs_projects")
    template: Mapped["PrevisTemplate | None"] = relationship(back_populates="projects")
    video_tasks: Mapped[list["VideoTask"]] = relationship(back_populates="previs_project")


class AudioTrack(Base):
    """音频记录（TTS / BGM）。"""

    __tablename__ = "audio_tracks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("video_tasks.id"), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False)  # tts / bgm
    source_url: Mapped[str] = mapped_column(String(512), nullable=False)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    voice_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    task: Mapped["VideoTask | None"] = relationship(back_populates="audio_tracks")


class Setting(Base):
    """用户偏好设置。"""

    __tablename__ = "settings"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    default_aspect_ratio: Mapped[str | None] = mapped_column(String(16), nullable=True)
    default_quality: Mapped[str | None] = mapped_column(String(16), nullable=True)
    default_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cost_limit: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)


class GenerationLog(Base):
    """API 调用日志，用于成本审计。"""

    __tablename__ = "generation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("video_tasks.id"), nullable=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    call_type: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    cost: Mapped[float] = mapped_column(Numeric(10, 4), default=0, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)


class TaskRetry(Base):
    """任务重试记录。"""

    __tablename__ = "task_retries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("video_tasks.id"), nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    task: Mapped["VideoTask"] = relationship(back_populates="retries")


class TaskError(Base):
    """任务错误明细。"""

    __tablename__ = "task_errors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("video_tasks.id"), nullable=False, index=True)
    stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_code: Mapped[str] = mapped_column(String(64), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    stack_trace: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    task: Mapped["VideoTask"] = relationship(back_populates="errors")


class BgmLibrary(Base):
    """BGM 曲库。"""

    __tablename__ = "bgm_library"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    license: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)


class TaskConfigSnapshot(Base):
    """任务参数快照，用于复现与审计。"""

    __tablename__ = "task_config_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("video_tasks.id"), nullable=False, index=True)
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    task: Mapped["VideoTask"] = relationship(back_populates="config_snapshot")
