"""OAuth 2.0 / Social login router (Google, GitHub) via authlib."""
import os
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User
from app.auth import create_access_token, record_session, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/api/auth/oauth", tags=["OAuth"])

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")

APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8080")

# Build the enabled-provider map at startup
ENABLED_PROVIDERS: dict[str, dict] = {}

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    ENABLED_PROVIDERS["google"] = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://openidconnect.googleapis.com/v1/userinfo",
        "scope": "openid email profile",
    }

if GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET:
    ENABLED_PROVIDERS["github"] = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "emails_url": "https://api.github.com/user/emails",
        "scope": "user:email",
    }


@router.get("/providers")
async def list_providers():
    """Return list of configured OAuth providers."""
    return {"providers": list(ENABLED_PROVIDERS.keys())}


@router.get("/{provider}")
async def oauth_redirect(provider: str, request: Request):
    """Redirect the browser to the OAuth provider's authorization page."""
    if provider not in ENABLED_PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' is not configured")

    cfg = ENABLED_PROVIDERS[provider]
    state = secrets.token_urlsafe(16)

    # Store CSRF state in a signed cookie (stateless — no server session needed)
    callback_url = str(request.url_for("oauth_callback", provider=provider))
    auth_url = (
        f"{cfg['authorize_url']}"
        f"?client_id={cfg['client_id']}"
        f"&redirect_uri={callback_url}"
        f"&response_type=code"
        f"&scope={cfg['scope'].replace(' ', '%20')}"
        f"&state={state}"
    )
    if provider == "google":
        auth_url += "&access_type=offline"

    response = RedirectResponse(url=auth_url)
    # Store state in a short-lived cookie for CSRF validation on callback
    response.set_cookie("oauth_state", state, max_age=300, httponly=True, samesite="lax")
    return response


@router.get("/{provider}/callback", name="oauth_callback")
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle the OAuth provider callback, exchange code for token, create/link user."""
    if provider not in ENABLED_PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' is not configured")

    # CSRF state check
    stored_state = request.cookies.get("oauth_state")
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state (CSRF check failed)")

    cfg = ENABLED_PROVIDERS[provider]
    callback_url = str(request.url_for("oauth_callback", provider=provider))

    import httpx
    async with httpx.AsyncClient() as client:
        # Exchange code for access token
        token_resp = await client.post(
            cfg["token_url"],
            data={
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "code": code,
                "redirect_uri": callback_url,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange OAuth code for token")
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token in OAuth response")

        # Fetch user info
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        userinfo_resp = await client.get(cfg["userinfo_url"], headers=headers)
        if userinfo_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch user info from provider")
        userinfo = userinfo_resp.json()

        if provider == "google":
            oauth_id = userinfo.get("sub")
            email = userinfo.get("email")
            name = userinfo.get("name") or (email.split("@")[0] if email else "user")
            if not userinfo.get("email_verified"):
                raise HTTPException(status_code=400, detail="Google email is not verified")

        elif provider == "github":
            oauth_id = str(userinfo.get("id"))
            name = userinfo.get("login", "user")
            # Fetch primary verified email separately
            emails_resp = await client.get(cfg["emails_url"], headers=headers)
            email = None
            if emails_resp.status_code == 200:
                for e in emails_resp.json():
                    if e.get("primary") and e.get("verified"):
                        email = e["email"]
                        break
            if not email:
                raise HTTPException(status_code=400, detail="No verified email found in GitHub account")
        else:
            raise HTTPException(status_code=400, detail="Unknown provider")

    if not oauth_id or not email:
        raise HTTPException(status_code=400, detail="Could not retrieve required user info from provider")

    # Find or create user
    result = await db.execute(
        select(User).where(User.oauth_provider == provider, User.oauth_user_id == oauth_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        # Check if a local account already exists with this email — link it
        result2 = await db.execute(select(User).where(User.email == email))
        existing = result2.scalar_one_or_none()
        if existing:
            existing.oauth_provider = provider
            existing.oauth_user_id = oauth_id
            existing.email_verified = True
            user = existing
        else:
            # Create a new user
            username = await _unique_username(name, db)
            user = User(
                username=username,
                email=email,
                hashed_password="",  # no local password for OAuth users
                oauth_provider=provider,
                oauth_user_id=oauth_id,
                email_verified=True,
                is_active=True,
            )
            db.add(user)

    user.last_login = datetime.utcnow()
    await db.commit()
    await db.refresh(user)

    # Issue JWT and record session
    jwt_token, jti = create_access_token(data={"sub": user.username})
    ip = request.client.host if request.client else "unknown"
    device_info = request.headers.get("User-Agent", "")[:512]
    expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    await record_session(db, user.id, jti, ip, device_info, expires_at)

    # Redirect to frontend with token in URL fragment (never in query string)
    redirect = RedirectResponse(url=f"/static/index.html#oauth_token={jwt_token}")
    redirect.delete_cookie("oauth_state")
    return redirect


async def _unique_username(base: str, db: AsyncSession) -> str:
    """Generate a unique username based on the OAuth display name."""
    # Sanitize: keep only alphanumeric + underscore, lowercase, max 40 chars
    import re
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", base)[:40].lower().strip("_") or "user"
    candidate = clean
    suffix = 1
    while True:
        result = await db.execute(select(User).where(User.username == candidate))
        if result.scalar_one_or_none() is None:
            return candidate
        candidate = f"{clean}_{suffix}"
        suffix += 1
