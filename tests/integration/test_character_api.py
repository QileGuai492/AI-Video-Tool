"""角色库接口集成测试。"""


def test_create_character_and_multi_view(client, auth_headers) -> None:
    """创建角色后可以添加多角度参考图并查看详情。"""
    create_response = client.post(
        "/api/v1/characters",
        headers=auth_headers,
        json={
            "name": "测试角色",
            "reference_image_url": "https://example.com/ref.png",
            "description": "用于一致性测试",
        },
    )
    assert create_response.status_code == 200
    character_id = create_response.json()["id"]

    multi_view_response = client.post(
        f"/api/v1/characters/{character_id}/multi-views",
        headers=auth_headers,
        json={"view_name": "侧面", "image_url": "https://example.com/side.png"},
    )
    assert multi_view_response.status_code == 200
    assert multi_view_response.json()["view_name"] == "侧面"

    detail_response = client.get(
        f"/api/v1/characters/{character_id}",
        headers=auth_headers,
    )
    assert detail_response.status_code == 200
    assert len(detail_response.json()["multi_views"]) == 1


def test_delete_multi_view(client, auth_headers) -> None:
    """用户应能删除角色的多角度参考图。"""
    create_response = client.post(
        "/api/v1/characters",
        headers=auth_headers,
        json={"name": "多视角角色", "reference_image_url": "https://example.com/ref.png"},
    )
    character_id = create_response.json()["id"]
    multi_view_response = client.post(
        f"/api/v1/characters/{character_id}/multi-views",
        headers=auth_headers,
        json={"view_name": "正面", "image_url": "https://example.com/front.png"},
    )
    multi_view_id = multi_view_response.json()["id"]

    delete_response = client.delete(
        f"/api/v1/characters/{character_id}/multi-views/{multi_view_id}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 200

    detail_response = client.get(
        f"/api/v1/characters/{character_id}",
        headers=auth_headers,
    )
    assert detail_response.status_code == 200
    assert len(detail_response.json()["multi_views"]) == 0


def test_character_detail_not_owned(client, auth_headers) -> None:
    """访问不属于当前用户的角色应返回 404。"""
    # 先创建一个角色
    create_response = client.post(
        "/api/v1/characters",
        headers=auth_headers,
        json={"name": "私有角色", "reference_image_url": "https://example.com/a.png"},
    )
    character_id = create_response.json()["id"]

    # 注册另一个用户
    other_headers = None
    register_response = client.post(
        "/api/v1/auth/register",
        json={"username": "other_user", "password": "secret123"},
    )
    other_headers = {"Authorization": f"Bearer {register_response.json()['access_token']}"}

    detail_response = client.get(
        f"/api/v1/characters/{character_id}",
        headers=other_headers,
    )
    assert detail_response.status_code == 404


def test_delete_character(client, auth_headers) -> None:
    """用户应能删除自己的角色。"""
    create_response = client.post(
        "/api/v1/characters",
        headers=auth_headers,
        json={"name": "待删除角色", "reference_image_url": "https://example.com/a.png"},
    )
    character_id = create_response.json()["id"]
    delete_response = client.delete(f"/api/v1/characters/{character_id}", headers=auth_headers)
    assert delete_response.status_code == 200
    assert client.get(f"/api/v1/characters/{character_id}", headers=auth_headers).status_code == 404
