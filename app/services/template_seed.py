"""模板市场内置模板种子。"""

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Template, User

SYSTEM_USERNAME = "__system__"

BUILTIN_PROMPT_TEMPLATES = [
    {
        "name": "短视频口播模板",
        "config_json": {
            "prompt_template": "请用{subject}为主题，生成一段 60 秒短视频口播脚本，包含开场、正文、结尾引导。",
            "duration": 60,
            "aspect_ratio": "9:16",
        },
    },
    {
        "name": "产品展示模板",
        "config_json": {
            "prompt_template": "请围绕{product}生成产品展示视频脚本，突出卖点、使用场景和视觉风格。",
            "duration": 30,
            "aspect_ratio": "16:9",
        },
    },
    {
        "name": "剧情故事模板",
        "config_json": {
            "prompt_template": "请根据{story}生成 3 镜头剧情视频，包含起承转合与情绪变化。",
            "duration": 60,
            "aspect_ratio": "16:9",
        },
    },
    {
        "name": "知识科普模板",
        "config_json": {
            "prompt_template": "请用通俗易懂的方式讲解{topic}，配合画面建议和字幕重点。",
            "duration": 60,
            "aspect_ratio": "1:1",
        },
    },
]


def _get_or_create_system_user(db: Session) -> User:
    """获取或创建内置模板所属的系统用户。"""
    user = db.query(User).filter(User.username == SYSTEM_USERNAME).first()
    if user is not None:
        return user
    user = User(
        username=SYSTEM_USERNAME,
        password_hash=hash_password("builtin_system_password"),
        email="system@local",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def seed_builtin_prompt_templates(engine) -> None:
    """按名称幂等写入模板市场内置模板。"""
    with Session(engine) as db:
        system_user = _get_or_create_system_user(db)
        added = False
        for item in BUILTIN_PROMPT_TEMPLATES:
            exists = (
                db.query(Template)
                .filter(Template.is_builtin.is_(True), Template.name == item["name"])
                .first()
            )
            if exists is not None:
                continue
            db.add(
                Template(
                    user_id=system_user.id,
                    name=item["name"],
                    config_json=item["config_json"],
                    is_builtin=True,
                )
            )
            added = True
        if added:
            db.commit()
