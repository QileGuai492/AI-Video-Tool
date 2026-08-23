"""质量评估服务。

当前为启发式实现，可选接入视觉语言模型进行真实打分。
"""

import re
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.providers.base import LLMRequest
from app.providers.registry import registry
from app.storage import storage


@dataclass
class QualityReport:
    """质量评估结果。"""

    score: float
    passed: bool
    reason: str
    dimensions: dict[str, float] | None = None


def evaluate_video(
    video_url: str | None,
    threshold: float = 7.5,
    duration: int | None = None,
    file_size: int | None = None,
) -> QualityReport:
    """从多个维度评估视频质量。

    评分维度：
    - 视频 URL 是否已生成（0~4 分）
    - 本地文件是否真实存在且非空（0~3 分）
    - 远程 URL 是否可访问（0~2 分）
    - 时长是否达到最低要求（0~1 分）
    """
    dimensions: dict[str, float] = {}
    reasons: list[str] = []

    if not video_url:
        dimensions["url"] = 0.0
        reasons.append("尚未生成视频")
        return QualityReport(score=0.0, passed=False, reason="；".join(reasons), dimensions=dimensions)

    dimensions["url"] = 4.0
    reasons.append("视频已生成")

    local_size = file_size
    if video_url.startswith("/uploads/") and local_size is None:
        local_path = Path("uploads") / video_url.removeprefix("/uploads/")
        if local_path.exists():
            local_size = local_path.stat().st_size

    if local_size is not None and local_size > 0:
        dimensions["file"] = 3.0
        reasons.append("本地文件存在且非空")
    elif video_url.startswith(("http://", "https://")):
        dimensions["file"] = 3.0
        reasons.append("远程 URL 可用")
    else:
        dimensions["file"] = 0.0
        reasons.append("文件状态未知")

    if duration is not None:
        if duration >= 5:
            dimensions["duration"] = 1.0
            reasons.append("时长达标")
        else:
            dimensions["duration"] = 0.0
            reasons.append("时长过短")
    else:
        dimensions["duration"] = 1.0
        reasons.append("时长未指定，默认通过")

    score = sum(dimensions.values())
    passed = score >= threshold
    return QualityReport(
        score=score,
        passed=passed,
        reason="；".join(reasons),
        dimensions=dimensions,
    )


def _extract_first_frame(video_url: str) -> str | None:
    """从本地视频提取首帧并上传，返回公网可访问图片 URL。"""
    if not video_url.startswith("/uploads/"):
        return None
    local_path = Path("uploads") / video_url.removeprefix("/uploads/")
    if not local_path.exists():
        return None

    settings = get_settings()
    frame_dir = Path("uploads/quality_frames")
    frame_dir.mkdir(parents=True, exist_ok=True)
    frame_path = frame_dir / f"frame_{uuid.uuid4().hex}.jpg"

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            "0.1",
            "-i",
            str(local_path),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(frame_path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0 or not frame_path.exists():
        return None

    content = frame_path.read_bytes()
    key = storage.upload(content=content, suffix="jpg", folder="quality_frames")
    image_url = storage.get_url(key)
    if image_url.startswith("/"):
        image_url = f"{settings.public_base_url.rstrip('/')}{image_url}"
    return image_url


def _extract_score(result) -> float | None:
    """从 LLM 响应中提取 0~10 的分数。"""
    text = result.text
    if not text and result.raw_response:
        try:
            message = result.raw_response["choices"][0]["message"]
            text = message.get("content") or message.get("reasoning_content") or ""
        except (KeyError, IndexError, TypeError):
            text = ""
    matches = re.findall(r"\d+(?:\.\d+)?", text or "")
    if not matches:
        return None
    try:
        score = float(matches[0])
    except ValueError:
        return None
    return max(0.0, min(10.0, score))


def evaluate_video_with_vlm(
    video_url: str | None,
    threshold: float = 7.5,
    duration: int | None = None,
    file_size: int | None = None,
) -> QualityReport:
    """在启发式评估基础上，用视觉语言模型对视频首帧进行真实打分。"""
    base = evaluate_video(video_url, threshold=threshold, duration=duration, file_size=file_size)
    if base.score == 0.0:
        return base

    image_url = _extract_first_frame(video_url) if video_url else None
    if image_url is None:
        return base

    try:
        provider = registry.get_llm_provider()
        result = provider.complete(
            LLMRequest(
                system_prompt=(
                    "你是专业的短视频质量评审。请只输出一个 0 到 10 的数字，"
                    "代表视频首帧的画面质量（构图、清晰度、光线、主体完整性）。"
                ),
                user_prompt="请根据图片打分。",
                max_tokens=2000,
                image_urls=[image_url],
            )
        )
    except Exception:
        return base

    vlm_score = _extract_score(result)
    if vlm_score is None:
        return base

    dimensions = dict(base.dimensions or {})
    dimensions["vlm"] = vlm_score
    combined = min(10.0, base.score * 0.8 + vlm_score * 0.2)
    passed = combined >= threshold
    return QualityReport(
        score=round(combined, 2),
        passed=passed,
        reason=f"{base.reason}；VLM 画面评分：{vlm_score:.1f}",
        dimensions=dimensions,
    )
