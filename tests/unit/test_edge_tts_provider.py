"""Edge TTS Provider 单元测试。"""

from decimal import Decimal

from app.providers.base import TTSRequest
from app.providers.edge_tts import EdgeTTSProvider


class FakeCommunicate:
    """模拟 edge_tts.Communicate。"""

    def __init__(self, text: str, voice: str, rate: str) -> None:
        self.text = text
        self.voice = voice
        self.rate = rate

    async def save(self, path: str) -> None:
        """写入模拟音频字节。"""
        with open(path, "wb") as f:
            f.write(b"fake-mp3-bytes")


class FakeStorage:
    """模拟存储层。"""

    def __init__(self) -> None:
        self.uploaded: tuple[bytes, str, str] | None = None

    def upload(self, content: bytes, suffix: str, folder: str) -> str:
        self.uploaded = (content, suffix, folder)
        return f"{folder}/abc.mp3"

    def get_url(self, key: str) -> str:
        return f"/uploads/{key}"


def test_edge_tts_synthesize_uses_mapped_voice(monkeypatch) -> None:
    """应使用中文女声别名并上传生成的音频。"""
    provider = EdgeTTSProvider()
    fake_storage = FakeStorage()
    monkeypatch.setattr("app.providers.edge_tts.storage", fake_storage)
    monkeypatch.setattr(
        "app.providers.edge_tts.edge_tts.Communicate",
        FakeCommunicate,
    )

    result = provider.synthesize(TTSRequest(text="你好", voice_id="female_01"))

    assert result.provider == "edge_tts"
    assert result.audio_url == "/uploads/audio/abc.mp3"
    assert result.cost == Decimal("0")
    assert fake_storage.uploaded is not None
    assert fake_storage.uploaded[0] == b"fake-mp3-bytes"
    assert fake_storage.uploaded[1] == "mp3"
    assert fake_storage.uploaded[2] == "audio"


def test_edge_tts_custom_voice_and_rate(monkeypatch) -> None:
    """自定义音色与语速应原样传递。"""
    provider = EdgeTTSProvider()
    fake_storage = FakeStorage()
    monkeypatch.setattr("app.providers.edge_tts.storage", fake_storage)
    monkeypatch.setattr(
        "app.providers.edge_tts.edge_tts.Communicate",
        FakeCommunicate,
    )
    captured: dict = {}

    original_communicate = FakeCommunicate

    class CapturingCommunicate(original_communicate):
        def __init__(self, text: str, voice: str, rate: str) -> None:
            super().__init__(text, voice, rate)
            captured["voice"] = voice
            captured["rate"] = rate

    monkeypatch.setattr(
        "app.providers.edge_tts.edge_tts.Communicate",
        CapturingCommunicate,
    )

    provider.synthesize(TTSRequest(text="测试", voice_id="en-US-AriaNeural", speed=1.2))

    assert captured["voice"] == "en-US-AriaNeural"
    assert captured["rate"] == "+20%"
