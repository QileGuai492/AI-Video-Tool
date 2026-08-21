"""任务编排器工厂。"""

from app.core.config import get_settings
from app.orchestration.base import TaskOrchestrator
from app.orchestration.langgraph_orchestrator import LangGraphOrchestrator
from app.orchestration.simple import SimpleTaskOrchestrator


def get_orchestrator() -> TaskOrchestrator:
    """根据配置返回任务编排器。"""
    settings = get_settings()
    if settings.orchestrator_backend == "langgraph":
        return LangGraphOrchestrator()
    return SimpleTaskOrchestrator()


# 默认编排器实例
orchestrator = get_orchestrator()
