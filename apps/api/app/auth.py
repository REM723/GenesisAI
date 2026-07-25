"""Auth routes (FR-01, §7): register, login, refresh (with rotation), logout.

NOTE: SRS §9 lists no auth routes but assumes them ("all endpoints require Bearer
except auth routes"). These paths are a documented divergence — see docs/architecture.
Refresh-token state is held in Redis so rotation and revocation need no extra table.
"""

import uuid

import jwt
from fastapi import APIRouter, Depends, HTTPException, Response, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.deps import get_current_user, get_redis, get_session
from app.models import User
from app.repositories import UserRepository, write_log
from app.schemas import LoginIn, RefreshIn, TokenPair, UserCreate, UserOut
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _refresh_key(jti: str) -> str:
    return f"refresh:{jti}"


async def _issue_pair(user: User, redis: Redis, settings: Settings) -> TokenPair:
    access = create_access_token(
        str(user.id), user.role, settings.jwt_secret, settings.jwt_access_ttl
    )
    refresh, jti = create_refresh_token(str(user.id), settings.jwt_secret, settings.jwt_refresh_ttl)
    await redis.set(_refresh_key(jti), str(user.id), ex=settings.jwt_refresh_ttl)
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserOut)
async def register(
    body: UserCreate,
    session: AsyncSession = Depends(get_session),
) -> User:
    repo = UserRepository(session)
    if await repo.get_by_email(body.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = await repo.create(email=body.email, password_hash=hash_password(body.password))
    await write_log(session, event="auth.register", user_id=user.id)
    return user


@router.post("/login", response_model=TokenPair)
async def login(
    body: LoginIn,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> TokenPair:
    user = await UserRepository(session).get_by_email(body.email)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    await write_log(session, event="auth.login", user_id=user.id)
    return await _issue_pair(user, redis, settings)


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    body: RefreshIn,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> TokenPair:
    try:
        payload = decode_token(body.refresh_token, settings.jwt_secret)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token") from exc
    if payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not a refresh token")

    jti = payload["jti"]
    # Rotation: the old jti must still be live. Atomically consume it to block reuse.
    owner = await redis.getdel(_refresh_key(jti))
    if owner is None or owner != payload["sub"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token revoked or reused")

    user = await UserRepository(session).get(uuid.UUID(payload["sub"]))
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
    return await _issue_pair(user, redis, settings)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: RefreshIn,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> Response:
    try:
        payload = decode_token(body.refresh_token, settings.jwt_secret)
        await redis.delete(_refresh_key(payload["jti"]))
    except jwt.InvalidTokenError:
        pass  # already-invalid token is fine to "log out"
    await write_log(session, event="auth.logout", user_id=user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
