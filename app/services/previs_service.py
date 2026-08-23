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
    """将 WebM 转换为 MP4（H.264 + yuv420p）。"""
    ffmpeg = _get_ffmpeg()
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(source),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg 转 MP4 失败：{result.stderr[-500:]}")
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
    result = subprocess.run(command, capture_output=True, text=True, timeout=300)
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
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
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
    scene.setdefault("objects", [])
    scene.setdefault("keyframes", {})
    scene.setdefault("cameraKeyframes", [{"time": 0, "position": [5, 4, 5], "target": [0, 0, 0]}])
    scene.setdefault("shotMarkers", [])
    scene.setdefault("shotDescriptions", {})
    scene.setdefault("duration", 5)
    return scene
