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


# ---- Projects (§9) ----
class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    idea: str = Field(min_length=1)


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    status: str
    created_at: datetime


class ProjectPage(BaseModel):
    items: list[ProjectOut]
    next_cursor: str | None = None


class ArtifactRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    path: str | None = None
    type: str | None = None
    language: str | None = None
    version: int


class RunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    status: str
    current_agent: str | None = None


class ProjectDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    idea: str
    status: str
    created_at: datetime
    code: list[ArtifactRef] = []
    documents: list[ArtifactRef] = []
    latest_run: RunSummary | None = None


# ---- Prompts (§9) ----
class PromptGenerateIn(BaseModel):
    project_id: uuid.UUID


class PromptVersionOut(BaseModel):
    version: int
    score: float | None = None


class PromptOut(BaseModel):
    id: uuid.UUID
    type: str
    content: str
    score: float | None = None
    versions: list[PromptVersionOut] = []


# ---- Agents (§9) ----
class AgentRunIn(BaseModel):
    project_id: uuid.UUID
    run_id: uuid.UUID | None = None  # supplied -> resume


class RunAccepted(BaseModel):
    run_id: uuid.UUID
    status: str


# ---- Code review / tests (§9) ----
class CodeReviewIn(BaseModel):
    project_id: uuid.UUID


class CodeReviewOut(BaseModel):
    project_id: uuid.UUID
    passed: bool
    files_reviewed: int


class TestsGenerateIn(BaseModel):
    project_id: uuid.UUID


class TestsGenerateOut(BaseModel):
    project_id: uuid.UUID
    content: str
