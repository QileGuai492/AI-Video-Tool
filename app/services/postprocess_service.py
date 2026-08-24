"""视频后处理服务。

提供可选的后处理能力：
- 超分/放大：通过 FFmpeg 缩放到目标分辨率，并可选锐化。
- 插帧：通过 FFmpeg minterpolate 做运动插帧，提升流畅度。

后续可替换为 Real-ESRGAN / RIFE 等更高质量的外部工具，接口保持不变。
"""

import shutil
import subprocess
from pathlib import Path

from app.core.config import get_settings
from app.services.video_stitcher import _get_ffmpeg_executable

# 目标分辨率 -> 目标高度（宽高比保持不变）
_TARGET_HEIGHTS = {
    "720p": 720,
    "1080p": 1080,
    "2160p": 2160,
}


class PostProcessError(Exception):
    """视频后处理失败。"""


def _get_video_fps(video_path: Path) -> float:
    """使用 ffprobe 获取视频帧率；失败时返回 24.0。"""
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        return 24.0
    command = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=avg_frame_rate",
        "-of",
        "csv=p=0",
        str(video_path.resolve()),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if result.returncode != 0:
            return 24.0
        numerator, _, denominator = result.stdout.strip().partition("/")
        fps = float(numerator) / float(denominator) if denominator else float(numerator)
        return fps if fps > 0 else 24.0
    except Exception:  # noqa: BLE001
        return 24.0


def _find_tool(*names: str) -> str | None:
    """在 PATH 中查找外部工具。"""
    for name in names:
        path = shutil.which(name)
        if path:
            return path
    return None


def _try_realesrgan(video_path: Path, output_path: Path) -> Path | None:
    """尝试使用 Real-ESRGAN 超分；不可用或失败时返回 None。"""
    tool = _find_tool("realesrgan-ncnn-vulkan", "realesrgan")
    if tool is None:
        return None
    command = [
        tool,
        "-i",
        str(video_path.resolve()),
        "-o",
        str(output_path.resolve()),
        "-s",
        "2",
        "-n",
        "realesrgan-x4plus",
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
    except Exception:  # noqa: BLE001
        return None
    if result.returncode != 0 or not output_path.exists():
        return None
    return output_path


def _try_rife(video_path: Path, output_path: Path, factor: int) -> Path | None:
    """尝试使用 RIFE 插帧；不可用或失败时返回 None。"""
    tool = _find_tool("rife-ncnn-vulkan", "rife")
    if tool is None:
        return None
    command = [
        tool,
        "-i",
        str(video_path.resolve()),
        "-o",
        str(output_path.resolve()),
        "-s",
        str(factor),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900,
        )
    except Exception:  # noqa: BLE001
        return None
    if result.returncode != 0 or not output_path.exists():
        return None
    return output_path


def enhance_video(video_path: Path, output_path: Path, target_resolution: str = "1080p", sharpen: bool = True) -> Path:
    """超分/放大视频到目标分辨率，可选锐化。

    优先使用 Real-ESRGAN；不可用时回退 FFmpeg scale + unsharp。
    """
    external = _try_realesrgan(video_path, output_path)
    if external is not None:
        return external

    ffmpeg = _get_ffmpeg_executable()
    height = _TARGET_HEIGHTS.get(target_resolution, 1080)
    vf = f"scale=-2:{height}"
    if sharpen:
        vf += ",unsharp=5:5:0.6:5:5:0.0"
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path.resolve()),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        str(output_path.resolve()),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
    except FileNotFoundError as exc:
        raise PostProcessError("未找到 ffmpeg，请先安装 FFmpeg") from exc

    if result.returncode != 0 or not output_path.exists():
        raise PostProcessError(f"FFmpeg 超分失败：{(result.stderr or '')[-500:]}")

    return output_path


def interpolate_frames(video_path: Path, output_path: Path, factor: int = 2) -> Path:
    """使用 RIFE（若可用）或 FFmpeg minterpolate 做运动插帧。"""
    if factor <= 1:
        shutil.copyfile(video_path, output_path)
        return output_path

    external = _try_rife(video_path, output_path, factor)
    if external is not None:
        return external

    ffmpeg = _get_ffmpeg_executable()
    source_fps = _get_video_fps(video_path)
    target_fps = max(24, int(round(source_fps * factor)))
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path.resolve()),
        "-vf",
        f"minterpolate=fps={target_fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        str(output_path.resolve()),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900,
        )
    except FileNotFoundError as exc:
        raise PostProcessError("未找到 ffmpeg，请先安装 FFmpeg") from exc

    if result.returncode != 0 or not output_path.exists():
        raise PostProcessError(f"FFmpeg 插帧失败：{(result.stderr or '')[-500:]}")

    return output_path


def postprocess_video(video_path: Path, output_path: Path) -> Path:
    """按全局配置执行完整后处理：先插帧，再超分/锐化。"""
    settings = get_settings()
    current = video_path
    tmp_dir = output_path.parent

    if settings.video_interpolate_factor > 1:
        interpolated = tmp_dir / f"interpolated_{output_path.stem}.mp4"
        try:
            interpolate_frames(current, interpolated, settings.video_interpolate_factor)
            current = interpolated
        except PostProcessError:
            # 插帧失败不阻断，继续超分
            current = video_path

    try:
        enhance_video(
            current,
            output_path,
            target_resolution=settings.video_target_resolution,
            sharpen=settings.video_sharpen,
        )
    finally:
        if current != video_path:
            current.unlink(missing_ok=True)

    return output_path
