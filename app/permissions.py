"""
Permission scopes and the require_permission() dependency factory.

Admins (is_admin=True) bypass all scope checks.
Non-admin users are granted permissions from their assigned role's `permissions`
list plus any additional scopes stored directly on `user.permissions`.
"""

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db

# Canonical permission scope names
SCOPES = [
    "users:read",
    "users:write",
    "roles:manage",
    "invitations:manage",
    "logs:read",
    "backups:read",
    "backups:write",
    "system:read",
    "api_keys:manage",
    "feature_flags:manage",
]


def get_effective_permissions(user) -> set:
    """Return the union of role permissions and user-level additional permissions."""
    effective: set = set()
    if user.role and user.role.permissions:
        effective.update(user.role.permissions)
    if user.permissions:
        if isinstance(user.permissions, list):
            effective.update(user.permissions)
        elif isinstance(user.permissions, dict):
            effective.update(user.permissions.keys())
    return effective


def require_permission(scope: str):
    """
    Dependency factory. Returns a FastAPI dependency that enforces the given scope.

    Admins bypass all permission checks. Non-admins need the scope in their
    effective permissions (role permissions ∪ user.permissions).

    Usage:
        @router.get("/some-endpoint")
        async def endpoint(user = Depends(require_permission("users:read"))):
            ...
    """
    # Import here to avoid circular imports — auth.py → models.py is fine;
    # permissions.py imports auth.py (one-way, no cycle).
    from app.auth import get_current_active_user
    from app.models import Role

    async def _check(
        current_user=Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
    ):
        if current_user.is_admin:
            return current_user
        # Eagerly load role if it isn't already attached
        if current_user.role_id and current_user.role is None:
            result = await db.execute(select(Role).where(Role.id == current_user.role_id))
            current_user.role = result.scalar_one_or_none()
        effective = get_effective_permissions(current_user)
        if scope not in effective:
            raise HTTPException(
                status_code=403,
                detail=f"Permission '{scope}' required.",
            )
        return current_user

    return _check
