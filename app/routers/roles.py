"""
Role management endpoints — /api/admin/roles
Admin-only CRUD for the roles table.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.database import get_db
from app.models import Role, User
from app.schemas import RoleCreate, RoleUpdate, RoleResponse
from app.auth import get_current_admin_user

router = APIRouter(prefix="/api/admin/roles", tags=["roles"])

# Role names that exist solely for structural reference and cannot be deleted
# (admins can still edit their permissions/description)
_SEEDED_ROLES = {"viewer", "editor", "manager"}


@router.get("", response_model=List[RoleResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    result = await db.execute(select(Role).order_by(Role.id))
    return result.scalars().all()


@router.post("", response_model=RoleResponse, status_code=201)
async def create_role(
    data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    name = data.name.strip().lower()
    if not name:
        raise HTTPException(status_code=400, detail="Role name cannot be empty.")
    existing = await db.execute(select(Role).where(Role.name == name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Role '{name}' already exists.")
    role = Role(
        name=name,
        description=data.description,
        permissions=data.permissions,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found.")
    if data.description is not None:
        role.description = data.description
    if data.permissions is not None:
        role.permissions = data.permissions
    await db.commit()
    await db.refresh(role)
    return role


@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin_user),
):
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found.")
    if role.name in _SEEDED_ROLES:
        raise HTTPException(
            status_code=409,
            detail=f"Built-in role '{role.name}' cannot be deleted. You can edit its permissions.",
        )
    # Check if any users are assigned this role
    count_result = await db.execute(
        select(func.count()).select_from(User).where(User.role_id == role_id)
    )
    count = count_result.scalar_one()
    if count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete: {count} user(s) are assigned this role.",
        )
    await db.delete(role)
    await db.commit()
    return {"message": f"Role '{role.name}' deleted."}
