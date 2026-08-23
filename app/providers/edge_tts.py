"""Edge TTS Provider（免费，无需 API Key）。

使用 Microsoft Edge 在线语音合成，适合个人创作者低成本接入真实 TTS。
"""

import asyncio
import tempfile
import time
from decimal import Decimal
from pathlib import Path

import edge_tts

from app.providers.base import TTSRequest, TTSResult
from app.storage import storage


class EdgeTTSProvider:
    """基于 edge-tts 的免费 TTS Provider。"""

    name = "edge_tts"

    _VOICE_ALIASES = {
        "female_01": "zh-CN-XiaoxiaoNeural",
        "female_02": "zh-CN-XiaoyiNeural",
        "male_01": "zh-CN-YunxiNeural",
        "male_02": "zh-CN-YunyangNeural",
    }

    def synthesize(self, request: TTSRequest) -> TTSResult:
        """合成语音并上传到存储层。"""
        voice = self._VOICE_ALIASES.get(request.voice_id, request.voice_id)
        output_path = Path(tempfile.gettempdir()) / f"edge_tts_{time.time()}.mp3"
        rate = f"{round((request.speed - 1) * 100):+d}%"

        async def _generate() -> None:
            communicate = edge_tts.Communicate(request.text, voice=voice, rate=rate)
            await communicate.save(str(output_path))

        asyncio.run(_generate())

        try:
            content = output_path.read_bytes()
            key = storage.upload(content=content, suffix="mp3", folder="audio")
            audio_url = storage.get_url(key)
            return TTSResult(
                audio_url=audio_url,
                provider=self.name,
                cost=Decimal("0"),
                raw_response={"voice": voice},
            )
        finally:
            output_path.unlink(missing_ok=True)
