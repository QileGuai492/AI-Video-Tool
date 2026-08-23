"""Simple 编排器集成测试。"""

from app.models import VideoTask
from app.orchestration import simple as simple_module
from app.orchestration.simple import SimpleTaskOrchestrator
from tests.conftest import TestingSessionLocal


def test_simple_orchestrator_completes_multiple_segments(db_session, monkeypatch) -> None:
    """Simple 编排器应能并行生成多个短视频片段并完成拼接。"""
    monkeypatch.setattr(simple_module, "SessionLocal", TestingSessionLocal)

    task = VideoTask(
        user_id=1,
        prompt="Simple 多片段测试",
        status="pending",
        duration=10,
        aspect_ratio="16:9",
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    SimpleTaskOrchestrator().run(task.id)

    db_session.refresh(task)
    assert task.status == "completed"
    assert task.video_url
    segments = task.segments
    assert len(segments) == 2
