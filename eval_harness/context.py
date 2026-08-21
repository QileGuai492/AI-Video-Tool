"""评测运行上下文与隔离环境准备。"""

import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.providers.registry import registry
from eval_harness.models import EvalContext


def prepare_environment() -> None:
    """在导入 app 前调用，确保评测使用隔离的本地环境。

    - 使用本地 SQLite，避免污染开发/生产数据库。
    - 清空 SiliconFlow Key，强制走 Mock Provider。
    - 使用本地存储，避免真实云存储调用。
    """
    os.environ["APP_ENV"] = "local"
    os.environ["SILICONFLOW_API_KEY"] = ""
    os.environ["DATABASE_URL"] = "sqlite:///./.eval_tmp/eval.db"
    os.environ["STORAGE_BACKEND"] = "local"
    os.environ["ORCHESTRATOR_BACKEND"] = "simple"

    eval_dir = Path(".eval_tmp")
    eval_dir.mkdir(exist_ok=True)


class EvalContextImpl:
    """评测上下文实现。"""

    def __init__(self) -> None:
        Base.metadata.create_all(bind=engine)
        # 强制只保留 Mock Provider，保证评测可复现、不依赖外部 API
        registry.image_providers = {"mock": registry.image_providers["mock"]}
        registry.video_providers = {"mock": registry.video_providers["mock"]}
        registry.tts_providers = {"mock": registry.tts_providers["mock"]}
        registry.llm_providers = {"mock": registry.llm_providers["mock"]}
        self._client = TestClient(app)

    def db_session(self):
        """创建数据库会话。"""
        return SessionLocal()

    @property
    def client(self):
        """返回 FastAPI TestClient。"""
        return self._client


def create_context() -> EvalContext:
    """创建评测上下文。"""
    return EvalContextImpl()
