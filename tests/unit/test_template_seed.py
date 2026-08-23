"""模板市场内置模板种子单元测试。"""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  确保模型注册到 Base.metadata
from app.db.base import Base
from app.models import Template, User
from app.services.template_seed import BUILTIN_PROMPT_TEMPLATES, seed_builtin_prompt_templates


def test_seed_builtin_prompt_templates_idempotent() -> None:
    """内置模板种子应幂等，并创建系统用户。"""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    seed_builtin_prompt_templates(engine)
    seed_builtin_prompt_templates(engine)

    with Session(engine) as db:
        count = db.query(Template).filter(Template.is_builtin.is_(True)).count()
        system = db.query(User).filter(User.username == "__system__").first()
    assert count == len(BUILTIN_PROMPT_TEMPLATES)
    assert system is not None
