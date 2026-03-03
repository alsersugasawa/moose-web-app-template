"""
Feature flag endpoints.

Admin CRUD:  /api/admin/feature-flags
Public read: /api/feature-flags/{name}
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models import FeatureFlag, User
from app.schemas import FeatureFlagCreate, FeatureFlagUpdate, FeatureFlagResponse
from app.auth import get_current_admin_user
from app.permissions import require_permission

router = APIRouter(tags=["feature-flags"])

# Flag names seeded by migration — protected from deletion
_SEEDED_FLAGS = {"registration", "oauth_login", "api_keys", "invitations"}


# ─── Admin CRUD ───────────────────────────────────────────────────────────────

@router.get("/api/admin/feature-flags", response_model=List[FeatureFlagResponse])
async def list_feature_flags(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("feature_flags:manage")),
):
    result = await db.execute(select(FeatureFlag).order_by(FeatureFlag.id))
    return result.scalars().all()


@router.post("/api/admin/feature-flags", response_model=FeatureFlagResponse, status_code=201)
async def create_feature_flag(
    data: FeatureFlagCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    name = data.name.strip().lower().replace(" ", "_")
    if not name:
        raise HTTPException(status_code=400, detail="Flag name cannot be empty.")
    existing = await db.execute(select(FeatureFlag).where(FeatureFlag.name == name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Feature flag '{name}' already exists.")
    flag = FeatureFlag(name=name, description=data.description, is_enabled=data.is_enabled)
    db.add(flag)
    await db.commit()
    await db.refresh(flag)
    return flag


@router.put("/api/admin/feature-flags/{name}", response_model=FeatureFlagResponse)
async def update_feature_flag(
    name: str,
    data: FeatureFlagUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    result = await db.execute(select(FeatureFlag).where(FeatureFlag.name == name))
    flag = result.scalar_one_or_none()
    if flag is None:
        raise HTTPException(status_code=404, detail="Feature flag not found.")
    if data.description is not None:
        flag.description = data.description
    if data.is_enabled is not None:
        flag.is_enabled = data.is_enabled
    await db.commit()
    await db.refresh(flag)
    return flag


@router.delete("/api/admin/feature-flags/{name}")
async def delete_feature_flag(
    name: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    result = await db.execute(select(FeatureFlag).where(FeatureFlag.name == name))
    flag = result.scalar_one_or_none()
    if flag is None:
        raise HTTPException(status_code=404, detail="Feature flag not found.")
    if flag.name in _SEEDED_FLAGS:
        raise HTTPException(
            status_code=409,
            detail=f"Built-in flag '{flag.name}' cannot be deleted. You can toggle it instead.",
        )
    await db.delete(flag)
    await db.commit()
    return {"message": f"Feature flag '{name}' deleted."}


# ─── Public read ──────────────────────────────────────────────────────────────

@router.get("/api/feature-flags/{name}")
async def get_feature_flag(name: str, db: AsyncSession = Depends(get_db)):
    """Public endpoint — returns whether a named feature flag is enabled."""
    result = await db.execute(select(FeatureFlag).where(FeatureFlag.name == name))
    flag = result.scalar_one_or_none()
    if flag is None:
        raise HTTPException(status_code=404, detail="Feature flag not found.")
    return {"name": flag.name, "enabled": flag.is_enabled}
