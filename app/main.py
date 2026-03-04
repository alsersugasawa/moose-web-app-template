from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, Response
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
import os
from app.database import init_db
from app.routers import auth, admin
from app.routers import oauth as oauth_router
from app.routers import roles as roles_router
from app.routers import api_keys as api_keys_router
from app.routers import invitations as invitations_router
from app.routers import feature_flags as feature_flags_router
from app.routers import websocket as websocket_router
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
from plugins import load_plugins


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    await init_db()

    # Phase 4: Redis pool (shared by cache + rate limiter)
    redis_client = await init_redis()
    app.state.redis = redis_client

    # Phase 4: ARQ pool (background task queue)
    await init_arq_pool()

    print("=" * 70)
    print("SECURITY CONFIGURATION STATUS")
    print("=" * 70)
    print(f"Environment (APP_ENV):        {settings.app_env}")
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
    print("=" * 70)

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
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
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(oauth_router.router)
app.include_router(roles_router.router)
app.include_router(api_keys_router.router)
app.include_router(invitations_router.router)
app.include_router(feature_flags_router.router)
app.include_router(websocket_router.router)   # Phase 4

# Phase 3: Plugin auto-loader
load_plugins(app)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


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
