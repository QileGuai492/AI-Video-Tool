"""角色特征包服务单元测试。"""

from app.services.character_feature import CharacterFeaturePack, append_character_description


def test_append_character_description_with_description() -> None:
    """有描述时应在提示词后追加角色外貌特征。"""
    pack = CharacterFeaturePack(
        character_id=1,
        name="女主",
        description="黑色长发，红色外套",
    )
    prompt = "角色在花园散步"

    result = append_character_description(prompt, pack)

    assert "黑色长发" in result
    assert result.startswith(prompt)


def test_append_character_description_without_description() -> None:
    """无描述时不应改变原提示词。"""
    pack = CharacterFeaturePack(character_id=1, name="女主")

    result = append_character_description("原始提示词", pack)

    assert result == "原始提示词"
