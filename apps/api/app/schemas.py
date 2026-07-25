"""Pydantic request/response bodies. `encrypted_key` is never present in any Out model."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: EmailStr
    role: str
    created_at: datetime


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - literal token scheme, not a secret


class RefreshIn(BaseModel):
    refresh_token: str


class ApiKeyCreate(BaseModel):
    provider: str = Field(min_length=1, max_length=64)
    key: str = Field(min_length=1)


class ApiKeyOut(BaseModel):
    """Deliberately omits the key material (NFR-03, AC-08)."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    provider: str
    created_at: datetime
