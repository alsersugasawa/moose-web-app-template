from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timedelta
from typing import Optional
import uuid as uuid_module

from app.database import get_db
from app.models import User, PasswordResetToken, UserSession
from app.schemas import (
    UserCreate, UserLogin, UserResponse, Token,
    ForgotPasswordRequest, ResetPasswordRequest,
    TotpSetupResponse, TotpVerifyRequest, TotpCodeRequest,
    SessionResponse,
)
from app.auth import (
    get_password_hash, verify_password,
    create_access_token, get_current_user,
    record_session, ACCESS_TOKEN_EXPIRE_MINUTES,
    SECRET_KEY, ALGORITHM,
)
from app.security import generate_secure_token, PasswordValidator
from app.email import send_verification_email, send_password_reset_email

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

TOTP_PENDING_EXPIRE_MINUTES = 5


# ─── Registration ─────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already registered")

    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user_data.password)
    verification_token = generate_secure_token(32)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        email_verified=False,
        email_verification_token=verification_token,
        email_verification_expires=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    await send_verification_email(new_user.email, new_user.username, verification_token)
    return new_user


# ─── Login ────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == user_data.username))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive. Please contact administrator.")

    user.last_login = datetime.utcnow()
    await db.commit()

    # Two-step login: if TOTP is enabled return a short-lived pending token
    if user.totp_enabled:
        pending_token = create_access_token(
            data={"sub": user.username, "totp_pending": True},
            expires_delta=timedelta(minutes=TOTP_PENDING_EXPIRE_MINUTES),
        )
        return {"access_token": pending_token, "token_type": "bearer", "totp_required": True}

    # Normal login: issue full JWT and record session
    access_token, jti = create_access_token(data={"sub": user.username})
    ip = request.client.host if request.client else "unknown"
    device_info = request.headers.get("User-Agent", "")[:512]
    expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    await record_session(db, user.id, jti, ip, device_info, expires_at)

    return {"access_token": access_token, "token_type": "bearer", "totp_required": False}


# ─── Current user ─────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user


# ─── Email verification ───────────────────────────────────────────────────────

@router.post("/verify-email")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.email_verification_token == token)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid verification token")
    if user.email_verification_expires and user.email_verification_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Verification token has expired")
    user.email_verified = True
    user.email_verification_token = None
    user.email_verification_expires = None
    await db.commit()
    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
async def resend_verification(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.email_verified:
        raise HTTPException(status_code=400, detail="Email is already verified")
    token = generate_secure_token(32)
    current_user.email_verification_token = token
    current_user.email_verification_expires = datetime.utcnow() + timedelta(hours=24)
    await db.commit()
    await send_verification_email(current_user.email, current_user.username, token)
    return {"message": "Verification email sent"}


# ─── Password reset ───────────────────────────────────────────────────────────

@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    # Always return 200 to prevent user enumeration (OWASP)
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if user and user.is_active:
        token_str = generate_secure_token(32)
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=token_str,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(reset_token)
        await db.commit()
        await send_password_reset_email(user.email, user.username, token_str)
    return {"message": "If that email is registered, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == data.token)
    )
    reset = result.scalar_one_or_none()
    if not reset or reset.used or reset.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    is_valid, errors = PasswordValidator.validate_password(data.new_password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=errors)

    result2 = await db.execute(select(User).where(User.id == reset.user_id))
    user = result2.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    user.hashed_password = get_password_hash(data.new_password)
    reset.used = True
    await db.commit()

    # Revoke all active sessions so old tokens cannot be used after a password reset
    await _revoke_all_user_sessions(db, user.id)
    return {"message": "Password reset successfully. Please log in again."}


# ─── TOTP ─────────────────────────────────────────────────────────────────────

@router.post("/totp/setup", response_model=TotpSetupResponse)
async def totp_setup(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import pyotp, qrcode, io, base64
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=current_user.email, issuer_name="Web Platform")
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()
    # Store pending secret (totp_enabled stays False until confirmed)
    current_user.totp_secret = secret
    await db.commit()
    return {"secret": secret, "qr_code": f"data:image/png;base64,{qr_b64}"}


@router.post("/totp/enable")
async def totp_enable(
    data: TotpCodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import pyotp
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="Call /api/auth/totp/setup first")
    if not pyotp.TOTP(current_user.totp_secret).verify(data.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    current_user.totp_enabled = True
    await db.commit()
    return {"message": "Two-factor authentication enabled"}


@router.post("/totp/disable")
async def totp_disable(
    data: TotpCodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import pyotp
    if not current_user.totp_enabled or not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="TOTP is not enabled")
    if not pyotp.TOTP(current_user.totp_secret).verify(data.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    current_user.totp_enabled = False
    current_user.totp_secret = None
    await db.commit()
    return {"message": "Two-factor authentication disabled"}


@router.post("/totp/verify", response_model=Token)
async def totp_verify(
    data: TotpVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Verify a TOTP code using the pending token from /login. Returns a full JWT."""
    from jose import JWTError, jwt
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired pending token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(data.token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("totp_pending"):
            raise credentials_exception
        username: str = payload.get("sub")
        if not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    import pyotp
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not user.totp_enabled or not user.totp_secret:
        raise credentials_exception
    if not pyotp.TOTP(user.totp_secret).verify(data.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")

    access_token, jti = create_access_token(data={"sub": user.username})
    ip = request.client.host if request.client else "unknown"
    device_info = request.headers.get("User-Agent", "")[:512]
    expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    await record_session(db, user.id, jti, ip, device_info, expires_at)

    return {"access_token": access_token, "token_type": "bearer", "totp_required": False}


# ─── Session management ───────────────────────────────────────────────────────

@router.get("/sessions")
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserSession).where(
            UserSession.user_id == current_user.id,
            UserSession.is_revoked == False,
            UserSession.expires_at > datetime.utcnow(),
        ).order_by(UserSession.last_used.desc())
    )
    sessions = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "device_info": s.device_info,
            "ip_address": s.ip_address,
            "created_at": s.created_at.isoformat(),
            "last_used": s.last_used.isoformat(),
            "expires_at": s.expires_at.isoformat(),
            "is_revoked": s.is_revoked,
        }
        for s in sessions
    ]


@router.delete("/sessions/all")
async def revoke_all_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _revoke_all_user_sessions(db, current_user.id)
    return {"message": "All sessions revoked. Please log in again."}


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        sid = uuid_module.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID")

    result = await db.execute(
        select(UserSession).where(
            UserSession.id == sid,
            UserSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.is_revoked = True
    await db.commit()
    return {"message": "Session revoked"}


# ─── Account management ───────────────────────────────────────────────────────

@router.put("/update-email")
async def update_email(
    new_email: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == new_email))
    existing_user = result.scalar_one_or_none()
    if existing_user and existing_user.id != current_user.id:
        raise HTTPException(status_code=400, detail="Email already registered")
    current_user.email = new_email
    current_user.email_verified = False
    current_user.email_verification_token = generate_secure_token(32)
    current_user.email_verification_expires = datetime.utcnow() + timedelta(hours=24)
    await db.commit()
    await send_verification_email(new_email, current_user.username, current_user.email_verification_token)
    return {"message": "Email updated. Please verify your new email address."}


@router.put("/update-password")
async def update_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.hashed_password:
        raise HTTPException(status_code=400, detail="This account uses social login")
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = get_password_hash(new_password)
    await db.commit()
    return {"message": "Password updated successfully"}


@router.delete("/delete-account")
async def delete_account(
    password: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.hashed_password:
        raise HTTPException(status_code=400, detail="This account uses social login")
    if not verify_password(password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Password is incorrect")
    await db.delete(current_user)
    await db.commit()
    return {"message": "Account deleted successfully"}


# ─── Internal helpers ─────────────────────────────────────────────────────────

async def _revoke_all_user_sessions(db: AsyncSession, user_id: int) -> None:
    await db.execute(
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.is_revoked == False)
        .values(is_revoked=True)
    )
    await db.commit()
