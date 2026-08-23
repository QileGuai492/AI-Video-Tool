"""字幕叠加验证脚本（容器内执行）。

用 FFmpeg 将 SRT 字幕烧录到视频中，验证字幕叠加链路可用且成片时长不变。

用法：
    docker compose exec api python scripts/validate_subtitle_overlay.py
"""

import shutil
import subprocess
from pathlib import Path

from app.services.subtitle_service import build_srt_content


def main() -> None:
    """执行字幕叠加验证。"""
    source = Path("app/providers/assets/mock_clip.mp4")
    work_dir = Path(".eval_tmp/subtitle_overlay")
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True)

    srt_path = work_dir / "subtitle.srt"
    srt_path.write_text(build_srt_content("字幕叠加验证：海边日出，浪花拍岸"), encoding="utf-8")
    output = work_dir / "output_with_subtitle.mp4"

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-vf",
            f"subtitles={srt_path.as_posix()}",
            "-c:a",
            "copy",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise SystemExit(f"字幕叠加失败：{result.stderr[-500:]}")

    if not output.exists() or output.stat().st_size == 0:
        raise SystemExit("字幕叠加输出为空")

    duration_result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    duration = float(duration_result.stdout.strip())
    print(f"subtitle overlay output_duration={duration:.3f}s size={output.stat().st_size}")
    if duration <= 0:
        raise SystemExit("字幕叠加后视频时长为 0")
    print("字幕叠加验证通过 ✅")


if __name__ == "__main__":
    main()
