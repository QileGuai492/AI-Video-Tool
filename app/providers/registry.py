"""Provider 注册与选择。"""

from app.core.config import get_settings
from app.providers.base import (
    ImageProvider,
    LLMProvider,
    TTSProvider,
    VideoProvider,
)
from app.providers.mock import (
    MockImageProvider,
    MockLLMProvider,
    MockTTSProvider,
    MockVideoProvider,
)


class ProviderRegistry:
    """Provider 注册表，支持 Mock 与真实厂商。"""

    def __init__(self) -> None:
        self.image_providers: dict[str, ImageProvider] = {}
        self.video_providers: dict[str, VideoProvider] = {}
        self.tts_providers: dict[str, TTSProvider] = {}
        self.llm_providers: dict[str, LLMProvider] = {}

    def register_mock_providers(self) -> None:
        """注册 Mock Provider，便于本地开发。"""
        self.image_providers["mock"] = MockImageProvider()
        self.video_providers["mock"] = MockVideoProvider()
        self.tts_providers["mock"] = MockTTSProvider()
        self.llm_providers["mock"] = MockLLMProvider()

    def register_real_providers(self) -> None:
        """根据环境变量注册真实 Provider，未配置 Key 时跳过。"""
        settings = get_settings()

        if settings.agnes_api_key:
            from app.providers.agnes import (
                AgnesImageProvider,
                AgnesLLMProvider,
                AgnesVideoProvider,
            )

            self.llm_providers["agnes"] = AgnesLLMProvider()
            self.image_providers["agnes"] = AgnesImageProvider()
            self.video_providers["agnes"] = AgnesVideoProvider()

        # Edge TTS 免费可用，无需 Key，作为默认真实 TTS Provider
        from app.providers.edge_tts import EdgeTTSProvider

        self.tts_providers["edge_tts"] = EdgeTTSProvider()

        if settings.siliconflow_api_key:
            from app.providers.siliconflow import (
                SiliconFlowImageProvider,
                SiliconFlowLLMProvider,
                SiliconFlowTTSProvider,
                SiliconFlowVideoProvider,
            )

            self.llm_providers["siliconflow"] = SiliconFlowLLMProvider()
            self.image_providers["siliconflow"] = SiliconFlowImageProvider()
            self.video_providers["siliconflow"] = SiliconFlowVideoProvider()
            self.tts_providers["siliconflow"] = SiliconFlowTTSProvider()

        if settings.claude_api_key:
            from app.providers.claude import ClaudeLLMProvider

            self.llm_providers["claude"] = ClaudeLLMProvider()

        if settings.tongyi_api_key:
            from app.providers.tongyi import TongyiImageProvider

            self.image_providers["tongyi"] = TongyiImageProvider()

        if settings.minimax_api_key:
            from app.providers.minimax import MiniMaxVideoProvider

            self.video_providers["minimax"] = MiniMaxVideoProvider()

    def get_image_provider(self, name: str | None = None) -> ImageProvider:
        """获取文生图 Provider；未指定时优先使用真实 Provider，否则回退 Mock。"""
        return self._resolve(self.image_providers, name)

    def get_video_provider(self, name: str | None = None) -> VideoProvider:
        """获取视频生成 Provider；未指定时优先使用真实 Provider，否则回退 Mock。"""
        return self._resolve(self.video_providers, name)

    def get_tts_provider(self, name: str | None = None) -> TTSProvider:
        """获取 TTS Provider；未指定时优先使用真实 Provider，否则回退 Mock。"""
        return self._resolve(self.tts_providers, name)

    def get_llm_provider(self, name: str | None = None) -> LLMProvider:
        """获取 LLM Provider；未指定时优先使用真实 Provider，否则回退 Mock。"""
        return self._resolve(self.llm_providers, name)

    def _resolve(self, providers: dict[str, object], name: str | None) -> object:
        """按名称或默认优先级选择 Provider。"""
        if name and name in providers:
            return providers[name]

        # 优先返回第一个非 mock 的真实 Provider
        for provider_name, provider in providers.items():
            if provider_name != "mock":
                return provider

        return providers["mock"]


# 全局 Provider 注册表
registry = ProviderRegistry()
registry.register_mock_providers()
registry.register_real_providers()
