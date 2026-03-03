from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, Response
from starlette.middleware.sessions import SessionMiddleware
from contextlib import asynccontextmanager
import json
import os
from app.database import init_db
from app.routers import auth, admin
from app.routers import oauth as oauth_router
from app.routers import roles as roles_router
from app.routers import api_keys as api_keys_router
from app.routers import invitations as invitations_router
from app.routers import feature_flags as feature_flags_router
from app.auth import get_secret_key, get_current_admin_user
from app.security import (
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
    SECURITY_HEADERS_ENABLED,
    RATE_LIMIT_ENABLED
)
from app.settings import settings
from plugins import load_plugins


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    await init_db()
    print("=" * 70)
    print("SECURITY CONFIGURATION STATUS")
    print("=" * 70)
    print(f"Environment (APP_ENV):        {settings.app_env}")
    print(f"Security Headers:             {'ENABLED' if SECURITY_HEADERS_ENABLED else 'DISABLED'}")
    print(f"Rate Limiting:                {'ENABLED' if RATE_LIMIT_ENABLED else 'DISABLED'}")
    print(f"Session Timeout:              {os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '30')} minutes")
    print(f"CORS Origins:                 {os.getenv('CORS_ORIGINS', 'http://localhost:8080,http://127.0.0.1:8080')}")
    print(f"Invite-Only Registration:     {'ENABLED' if os.getenv('INVITE_ONLY', 'false').lower() == 'true' else 'DISABLED'}")
    print("=" * 70)
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="Web Platform",
    version="1.0.0",
    lifespan=lifespan,
    # Disable automatic docs in production (OWASP ASVS 14.1.3)
    docs_url="/docs" if os.getenv("ENVIRONMENT", "development") == "development" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT", "development") == "development" else None,
)

# Session middleware for OAuth CSRF state (uses SECRET_KEY for signing)
app.add_middleware(SessionMiddleware, secret_key=get_secret_key(), https_only=False)

# Add Security Headers Middleware (OWASP ASVS 14.4.1-7, NIST SP 800-53 SC-8)
if SECURITY_HEADERS_ENABLED:
    app.add_middleware(SecurityHeadersMiddleware)

# Add Rate Limiting Middleware (NIST SP 800-53 SC-5, OWASP ASVS 2.2.1)
if RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)

# Configure CORS with whitelist (OWASP ASVS 14.5.3, NIST SP 800-53 AC-4)
# In production, set CORS_ORIGINS environment variable to your frontend domains
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080")
cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,  # Whitelist only - CRITICAL CHANGE
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],  # Explicit methods
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "X-API-Key"],  # Explicit headers
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Add Trusted Host Middleware (OWASP ASVS 14.4.4)
# Prevents Host header injection attacks
trusted_hosts_str = os.getenv("TRUSTED_HOSTS", "localhost,127.0.0.1,*.localhost")
trusted_hosts = [host.strip() for host in trusted_hosts_str.split(",") if host.strip()]
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=trusted_hosts
)

# Include routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(oauth_router.router)
app.include_router(roles_router.router)
app.include_router(api_keys_router.router)
app.include_router(invitations_router.router)
app.include_router(feature_flags_router.router)

# Load plugins (Phase 3) — scans plugins/ directory and auto-registers routers
load_plugins(app)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Redirect root to the main application."""
    return RedirectResponse(url="/static/index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# ─── Phase 3: Developer Tools export endpoints ────────────────────────────────

@app.get(
    "/api/admin/export/openapi",
    tags=["developer-tools"],
    summary="Export OpenAPI specification",
)
async def export_openapi(_=Depends(get_current_admin_user)):
    """Return the raw OpenAPI 3.x spec as JSON (available in all environments)."""
    return app.openapi()


@app.get(
    "/api/admin/export/typescript-client",
    tags=["developer-tools"],
    summary="Download auto-generated TypeScript client",
)
async def export_typescript_client(_=Depends(get_current_admin_user)):
    """
    Generate and return a typed TypeScript client derived from the current OpenAPI spec.
    The file is streamed as a downloadable attachment.
    """
    from app.ts_generator import generate_typescript_client

    spec = app.openapi()
    ts_source = generate_typescript_client(spec)
    return Response(
        content=ts_source,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="client.ts"'},
    )
