from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List, Dict, Any


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool
    is_active: bool
    onboarding_completed: bool
    email_verified: bool
    last_login: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    totp_required: bool = False


# Admin Schemas
class AdminUserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    is_admin: bool = False
    permissions: Optional[Dict[str, Any]] = None


class AdminUserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
    permissions: Optional[Dict[str, Any]] = None


class AdminUserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool
    is_active: bool
    permissions: Optional[Dict[str, Any]] = None
    last_login: Optional[datetime] = None
    onboarding_completed: bool
    email_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SystemLogResponse(BaseModel):
    id: int
    level: str
    message: str
    user_id: Optional[int] = None
    action: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BackupCreate(BaseModel):
    backup_type: str  # "database" or "full"


class BackupResponse(BaseModel):
    id: int
    filename: str
    backup_type: str
    file_size: Optional[int] = None
    created_by: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_users: int
    active_users: int
    recent_logs: List[SystemLogResponse]
    app_version: str
    uptime: str
    database_size: Optional[str] = None
    cpu_percent: float
    cpu_cores: int
    cpu_speed: str
    memory_percent: float
    memory_total: str
    memory_available: str
    disk_percent: float
    disk_total: str
    disk_available: str
    python_version: str
    platform: str
    architecture: str


class AdminSetup(BaseModel):
    app_name: str
    username: str
    email: EmailStr
    password: str


# ─── Phase 1: Email verification ─────────────────────────────────────────────

class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    pass  # uses auth token from header


# ─── Phase 1: Password reset ─────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# ─── Phase 1: TOTP ───────────────────────────────────────────────────────────

class TotpSetupResponse(BaseModel):
    secret: str
    qr_code: str  # data URI (data:image/png;base64,...)


class TotpVerifyRequest(BaseModel):
    token: str   # the pending JWT
    code: str    # 6-digit TOTP code


class TotpCodeRequest(BaseModel):
    code: str    # 6-digit TOTP code


# ─── Phase 1: Session management ─────────────────────────────────────────────

class SessionResponse(BaseModel):
    id: str
    device_info: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime
    last_used: datetime
    expires_at: datetime
    is_revoked: bool

    class Config:
        from_attributes = True


# ─── Phase 1: Certificate management ─────────────────────────────────────────

class CertStatus(BaseModel):
    present: bool
    subject: Optional[str] = None
    issuer: Optional[str] = None
    not_valid_before: Optional[str] = None
    not_valid_after: Optional[str] = None
    days_remaining: Optional[int] = None
    is_expired: Optional[bool] = None
    serial_number: Optional[str] = None


class CertUploadResponse(BaseModel):
    message: str
    cert_info: CertStatus
