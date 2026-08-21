"""音频服务。"""

from sqlalchemy.orm import Session

from app.models import AudioTrack, BgmLibrary
from app.providers.base import TTSRequest
from app.providers.registry import registry


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

    source_url = bgm.url if bgm is not None else "https://mock.local/audio/bgm.mp3"
    track = AudioTrack(
        task_id=task_id,
        type="bgm",
        source_url=source_url,
    )
    db.add(track)
    db.commit()
    db.refresh(track)
    return track
