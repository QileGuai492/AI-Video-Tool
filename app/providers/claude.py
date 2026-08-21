"""Claude LLM Provider。

调用 Anthropic Messages API 进行提示词优化 / 台词生成。
"""

from decimal import Decimal

import httpx

from app.core.config import get_settings
from app.providers.base import LLMRequest, LLMResult


class ClaudeLLMProvider:
    """Claude 大模型 Provider。"""

    name = "claude"

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.claude_api_key or ""
        self.model = "claude-3-5-sonnet-20240620"
        self.endpoint = "https://api.anthropic.com/v1/messages"

    def complete(self, request: LLMRequest) -> LLMResult:
        """调用 Claude 生成文本。"""
        if not self.api_key:
            raise RuntimeError("未配置 CLAUDE_API_KEY")

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "system": request.system_prompt,
            "messages": [{"role": "user", "content": request.user_prompt}],
        }

        response = httpx.post(self.endpoint, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        text = "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        )

        return LLMResult(
            text=text,
            provider=self.name,
            cost=Decimal("0"),
            raw_response=data,
        )
