"""模板市场接口集成测试。"""


def test_template_list_and_fork(client, auth_headers) -> None:
    """模板市场应能列出模板并复制到当前用户。"""
    create = client.post(
        "/api/v1/templates",
        headers=auth_headers,
        json={"name": "我的模板", "config_json": {"prompt": "测试"}},
    )
    assert create.status_code == 200
    template_id = create.json()["id"]

    # 当前用户能看到自己的模板
    list_response = client.get("/api/v1/templates", headers=auth_headers)
    assert list_response.status_code == 200
    assert any(item["id"] == template_id for item in list_response.json())

    # 复制自己的模板
    fork = client.post(f"/api/v1/templates/{template_id}/fork", headers=auth_headers)
    assert fork.status_code == 200
    assert fork.json()["name"].endswith("（副本）")
    assert fork.json()["id"] != template_id


def test_template_get_builtin_visible(client, auth_headers, db_session) -> None:
    """内置模板应对所有用户可见。"""
    from app.models import Template

    builtin = Template(
        user_id=1,
        name="官方模板",
        config_json={"prompt": "内置"},
        is_builtin=True,
    )
    db_session.add(builtin)
    db_session.commit()
    db_session.refresh(builtin)

    response = client.get(f"/api/v1/templates/{builtin.id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["name"] == "官方模板"
