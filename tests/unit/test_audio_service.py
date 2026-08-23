"""音频服务单元测试。"""

import io
import wave

from app.services.audio_service import _generate_simple_bgm_wav


def test_generate_simple_bgm_wav_returns_valid_wav() -> None:
    """内置 BGM 应生成可解析的 WAV 音频数据。"""
    content = _generate_simple_bgm_wav()
    assert content.startswith(b"RIFF")
    assert content[8:12] == b"WAVE"

    with wave.open(io.BytesIO(content), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 22050
        assert wav.getnframes() > 0
