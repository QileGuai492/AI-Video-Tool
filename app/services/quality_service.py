"""质量评估服务。

当前为启发式实现，后续可接入视觉语言模型进行真实打分。
"""

from dataclasses import dataclass
from pathlib import Path


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
