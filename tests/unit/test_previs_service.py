"""白模预演服务单元测试。"""

from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  确保模型注册到 Base.metadata
from app.db.base import Base
from app.models import PrevisTemplate
from app.providers.base import LLMResult
from app.services.previs_service import (
    BUILTIN_PREVIS_TEMPLATES,
    _parse_scene_json,
    build_segment_prompt,
    build_shot_prompt,
    convert_webm_to_mp4,
    generate_previs_scene_from_text,
    generate_previs_scene_from_video,
    normalize_previs_scene,
    seed_builtin_previs_templates,
)


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


def test_build_segment_prompt_merges_shot_description() -> None:
    """镜头描述应合并进基础提示词。"""
    prompt = build_segment_prompt(
        "一只猫在夕阳下奔跑",
        {"action": "从左侧跑向右侧", "camera": "侧面跟拍"},
    )
    assert "一只猫在夕阳下奔跑" in prompt
    assert "动作：从左侧跑向右侧" in prompt
    assert "运镜：侧面跟拍" in prompt


class FakeSceneLLM:
    """模拟返回场景 JSON 的 LLM。"""

    name = "fake_scene"

    def complete(self, request):
        return LLMResult(
            text=(
                '{"objects": [{"id": "obj_1", "name": "方块", "type": "box", '
                '"position": [0,0.5,0], "rotation": [0,0,0], "scale": [1,1,1]}], '
                '"keyframes": {}, "cameraKeyframes": [{"time": 0, "position": [5,4,5], '
                '"target": [0,0,0]}], "shotMarkers": [1, 3], "shotDescriptions": '
                '{"1": {"action": "人物走入画面", "camera": "侧面跟拍"}}, "duration": 5}'
            ),
            provider=self.name,
            cost=Decimal("0"),
            raw_response={},
        )


def test_parse_scene_json_with_code_fence() -> None:
    """应能解析代码块包裹的 JSON。"""
    scene = _parse_scene_json('```json\n{"objects": []}\n```')
    assert scene == {"objects": []}


def test_generate_previs_scene_from_text(monkeypatch) -> None:
    """文字生成白模应返回规范化场景。"""
    monkeypatch.setattr(
        "app.services.previs_service.registry.get_llm_provider",
        lambda: FakeSceneLLM(),
    )
    scene = generate_previs_scene_from_text("一只猫在夕阳下奔跑")
    assert scene["objects"]
    assert scene["objects"][0]["type"] == "box"
    assert scene["duration"] == 5
    assert scene["shotMarkers"] == [1, 3]


def test_normalize_previs_scene_fixes_invalid_data() -> None:
    """规范化应修复非法类型、重复 ID、错误向量和越界镜头。"""
    scene = normalize_previs_scene(
        {
            "objects": [
                {"id": "a", "type": "car", "position": [0, 1]},
                {"id": "a", "type": "sphere", "position": "bad"},
            ],
            "keyframes": {"a": [{"time": -1, "position": [1, 2, 3]}]},
            "cameraKeyframes": [{"time": 99, "position": [1, 2]}],
            "shotMarkers": [-1, 3, 99, 3],
            "shotDescriptions": {1: {"action": "走", "camera": "跟拍"}},
            "duration": 0,
        }
    )
    assert scene["duration"] == 5.0
    assert scene["objects"][0]["type"] == "box"
    assert scene["objects"][0]["position"] == [0, 0.5, 0]
    assert scene["objects"][1]["id"] != scene["objects"][0]["id"]
    assert scene["shotMarkers"] == [3.0]
    assert scene["cameraKeyframes"][0]["time"] == 5.0
    assert "1" in scene["shotDescriptions"]


def test_seed_builtin_previs_templates_idempotent() -> None:
    """内置模板种子应幂等，重复执行不会重复写入。"""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    seed_builtin_previs_templates(engine)
    seed_builtin_previs_templates(engine)
    with Session(engine) as db:
        count = db.query(PrevisTemplate).filter(PrevisTemplate.is_builtin.is_(True)).count()
    assert count == len(BUILTIN_PREVIS_TEMPLATES)


def test_convert_webm_to_mp4_scales_even_dimensions(monkeypatch, local_tmp_path) -> None:
    """WebM 转 MP4 应把奇数宽高缩放到偶数，避免 libx264 拒绝编码。"""
    source = local_tmp_path / "input.webm"
    source.write_bytes(b"fake-webm")
    output = local_tmp_path / "output.mp4"
    captured: dict[str, list[str]] = {}

    class FakeResult:
        returncode = 0
        stderr = ""

    def fake_run(command, **kwargs):
        captured["command"] = command
        return FakeResult()

    monkeypatch.setattr("app.services.previs_service._get_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr("app.services.previs_service.subprocess.run", fake_run)

    convert_webm_to_mp4(source, output)

    command = captured["command"]
    assert "-vf" in command
    assert "scale=trunc(iw/2)*2:trunc(ih/2)*2" in command


def test_generate_previs_scene_from_video_passes_image_urls(monkeypatch) -> None:
    """视频生成白模应把关键帧图片 URL 传给多模态 LLM。"""
    captured: dict = {}

    class FakeVideoLLM:
        name = "fake_video"

        def complete(self, request):
            captured["image_urls"] = request.image_urls
            return LLMResult(
                text=(
                    '{"objects": [{"id": "obj_1", "name": "灰模人形", "type": "humanoid", '
                    '"position": [0,0.5,0], "rotation": [0,0,0], "scale": [1,1,1]}], '
                    '"keyframes": {}, "cameraKeyframes": [{"time": 0, "position": [5,4,5], '
                    '"target": [0,0,0]}], "shotMarkers": [], "shotDescriptions": {}, "duration": 5}'
                ),
                provider=self.name,
                cost=Decimal("0"),
                raw_response={},
            )

    monkeypatch.setattr(
        "app.services.previs_service.registry.get_llm_provider",
        lambda: FakeVideoLLM(),
    )

    scene = generate_previs_scene_from_video(
        "参考视频",
        ["/uploads/previs_frames/1.jpg", "/uploads/previs_frames/2.jpg"],
    )
    assert captured["image_urls"] == [
        "/uploads/previs_frames/1.jpg",
        "/uploads/previs_frames/2.jpg",
    ]
    assert scene["objects"][0]["type"] == "humanoid"
