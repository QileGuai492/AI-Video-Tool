"""白模预演服务。

Phase 1 提供：
- 白模视频关键帧抽取（FFmpeg）
- 基于镜头脚本生成提示词
"""

import shutil
import subprocess
import uuid
from pathlib import Path

from app.storage import storage


def _resolve_local_path(video_url: str) -> Path:
    """将 /uploads/ 开头的 URL 解析为本地路径。"""
    if video_url.startswith("/uploads/"):
        return Path("uploads") / video_url.removeprefix("/uploads/")
    raise ValueError("当前仅支持本地 /uploads/ 白模视频抽帧")


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

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        try:
            import imageio_ffmpeg

            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("未找到 FFmpeg，无法抽取关键帧") from exc

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
