"""LangGraph 编排器集成测试。"""

from app.models import VideoTask
from app.orchestration import langgraph_orchestrator as langgraph_module
from app.orchestration.langgraph_orchestrator import LangGraphOrchestrator
from tests.conftest import TestingSessionLocal


def test_langgraph_orchestrator_completes_task(db_session, monkeypatch) -> None:
    """LangGraph 编排器应能完成视频生成流水线。"""
    monkeypatch.setattr(langgraph_module, "SessionLocal", TestingSessionLocal)

    task = VideoTask(
        user_id=1,
        prompt="LangGraph 测试视频",
        status="pending",
        duration=5,
        aspect_ratio="16:9",
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    LangGraphOrchestrator().run(task.id)

    db_session.refresh(task)
    assert task.status == "completed"
    assert task.video_url
