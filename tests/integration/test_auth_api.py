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
