"""Audit log read surface (SRS §7). Admin-only, cursor-paginated.

This is where the RBAC `require_role("admin")` guard (built in Phase 1) is finally wired.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session, require_role
from app.models import User
from app.pagination import decode_cursor, encode_cursor
from app.ratelimit import rate_limit
from app.repositories import LogRepository
from app.schemas import LogOut, LogPage

router = APIRouter(prefix="/logs", tags=["audit"], dependencies=[Depends(rate_limit)])

_admin_only = require_role("admin")


@router.get("", response_model=LogPage)
async def list_logs(
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = None,
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(_admin_only),
) -> LogPage:
    decoded = None
    if cursor is not None:
        try:
            decoded = decode_cursor(cursor)
        except (ValueError, KeyError) as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid cursor") from exc

    rows = await LogRepository(session).list(limit=limit + 1, cursor=decoded)
    items = rows[:limit]
    next_cursor = encode_cursor(items[-1].created_at, items[-1].id) if len(rows) > limit else None
    return LogPage(items=[LogOut.model_validate(r) for r in items], next_cursor=next_cursor)
