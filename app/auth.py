from datetime import datetime, timedelta
from typing import Optional
import os
import secrets
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import User

# Security Configuration - ISO 27001 A.9.4.3, NIST SP 800-53 IA-5, OWASP ASVS 2.6.3
# Generate secure SECRET_KEY if not provided
def get_secret_key() -> str:
    """Get SECRET_KEY from environment or generate secure one."""
    secret = os.getenv("SECRET_KEY")
    if not secret or secret == "your-secret-key-change-this-in-production":
        # Generate cryptographically secure random key
        # CRITICAL: In production, set SECRET_KEY in environment variables
        print("WARNING: Using generated SECRET_KEY. Set SECRET_KEY environment variable in production!")
        return secrets.token_urlsafe(32)
    return secret

SECRET_KEY = get_secret_key()
ALGORITHM = "HS256"

# Session timeout aligned with ISO 27001 A.9.4.2, NIST SP 800-53 AC-12
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Password hashing with bcrypt (NIST SP 800-63B, OWASP ASVS 2.4.1)
# Bcrypt automatically uses salt and has configurable work factor
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Work factor (OWASP ASVS 2.4.2)
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Truncate to 72 bytes for bcrypt compatibility
    password_bytes = plain_password.encode('utf-8')[:72]
    return pwd_context.verify(password_bytes, hashed_password)


def get_password_hash(password: str) -> str:
    # Truncate to 72 bytes for bcrypt compatibility
    password_bytes = password.encode('utf-8')[:72]
    return pwd_context.hash(password_bytes)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
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
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin access required."
        )
    return current_user


async def check_first_run(db: AsyncSession) -> bool:
    """Check if this is the first run (no admin users exist)"""
    result = await db.execute(select(User).where(User.is_admin == True))
    admin_users = result.scalars().all()
    return len(admin_users) == 0
