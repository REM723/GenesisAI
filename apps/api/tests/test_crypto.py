"""Unit tests for security primitives — no infrastructure required."""

import base64

import pytest
from cryptography.exceptions import InvalidTag

from app.security import (
    create_access_token,
    decode_token,
    decrypt_api_key,
    encrypt_api_key,
    hash_password,
    verify_password,
)

KEY = base64.b64encode(b"1" * 32).decode()


def test_encrypt_roundtrip() -> None:
    ct = encrypt_api_key("sk-secret", KEY)
    assert "sk-secret" not in ct
    assert decrypt_api_key(ct, KEY) == "sk-secret"


def test_nonce_is_unique() -> None:
    assert encrypt_api_key("same", KEY) != encrypt_api_key("same", KEY)


def test_wrong_key_rejected() -> None:
    ct = encrypt_api_key("x", KEY)
    other = base64.b64encode(b"2" * 32).decode()
    with pytest.raises(InvalidTag):
        decrypt_api_key(ct, other)


def test_bad_key_length() -> None:
    with pytest.raises(ValueError, match="32 bytes"):
        encrypt_api_key("x", base64.b64encode(b"short").decode())


def test_password_hashing() -> None:
    h = hash_password("hunter2000")
    assert h != "hunter2000"
    assert verify_password("hunter2000", h)
    assert not verify_password("wrong-password", h)


def test_access_token_roundtrip() -> None:
    token = create_access_token("uid-1", "member", "secret", 60)
    payload = decode_token(token, "secret")
    assert payload["sub"] == "uid-1"
    assert payload["role"] == "member"
    assert payload["type"] == "access"
