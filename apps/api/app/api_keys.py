"""BYO provider API keys (FR-14). Keys are AES-GCM encrypted at rest and never returned.

NOTE: not in SRS §9's endpoint list, but FR-14 requires per-user key management.
Documented divergence — see docs/architecture.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.deps import get_current_user, get_session
from app.models import User
from app.repositories import ApiKeyRepository, write_log
from app.schemas import ApiKeyCreate, ApiKeyOut
from app.security import encrypt_api_key

router = APIRouter(prefix="/keys", tags=["api-keys"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiKeyOut)
async def add_key(
    body: ApiKeyCreate,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    user: User = Depends(get_current_user),
) -> object:
    if not settings.genesis_encryption_key:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Encryption key not configured")
    encrypted = encrypt_api_key(body.key, settings.genesis_encryption_key)
    key = await ApiKeyRepository(session).create(
        user_id=user.id, provider=body.provider, encrypted_key=encrypted
    )
    # payload carries provider only — never the key material (AC-08).
    await write_log(
        session, event="apikey.add", user_id=user.id, payload={"provider": body.provider}
    )
    return key


@router.get("", response_model=list[ApiKeyOut])
async def list_keys(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> object:
    return await ApiKeyRepository(session).list_for_user(user.id)
