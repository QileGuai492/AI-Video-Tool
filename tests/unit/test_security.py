"""安全工具单元测试。"""

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password() -> None:
    """密码哈希后可以正确校验。"""
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_create_and_decode_token() -> None:
    """JWT 可以正确编码和解码。"""
    token = create_access_token("42")
    assert decode_access_token(token) == "42"
    assert decode_access_token("invalid_token") is None
