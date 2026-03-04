"""
Centralised application settings using pydantic-settings.

Supports environment-specific config profiles:
  - Base:       .env
  - Profile:    .env.{APP_ENV}   (overrides base)

Set APP_ENV to 'development' (default), 'staging', or 'production'.
Values in .env.{APP_ENV} take precedence over .env.

Usage:
    from app.settings import settings
    print(settings.app_env)
    print(settings.database_url)
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolved before Settings is instantiated so it can be used in model_config
APP_ENV = os.getenv("APP_ENV", "development")


class Settings(BaseSettings):
    # ── Core ─────────────────────────────────────────────────────────────────
    app_env: str = APP_ENV
    environment: str = "development"          # development | production (controls /docs)
    secret_key: str = ""
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/webapp"
    access_token_expire_minutes: int = 30

    # ── Registration & CORS ──────────────────────────────────────────────────
    invite_only: bool = False
    cors_origins: str = "http://localhost:8080,http://127.0.0.1:8080"
    trusted_hosts: str = "localhost,127.0.0.1,*.localhost"

    # ── Security middleware ───────────────────────────────────────────────────
    security_headers_enabled: bool = True
    rate_limit_enabled: bool = True

    # ── Email / SMTP ──────────────────────────────────────────────────────────
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_tls: bool = True

    # ── OAuth ─────────────────────────────────────────────────────────────────
    oauth_google_client_id: str = ""
    oauth_google_client_secret: str = ""
    oauth_google_redirect_uri: str = ""
    oauth_github_client_id: str = ""
    oauth_github_client_secret: str = ""
    oauth_github_redirect_uri: str = ""

    # ── Backups ───────────────────────────────────────────────────────────────
    backup_dir: str = "/app/backups"
    backup_retention_days: int = 30

    # SMB
    smb_backup_enabled: bool = False
    smb_host: Optional[str] = None
    smb_share: Optional[str] = None
    smb_username: Optional[str] = None
    smb_password: Optional[str] = None
    smb_mount_point: str = "/mnt/smb_backups"

    # NFS
    nfs_backup_enabled: bool = False
    nfs_host: Optional[str] = None
    nfs_export: Optional[str] = None
    nfs_mount_point: str = "/mnt/nfs_backups"

    # ── Caddy ─────────────────────────────────────────────────────────────────
    caddy_admin_url: str = "http://caddy:2019"

    # ── Phase 4: Redis ────────────────────────────────────────────────────────
    # Empty string disables Redis (falls back to in-memory rate limiting, no cache)
    redis_url: str = ""

    # ── Phase 4: Database pool tuning ─────────────────────────────────────────
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800   # recycle connections after 30 minutes
    db_echo: bool = False          # log SQL (dev only)

    # ── Phase 4: Read replica ─────────────────────────────────────────────────
    # Empty string = reads fall back to the primary (write) connection
    database_replica_url: str = ""

    # ── App base URL (used in email links + ARQ worker) ───────────────────────
    app_base_url: str = "http://localhost:8080"

    # ── Phase 5: Structured logging ───────────────────────────────────────────
    log_level: str = "INFO"    # DEBUG | INFO | WARNING | ERROR
    log_format: str = "json"   # json (production) | text (development)

    # ── Phase 5: Prometheus metrics ───────────────────────────────────────────
    prometheus_enabled: bool = True

    # ── Phase 5: OpenTelemetry tracing ────────────────────────────────────────
    otel_enabled: bool = False
    otel_endpoint: str = ""             # e.g. http://jaeger:4318/v1/traces
    otel_service_name: str = "web-platform"

    # ── Phase 5: Sentry error tracking ────────────────────────────────────────
    sentry_dsn: str = ""                # empty = Sentry disabled

    # ── Phase 5: Automated migration runner ───────────────────────────────────
    auto_migrate: bool = False          # apply pending .sql files on startup

    model_config = SettingsConfigDict(
        # Base file first; profile file overlays on top
        env_file=[".env", f".env.{APP_ENV}"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Module-level singleton — import this everywhere
settings = Settings()
