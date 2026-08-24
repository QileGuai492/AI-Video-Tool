"""角色特征包服务。

用于把角色库中的主参考图、多视角参考图、外貌描述组装成特征包，
并注入到提示词中，增强跨任务/跨对话的角色一致性。
"""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models import Character, CharacterMultiView


@dataclass
class CharacterFeaturePack:
    """角色特征包。"""

    character_id: int
    name: str
    description: str | None = None
    reference_image_urls: list[str] = field(default_factory=list)
    multi_view_urls: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "character_id": self.character_id,
            "name": self.name,
            "description": self.description,
            "reference_image_urls": self.reference_image_urls,
            "multi_view_urls": self.multi_view_urls,
        }


def build_character_feature_pack(db: Session, character_id: int) -> CharacterFeaturePack | None:
    """根据角色 ID 构建特征包。"""
    character = db.query(Character).filter(Character.id == character_id).first()
    if character is None:
        return None
    multi_views = (
        db.query(CharacterMultiView)
        .filter(CharacterMultiView.character_id == character_id)
        .all()
    )
    return CharacterFeaturePack(
        character_id=character.id,
        name=character.name,
        description=character.description,
        reference_image_urls=[character.reference_image_url],
        multi_view_urls=[view.image_url for view in multi_views],
    )


def append_character_description(prompt: str, feature_pack: CharacterFeaturePack | None) -> str:
    """把角色外貌描述追加到提示词中。"""
    if feature_pack is None or not feature_pack.description:
        return prompt
    return f"{prompt}；角色“{feature_pack.name}”的外貌特征：{feature_pack.description}"
