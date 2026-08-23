"""用户设置接口集成测试。"""


def test_get_and_update_settings(client, auth_headers) -> None:
    """用户设置应支持读取与更新。"""
    response = client.get("/api/v1/settings", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["default_aspect_ratio"] is None

    update = client.put(
        "/api/v1/settings",
        headers=auth_headers,
        json={
            "default_aspect_ratio": "9:16",
            "default_quality": "high",
            "cost_limit": 80,
        },
    )
    assert update.status_code == 200
    data = update.json()
    assert data["default_aspect_ratio"] == "9:16"
    assert data["default_quality"] == "high"
    assert data["cost_limit"] == 80
