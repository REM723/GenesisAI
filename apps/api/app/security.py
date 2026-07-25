"""Password hashing, JWT issue/verify, and AES-GCM key encryption (SRS §7, FR-14).

The AES-GCM key material is decrypted in memory only at call time and never logged.
Refresh-token *state* (rotation / revocation) lives in Redis, keyed by the token's jti.
"""

import base64
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_NONCE_BYTES = 12


# ---- Passwords ----
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


# ---- JWT ----
def _encode(payload: dict[str, Any], secret: str, ttl: int) -> str:
    now = datetime.now(UTC)
    body = {**payload, "iat": now, "exp": now + timedelta(seconds=ttl)}
    return jwt.encode(body, secret, algorithm="HS256")


def create_access_token(user_id: str, role: str, secret: str, ttl: int) -> str:
    return _encode({"sub": user_id, "role": role, "type": "access"}, secret, ttl)


def create_refresh_token(user_id: str, secret: str, ttl: int) -> tuple[str, str]:
    """Return (token, jti). Store the jti in Redis to allow rotation/revocation."""
    jti = str(uuid.uuid4())
    token = _encode({"sub": user_id, "type": "refresh", "jti": jti}, secret, ttl)
    return token, jti


def decode_token(token: str, secret: str) -> dict[str, Any]:
    """Decode + verify signature and expiry. Raises jwt.InvalidTokenError on failure."""
    return jwt.decode(token, secret, algorithms=["HS256"])


# ---- API key encryption (AES-256-GCM) ----
def _load_key(b64_key: str) -> bytes:
    key = base64.b64decode(b64_key)
    if len(key) != 32:
        raise ValueError("GENESIS_ENCRYPTION_KEY must be base64 of exactly 32 bytes")
    return key


def encrypt_api_key(plaintext: str, b64_key: str) -> str:
    """Encrypt a provider key. Output is base64(nonce || ciphertext). Never log the input."""
    aes = AESGCM(_load_key(b64_key))
    nonce = os.urandom(_NONCE_BYTES)
    ct = aes.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode()


def decrypt_api_key(token: str, b64_key: str) -> str:
    raw = base64.b64decode(token)
    aes = AESGCM(_load_key(b64_key))
    return aes.decrypt(raw[:_NONCE_BYTES], raw[_NONCE_BYTES:], None).decode()
