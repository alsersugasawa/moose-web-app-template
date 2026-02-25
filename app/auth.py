from datetime import datetime, timedelta
from typing import Optional, Tuple
import os
import secrets
import uuid as uuid_module
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import User, UserSession

# Security Configuration - ISO 27001 A.9.4.3, NIST SP 800-53 IA-5, OWASP ASVS 2.6.3
def get_secret_key() -> str:
    secret = os.getenv("SECRET_KEY")
    if not secret or secret == "your-secret-key-change-this-in-production":
        print("WARNING: Using generated SECRET_KEY. Set SECRET_KEY environment variable in production!")
        return secrets.token_urlsafe(32)
    return secret


SECRET_KEY = get_secret_key()
ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# REQUIRE_JTI=true enforces session tracking for all JWTs.
# Set to false during migration period so old tokens without jti still work.
REQUIRE_JTI = os.getenv("REQUIRE_JTI", "false").lower() == "true"

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode('utf-8')[:72]
    return pwd_context.verify(password_bytes, hashed_password)


def get_password_hash(password: str) -> str:
    password_bytes = password.encode('utf-8')[:72]
    return pwd_context.hash(password_bytes)


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> Tuple[str, str]:
    """Create a JWT access token.

    Returns:
        (encoded_jwt, jti) — a tuple of the token string and its unique ID.
        The jti should be stored in user_sessions for revocation support.
    """
    to_encode = data.copy()
    jti = str(uuid_module.uuid4())
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "jti": jti})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, jti


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        # Reject TOTP-pending tokens from accessing normal endpoints
        if payload.get("totp_pending"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="TOTP verification required",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    # Session revocation check
    jti = payload.get("jti")
    if jti:
        try:
            jti_uuid = uuid_module.UUID(jti)
        except ValueError:
            raise credentials_exception
        session_result = await db.execute(
            select(UserSession).where(
                UserSession.jti == jti_uuid,
                UserSession.is_revoked == False,
            )
        )
        session = session_result.scalar_one_or_none()
        if session is None:
            raise credentials_exception
        # Update last_used only if more than 60 s old to reduce write amplification
        if (datetime.utcnow() - session.last_used).total_seconds() > 60:
            session.last_used = datetime.utcnow()
            await db.commit()
    elif REQUIRE_JTI:
        # Strict mode: tokens without jti are rejected
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin access required.",
        )
    return current_user


async def require_verified_email(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Dependency that requires the user's email to be verified."""
    force = os.getenv("FORCE_EMAIL_VERIFICATION", "false").lower() == "true"
    if force and not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required. Check your inbox.",
        )
    return current_user


async def check_first_run(db: AsyncSession) -> bool:
    result = await db.execute(select(User).where(User.is_admin == True))
    admin_users = result.scalars().all()
    return len(admin_users) == 0


async def record_session(
    db: AsyncSession,
    user_id: int,
    jti: str,
    ip_address: str,
    device_info: str,
    expires_at: datetime,
) -> UserSession:
    """Persist a new session record for JWT revocation tracking."""
    session = UserSession(
        user_id=user_id,
        jti=uuid_module.UUID(jti),
        ip_address=ip_address,
        device_info=device_info,
        expires_at=expires_at,
    )
    db.add(session)
    await db.commit()
    return session
