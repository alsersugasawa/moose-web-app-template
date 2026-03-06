"""
Task enqueueing helpers (Phase 4).

Each helper enqueues a job on the ARQ Redis queue when the pool is available,
and falls back to calling the underlying function directly (inline) when Redis
is not configured.  This means the application works correctly with or without
a running ARQ worker — no configuration change required for single-instance
development deployments.

Usage
-----
    from app.tasks import enqueue_verification_email, enqueue_password_reset_email

    await enqueue_verification_email(user.email, user.username, token)
"""

import logging
from typing import Optional
from app.settings import settings

logger = logging.getLogger(__name__)

# Module-level ARQ pool — set by init_arq_pool() during app lifespan
_arq_pool: Optional[object] = None


async def init_arq_pool() -> Optional[object]:
    """
    Create and store the ARQ connection pool.
    Called once from the FastAPI lifespan handler.
    Returns None when REDIS_URL is not configured.
    """
    global _arq_pool
    if not settings.redis_url:
        logger.info("[tasks] REDIS_URL not set — email tasks will run inline (no background queue)")
        return None
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
        _arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        logger.info("[tasks] ARQ pool ready: %s", settings.redis_url)
        return _arq_pool
    except Exception as exc:
        logger.warning("[tasks] ARQ pool creation failed (%s) — email tasks will run inline", exc)
        _arq_pool = None
        return None


async def close_arq_pool() -> None:
    """Close the ARQ pool on app shutdown."""
    global _arq_pool
    if _arq_pool is not None:
        await _arq_pool.aclose()
        _arq_pool = None


# ── Enqueue helpers ───────────────────────────────────────────────────────────

async def enqueue_verification_email(to: str, username: str, token: str) -> None:
    """
    Send an email-verification link via the ARQ worker queue.
    Falls back to inline send if ARQ is unavailable.
    """
    if _arq_pool is not None:
        await _arq_pool.enqueue_job("send_verification_email_task", to, username, token)
        logger.debug("[tasks] queued send_verification_email for %s", to)
    else:
        from app.email import send_verification_email
        await send_verification_email(to, username, token)


async def enqueue_password_reset_email(to: str, username: str, token: str) -> None:
    """
    Send a password-reset link via the ARQ worker queue.
    Falls back to inline send if ARQ is unavailable.
    """
    if _arq_pool is not None:
        await _arq_pool.enqueue_job("send_password_reset_email_task", to, username, token)
        logger.debug("[tasks] queued send_password_reset_email for %s", to)
    else:
        from app.email import send_password_reset_email
        await send_password_reset_email(to, username, token)


async def enqueue_welcome_email(to: str, username: str) -> None:
    """Send a welcome email after successful registration."""
    if _arq_pool is not None:
        await _arq_pool.enqueue_job("send_welcome_email_task", to, username)
        logger.debug("[tasks] queued send_welcome_email for %s", to)
    else:
        from app.email import send_email
        subject = "Welcome to the platform!"
        html_body = (
            f"<p>Hi <strong>{username}</strong>,</p>"
            f"<p>Your account has been created. You can log in at "
            f'<a href="{settings.app_base_url}">{settings.app_base_url}</a>.</p>'
            f"<p>Enjoy!</p>"
        )
        text_body = f"Hi {username}, your account is ready. Log in at {settings.app_base_url}"
        await send_email(to, subject, html_body, text_body)


async def enqueue_user_notification(user_id: int, message: str) -> None:
    """
    Create an in-app notification for a user and push it via WebSocket.
    Falls back to inline DB insert + WS push if ARQ is unavailable.
    """
    if _arq_pool is not None:
        await _arq_pool.enqueue_job("create_notification_task", user_id, message)
        logger.debug("[tasks] queued create_notification for user_id=%s", user_id)
    else:
        from app.database import async_session_maker
        from app.models import Notification
        from app.ws_manager import ws_manager
        async with async_session_maker() as db:
            notif = Notification(user_id=user_id, message=message)
            db.add(notif)
            await db.commit()
            await db.refresh(notif)
        await ws_manager.send_to_user(user_id, {
            "type": "notification",
            "id": notif.id,
            "message": notif.message,
        })


async def enqueue_webhook_delivery(webhook_id: int, event: str, payload: dict) -> None:
    """
    Deliver a signed POST payload to a registered webhook URL.
    Falls back to inline delivery if ARQ is unavailable.
    """
    if _arq_pool is not None:
        await _arq_pool.enqueue_job("deliver_webhook_task", webhook_id, event, payload)
        logger.debug("[tasks] queued deliver_webhook webhook_id=%s event=%s", webhook_id, event)
    else:
        import hashlib
        import hmac as _hmac
        import json
        import httpx
        from sqlalchemy import select
        from app.database import async_session_maker
        from app.models import Webhook, WebhookDelivery
        async with async_session_maker() as db:
            result = await db.execute(select(Webhook).where(Webhook.id == webhook_id))
            webhook = result.scalar_one_or_none()
            if webhook is None or not webhook.is_active:
                return
            body_bytes = json.dumps(payload, default=str).encode()
            sig = _hmac.new(webhook.secret.encode(), body_bytes, hashlib.sha256).hexdigest()
            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Event": event,
                "X-Webhook-Signature": f"sha256={sig}",
            }
            status_code = None
            success = False
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(webhook.url, content=body_bytes, headers=headers)
                status_code = response.status_code
                success = status_code < 400
            except Exception as exc:
                logger.warning("[tasks] inline webhook delivery failed webhook_id=%s: %s", webhook_id, exc)
            db.add(WebhookDelivery(
                webhook_id=webhook_id, event=event, payload=payload,
                status_code=status_code, success=success,
            ))
            await db.commit()
