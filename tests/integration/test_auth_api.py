"""认证接口集成测试。"""


def test_register_and_login(client) -> None:
    """注册后可以登录并获取令牌。"""
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "alice",
            "password": "secret123",
            "email": "alice@example.com",
        },
    )
    assert register_response.status_code == 200
    assert register_response.json()["access_token"]

    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "secret123"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["access_token"]


def test_register_duplicate_username(client) -> None:
    """重复用户名注册应返回 400。"""
    payload = {"username": "bob", "password": "secret123"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 200
    assert client.post("/api/v1/auth/register", json=payload).status_code == 400


def test_register_weak_password_rejected(client) -> None:
    """纯数字或纯字母等弱密码应注册失败。"""
    for password in ["12345678", "abcdefgh", "123456"]:
        response = client.post(
            "/api/v1/auth/register",
            json={"username": f"weak_{password}", "password": password},
        )
        assert response.status_code == 422


def test_update_weak_password_rejected(client, auth_headers) -> None:
    """修改密码时弱密码应被拒绝。"""
    response = client.put(
        "/api/v1/auth/me",
        headers=auth_headers,
        json={"password": "12345678"},
    )
    assert response.status_code == 422


def test_login_wrong_password(client) -> None:
    """错误密码登录应返回 401。"""
    client.post(
        "/api/v1/auth/register",
        json={"username": "carol", "password": "secret123"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "carol", "password": "wrong"},
    )
    assert response.status_code == 401


def test_get_and_update_current_user(client, auth_headers) -> None:
    """当前用户可查看并更新邮箱/密码。"""
    get_response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()["username"] == "test_user"

    update_response = client.put(
        "/api/v1/auth/me",
        headers=auth_headers,
        json={"email": "new@example.com", "password": "newpass123"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["email"] == "new@example.com"

    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "test_user", "password": "newpass123"},
    )
    assert login_response.status_code == 200
