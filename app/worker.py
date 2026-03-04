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


# ── Worker settings ───────────────────────────────────────────────────────────

class WorkerSettings:
    functions = [
        send_verification_email_task,
        send_password_reset_email_task,
    ]

    # Connect to the same Redis instance as the web process
    redis_settings = RedisSettings.from_dsn(settings.redis_url or "redis://localhost:6379/0")

    max_jobs = 10
    job_timeout = 60          # seconds before a running job is cancelled
    retry_jobs = True
    max_tries = 3             # max attempts per job (includes first try)
    health_check_interval = 30
    keep_result = 300         # keep job result in Redis for 5 minutes
