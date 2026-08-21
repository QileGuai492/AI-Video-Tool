"""可选的 LLM-as-Judge 评测器。

仅在配置了真实 SiliconFlow Key 时启用，用于对文本类输出做主观质量打分。
默认 Mock 模式下不启用，避免产生额外费用。
"""

import re

from app.core.config import get_settings
from app.providers.base import LLMRequest
from app.providers.siliconflow import SiliconFlowLLMProvider


class LLMJudge:
    """基于 LLM 的评测裁判。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._provider = SiliconFlowLLMProvider() if self.settings.siliconflow_api_key else None

    @property
    def available(self) -> bool:
        """是否可执行 LLM 评测。"""
        return self._provider is not None

    def score(self, text: str, criteria: str) -> float | None:
        """对文本按 criteria 打分，返回 0~1；不可用时返回 None。"""
        if not self.available or not text:
            return None

        result = self._provider.complete(
            LLMRequest(
                system_prompt=(
                    "你是一个严格的评测裁判。请只输出一个 0 到 100 之间的整数分数，"
                    "不要输出解释。分数越高表示越符合评测标准。"
                ),
                user_prompt=f"评测标准：{criteria}\n\n待评测文本：\n{text}",
                max_tokens=10,
                temperature=0,
            )
        )
        match = re.search(r"(\d{1,3})", result.text or "")
        if not match:
            return None
        return max(0.0, min(1.0, int(match.group(1)) / 100.0))
