"""
Invitation management endpoints.
Admin: /api/admin/invitations — create and revoke invitation links.
Public: /api/auth/invite/validate — validate a token before registration.
"""

import secrets
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Invitation, User
from app.schemas import InvitationCreate, InvitationResponse
from app.auth import get_current_admin_user
from app.permissions import require_permission

router = APIRouter(tags=["invitations"])


# ── Admin endpoints ────────────────────────────────────────────────────────────

@router.get("/api/admin/invitations", response_model=List[InvitationResponse])
async def list_invitations(
    used: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("invitations:manage")),
):
    query = select(Invitation).order_by(Invitation.created_at.desc()).offset(skip).limit(limit)
    if used is True:
        query = query.where(Invitation.used_at.isnot(None))
    elif used is False:
        query = query.where(Invitation.used_at.is_(None))
    result = await db.execute(query)
    invitations = result.scalars().all()
    return [_to_response(inv) for inv in invitations]


@router.post("/api/admin/invitations", response_model=InvitationResponse, status_code=201)
async def create_invitation(
    data: InvitationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("invitations:manage")),
):
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=data.expires_in_hours)
    invitation = Invitation(
        token=token,
        email=str(data.email) if data.email else None,
        created_by=current_user.id,
        expires_at=expires_at,
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    return _to_response(invitation)


@router.delete("/api/admin/invitations/{invitation_id}")
async def revoke_invitation(
    invitation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("invitations:manage")),
):
    import uuid as uuid_module
    try:
        inv_uuid = uuid_module.UUID(invitation_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Invitation not found.")
    result = await db.execute(select(Invitation).where(Invitation.id == inv_uuid))
    invitation = result.scalar_one_or_none()
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found.")
    if invitation.used_at is not None:
        raise HTTPException(status_code=409, detail="Cannot revoke an already-used invitation.")
    await db.delete(invitation)
    await db.commit()
    return {"message": "Invitation revoked."}


# ── Public validation endpoint ────────────────────────────────────────────────

@router.get("/api/auth/invite/validate")
async def validate_invite_token(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Check whether an invite token is valid without consuming it."""
    result = await db.execute(select(Invitation).where(Invitation.token == token))
    invitation = result.scalar_one_or_none()
    if invitation is None or invitation.used_at is not None or invitation.expires_at < datetime.utcnow():
        return {"valid": False, "email": None}
    return {"valid": True, "email": invitation.email}


# ── Internal helper (used by auth.py register endpoint) ──────────────────────

async def validate_and_consume_invite(
    token: str,
    user_id: int,
    db: AsyncSession,
) -> None:
    """
    Validate an invite token and mark it as consumed.
    Raises HTTPException(400) if the token is invalid, expired, or already used.
    """
    result = await db.execute(select(Invitation).where(Invitation.token == token))
    invitation = result.scalar_one_or_none()
    if invitation is None:
        raise HTTPException(status_code=400, detail="Invalid or expired invitation token.")
    if invitation.used_at is not None:
        raise HTTPException(status_code=400, detail="Invitation has already been used.")
    if invitation.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired invitation token.")
    invitation.used_by = user_id
    invitation.used_at = datetime.utcnow()
    await db.commit()


# ── Helper ────────────────────────────────────────────────────────────────────

def _to_response(inv: Invitation) -> InvitationResponse:
    return InvitationResponse(
        id=str(inv.id),
        token=inv.token,
        email=inv.email,
        expires_at=inv.expires_at,
        used_at=inv.used_at,
        used_by=inv.used_by,
        created_at=inv.created_at,
    )
