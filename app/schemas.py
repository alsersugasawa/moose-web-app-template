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
    last_login: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


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
    # System resources
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
