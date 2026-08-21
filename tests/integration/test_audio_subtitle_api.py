"""音频与字幕接口集成测试。"""


def test_generate_tts_audio(client, auth_headers) -> None:
    """TTS 音频接口应返回音频记录。"""
    response = client.post(
        "/api/v1/generate/audio",
        headers=auth_headers,
        json={
            "type": "tts",
            "text": "这是一段测试配音。",
            "voice_id": "female_01",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "tts"
    assert data["source_url"]


def test_generate_bgm_audio(client, auth_headers) -> None:
    """BGM 音频接口应返回音频记录。"""
    response = client.post(
        "/api/v1/generate/audio",
        headers=auth_headers,
        json={"type": "bgm"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "bgm"
    assert data["source_url"]


def test_generate_subtitle(client, auth_headers) -> None:
    """字幕接口应返回 SRT 文件 URL 和内容。"""
    response = client.post(
        "/api/v1/generate/subtitle",
        headers=auth_headers,
        json={"text": "一只猫在雨天奔跑"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["subtitle_url"]
    assert "一只猫在雨天奔跑" in data["content"]
