"""
Phase 7: File storage router.

User-facing endpoints  — /api/files/*   (requires authenticated user)
Admin endpoints        — /api/admin/files/* (requires admin)
"""

import uuid
import mimetypes
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.auth import get_current_user, get_current_admin_user
from app.database import get_db
from app.models import StoredFile, User
from app.settings import settings
import app.storage as storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/files", tags=["files"])
admin_router = APIRouter(prefix="/api/admin/files", tags=["admin-files"])

# 50 MB default upload ceiling
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def _storage_required() -> None:
    if not settings.storage_bucket:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File storage is not configured (STORAGE_BUCKET is not set)",
        )


def _file_to_dict(f: StoredFile) -> dict:
    return {
        "id": str(f.id),
        "filename": f.filename,
        "content_type": f.content_type,
        "size_bytes": f.size_bytes,
        "has_thumbnail": f.thumbnail_key is not None,
        "created_at": f.created_at.isoformat(),
    }


# ── User-facing endpoints ──────────────────────────────────────────────────────

@router.post("/upload", status_code=status.HTTP_201_CREATED, summary="Upload a file")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file to S3-compatible object storage.

    Images (JPEG, PNG, GIF, WebP) automatically receive a 256×256 JPEG
    thumbnail stored alongside the original.
    """
    _storage_required()

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {MAX_UPLOAD_BYTES // 1024 // 1024} MB upload limit",
        )

    file_id = uuid.uuid4()
    original_name = file.filename or "upload"
    content_type = (
        file.content_type
        or mimetypes.guess_type(original_name)[0]
        or "application/octet-stream"
    )
    s3_key = f"uploads/{file_id}/{original_name}"

    await storage.upload_file(s3_key, data, content_type)

    # Generate thumbnail for images
    thumbnail_key: Optional[str] = None
    if content_type in storage.IMAGE_CONTENT_TYPES:
        thumb_data = storage.make_thumbnail(data)
        if thumb_data:
            thumbnail_key = f"thumbnails/{file_id}/thumb.jpg"
            await storage.upload_file(thumbnail_key, thumb_data, "image/jpeg")

    stored = StoredFile(
        id=file_id,
        user_id=current_user.id,
        filename=original_name,
        content_type=content_type,
        size_bytes=len(data),
        s3_key=s3_key,
        thumbnail_key=thumbnail_key,
    )
    db.add(stored)
    await db.commit()
    await db.refresh(stored)

    logger.info(
        "[files] upload user_id=%s file_id=%s name=%s size=%d",
        current_user.id, file_id, original_name, len(data),
    )
    return _file_to_dict(stored)


@router.get("", summary="List my uploaded files")
async def list_files(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[dict]:
    """Return all files uploaded by the authenticated user."""
    result = await db.execute(
        select(StoredFile)
        .where(StoredFile.user_id == current_user.id)
        .order_by(StoredFile.created_at.desc())
    )
    return [_file_to_dict(f) for f in result.scalars().all()]


@router.get("/{file_id}/url", summary="Get a presigned download URL")
async def get_file_url(
    file_id: str,
    thumbnail: bool = Query(False, description="Return URL for the thumbnail instead of the original"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a presigned URL that allows direct download of the file."""
    _storage_required()
    try:
        fid = uuid.UUID(file_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file id")

    result = await db.execute(
        select(StoredFile).where(StoredFile.id == fid, StoredFile.user_id == current_user.id)
    )
    f = result.scalar_one_or_none()
    if f is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    key = f.thumbnail_key if (thumbnail and f.thumbnail_key) else f.s3_key
    url = await storage.generate_presigned_url(key)
    return {"url": url, "expires_in": settings.storage_presign_expiry}


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a file")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a file and its thumbnail (if any) from object storage and the database."""
    _storage_required()
    try:
        fid = uuid.UUID(file_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file id")

    result = await db.execute(
        select(StoredFile).where(StoredFile.id == fid, StoredFile.user_id == current_user.id)
    )
    f = result.scalar_one_or_none()
    if f is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    await storage.delete_file(f.s3_key)
    if f.thumbnail_key:
        await storage.delete_file(f.thumbnail_key)

    await db.delete(f)
    await db.commit()
    logger.info("[files] deleted user_id=%s file_id=%s", current_user.id, file_id)


# ── Admin endpoints ────────────────────────────────────────────────────────────

@admin_router.get("", summary="List all uploaded files (admin)")
async def admin_list_files(
    _=Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
) -> List[dict]:
    """Return all files across all users."""
    result = await db.execute(
        select(StoredFile).order_by(StoredFile.created_at.desc())
    )
    return [_file_to_dict(f) for f in result.scalars().all()]


@admin_router.get("/{file_id}/url", summary="Get a presigned download URL (admin)")
async def admin_get_file_url(
    file_id: str,
    thumbnail: bool = Query(False),
    _=Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    _storage_required()
    try:
        fid = uuid.UUID(file_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file id")

    result = await db.execute(select(StoredFile).where(StoredFile.id == fid))
    f = result.scalar_one_or_none()
    if f is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    key = f.thumbnail_key if (thumbnail and f.thumbnail_key) else f.s3_key
    url = await storage.generate_presigned_url(key)
    return {"url": url, "expires_in": settings.storage_presign_expiry}


@admin_router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete any file (admin)")
async def admin_delete_file(
    file_id: str,
    _=Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    _storage_required()
    try:
        fid = uuid.UUID(file_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file id")

    result = await db.execute(select(StoredFile).where(StoredFile.id == fid))
    f = result.scalar_one_or_none()
    if f is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    await storage.delete_file(f.s3_key)
    if f.thumbnail_key:
        await storage.delete_file(f.thumbnail_key)

    await db.delete(f)
    await db.commit()
    logger.info("[files] admin deleted file_id=%s", file_id)
