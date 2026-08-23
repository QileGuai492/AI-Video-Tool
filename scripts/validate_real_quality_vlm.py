"""真实 VLM 质量评估验证脚本（容器内执行）。

使用 Agnes 视觉语言模型对视频首帧进行真实打分，验证 QualityCheckAgent 的 VLM 链路。

用法：
    docker compose exec api python scripts/validate_real_quality_vlm.py
"""

import os
import shutil
from pathlib import Path

os.environ["APP_ENV"] = "local"

from app.services.quality_service import evaluate_video_with_vlm  # noqa: E402


def main() -> None:
    """执行真实 VLM 质量评估。"""
    Path("uploads/videos").mkdir(parents=True, exist_ok=True)
    shutil.copyfile("app/providers/assets/mock_clip.mp4", "uploads/videos/quality_vlm.mp4")

    report = evaluate_video_with_vlm(
        "/uploads/videos/quality_vlm.mp4",
        threshold=7.5,
        duration=1,
    )
    print("score", report.score)
    print("passed", report.passed)
    print("reason", report.reason)
    print("dimensions", report.dimensions)

    if "vlm" not in (report.dimensions or {}):
        raise SystemExit("VLM 评分未生效")
    print("真实 VLM 质量评估验证通过 ✅")


if __name__ == "__main__":
    main()
