"""白模预演接口集成测试。"""


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
