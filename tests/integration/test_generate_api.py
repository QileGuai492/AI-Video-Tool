"""视频生成接口集成测试。

依赖 Celery eager 模式（本地配置），任务会同步执行。
"""

from app.models import User, VideoTask


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
        f"/api/v1/generate/status/{task['uid']}",
        headers=auth_headers,
    )
    assert status_response.status_code == 200
    assert status_response.json()["task_uid"] == task["uid"]


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
    task_uid = submit_response.json()["uid"]

    download_response = client.get(
        f"/api/v1/generate/{task_uid}/download",
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


def test_submit_batch_tasks(client, auth_headers) -> None:
    """批量提交应返回多个任务 ID。"""
    response = client.post(
        "/api/v1/generate/batch",
        headers=auth_headers,
        json={
            "prompt": "批量生成测试",
            "count": 3,
            "duration": 5,
            "aspect_ratio": "16:9",
            "quality": "standard",
            "previs_video_url": "/uploads/videos/batch_previs.mp4",
            "previs_type": "coarse",
            "camera_script": {"shots": [{"start": 0, "end": 5, "action": "测试", "camera": "跟拍"}]},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 3
    assert len(body["task_ids"]) == 3
    assert len(body["task_uids"]) == 3
    assert body["batch_id"]


def test_retry_cancelled_task(client, auth_headers, db_session) -> None:
    """已取消任务应可以重试。"""
    user = db_session.query(User).filter_by(username="test_user").first()
    task = VideoTask(
        user_id=user.id,
        prompt="已取消的任务",
        status="cancelled",
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    response = client.post(
        f"/api/v1/generate/{task.uid}/retry",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "pending"


def test_delete_own_task(client, auth_headers, db_session) -> None:
    """用户可删除自己的任务。"""
    user = db_session.query(User).filter_by(username="test_user").first()
    task = VideoTask(
        user_id=user.id,
        prompt="待删除任务",
        status="completed",
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    response = client.delete(f"/api/v1/generate/{task.uid}", headers=auth_headers)
    assert response.status_code == 200
    assert db_session.query(VideoTask).filter(VideoTask.id == task.id).first() is None


def test_task_uid_cross_user_isolated(client, auth_headers, db_session) -> None:
    """其他用户不能通过任务 UID 访问不属于自己的任务。"""
    user = db_session.query(User).filter_by(username="test_user").first()
    task = VideoTask(
        user_id=user.id,
        prompt="私有任务",
        status="pending",
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    register_response = client.post(
        "/api/v1/auth/register",
        json={"username": "other_user", "password": "secret123"},
    )
    assert register_response.status_code == 200
    other_headers = {"Authorization": f"Bearer {register_response.json()['access_token']}"}

    status_response = client.get(
        f"/api/v1/generate/status/{task.uid}",
        headers=other_headers,
    )
    assert status_response.status_code == 404

    cancel_response = client.post(
        f"/api/v1/generate/{task.uid}/cancel",
        headers=other_headers,
    )
    assert cancel_response.status_code == 404


def test_submit_task_with_voice_and_subtitle(client, auth_headers, db_session) -> None:
    """提交任务时应保存配音音色与字幕开关。"""
    response = client.post(
        "/api/v1/generate/video",
        headers=auth_headers,
        json={
            "prompt": "蜘蛛侠测试",
            "voice_id": "male_01",
            "with_subtitle": False,
            "duration": 5,
            "aspect_ratio": "16:9",
            "quality": "standard",
        },
    )
    assert response.status_code == 200
    task = db_session.query(VideoTask).filter(VideoTask.id == response.json()["id"]).first()
    assert task is not None
    assert task.voice_id == "male_01"
    assert task.with_subtitle is False


def test_submit_task_with_reference_images(client, auth_headers, db_session) -> None:
    """提交任务时应保存首图与多张参考图 URL。"""
    response = client.post(
        "/api/v1/generate/video",
        headers=auth_headers,
        json={
            "prompt": "根据参考图生成视频",
            "image_url": "/uploads/images/first.png",
            "reference_image_urls": [
                "/uploads/images/ref1.png",
                "/uploads/images/ref2.png",
            ],
            "duration": 5,
            "aspect_ratio": "16:9",
            "quality": "standard",
        },
    )
    assert response.status_code == 200
    task = db_session.query(VideoTask).filter(VideoTask.id == response.json()["id"]).first()
    assert task is not None
    assert task.image_url == "/uploads/images/first.png"
    assert task.reference_image_urls == [
        "/uploads/images/ref1.png",
        "/uploads/images/ref2.png",
    ]

