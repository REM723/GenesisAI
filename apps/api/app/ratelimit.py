"""Redis fixed-window rate limiting (SRS §7): per user and per IP, 429 + Retry-After.

ponytail: fixed-window counter (INCR + EXPIRE). Simple and correct for MVP; swap to a sliding
window or token bucket if burst behaviour at window edges becomes a problem.
"""

import jwt
from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis

from app.config import Settings, get_settings
from app.deps import get_redis

WINDOW_SECONDS = 60
DEFAULT_LIMIT = 120  # requests per window, per identity


async def _hit(redis: Redis, key: str, limit: int, window: int) -> tuple[bool, int]:
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, window)
    ttl = await redis.ttl(key)
    retry_after = ttl if ttl and ttl > 0 else window
    return count <= limit, retry_after


def _user_id(request: Request, secret: str) -> str | None:
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    try:
        payload = jwt.decode(header.split(" ", 1)[1], secret, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return None
    sub = payload.get("sub")
    return str(sub) if sub else None


async def rate_limit(
    request: Request,
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> None:
    ip = request.client.host if request.client else "unknown"
    identities = [f"rl:ip:{ip}"]
    uid = _user_id(request, settings.jwt_secret)
    if uid:
        identities.append(f"rl:user:{uid}")

    for identity in identities:
        allowed, retry_after = await _hit(
            redis, f"{identity}:{WINDOW_SECONDS}", DEFAULT_LIMIT, WINDOW_SECONDS
        )
        if not allowed:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )
