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
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)
    except FileNotFoundError as exc:
        raise StitchingError("未找到 ffmpeg，请先安装 FFmpeg") from exc

    if result.returncode != 0:
        raise StitchingError(f"FFmpeg 拼接失败：{result.stderr[-500:]}")

    return output_path
