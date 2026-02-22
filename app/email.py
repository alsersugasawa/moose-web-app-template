"""Async email sending via aiosmtplib."""
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@example.com")
SMTP_TLS = os.getenv("SMTP_TLS", "true").lower() == "true"
EMAIL_ENABLED = bool(SMTP_HOST)

APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8080")


async def send_email(to: str, subject: str, html_body: str, text_body: str) -> bool:
    """Send email. Returns False silently if email is not configured."""
    if not EMAIL_ENABLED:
        print(f"[EMAIL DISABLED] To: {to} | Subject: {subject}")
        print(f"[EMAIL DISABLED] Body: {text_body}")
        return False
    try:
        import aiosmtplib
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = to
        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER or None,
            password=SMTP_PASSWORD or None,
            start_tls=SMTP_TLS,
        )
        return True
    except Exception as exc:
        print(f"[EMAIL ERROR] Failed to send to {to}: {exc}")
        return False


async def send_verification_email(to: str, username: str, token: str) -> bool:
    link = f"{APP_BASE_URL}/static/index.html?verify_token={token}"
    html = (
        f"<p>Hi <strong>{username}</strong>,</p>"
        f"<p>Please verify your email address by clicking the link below:</p>"
        f"<p><a href='{link}'>Verify Email Address</a></p>"
        f"<p>This link expires in 24 hours.</p>"
        f"<p>If you did not register, you can ignore this email.</p>"
    )
    text = (
        f"Hi {username},\n\n"
        f"Please verify your email address:\n{link}\n\n"
        f"This link expires in 24 hours.\n"
        f"If you did not register, ignore this email."
    )
    return await send_email(to, "Verify your email address", html, text)


async def send_password_reset_email(to: str, username: str, token: str) -> bool:
    link = f"{APP_BASE_URL}/static/index.html?reset_token={token}"
    html = (
        f"<p>Hi <strong>{username}</strong>,</p>"
        f"<p>A password reset was requested for your account. Click below to reset:</p>"
        f"<p><a href='{link}'>Reset Password</a></p>"
        f"<p>This link expires in 1 hour. If you did not request a reset, ignore this email.</p>"
    )
    text = (
        f"Hi {username},\n\n"
        f"Reset your password:\n{link}\n\n"
        f"This link expires in 1 hour.\n"
        f"If you did not request a reset, ignore this email."
    )
    return await send_email(to, "Reset your password", html, text)
