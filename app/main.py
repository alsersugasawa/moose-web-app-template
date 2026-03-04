from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, Response
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
from sqlalchemy import text
import os
from app.database import init_db, engine
from app.routers import auth, admin
from app.routers import oauth as oauth_router
from app.routers import roles as roles_router
from app.routers import api_keys as api_keys_router
from app.routers import invitations as invitations_router
from app.routers import feature_flags as feature_flags_router
from app.routers import websocket as websocket_router
from app.routers import health as health_router        # Phase 5
from app.auth import get_secret_key, get_current_admin_user
from app.security import (
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
    SECURITY_HEADERS_ENABLED,
    RATE_LIMIT_ENABLED,
)
from app.settings import settings
from app.cache import init_redis, close_redis
from app.tasks import init_arq_pool, close_arq_pool
from app.logging_config import configure_logging, RequestLoggingMiddleware  # Phase 5
from plugins import load_plugins


# ── Phase 5: Automated migration runner ───────────────────────────────────────

async def _run_migrations() -> None:
    """Apply any .sql files in migrations/ not yet recorded in schema_migrations."""
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename   VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
            )
        """))
        migration_dir = Path("migrations")
        if not migration_dir.is_dir():
            return
        for f in sorted(migration_dir.glob("*.sql")):
            row = await conn.execute(
                text("SELECT 1 FROM schema_migrations WHERE filename = :fn"),
                {"fn": f.name},
            )
            if not row.scalar():
                print(f"[migrations] Applying {f.name}...")
                await conn.execute(text(f.read_text()))
                await conn.execute(
                    text("INSERT INTO schema_migrations (filename) VALUES (:fn)"),
                    {"fn": f.name},
                )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────

    # Phase 5: Structured logging — configure first so all subsequent output is structured
    configure_logging(level=settings.log_level, fmt=settings.log_format)

    # Phase 5: Sentry (init before anything that could raise)
    if settings.sentry_dsn:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            integrations=[FastApiIntegration(), SqlalchemyIntegration()],
            traces_sample_rate=0.1,
            environment=settings.app_env,
            send_default_pii=False,
        )

    await init_db()

    # Phase 5: Automated migration runner
    if settings.auto_migrate:
        await _run_migrations()

    # Phase 4: Redis pool (shared by cache + rate limiter)
    redis_client = await init_redis()
    app.state.redis = redis_client

    # Phase 4: ARQ pool (background task queue)
    await init_arq_pool()

    # Phase 5: OpenTelemetry (after engine is ready)
    from app.tracing import init_tracing
    init_tracing(app, engine)

    # Phase 5: Prometheus DB pool gauge background task
    pool_gauge_task = None
    if settings.prometheus_enabled:
        from app.metrics import start_pool_gauge_updater
        pool_gauge_task = start_pool_gauge_updater(engine)

    print("=" * 70)
    print("STARTUP CONFIGURATION")
    print("=" * 70)
    print(f"Environment (APP_ENV):        {settings.app_env}")
    print(f"Log Level / Format:           {settings.log_level} / {settings.log_format}")
    print(f"Security Headers:             {'ENABLED' if SECURITY_HEADERS_ENABLED else 'DISABLED'}")
    print(f"Rate Limiting:                {'ENABLED' if RATE_LIMIT_ENABLED else 'DISABLED'}")
    print(f"Rate Limit Backend:           {'Redis' if redis_client else 'In-memory (single-instance)'}")
    print(f"Redis Cache:                  {'ENABLED' if redis_client else 'DISABLED'}")
    print(f"Background Queue (ARQ):       {'ENABLED' if settings.redis_url else 'DISABLED (inline fallback)'}")
    print(f"Session Timeout:              {os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '30')} minutes")
    print(f"CORS Origins:                 {os.getenv('CORS_ORIGINS', 'http://localhost:8080,http://127.0.0.1:8080')}")
    print(f"Invite-Only Registration:     {'ENABLED' if os.getenv('INVITE_ONLY', 'false').lower() == 'true' else 'DISABLED'}")
    print(f"DB Pool:                      size={settings.db_pool_size} overflow={settings.db_max_overflow} recycle={settings.db_pool_recycle}s")
    print(f"Read Replica:                 {'ENABLED' if settings.database_replica_url else 'DISABLED (primary used for reads)'}")
    print(f"Prometheus Metrics:           {'ENABLED (/metrics)' if settings.prometheus_enabled else 'DISABLED'}")
    print(f"OpenTelemetry Tracing:        {'ENABLED → ' + settings.otel_endpoint if settings.otel_enabled and settings.otel_endpoint else 'DISABLED'}")
    print(f"Sentry Error Tracking:        {'ENABLED' if settings.sentry_dsn else 'DISABLED'}")
    print(f"Auto Migration Runner:        {'ENABLED' if settings.auto_migrate else 'DISABLED'}")
    print("=" * 70)

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    if pool_gauge_task:
        pool_gauge_task.cancel()
    await close_arq_pool()
    await close_redis()


app = FastAPI(
    title="Web Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("ENVIRONMENT", "development") == "development" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT", "development") == "development" else None,
)

# Session middleware for OAuth CSRF state
app.add_middleware(SessionMiddleware, secret_key=get_secret_key(), https_only=False)

# Phase 5: Structured access logging
app.add_middleware(RequestLoggingMiddleware)

# Phase 5: Prometheus request metrics
if settings.prometheus_enabled:
    from app.metrics import PrometheusMiddleware
    app.add_middleware(PrometheusMiddleware)

# Security Headers (OWASP ASVS 14.4.1-7, NIST SP 800-53 SC-8)
if SECURITY_HEADERS_ENABLED:
    app.add_middleware(SecurityHeadersMiddleware)

# Rate Limiting (NIST SP 800-53 SC-5, OWASP ASVS 2.2.1)
if RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)

# CORS (OWASP ASVS 14.5.3, NIST SP 800-53 AC-4)
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080")
cors_origins = [o.strip() for o in cors_origins_str.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "X-API-Key"],
    max_age=600,
)

# Trusted Host (OWASP ASVS 14.4.4)
trusted_hosts_str = os.getenv("TRUSTED_HOSTS", "localhost,127.0.0.1,*.localhost")
trusted_hosts = [h.strip() for h in trusted_hosts_str.split(",") if h.strip()]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health_router.router)           # Phase 5: /health, /health/detailed, /metrics
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(oauth_router.router)
app.include_router(roles_router.router)
app.include_router(api_keys_router.router)
app.include_router(invitations_router.router)
app.include_router(feature_flags_router.router)
app.include_router(websocket_router.router)        # Phase 4

# Phase 3: Plugin auto-loader
load_plugins(app)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")


# ── Phase 3: Developer Tools ──────────────────────────────────────────────────

@app.get("/api/admin/export/openapi", tags=["developer-tools"],
         summary="Export OpenAPI specification")
async def export_openapi(_=Depends(get_current_admin_user)):
    """Return the raw OpenAPI 3.x spec as JSON (all environments)."""
    return app.openapi()


@app.get("/api/admin/export/typescript-client", tags=["developer-tools"],
         summary="Download auto-generated TypeScript client")
async def export_typescript_client(_=Depends(get_current_admin_user)):
    """Generate and return a typed TypeScript client from the live OpenAPI spec."""
    from app.ts_generator import generate_typescript_client
    ts_source = generate_typescript_client(app.openapi())
    return Response(
        content=ts_source,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="client.ts"'},
    )
