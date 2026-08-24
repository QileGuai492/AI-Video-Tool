"""视频拼接服务。

使用 FFmpeg concat 协议将多个片段拼接为一个视频。
如果片段只有一个，直接复制；如果 FFmpeg 不可用或拼接失败，抛出 StitchingError。
"""

import shutil
import subprocess
from pathlib import Path


class StitchingError(Exception):
    """视频拼接失败。"""


def build_concat_file(segment_paths: list[Path], list_file: Path) -> None:
    """生成 FFmpeg concat 所需的文件列表（使用绝对路径）。"""
    lines = [f"file '{path.resolve().as_posix()}'" for path in segment_paths]
    list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _get_ffmpeg_executable() -> str:
    """返回可用的 ffmpeg 可执行文件路径。"""
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def stitch_videos(segment_paths: list[Path], output_path: Path) -> Path:
    """拼接多个视频片段到 output_path。"""
    if not segment_paths:
        raise StitchingError("没有可拼接的视频片段")

    # 单个片段直接复制，避免不必要的转码
    if len(segment_paths) == 1:
        shutil.copyfile(segment_paths[0], output_path)
        return output_path

    list_file = output_path.with_suffix(".txt")
    build_concat_file(segment_paths, list_file)

    command = [
        _get_ffmpeg_executable(),
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-c",
        "copy",
        str(output_path),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
    except FileNotFoundError as exc:
        raise StitchingError("未找到 ffmpeg，请先安装 FFmpeg") from exc

    if result.returncode != 0:
        raise StitchingError(f"FFmpeg 拼接失败：{(result.stderr or '')[-500:]}")

    return output_path


def merge_audio(video_path: Path, audio_path: Path, output_path: Path) -> Path:
    """把外部音频（TTS/配音）替换进视频，替换原视频音轨。"""
    ffmpeg = _get_ffmpeg_executable()
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path.resolve()),
        "-i",
        str(audio_path.resolve()),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
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
        raise StitchingError("未找到 ffmpeg，请先安装 FFmpeg") from exc

    if result.returncode != 0:
        raise StitchingError(f"FFmpeg 音频合成失败：{(result.stderr or '')[-500:]}")

    return output_path


def burn_subtitle(video_path: Path, srt_path: Path, output_path: Path) -> Path:
    """把 SRT 字幕烧录到视频中。

    通过把工作目录设为字幕所在目录并使用相对文件名，规避 Windows 路径冒号/中文路径问题。
    """
    ffmpeg = _get_ffmpeg_executable()
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path.resolve()),
        "-vf",
        f"subtitles=filename={srt_path.name}:charenc=utf-8:force_style='FontName=Noto Sans CJK SC'",
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        str(output_path.resolve()),
    ]
    try:
        result = subprocess.run(
            command,
            cwd=srt_path.parent,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
    except FileNotFoundError as exc:
        raise StitchingError("未找到 ffmpeg，请先安装 FFmpeg") from exc

    if result.returncode != 0:
        raise StitchingError(f"FFmpeg 字幕烧录失败：{(result.stderr or '')[-500:]}")

    return output_path
