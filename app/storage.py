"""
Phase 7: S3-compatible file storage helpers.

Supports Amazon S3, MinIO, and Cloudflare R2.
Set STORAGE_ENDPOINT_URL to a custom endpoint for MinIO / R2;
leave it empty to use native AWS S3.

All public functions are async — boto3 calls are dispatched to the
default thread-pool executor so they don't block the event loop.
"""

import io
import asyncio
import logging
from functools import partial
from typing import Optional

from app.settings import settings

logger = logging.getLogger(__name__)

# Image MIME types that trigger thumbnail generation
IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/bmp",
    "image/tiff",
}


def _make_client():
    """Build a boto3 S3 client from the current settings."""
    import boto3

    kwargs: dict = {
        "aws_access_key_id": settings.storage_access_key or None,
        "aws_secret_access_key": settings.storage_secret_key or None,
        "region_name": settings.storage_region or None,
    }
    if settings.storage_endpoint_url:
        kwargs["endpoint_url"] = settings.storage_endpoint_url
    return boto3.client("s3", **kwargs)


async def _run(fn, *args, **kwargs):
    """Dispatch a blocking boto3 call to the thread-pool executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(fn, *args, **kwargs))


async def upload_file(
    key: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> None:
    """Upload *data* to the configured bucket under *key*."""
    client = _make_client()
    await _run(
        client.put_object,
        Bucket=settings.storage_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    logger.debug("[storage] uploaded key=%s size=%d", key, len(data))


async def delete_file(key: str) -> None:
    """Delete the object at *key* from the configured bucket."""
    client = _make_client()
    await _run(
        client.delete_object,
        Bucket=settings.storage_bucket,
        Key=key,
    )
    logger.debug("[storage] deleted key=%s", key)


async def generate_presigned_url(
    key: str,
    expires_in: Optional[int] = None,
) -> str:
    """Return a presigned GET URL for *key*.

    The URL is valid for *expires_in* seconds (defaults to
    ``settings.storage_presign_expiry``).
    """
    expiry = expires_in if expires_in is not None else settings.storage_presign_expiry
    client = _make_client()
    url: str = await _run(
        client.generate_presigned_url,
        "get_object",
        Params={"Bucket": settings.storage_bucket, "Key": key},
        ExpiresIn=expiry,
    )
    return url


def make_thumbnail(
    data: bytes,
    max_size: tuple = (256, 256),
) -> Optional[bytes]:
    """Generate a JPEG thumbnail from image *data*.

    Returns ``None`` if *data* is not a recognised image format or if
    Pillow raises any error during processing.
    """
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(data))
        img.thumbnail(max_size, Image.LANCZOS)
        out = img.convert("RGB")
        buf = io.BytesIO()
        out.save(buf, format="JPEG", quality=85)
        return buf.getvalue()
    except Exception as exc:
        logger.debug("[storage] thumbnail generation failed: %s", exc)
        return None
