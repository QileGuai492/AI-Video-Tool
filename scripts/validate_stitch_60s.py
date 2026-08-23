"""60 秒拼接验证脚本（容器内执行）。

验证多个视频片段通过 FFmpeg concat 拼接后，成片时长达到 60 秒。

用法：
    docker compose exec api python scripts/validate_stitch_60s.py
"""

import math
import shutil
import subprocess
from pathlib import Path

from app.services.video_stitcher import stitch_videos


def _get_duration(path: Path) -> float:
    """通过 ffprobe 获取视频时长（秒）。"""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return float(result.stdout.strip())


def main() -> None:
    """执行 60 秒拼接验证。"""
    source = Path("app/providers/assets/mock_clip.mp4")
    work_dir = Path(".eval_tmp/stitch_60s")
    if work_dir.exists():
        shutil.rmtree(work_dir)
    segments_dir = work_dir / "segments"
    segments_dir.mkdir(parents=True)

    source_duration = _get_duration(source)
    copies = max(1, math.ceil(60.0 / source_duration))
    segment_paths: list[Path] = []
    for i in range(copies):
        segment = segments_dir / f"segment_{i:02d}.mp4"
        shutil.copyfile(source, segment)
        segment_paths.append(segment)

    output = work_dir / "output_60s.mp4"
    stitch_videos(segment_paths, output)

    output_duration = _get_duration(output)
    print(f"source_duration={source_duration:.3f}s copies={copies} output_duration={output_duration:.3f}s")
    if output_duration < 60:
        raise SystemExit(f"拼接结果不足 60 秒：{output_duration:.3f}s")
    print("60 秒拼接验证通过 ✅")


if __name__ == "__main__":
    main()
