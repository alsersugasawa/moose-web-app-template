"""
API key management endpoints — /api/auth/api-keys
Users can create, list, update, and revoke their own API keys.
"""

import secrets
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import ApiKey, User
from app.schemas import ApiKeyCreate, ApiKeyPatch, ApiKeyCreateResponse, ApiKeyResponse
from app.auth import get_current_active_user, get_password_hash

router = APIRouter(prefix="/api/auth/api-keys", tags=["api-keys"])

_MAX_KEYS_PER_USER = 20


@router.get("", response_model=List[ApiKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == current_user.id)
        .order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [
        ApiKeyResponse(
            id=str(k.id),
            name=k.name,
            key_prefix=k.key_prefix,
            scopes=k.scopes or [],
            last_used=k.last_used,
            expires_at=k.expires_at,
            is_active=k.is_active,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.post("", response_model=ApiKeyCreateResponse, status_code=201)
async def create_api_key(
    data: ApiKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # Enforce per-user key limit
    count_result = await db.execute(
        select(ApiKey).where(ApiKey.user_id == current_user.id, ApiKey.is_active == True)
    )
    active_keys = count_result.scalars().all()
    if len(active_keys) >= _MAX_KEYS_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum of {_MAX_KEYS_PER_USER} active API keys allowed.",
        )

    name = data.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Key name cannot be empty.")

    # Generate key: mpk_ + 40 hex chars = 44 chars total
    raw_key = "mpk_" + secrets.token_hex(20)
    key_prefix = raw_key[:10]
    key_hash = get_password_hash(raw_key)

    expires_at: Optional[datetime] = None
    if data.expires_in_days is not None and data.expires_in_days > 0:
        expires_at = datetime.utcnow() + timedelta(days=data.expires_in_days)

    api_key = ApiKey(
        user_id=current_user.id,
        name=name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        scopes=data.scopes,
        expires_at=expires_at,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    return ApiKeyCreateResponse(
        id=str(api_key.id),
        name=api_key.name,
        key=raw_key,          # full key — shown ONCE
        key_prefix=key_prefix,
        scopes=api_key.scopes or [],
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


@router.patch("/{key_id}", response_model=ApiKeyResponse)
async def patch_api_key(
    key_id: str,
    data: ApiKeyPatch,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    api_key = await _get_user_key(key_id, current_user.id, db)
    if data.name is not None:
        name = data.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Key name cannot be empty.")
        api_key.name = name
    if data.is_active is not None:
        api_key.is_active = data.is_active
    await db.commit()
    await db.refresh(api_key)
    return ApiKeyResponse(
        id=str(api_key.id),
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes or [],
        last_used=api_key.last_used,
        expires_at=api_key.expires_at,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
    )


@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    api_key = await _get_user_key(key_id, current_user.id, db)
    await db.delete(api_key)
    await db.commit()
    return {"message": "API key revoked."}


async def _get_user_key(key_id: str, user_id: int, db: AsyncSession) -> ApiKey:
    """Fetch a key by ID and verify it belongs to the requesting user."""
    import uuid as uuid_module
    try:
        key_uuid = uuid_module.UUID(key_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="API key not found.")
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_uuid, ApiKey.user_id == user_id)
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise HTTPException(status_code=404, detail="API key not found.")
    return api_key
