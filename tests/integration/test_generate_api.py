"""视频生成接口集成测试。

依赖 Celery eager 模式（本地配置），任务会同步执行。
"""


def test_submit_and_query_task(client, auth_headers) -> None:
    """提交任务后可以查询状态。"""
    submit_response = client.post(
        "/api/v1/generate/video",
        headers=auth_headers,
        json={
            "prompt": "一只猫在雨天奔跑",
            "duration": 5,
            "aspect_ratio": "16:9",
            "quality": "standard",
        },
    )
    assert submit_response.status_code == 200
    task = submit_response.json()
    assert task["id"] > 0
    assert task["status"] in {"pending", "completed"}

    status_response = client.get(
        f"/api/v1/generate/status/{task['id']}",
        headers=auth_headers,
    )
    assert status_response.status_code == 200
    assert status_response.json()["task_id"] == task["id"]


def test_download_completed_video(client, auth_headers) -> None:
    """生成完成后应能下载视频文件。"""
    submit_response = client.post(
        "/api/v1/generate/video",
        headers=auth_headers,
        json={
            "prompt": "海边日出",
            "duration": 5,
            "aspect_ratio": "16:9",
            "quality": "fast",
        },
    )
    assert submit_response.status_code == 200
    task_id = submit_response.json()["id"]

    download_response = client.get(
        f"/api/v1/generate/{task_id}/download",
        headers=auth_headers,
    )
    # Mock 任务会保存占位视频到本地，因此应返回文件
    assert download_response.status_code in {200, 307}


def test_submit_task_with_character_id(client, auth_headers) -> None:
    """提交任务时携带角色 ID 应能正常生成。"""
    character_response = client.post(
        "/api/v1/characters",
        headers=auth_headers,
        json={
            "name": "角色A",
            "reference_image_url": "https://example.com/ref.png",
        },
    )
    assert character_response.status_code == 200
    character_id = character_response.json()["id"]

    submit_response = client.post(
        "/api/v1/generate/video",
        headers=auth_headers,
        json={
            "prompt": "角色在花园里散步",
            "duration": 5,
            "aspect_ratio": "9:16",
            "quality": "standard",
            "character_id": character_id,
        },
    )
    assert submit_response.status_code == 200
    assert submit_response.json()["id"] > 0

