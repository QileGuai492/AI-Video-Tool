"""质量评估服务。

当前为启发式实现，后续可接入视觉语言模型进行真实打分。
"""

from dataclasses import dataclass


@dataclass
class QualityReport:
    """质量评估结果。"""

    score: float
    passed: bool
    reason: str


def evaluate_video(video_url: str | None, threshold: float = 7.5) -> QualityReport:
    """评估视频是否通过质量门槛。"""
    if video_url:
        return QualityReport(score=9.0, passed=9.0 >= threshold, reason="视频已生成")
    return QualityReport(score=0.0, passed=False, reason="尚未生成视频")
