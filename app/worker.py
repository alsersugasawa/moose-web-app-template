"""
ARQ background worker (Phase 4).

Runs as a separate process/container:
    arq app.worker.WorkerSettings

Tasks defined here are enqueued via app/tasks.py and executed by this worker.
The worker shares the same DATABASE_URL and SMTP_* env vars as the web process.

Retry behaviour: up to 3 attempts with exponential back-off (ARQ default).
"""

import logging
from arq.connections import RedisSettings
from app.settings import settings

logger = logging.getLogger(__name__)


# ── Task functions ────────────────────────────────────────────────────────────

async def send_verification_email_task(ctx, to: str, username: str, token: str) -> bool:
    """ARQ task: send an email-verification link."""
    from app.email import send_verification_email
    logger.info("[worker] send_verification_email to=%s", to)
    return await send_verification_email(to, username, token)


async def send_password_reset_email_task(ctx, to: str, username: str, token: str) -> bool:
    """ARQ task: send a password-reset link."""
    from app.email import send_password_reset_email
    logger.info("[worker] send_password_reset_email to=%s", to)
    return await send_password_reset_email(to, username, token)


async def send_welcome_email_task(ctx, to: str, username: str) -> bool:
    """ARQ task: send a welcome email after registration."""
    from app.email import send_email
    from app.settings import settings as _settings
    logger.info("[worker] send_welcome_email to=%s", to)
    subject = "Welcome to the platform!"
    html_body = (
        f"<p>Hi <strong>{username}</strong>,</p>"
        f"<p>Your account has been created. You can log in at "
        f'<a href="{_settings.app_base_url}">{_settings.app_base_url}</a>.</p>'
        f"<p>Enjoy!</p>"
    )
    text_body = f"Hi {username}, your account is ready. Log in at {_settings.app_base_url}"
    return await send_email(to, subject, html_body, text_body)


async def create_notification_task(ctx, user_id: int, message: str) -> None:
    """ARQ task: persist a notification and push it via WebSocket."""
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
    logger.info("[worker] notification created for user_id=%s", user_id)


async def deliver_webhook_task(ctx, webhook_id: int, event: str, payload: dict) -> None:
    """ARQ task: POST a signed payload to a registered webhook URL."""
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
            logger.warning("[worker] webhook delivery failed webhook_id=%s: %s", webhook_id, exc)

        delivery = WebhookDelivery(
            webhook_id=webhook_id,
            event=event,
            payload=payload,
            status_code=status_code,
            success=success,
        )
        db.add(delivery)
        await db.commit()
        logger.info(
            "[worker] webhook delivered webhook_id=%s event=%s status=%s success=%s",
            webhook_id, event, status_code, success,
        )


# ── Worker settings ───────────────────────────────────────────────────────────

class WorkerSettings:
    functions = [
        send_verification_email_task,
        send_password_reset_email_task,
        send_welcome_email_task,
        create_notification_task,
        deliver_webhook_task,
    ]

    # Connect to the same Redis instance as the web process
    redis_settings = RedisSettings.from_dsn(settings.redis_url or "redis://localhost:6379/0")

    max_jobs = 10
    job_timeout = 60          # seconds before a running job is cancelled
    retry_jobs = True
    max_tries = 3             # max attempts per job (includes first try)
    health_check_interval = 30
    keep_result = 300         # keep job result in Redis for 5 minutes
