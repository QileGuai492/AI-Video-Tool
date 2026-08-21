"""应用配置模块。

所有配置从环境变量或 .env 文件读取。
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用
    app_name: str = "AI 视频生成工具"
    app_env: str = "local"
    debug: bool = True
    secret_key: str = "please_change_me"
    jwt_secret: str = "please_change_me_jwt"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # 数据库
    database_url: str = "sqlite:///./ai_video.db"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # 外部 API Key
    minimax_api_key: str | None = None
    tongyi_api_key: str | None = None
    claude_api_key: str | None = None
    siliconflow_api_key: str | None = None
    siliconflow_base_url: str = "https://api.siliconflow.cn/v1"
    siliconflow_llm_model: str = "deepseek-ai/DeepSeek-V3"
    siliconflow_image_model: str = "Qwen/Qwen-Image"
    siliconflow_video_model: str = "Wan-AI/Wan2.2-T2V-A14B"

    # 阿里云 OSS
    oss_access_key_id: str | None = None
    oss_access_key_secret: str | None = None
    oss_bucket: str | None = None
    oss_endpoint: str | None = None
    oss_public_base_url: str | None = None

    # 文件存储
    storage_backend: str = "local"  # local / oss
    max_upload_size_mb: int = 200
    allowed_image_types: str = "jpg,jpeg,png,webp"
    allowed_audio_types: str = "mp3,wav"
    allowed_video_types: str = "mp4"

    # 成本与质量
    default_cost_limit: float = 50.0
    quality_threshold: float = 7.5

    # 任务编排
    orchestrator_backend: str = "simple"  # simple / langgraph

    # 本地开发自动建表（生产环境应使用 Alembic）
    auto_create_tables: bool = True


@lru_cache
def get_settings() -> Settings:
    """返回全局设置单例。"""
    return Settings()
