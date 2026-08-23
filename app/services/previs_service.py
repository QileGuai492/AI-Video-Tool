"""白模预演服务。

Phase 1 提供：
- 白模视频关键帧抽取（FFmpeg）
- 基于镜头脚本生成提示词
"""

import json
import re
import shutil
import subprocess
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.models import PrevisTemplate
from app.providers.base import LLMRequest
from app.providers.registry import registry
from app.storage import storage


def _resolve_local_path(video_url: str) -> Path:
    """将 /uploads/ 开头的 URL 解析为本地路径。"""
    if video_url.startswith("/uploads/"):
        return Path("uploads") / video_url.removeprefix("/uploads/")
    raise ValueError("当前仅支持本地 /uploads/ 白模视频抽帧")


def _get_ffmpeg() -> str:
    """返回可用的 FFmpeg 可执行文件路径。"""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is not None:
        return ffmpeg
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("未找到 FFmpeg") from exc


def convert_webm_to_mp4(source: Path, output: Path) -> Path:
    """将 WebM 转换为 MP4（H.264 + yuv420p）。

    增加 genpts/analyzeduration/probesize，兼容浏览器 MediaRecorder 产出的
    无 duration、时间戳不完整的 WebM。
    """
    ffmpeg = _get_ffmpeg()
    command = [
        ffmpeg,
        "-y",
        "-fflags",
        "+genpts",
        "-analyzeduration",
        "100M",
        "-probesize",
        "100M",
        "-i",
        str(source),
        "-vf",
        "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(output),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg 转 MP4 失败：{(result.stderr or '')[-500:]}")
    return output


def extract_keyframes(
    video_url: str,
    interval_seconds: float = 1.0,
) -> list[str]:
    """从白模视频中按固定间隔抽取关键帧，返回可访问 URL 列表。

    依赖 FFmpeg；输出文件保存到 uploads/previs_frames。
    """
    source = _resolve_local_path(video_url)
    if not source.exists():
        raise FileNotFoundError(f"白模视频不存在：{source}")

    ffmpeg = _get_ffmpeg()

    output_dir = Path("uploads/previs_frames")
    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = output_dir / f"{uuid.uuid4().hex}_%03d.jpg"

    command = [
        ffmpeg,
        "-y",
        "-i",
        str(source),
        "-vf",
        f"fps=1/{interval_seconds}",
        str(pattern),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg 抽帧失败：{result.stderr[-500:]}")

    frames = sorted(output_dir.glob(f"{pattern.stem.replace('%03d', '*')}.jpg"))
    return [storage.get_url(f"previs_frames/{frame.name}") for frame in frames]


def extract_shot_keyframes(video_url: str, shots: list[dict]) -> list[str]:
    """按镜头区间从白模视频中每个镜头抽 1 帧（取镜头中点）。"""
    if not shots:
        return extract_keyframes(video_url)

    source = _resolve_local_path(video_url)
    if not source.exists():
        raise FileNotFoundError(f"白模视频不存在：{source}")

    ffmpeg = _get_ffmpeg()
    output_dir = Path("uploads/previs_frames")
    output_dir.mkdir(parents=True, exist_ok=True)
    urls: list[str] = []

    for shot in shots:
        start = float(shot.get("start", 0))
        end = float(shot.get("end", start + 1))
        capture_time = start + (end - start) / 2
        output = output_dir / f"{uuid.uuid4().hex}.jpg"
        command = [
            ffmpeg,
            "-y",
            "-ss",
            str(capture_time),
            "-i",
            str(source),
            "-frames:v",
            "1",
            str(output),
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        if result.returncode != 0 or not output.exists():
            raise RuntimeError(f"FFmpeg 镜头抽帧失败：{result.stderr[-500:]}")
        urls.append(storage.get_url(f"previs_frames/{output.name}"))

    return urls


def build_segment_prompt(base_prompt: str, shot: dict | None) -> str:
    """将镜头动作/运镜描述合并到基础提示词中。"""
    if not shot:
        return base_prompt
    action = shot.get("action", "")
    camera = shot.get("camera", "")
    parts = [base_prompt]
    if action:
        parts.append(f"动作：{action}")
    if camera:
        parts.append(f"运镜：{camera}")
    return "；".join(parts)


def build_shot_prompt(
    mapping_rules: dict | None,
    shot: dict,
) -> str:
    """根据映射规则与单个镜头生成提示词。"""
    mapping_text = ""
    if mapping_rules:
        for source, target in mapping_rules.items():
            mapping_text += f"将白模中的{source}映射为{target}；"

    action = shot.get("action", "")
    camera = shot.get("camera", "")
    scene = shot.get("scene", "")
    start = shot.get("start", "0s")
    end = shot.get("end", "5s")

    return (
        f"镜头 {start}-{end}：{action}。"
        f"运镜：{camera}。"
        f"场景：{scene}。"
        f"{mapping_text}"
        "不保留白模材质、轨迹线、坐标线或相机锥体。"
    )


def _parse_scene_json(text: str) -> dict:
    """从 LLM 输出中解析场景 JSON，兼容代码块包裹。"""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        # 尝试提取第一个 { ... } 块
        match = re.search(r"\{.*\}", cleaned, re.S)
        if match is None:
            raise ValueError("LLM 未返回有效的场景 JSON") from exc
        data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("场景 JSON 必须为对象")
    return data


_ALLOWED_OBJECT_TYPES = {"box", "cylinder", "sphere", "plane", "humanoid"}


def _normalize_vec3(value: object, default: list[float]) -> list[float]:
    """规范化三维向量。"""
    if not isinstance(value, list) or len(value) != 3:
        return list(default)
    result: list[float] = []
    for item in value:
        try:
            result.append(float(item))
        except (TypeError, ValueError):
            return list(default)
    return result


def normalize_previs_scene(scene: dict) -> dict:
    """规范化 LLM 生成的白模场景，保证前端可加载。"""
    duration = max(1.0, float(scene.get("duration", 5) or 5))

    objects: list[dict] = []
    used_ids: set[str] = set()
    for index, obj in enumerate(scene.get("objects", []) or []):
        if not isinstance(obj, dict):
            continue
        obj_type = obj.get("type", "box")
        if obj_type not in _ALLOWED_OBJECT_TYPES:
            obj_type = "box"
        obj_id = str(obj.get("id") or f"obj_{index + 1}")
        if obj_id in used_ids:
            obj_id = f"{obj_id}_{index + 1}"
        used_ids.add(obj_id)
        objects.append(
            {
                "id": obj_id,
                "name": str(obj.get("name") or obj_type),
                "type": obj_type,
                "position": _normalize_vec3(obj.get("position"), [0, 0.5, 0]),
                "rotation": _normalize_vec3(obj.get("rotation"), [0, 0, 0]),
                "scale": _normalize_vec3(obj.get("scale"), [1, 1, 1]),
            }
        )

    keyframes: dict[str, list[dict]] = {}
    raw_keyframes = scene.get("keyframes", {}) or {}
    if isinstance(raw_keyframes, dict):
        for obj_id, frames in raw_keyframes.items():
            if not isinstance(frames, list):
                continue
            normalized_frames = []
            for frame in frames:
                if not isinstance(frame, dict):
                    continue
                try:
                    time = float(frame.get("time", 0))
                except (TypeError, ValueError):
                    continue
                normalized_frames.append(
                    {
                        "time": max(0.0, min(duration, time)),
                        "position": _normalize_vec3(frame.get("position"), [0, 0.5, 0]),
                        "rotation": _normalize_vec3(frame.get("rotation"), [0, 0, 0]),
                        "scale": _normalize_vec3(frame.get("scale"), [1, 1, 1]),
                    }
                )
            if normalized_frames:
                keyframes[str(obj_id)] = normalized_frames

    camera_keyframes: list[dict] = []
    for frame in scene.get("cameraKeyframes", []) or []:
        if not isinstance(frame, dict):
            continue
        try:
            time = float(frame.get("time", 0))
        except (TypeError, ValueError):
            continue
        camera_keyframes.append(
            {
                "time": max(0.0, min(duration, time)),
                "position": _normalize_vec3(frame.get("position"), [5, 4, 5]),
                "target": _normalize_vec3(frame.get("target"), [0, 0, 0]),
            }
        )
    if not camera_keyframes:
        camera_keyframes = [{"time": 0, "position": [5, 4, 5], "target": [0, 0, 0]}]

    shot_markers: list[float] = []
    for marker in scene.get("shotMarkers", []) or []:
        try:
            value = float(marker)
        except (TypeError, ValueError):
            continue
        if 0 < value < duration and value not in shot_markers:
            shot_markers.append(value)
    shot_markers.sort()

    shot_descriptions: dict[str, dict] = {}
    raw_descriptions = scene.get("shotDescriptions", {}) or {}
    if isinstance(raw_descriptions, dict):
        for key, description in raw_descriptions.items():
            if not isinstance(description, dict):
                continue
            shot_descriptions[str(key)] = {
                "action": str(description.get("action", "")),
                "camera": str(description.get("camera", "")),
            }

    return {
        "objects": objects,
        "keyframes": keyframes,
        "cameraKeyframes": camera_keyframes,
        "shotMarkers": shot_markers,
        "shotDescriptions": shot_descriptions,
        "duration": duration,
    }


BUILTIN_PREVIS_TEMPLATES = [
    {
        "name": "人物行走模板",
        "description": "灰模人形从画面一侧走到另一侧，适合人物出场镜头",
        "category": "人物",
        "scene_json": {
            "objects": [
                {"id": "obj_1", "name": "灰模人形", "type": "humanoid", "position": [-2, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
                {"id": "obj_2", "name": "地面", "type": "plane", "position": [0, 0, 0], "rotation": [-1.5708, 0, 0], "scale": [5, 5, 5]},
            ],
            "keyframes": {
                "obj_1": [
                    {"time": 0, "position": [-2, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
                    {"time": 4, "position": [2, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
                ]
            },
            "cameraKeyframes": [
                {"time": 0, "position": [5, 3, 5], "target": [0, 0, 0]},
                {"time": 4, "position": [5, 3, 5], "target": [0, 0, 0]},
            ],
            "shotMarkers": [2, 4],
            "shotDescriptions": {"2": {"action": "人物走入画面", "camera": "侧面跟拍"}},
            "duration": 5,
        },
    },
    {
        "name": "产品展示模板",
        "description": "产品居中展示，相机环绕，适合电商/产品镜头",
        "category": "产品",
        "scene_json": {
            "objects": [
                {"id": "obj_1", "name": "圆柱", "type": "cylinder", "position": [0, 0.5, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
                {"id": "obj_2", "name": "展示台", "type": "box", "position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [2, 0.1, 2]},
            ],
            "keyframes": {},
            "cameraKeyframes": [
                {"time": 0, "position": [4, 2, 0], "target": [0, 0.5, 0]},
                {"time": 4, "position": [0, 2, 4], "target": [0, 0.5, 0]},
            ],
            "shotMarkers": [2],
            "shotDescriptions": {"2": {"action": "产品旋转展示", "camera": "环绕"}},
            "duration": 5,
        },
    },
    {
        "name": "双人对话模板",
        "description": "两个灰模人形面对面，适合对话/访谈场景",
        "category": "人物",
        "scene_json": {
            "objects": [
                {"id": "obj_1", "name": "角色A", "type": "humanoid", "position": [-1.2, 0, 0], "rotation": [0, 0.5, 0], "scale": [1, 1, 1]},
                {"id": "obj_2", "name": "角色B", "type": "humanoid", "position": [1.2, 0, 0], "rotation": [0, -0.5, 0], "scale": [1, 1, 1]},
                {"id": "obj_3", "name": "地面", "type": "plane", "position": [0, 0, 0], "rotation": [-1.5708, 0, 0], "scale": [5, 5, 5]},
            ],
            "keyframes": {},
            "cameraKeyframes": [
                {"time": 0, "position": [0, 2, 5], "target": [0, 1, 0]},
            ],
            "shotMarkers": [2, 4],
            "shotDescriptions": {"2": {"action": "角色A说话", "camera": "过肩镜头"}},
            "duration": 5,
        },
    },
    {
        "name": "场景空镜模板",
        "description": "无人空场景，相机缓慢摇移，适合转场/空镜",
        "category": "场景",
        "scene_json": {
            "objects": [
                {"id": "obj_1", "name": "地面", "type": "plane", "position": [0, 0, 0], "rotation": [-1.5708, 0, 0], "scale": [8, 8, 8]},
                {"id": "obj_2", "name": "背景墙", "type": "box", "position": [0, 1, -4], "rotation": [0, 0, 0], "scale": [8, 3, 0.3]},
            ],
            "keyframes": {},
            "cameraKeyframes": [
                {"time": 0, "position": [0, 2, 6], "target": [0, 1, 0]},
                {"time": 4, "position": [4, 2, 4], "target": [0, 1, 0]},
            ],
            "shotMarkers": [2],
            "shotDescriptions": {"2": {"action": "空镜缓慢摇移", "camera": "横摇"}},
            "duration": 5,
        },
    },
    {
        "name": "追逐动作模板",
        "description": "角色快速跑过场景，适合追逐/动作镜头",
        "category": "动作",
        "scene_json": {
            "objects": [
                {"id": "obj_1", "name": "奔跑者", "type": "humanoid", "position": [-3, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
                {"id": "obj_2", "name": "地面", "type": "plane", "position": [0, 0, 0], "rotation": [-1.5708, 0, 0], "scale": [10, 4, 10]},
                {"id": "obj_3", "name": "障碍物", "type": "box", "position": [1, 0.5, 0], "rotation": [0, 0, 0], "scale": [0.5, 1, 0.5]},
            ],
            "keyframes": {
                "obj_1": [
                    {"time": 0, "position": [-3, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
                    {"time": 4, "position": [3, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
                ]
            },
            "cameraKeyframes": [
                {"time": 0, "position": [-2, 2, 4], "target": [-2, 1, 0]},
                {"time": 4, "position": [2, 2, 4], "target": [2, 1, 0]},
            ],
            "shotMarkers": [2, 4],
            "shotDescriptions": {"2": {"action": "角色快速奔跑并越过障碍", "camera": "侧面跟拍"}},
            "duration": 5,
        },
    },
    {
        "name": "多镜头分镜模板",
        "description": "两个角色多镜头切换，适合叙事/剧情场景",
        "category": "多镜头",
        "scene_json": {
            "objects": [
                {"id": "obj_1", "name": "角色A", "type": "humanoid", "position": [-1, 0, 0], "rotation": [0, 0.5, 0], "scale": [1, 1, 1]},
                {"id": "obj_2", "name": "角色B", "type": "humanoid", "position": [1, 0, 0], "rotation": [0, -0.5, 0], "scale": [1, 1, 1]},
                {"id": "obj_3", "name": "地面", "type": "plane", "position": [0, 0, 0], "rotation": [-1.5708, 0, 0], "scale": [6, 6, 6]},
            ],
            "keyframes": {},
            "cameraKeyframes": [
                {"time": 0, "position": [0, 2, 5], "target": [0, 1, 0]},
                {"time": 2, "position": [-2, 2, 3], "target": [-1, 1, 0]},
                {"time": 4, "position": [2, 2, 3], "target": [1, 1, 0]},
            ],
            "shotMarkers": [1, 2, 3, 4],
            "shotDescriptions": {
                "1": {"action": "双人全景", "camera": "中景"},
                "2": {"action": "角色A特写", "camera": "近景"},
                "3": {"action": "角色B特写", "camera": "近景"},
            },
            "duration": 5,
        },
    },
]


def seed_builtin_previs_templates(engine) -> None:
    """按名称幂等写入内置白模模板。"""
    with Session(engine) as db:
        added = False
        for template in BUILTIN_PREVIS_TEMPLATES:
            exists = (
                db.query(PrevisTemplate)
                .filter(PrevisTemplate.is_builtin.is_(True), PrevisTemplate.name == template["name"])
                .first()
            )
            if exists is not None:
                continue
            db.add(
                PrevisTemplate(
                    user_id=None,
                    name=template["name"],
                    description=template["description"],
                    scene_json=template["scene_json"],
                    category=template["category"],
                    is_builtin=True,
                )
            )
            added = True
        if added:
            db.commit()


def generate_previs_scene_from_text(prompt: str) -> dict:
    """根据文案调用 LLM 生成白模场景 JSON。"""
    system_prompt = (
        "你是 3D 白模预演场景生成器。根据用户的视频文案，生成可直接被 Three.js 编辑器加载的场景 JSON。"
        "只输出 JSON，不要解释。JSON 结构如下：\n"
        "{\n"
        '  "objects": [{"id": "obj_1", "name": "方块", "type": "box", "position": [0,0.5,0], "rotation": [0,0,0], "scale": [1,1,1]}],\n'
        '  "keyframes": {},\n'
        '  "cameraKeyframes": [{"time": 0, "position": [5,4,5], "target": [0,0,0]}],\n'
        '  "shotMarkers": [1, 3],\n'
        '  "shotDescriptions": {"1": {"action": "人物走入画面", "camera": "侧面跟拍"}},\n'
        '  "duration": 5\n'
        "}\n"
        "type 只能是 box/cylinder/sphere/plane/humanoid；objects 至少 1 个；duration 建议 5~10。"
    )
    result = registry.get_llm_provider().complete(
        LLMRequest(
            system_prompt=system_prompt,
            user_prompt=f"视频文案：{prompt}",
            temperature=0.4,
            max_tokens=3000,
        )
    )
    scene = _parse_scene_json(result.text)
    return normalize_previs_scene(scene)


def generate_previs_scene_from_video(prompt: str, frame_urls: list[str]) -> dict:
    """根据参考视频关键帧调用多模态 LLM 生成白模场景 JSON。"""
    system_prompt = (
        "你是 3D 白模预演场景生成器。用户会提供参考视频的关键帧图片，"
        "请分析画面中的人物、物体、动作和运镜，生成可直接被 Three.js 编辑器加载的白模场景 JSON。"
        "只输出 JSON，不要解释。JSON 结构如下：\n"
        "{\n"
        '  "objects": [{"id": "obj_1", "name": "灰模人形", "type": "humanoid", "position": [0,0.5,0], "rotation": [0,0,0], "scale": [1,1,1]}],\n'
        '  "keyframes": {},\n'
        '  "cameraKeyframes": [{"time": 0, "position": [5,4,5], "target": [0,0,0]}],\n'
        '  "shotMarkers": [1, 3],\n'
        '  "shotDescriptions": {"1": {"action": "人物走入画面", "camera": "侧面跟拍"}},\n'
        '  "duration": 5\n'
        "}\n"
        "type 只能是 box/cylinder/sphere/plane/humanoid；objects 至少 1 个；duration 建议 5~10。"
    )
    result = registry.get_llm_provider().complete(
        LLMRequest(
            system_prompt=system_prompt,
            user_prompt=f"参考视频描述：{prompt}\n请根据这些关键帧生成白模场景。",
            image_urls=frame_urls,
            temperature=0.4,
            max_tokens=3000,
        )
    )
    scene = _parse_scene_json(result.text)
    return normalize_previs_scene(scene)


def generate_previs_scene_from_video_advanced(prompt: str, frame_urls: list[str]) -> dict:
    """根据参考视频关键帧序列生成带关键帧动画的白模场景（高级版）。

    与 MVP 的区别：不仅识别静态物体，还要求 LLM 按时间顺序输出 humanoid/物体的
    keyframes 和 cameraKeyframes，让白模直接带有动作/运镜动画。
    """
    system_prompt = (
        "你是 3D 白模预演动画师。用户会按时间顺序提供参考视频的关键帧图片，"
        "请分析画面中人物/物体的运动轨迹、姿态变化和运镜，生成带关键帧动画的 Three.js 白模场景 JSON。"
        "只输出 JSON，不要解释。JSON 结构如下：\n"
        "{\n"
        '  "objects": [{"id": "obj_1", "name": "灰模人形", "type": "humanoid", "position": [0,0.5,0], "rotation": [0,0,0], "scale": [1,1,1]}],\n'
        '  "keyframes": {"obj_1": [{"time": 0, "position": [0,0.5,0], "rotation": [0,0,0], "scale": [1,1,1]}, {"time": 4, "position": [2,0.5,0], "rotation": [0,0,0], "scale": [1,1,1]}]},\n'
        '  "cameraKeyframes": [{"time": 0, "position": [5,4,5], "target": [0,0,0]}, {"time": 4, "position": [5,4,5], "target": [2,0,0]}],\n'
        '  "shotMarkers": [2, 4],\n'
        '  "shotDescriptions": {"2": {"action": "人物从左走到右", "camera": "侧面跟拍"}},\n'
        '  "duration": 5\n'
        "}\n"
        "type 只能是 box/cylinder/sphere/plane/humanoid；objects 至少 1 个；"
        "humanoid 必须包含至少 2 个不同时间的 keyframes 来体现动作；duration 建议 5~10。"
    )
    result = registry.get_llm_provider().complete(
        LLMRequest(
            system_prompt=system_prompt,
            user_prompt=f"参考视频描述：{prompt}\n请按关键帧顺序生成带动作动画的白模场景。",
            image_urls=frame_urls,
            temperature=0.3,
            max_tokens=4000,
        )
    )
    scene = _parse_scene_json(result.text)
    return normalize_previs_scene(scene)
