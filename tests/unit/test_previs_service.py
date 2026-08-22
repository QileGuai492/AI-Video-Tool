"""白模预演服务单元测试。"""

from app.services.previs_service import build_shot_prompt


def test_build_shot_prompt_contains_mapping_and_ban() -> None:
    """镜头提示词应包含映射规则与白模清理要求。"""
    prompt = build_shot_prompt(
        mapping_rules={"蓝色人形": "@图片1的女主"},
        shot={
            "start": "0s",
            "end": "5s",
            "action": "从画面左侧走到右侧",
            "camera": "跟拍",
            "scene": "黄昏街道",
        },
    )
    assert "蓝色人形" in prompt
    assert "@图片1的女主" in prompt
    assert "不保留白模材质" in prompt
    assert "0s-5s" in prompt
