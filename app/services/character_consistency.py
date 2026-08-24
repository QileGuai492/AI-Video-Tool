"""角色一致性检查服务。

可选能力：生成成片后抽取首/中/尾帧，与角色参考图一起交给支持图片的 LLM，
让模型给出 0~10 的一致性分数。默认关闭，避免额外成本。

当前实现为“检查并告警”，不自动重试。
"""

import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.providers.base import LLMRequest
from app.providers.registry import registry
from app.services.video_stitcher import extract_frame_at, extract_last_frame
from app.storage import storage


@dataclass
class ConsistencyReport:
    """角色一致性检查结果。"""

    score: float
    passed: bool
    reason: str


def _to_public_url(url: str) -> str:
    """把本地相对 URL 转为公网可访问 URL。"""
    if url.startswith("/"):
        return f"{get_settings().public_base_url.rstrip('/')}{url}"
    return url


def _extract_score(text: str | None) -> float | None:
    """从 LLM 输出中提取 0~1 的分数。"""
    if not text:
        return None
    matches = re.findall(r"\d+(?:\.\d+)?", text)
    if not matches:
        return None
    try:
        score = float(matches[0])
    except ValueError:
        return None
    return max(0.0, min(1.0, score / 10.0))


def evaluate_character_consistency(
    reference_image_urls: list[str],
    video_url: str,
) -> ConsistencyReport | None:
    """检查成片与参考图的角色一致性；无法执行时返回 None。"""
    if not reference_image_urls or not video_url.startswith("/uploads/"):
        return None

    settings = get_settings()
    if not settings.character_consistency_check_enabled:
        return None

    local_video = Path("uploads") / video_url.removeprefix("/uploads/")
    if not local_video.exists():
        return None

    frame_dir = Path("uploads/consistency_frames")
    frame_dir.mkdir(parents=True, exist_ok=True)
    frame_paths: list[Path] = []
    try:
        # 抽取首、中、尾三帧
        first = frame_dir / f"first_{uuid.uuid4().hex}.jpg"
        extract_frame_at(local_video, first, timestamp=0.1)
        frame_paths.append(first)

        mid = frame_dir / f"mid_{uuid.uuid4().hex}.jpg"
        extract_frame_at(local_video, mid, timestamp=2.5)
        frame_paths.append(mid)

        last = frame_dir / f"last_{uuid.uuid4().hex}.jpg"
        extract_last_frame(local_video, last)
        frame_paths.append(last)

        frame_urls = []
        for frame_path in frame_paths:
            key = storage.upload(content=frame_path.read_bytes(), suffix="jpg", folder="consistency_frames")
            frame_urls.append(_to_public_url(storage.get_url(key)))

        try:
            provider = registry.get_llm_provider()
            result = provider.complete(
                LLMRequest(
                    system_prompt=(
                        "你是严格的角色一致性评审。请只输出一个 0 到 10 的整数分数，"
                        "表示视频中的人物与参考图是否为同一角色。不要输出解释。"
                    ),
                    user_prompt="请对比参考图与视频帧，输出一致性分数。",
                    max_tokens=2000,
                    image_urls=[_to_public_url(url) for url in reference_image_urls] + frame_urls,
                )
            )
        except Exception:  # noqa: BLE001
            return None

        score = _extract_score(result.text if hasattr(result, "text") else None)
        if score is None:
            return None

        passed = score >= settings.character_consistency_threshold
        return ConsistencyReport(
            score=score,
            passed=passed,
            reason=f"角色一致性得分：{score:.2f}",
        )
    except Exception:  # noqa: BLE001
        return None
    finally:
        for frame_path in frame_paths:
            frame_path.unlink(missing_ok=True)
