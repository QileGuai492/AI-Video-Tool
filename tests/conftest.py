"""pytest 全局夹具。

提供独立 SQLite 内存数据库、FastAPI TestClient 和已登录用户令牌。
"""

import os
import shutil
import uuid
from pathlib import Path

# 测试环境强制使用 SQLite，避免读取 .env 中的 PostgreSQL 配置
os.environ["DATABASE_URL"] = "sqlite:///./test_ai_video.db"
os.environ["APP_ENV"] = "local"
os.environ["SILICONFLOW_API_KEY"] = ""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.orchestration import simple as simple_orchestration
from app.providers.registry import registry

# 使用 StaticPool 让多个连接共享同一个内存数据库
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 测试临时目录根（放在项目内，避免沙箱拒绝系统临时目录）
TEMP_ROOT = Path(".test-tmp")


@pytest.fixture()
def local_tmp_path():
    """提供项目内可写的临时目录。"""
    TEMP_ROOT.mkdir(exist_ok=True)
    path = TEMP_ROOT / f"test-{uuid.uuid4().hex}"
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(autouse=True)
def mock_providers_only():
    """测试环境强制只使用 Mock Provider，避免真实 API 调用。"""
    registry.image_providers = {"mock": registry.image_providers["mock"]}
    registry.video_providers = {"mock": registry.video_providers["mock"]}
    registry.tts_providers = {"mock": registry.tts_providers["mock"]}
    registry.llm_providers = {"mock": registry.llm_providers["mock"]}
    yield


@pytest.fixture()
def db_session():
    """提供测试数据库会话，并在测试后清理。"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session, monkeypatch):
    """提供 FastAPI 测试客户端，并让任务编排使用测试数据库。"""
    # 让 Celery eager 模式下编排器使用测试数据库
    monkeypatch.setattr(simple_orchestration, "SessionLocal", TestingSessionLocal)

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client) -> dict[str, str]:
    """注册并登录测试用户，返回认证请求头。"""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "test_user",
            "password": "secret123",
            "email": "test@example.com",
        },
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
