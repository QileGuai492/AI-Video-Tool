"""音频服务。"""

import io
import math
import struct
import wave

from sqlalchemy.orm import Session

from app.models import AudioTrack, BgmLibrary
from app.providers.base import TTSRequest
from app.providers.registry import registry
from app.storage import storage


def generate_tts_audio(
    db: Session,
    user_id: int,
    task_id: int | None,
    text: str,
    voice_id: str = "female_01",
) -> AudioTrack:
    """生成 TTS 音频并保存记录。"""
    provider = registry.get_tts_provider()
    result = provider.synthesize(TTSRequest(text=text, voice_id=voice_id))

    track = AudioTrack(
        task_id=task_id,
        type="tts",
        source_url=result.audio_url,
        text_content=text,
        voice_id=voice_id,
    )
    db.add(track)
    db.commit()
    db.refresh(track)
    return track


def _generate_simple_bgm_wav() -> bytes:
    """生成一段内置轻音乐 WAV（无外部依赖，可用于空曲库兜底）。"""
    sample_rate = 22050
    duration = 8.0
    amplitude = 0.22
    chords = [
        [261.63, 329.63, 392.00],  # C
        [220.00, 261.63, 329.63],  # Am
        [174.61, 220.00, 261.63],  # F
        [196.00, 246.94, 293.66],  # G
    ]
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        total_frames = int(sample_rate * duration)
        for i in range(total_frames):
            t = i / sample_rate
            chord = chords[int(t / 2.0) % len(chords)]
            value = sum(math.sin(2.0 * math.pi * freq * t) for freq in chord) / len(chord)
            sample = int(max(-1.0, min(1.0, value * amplitude)) * 32767)
            wav.writeframes(struct.pack("<h", sample))
    return buffer.getvalue()


def generate_bgm_audio(
    db: Session,
    user_id: int,
    task_id: int | None,
    bgm_id: int | None = None,
) -> AudioTrack:
    """生成 BGM 推荐并保存记录。"""
    bgm = None
    if bgm_id is not None:
        bgm = db.query(BgmLibrary).filter(BgmLibrary.id == bgm_id).first()
    if bgm is None:
        bgm = db.query(BgmLibrary).first()

    if bgm is not None:
        source_url = bgm.url
    else:
        content = _generate_simple_bgm_wav()
        key = storage.upload(content=content, suffix="wav", folder="audio")
        source_url = storage.get_url(key)

    track = AudioTrack(
        task_id=task_id,
        type="bgm",
        source_url=source_url,
    )
    db.add(track)
    db.commit()
    db.refresh(track)
    return track
