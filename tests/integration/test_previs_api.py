"""白模预演接口集成测试。"""

import shutil
import time
from pathlib import Path


def test_previs_template_and_project_flow(client, auth_headers) -> None:
    """白模模板、项目、更新与渲染应可用。"""
    template = client.post(
        "/api/v1/previs/templates",
        headers=auth_headers,
        json={
            "name": "人物行走模板",
            "description": "基础行走",
            "scene_json": {"objects": []},
            "category": "人物",
        },
    )
    assert template.status_code == 200
    template_id = template.json()["id"]

    list_response = client.get("/api/v1/previs/templates", headers=auth_headers)
    assert list_response.status_code == 200
    assert any(item["id"] == template_id for item in list_response.json())

    project = client.post(
        "/api/v1/previs/projects",
        headers=auth_headers,
        json={
            "title": "测试白模项目",
            "template_id": template_id,
            "mode": "manual",
            "scene_json": {"objects": [{"type": "box", "position": [0, 0, 0]}]},
            "camera_script": {"shots": []},
            "mapping_rules": {"blue_human": "女主"},
        },
    )
    assert project.status_code == 200
    project_id = project.json()["id"]

    update = client.put(
        f"/api/v1/previs/projects/{project_id}",
        headers=auth_headers,
        json={"title": "改名后的白模项目", "status": "draft"},
    )
    assert update.status_code == 200
    assert update.json()["title"] == "改名后的白模项目"

    render = client.post(f"/api/v1/previs/projects/{project_id}/render", headers=auth_headers)
    assert render.status_code == 200
    assert render.json()["status"] == "ready"

    detail = client.get(f"/api/v1/previs/projects/{project_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == project_id


def test_previs_project_not_found(client, auth_headers) -> None:
    """不存在的白模项目应返回 404。"""
    response = client.get("/api/v1/previs/projects/999999", headers=auth_headers)
    assert response.status_code == 404


def test_upload_previs_video(client, auth_headers) -> None:
    """白模项目应支持上传 MP4 视频。"""
    project = client.post(
        "/api/v1/previs/projects",
        headers=auth_headers,
        json={"title": "上传视频项目", "mode": "manual", "scene_json": {}},
    )
    assert project.status_code == 200
    project_id = project.json()["id"]

    response = client.post(
        f"/api/v1/previs/projects/{project_id}/video",
        headers=auth_headers,
        files={"file": ("previs.mp4", b"fake-mp4-bytes", "video/mp4")},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["previs_video_url"]


def test_generate_task_with_previs_video(client, auth_headers) -> None:
    """携带白模视频提交任务应能完成生成。"""
    # 准备一个本地白模视频文件
    video_dir = Path("uploads/videos")
    video_dir.mkdir(parents=True, exist_ok=True)
    source = Path("app/providers/assets/mock_clip.mp4")
    target = video_dir / "previs_pipeline_test.mp4"
    shutil.copyfile(source, target)

    response = client.post(
        "/api/v1/generate/video",
        headers=auth_headers,
        json={
            "prompt": "白模降级测试",
            "previs_video_url": "/uploads/videos/previs_pipeline_test.mp4",
            "previs_type": "coarse",
            "duration": 5,
            "aspect_ratio": "16:9",
            "quality": "standard",
        },
    )
    assert response.status_code == 200
    task_id = response.json()["id"]

    status = None
    for _ in range(20):
        status = client.get(f"/api/v1/generate/status/{task_id}", headers=auth_headers)
        if status.status_code == 200 and status.json()["status"] in {"completed", "failed", "cancelled"}:
            break
        time.sleep(0.5)

    assert status is not None
    assert status.json()["status"] == "completed"
    assert status.json()["progress"] == 1.0
