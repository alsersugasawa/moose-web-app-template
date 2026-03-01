from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from typing import List, Optional
from datetime import datetime, timedelta
import os
import subprocess
import psutil
import shutil
import json
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from app.database import get_db
from app.models import User, SystemLog, Backup, AppConfig, Role
from app.schemas import (
    AdminUserCreate, AdminUserUpdate, AdminUserUpdateV2,
    AdminUserResponse, AdminUserResponseV2,
    SystemLogResponse, BackupCreate, BackupResponse,
    DashboardStats, AdminSetup
)
from app.auth import (
    get_current_admin_user, get_password_hash, check_first_run
)
from app.permissions import require_permission
from app.config import backup_settings
from pydantic import BaseModel

router = APIRouter(prefix="/api/admin", tags=["admin"])

APP_VERSION = "1.0.0"
START_TIME = datetime.utcnow()


# Request models
class UpdateRequest(BaseModel):
    version: str


# Helper function to log actions
async def log_action(
    db: AsyncSession,
    level: str,
    message: str,
    user_id: int = None,
    action: str = None,
    details: dict = None,
    ip_address: str = None
):
    log = SystemLog(
        level=level,
        message=message,
        user_id=user_id,
        action=action,
        details=details,
        ip_address=ip_address
    )
    db.add(log)
    await db.commit()


@router.get("/check-first-run")
async def check_first_run_endpoint(db: AsyncSession = Depends(get_db)):
    """Check if this is the first run"""
    is_first_run = await check_first_run(db)
    return {"is_first_run": is_first_run}


@router.get("/config")
async def get_app_config(db: AsyncSession = Depends(get_db)):
    """Get application configuration (public endpoint)"""
    # Get app name
    result = await db.execute(
        select(AppConfig).where(AppConfig.key == "app_name")
    )
    app_name_config = result.scalar_one_or_none()
    app_name = app_name_config.value if app_name_config else "Web Platform"

    invite_only = os.getenv("INVITE_ONLY", "false").lower() == "true"
    return {
        "app_name": app_name,
        "invite_only": invite_only,
    }


@router.post("/setup", response_model=AdminUserResponse)
async def setup_admin(
    admin_data: AdminSetup,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create the first admin user during initial setup"""
    # Check if this is first run
    is_first_run = await check_first_run(db)
    if not is_first_run:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin user already exists"
        )

    # Check if username already exists
    result = await db.execute(select(User).where(User.username == admin_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == admin_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Save app configuration (app name)
    app_config_result = await db.execute(
        select(AppConfig).where(AppConfig.key == "app_name")
    )
    app_config = app_config_result.scalar_one_or_none()

    if app_config:
        # Update existing config
        app_config.value = admin_data.app_name
    else:
        # Create new config
        app_config = AppConfig(
            key="app_name",
            value=admin_data.app_name
        )
        db.add(app_config)

    # Create admin user (mark as email_verified — setup flow confirms identity)
    hashed_password = get_password_hash(admin_data.password)
    new_admin = User(
        username=admin_data.username,
        email=admin_data.email,
        hashed_password=hashed_password,
        is_admin=True,
        is_active=True,
        onboarding_completed=False,
        email_verified=True,
    )

    db.add(new_admin)
    await db.commit()
    await db.refresh(new_admin)

    # Log the action
    await log_action(
        db, "INFO", f"Admin user '{admin_data.username}' created during initial setup",
        user_id=new_admin.id, action="admin_setup",
        ip_address=request.client.host
    )

    return new_admin


# Dashboard Stats
@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard statistics"""
    # Count users
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar()

    # Count active users (logged in within last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    active_users_result = await db.execute(
        select(func.count(User.id)).where(
            User.is_active == True,
            User.last_login >= thirty_days_ago
        )
    )
    active_users = active_users_result.scalar()

    # Get recent logs
    logs_result = await db.execute(
        select(SystemLog).order_by(SystemLog.created_at.desc()).limit(10)
    )
    recent_logs = logs_result.scalars().all()

    # Calculate uptime
    uptime_delta = datetime.utcnow() - START_TIME
    uptime_str = str(uptime_delta).split('.')[0]  # Remove microseconds

    # Get database size
    try:
        db_size_result = await db.execute(text("SELECT pg_database_size(current_database())"))
        db_size_bytes = db_size_result.scalar()
        db_size_mb = db_size_bytes / (1024 * 1024)
        database_size = f"{db_size_mb:.2f} MB"
    except Exception:
        database_size = "N/A"

    # Get system resource usage
    import platform
    import sys

    # CPU metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_count = psutil.cpu_count()
    try:
        cpu_freq = psutil.cpu_freq()
        cpu_speed = f"{cpu_freq.current:.0f} MHz" if cpu_freq else "N/A"
    except:
        cpu_speed = "N/A"

    # Memory metrics
    memory = psutil.virtual_memory()
    memory_total_gb = memory.total / (1024**3)
    memory_available_gb = memory.available / (1024**3)
    memory_percent = memory.percent

    # Disk metrics
    disk = psutil.disk_usage('/')
    disk_total_gb = disk.total / (1024**3)
    disk_available_gb = disk.free / (1024**3)
    disk_percent = disk.percent

    return DashboardStats(
        total_users=total_users,
        active_users=active_users,
        recent_logs=recent_logs,
        app_version=APP_VERSION,
        uptime=uptime_str,
        database_size=database_size,
        cpu_percent=cpu_percent,
        cpu_cores=cpu_count,
        cpu_speed=cpu_speed,
        memory_percent=memory_percent,
        memory_total=f"{memory_total_gb:.2f} GB",
        memory_available=f"{memory_available_gb:.2f} GB",
        disk_percent=disk_percent,
        disk_total=f"{disk_total_gb:.2f} GB",
        disk_available=f"{disk_available_gb:.2f} GB",
        python_version=sys.version.split()[0],
        platform=platform.system(),
        architecture=platform.machine()
    )


# User Management
@router.get("/users", response_model=List[AdminUserResponseV2])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_permission("users:read")),
    db: AsyncSession = Depends(get_db)
):
    """List all users"""
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(User)
        .options(selectinload(User.role))
        .offset(skip).limit(limit).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return [
        AdminUserResponseV2(
            id=u.id,
            username=u.username,
            email=u.email,
            is_admin=u.is_admin,
            is_active=u.is_active,
            permissions=u.permissions,
            last_login=u.last_login,
            onboarding_completed=u.onboarding_completed,
            email_verified=u.email_verified,
            created_at=u.created_at,
            updated_at=u.updated_at,
            role_id=u.role_id,
            role=u.role,
            display_name=u.display_name,
        )
        for u in users
    ]


@router.post("/users", response_model=AdminUserResponse)
async def create_user(
    user_data: AdminUserCreate,
    request: Request,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new user"""
    # Check if username exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Check if email exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        is_admin=user_data.is_admin,
        is_active=True,
        permissions=user_data.permissions
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Log the action
    await log_action(
        db, "INFO", f"User '{user_data.username}' created by admin",
        user_id=current_admin.id, action="user_created",
        details={"created_user_id": new_user.id},
        ip_address=request.client.host
    )

    return new_user


@router.put("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: int,
    user_data: AdminUserUpdateV2,
    request: Request,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user details"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent admin from deactivating themselves
    if user_id == current_admin.id and user_data.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )

    # Update fields
    if user_data.email is not None:
        email_check = await db.execute(
            select(User).where(User.email == user_data.email, User.id != user_id)
        )
        if email_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        user.email = user_data.email

    if user_data.is_admin is not None:
        user.is_admin = user_data.is_admin

    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    if user_data.permissions is not None:
        user.permissions = user_data.permissions

    # Role assignment: 0 clears the role, positive int assigns it
    if user_data.role_id is not None:
        if user_data.role_id == 0:
            user.role_id = None
        else:
            role_check = await db.execute(select(Role).where(Role.id == user_data.role_id))
            if not role_check.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Role not found.")
            user.role_id = user_data.role_id

    user.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)

    # Log the action
    await log_action(
        db, "INFO", f"User '{user.username}' updated by admin",
        user_id=current_admin.id, action="user_updated",
        details={"updated_user_id": user_id},
        ip_address=request.client.host
    )

    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a user"""
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    username = user.username
    await db.delete(user)
    await db.commit()

    # Log the action
    await log_action(
        db, "WARNING", f"User '{username}' deleted by admin",
        user_id=current_admin.id, action="user_deleted",
        details={"deleted_user_id": user_id},
        ip_address=request.client.host
    )

    return {"message": f"User '{username}' deleted successfully"}


# Logs
@router.get("/logs", response_model=List[SystemLogResponse])
async def get_logs(
    skip: int = 0,
    limit: int = 100,
    level: str = None,
    current_user: User = Depends(require_permission("logs:read")),
    db: AsyncSession = Depends(get_db)
):
    """Get system logs"""
    query = select(SystemLog)

    if level:
        query = query.where(SystemLog.level == level)

    query = query.order_by(SystemLog.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()
    return logs


# Backups
@router.get("/backups", response_model=List[BackupResponse])
async def list_backups(
    current_user: User = Depends(require_permission("backups:read")),
    db: AsyncSession = Depends(get_db)
):
    """List all backups"""
    result = await db.execute(
        select(Backup).order_by(Backup.created_at.desc())
    )
    backups = result.scalars().all()
    return backups


@router.get("/backup-config")
async def get_backup_config(
    current_admin: User = Depends(get_current_admin_user)
):
    """Get backup configuration status including enabled destinations"""
    return {
        "local": {
            "enabled": True,
            "path": backup_settings.backup_dir,
            "status": "active"
        },
        "smb": {
            "enabled": backup_settings.smb_enabled,
            "host": backup_settings.smb_host or "",
            "share": backup_settings.smb_share or "",
            "username": backup_settings.smb_username or "",
            "mount_point": backup_settings.smb_mount_point or "/mnt/smb_backups",
            "status": "active" if (backup_settings.smb_enabled and os.path.ismount(backup_settings.smb_mount_point)) else "not_mounted" if backup_settings.smb_enabled else "disabled"
        },
        "nfs": {
            "enabled": backup_settings.nfs_enabled,
            "host": backup_settings.nfs_host or "",
            "export": backup_settings.nfs_export or "",
            "mount_point": backup_settings.nfs_mount_point or "/mnt/nfs_backups",
            "status": "active" if (backup_settings.nfs_enabled and os.path.ismount(backup_settings.nfs_mount_point)) else "not_mounted" if backup_settings.nfs_enabled else "disabled"
        },
        "retention_days": backup_settings.backup_retention_days
    }


@router.put("/backup-config")
async def update_backup_config(
    config: dict,
    request: Request,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Update backup configuration and write to .env file"""
    try:
        # Path to .env file
        env_path = "/app/../.env"

        # Read existing .env file or create from .env.example
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                env_lines = f.readlines()
        elif os.path.exists("/app/../.env.example"):
            with open("/app/../.env.example", 'r') as f:
                env_lines = f.readlines()
        else:
            env_lines = []

        # Parse existing env vars
        env_vars = {}
        for line in env_lines:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()

        # Update SMB settings
        if 'smb' in config:
            env_vars['SMB_BACKUP_ENABLED'] = str(config['smb'].get('enabled', False)).lower()
            if config['smb'].get('enabled'):
                env_vars['SMB_HOST'] = config['smb'].get('host', '')
                env_vars['SMB_SHARE'] = config['smb'].get('share', '')
                env_vars['SMB_USERNAME'] = config['smb'].get('username', '')
                if config['smb'].get('password'):
                    env_vars['SMB_PASSWORD'] = config['smb']['password']
                env_vars['SMB_MOUNT_POINT'] = config['smb'].get('mount_point', '/mnt/smb_backups')

        # Update NFS settings
        if 'nfs' in config:
            env_vars['NFS_BACKUP_ENABLED'] = str(config['nfs'].get('enabled', False)).lower()
            if config['nfs'].get('enabled'):
                env_vars['NFS_HOST'] = config['nfs'].get('host', '')
                env_vars['NFS_EXPORT'] = config['nfs'].get('export', '')
                env_vars['NFS_MOUNT_POINT'] = config['nfs'].get('mount_point', '/mnt/nfs_backups')

        # Update retention days
        if 'retention_days' in config:
            env_vars['BACKUP_RETENTION_DAYS'] = str(config['retention_days'])

        # Ensure required vars exist
        if 'DATABASE_URL' not in env_vars:
            env_vars['DATABASE_URL'] = 'postgresql+asyncpg://postgres:postgres@db:5432/webapp'
        if 'BACKUP_DIR' not in env_vars:
            env_vars['BACKUP_DIR'] = '/app/backups'
        if 'SECRET_KEY' not in env_vars:
            env_vars['SECRET_KEY'] = 'your-secret-key-change-this-in-production'

        # Write updated .env file
        with open(env_path, 'w') as f:
            f.write("# Database Configuration\n")
            f.write(f"DATABASE_URL={env_vars.get('DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@db:5432/webapp')}\n")
            f.write("\n# Backup Configuration\n")
            f.write(f"BACKUP_DIR={env_vars.get('BACKUP_DIR', '/app/backups')}\n")
            f.write(f"BACKUP_RETENTION_DAYS={env_vars.get('BACKUP_RETENTION_DAYS', '30')}\n")
            f.write("\n# SMB/CIFS File Share Configuration\n")
            f.write(f"SMB_BACKUP_ENABLED={env_vars.get('SMB_BACKUP_ENABLED', 'false')}\n")
            f.write(f"SMB_HOST={env_vars.get('SMB_HOST', 'your-smb-server.local')}\n")
            f.write(f"SMB_SHARE={env_vars.get('SMB_SHARE', 'backups')}\n")
            f.write(f"SMB_USERNAME={env_vars.get('SMB_USERNAME', 'backup_user')}\n")
            f.write(f"SMB_PASSWORD={env_vars.get('SMB_PASSWORD', 'your_secure_password')}\n")
            f.write(f"SMB_MOUNT_POINT={env_vars.get('SMB_MOUNT_POINT', '/mnt/smb_backups')}\n")
            f.write("\n# NFS File Share Configuration\n")
            f.write(f"NFS_BACKUP_ENABLED={env_vars.get('NFS_BACKUP_ENABLED', 'false')}\n")
            f.write(f"NFS_HOST={env_vars.get('NFS_HOST', 'your-nfs-server.local')}\n")
            f.write(f"NFS_EXPORT={env_vars.get('NFS_EXPORT', '/exports/backups')}\n")
            f.write(f"NFS_MOUNT_POINT={env_vars.get('NFS_MOUNT_POINT', '/mnt/nfs_backups')}\n")
            f.write("\n# Security\n")
            f.write(f"SECRET_KEY={env_vars.get('SECRET_KEY', 'your-secret-key-change-this-in-production')}\n")

        # Log the configuration change
        await log_action(
            db, "WARNING", "Backup configuration updated",
            user_id=current_admin.id, action="backup_config_updated",
            details={
                "smb_enabled": config.get('smb', {}).get('enabled', False),
                "nfs_enabled": config.get('nfs', {}).get('enabled', False)
            },
            ip_address=request.client.host if request else None
        )

        return {
            "message": "Backup configuration updated successfully. Container restart required for changes to take effect.",
            "restart_required": True
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update backup configuration: {str(e)}"
        )


def copy_to_file_shares(filepath: str, filename: str) -> List[str]:
    """Copy backup to configured file shares (SMB and NFS)."""
    destinations = []

    # Copy to SMB share if enabled
    if backup_settings.smb_enabled and os.path.ismount(backup_settings.smb_mount_point):
        try:
            smb_dest = os.path.join(backup_settings.smb_mount_point, filename)
            shutil.copy2(filepath, smb_dest)
            destinations.append(f"SMB: {smb_dest}")
        except Exception as e:
            destinations.append(f"SMB: Failed - {str(e)}")

    # Copy to NFS share if enabled
    if backup_settings.nfs_enabled and os.path.ismount(backup_settings.nfs_mount_point):
        try:
            nfs_dest = os.path.join(backup_settings.nfs_mount_point, filename)
            shutil.copy2(filepath, nfs_dest)
            destinations.append(f"NFS: {nfs_dest}")
        except Exception as e:
            destinations.append(f"NFS: Failed - {str(e)}")

    return destinations


def generate_key_from_password(password: str, salt: bytes = None) -> tuple[bytes, bytes]:
    """Generate encryption key from password using PBKDF2."""
    if salt is None:
        salt = os.urandom(16)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt


def encrypt_file(filepath: str, password: str) -> str:
    """Encrypt a file with password and return encrypted filepath."""
    # Read the original file
    with open(filepath, 'rb') as f:
        data = f.read()

    # Generate encryption key from password
    key, salt = generate_key_from_password(password)
    fernet = Fernet(key)

    # Encrypt the data
    encrypted_data = fernet.encrypt(data)

    # Save encrypted file with .encrypted extension
    encrypted_filepath = f"{filepath}.encrypted"
    with open(encrypted_filepath, 'wb') as f:
        # Write salt first (needed for decryption)
        f.write(salt)
        # Then write encrypted data
        f.write(encrypted_data)

    return encrypted_filepath


def decrypt_file(encrypted_filepath: str, password: str) -> str:
    """Decrypt a file with password and return decrypted filepath."""
    # Read the encrypted file
    with open(encrypted_filepath, 'rb') as f:
        # Read salt (first 16 bytes)
        salt = f.read(16)
        # Read encrypted data
        encrypted_data = f.read()

    # Generate key from password using the same salt
    key, _ = generate_key_from_password(password, salt)
    fernet = Fernet(key)

    # Decrypt the data
    try:
        decrypted_data = fernet.decrypt(encrypted_data)
    except Exception as e:
        raise ValueError("Incorrect password or corrupted file")

    # Save decrypted file (remove .encrypted extension)
    if encrypted_filepath.endswith('.encrypted'):
        decrypted_filepath = encrypted_filepath[:-10]  # Remove .encrypted
    else:
        decrypted_filepath = f"{encrypted_filepath}.decrypted"

    with open(decrypted_filepath, 'wb') as f:
        f.write(decrypted_data)

    return decrypted_filepath


def create_config_backup(filepath: str) -> dict:
    """Create a backup of application configuration."""
    config_data = {
        "version": APP_VERSION,
        "backup_timestamp": datetime.utcnow().isoformat(),
        "backup_settings": {
            "backup_dir": backup_settings.backup_dir,
            "backup_retention_days": backup_settings.backup_retention_days,
            "smb_enabled": backup_settings.smb_enabled,
            "smb_host": backup_settings.smb_host if backup_settings.smb_enabled else None,
            "smb_share": backup_settings.smb_share if backup_settings.smb_enabled else None,
            "smb_mount_point": backup_settings.smb_mount_point if backup_settings.smb_enabled else None,
            "nfs_enabled": backup_settings.nfs_enabled,
            "nfs_host": backup_settings.nfs_host if backup_settings.nfs_enabled else None,
            "nfs_export": backup_settings.nfs_export if backup_settings.nfs_enabled else None,
            "nfs_mount_point": backup_settings.nfs_mount_point if backup_settings.nfs_enabled else None,
        },
        "environment": {
            "database_url": os.getenv("DATABASE_URL", "").replace(
                os.getenv("PGPASSWORD", "postgres"), "***REDACTED***"
            ) if os.getenv("DATABASE_URL") else None,
        },
        "docker_files": {}
    }

    # Read docker-compose.yml if it exists
    docker_compose_path = "/app/../docker-compose.yml"
    if os.path.exists(docker_compose_path):
        try:
            with open(docker_compose_path, 'r') as f:
                config_data["docker_files"]["docker-compose.yml"] = f.read()
        except Exception:
            pass

    # Read Dockerfile if it exists
    dockerfile_path = "/app/../Dockerfile"
    if os.path.exists(dockerfile_path):
        try:
            with open(dockerfile_path, 'r') as f:
                config_data["docker_files"]["Dockerfile"] = f.read()
        except Exception:
            pass

    # Read .env.example if it exists (don't read actual .env for security)
    env_example_path = "/app/../.env.example"
    if os.path.exists(env_example_path):
        try:
            with open(env_example_path, 'r') as f:
                config_data["docker_files"][".env.example"] = f.read()
        except Exception:
            pass

    # Write configuration backup as JSON
    with open(filepath, 'w') as f:
        json.dump(config_data, f, indent=2)

    return config_data


@router.post("/backups", response_model=BackupResponse)
async def create_backup(
    backup_data: BackupCreate,
    request: Request,
    current_admin: User = Depends(require_permission("backups:write")),
    db: AsyncSession = Depends(get_db)
):
    """Create a new backup to local disk and configured file shares"""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    # Determine file extension based on backup type
    if backup_data.backup_type == "config":
        filename = f"backup_config_{timestamp}.json"
    else:
        filename = f"backup_{backup_data.backup_type}_{timestamp}.sql"

    # Use configured backup directory
    backup_dir = backup_settings.backup_dir
    os.makedirs(backup_dir, exist_ok=True)
    filepath = os.path.join(backup_dir, filename)

    try:
        if backup_data.backup_type == "database":
            # Database backup using pg_dump
            subprocess.run(
                [
                    "pg_dump",
                    "-h", "db",
                    "-U", "postgres",
                    "-d", "webapp",
                    "-f", filepath
                ],
                check=True,
                env={**os.environ, "PGPASSWORD": "postgres"}
            )
        elif backup_data.backup_type == "config":
            # Configuration backup
            create_config_backup(filepath)
        elif backup_data.backup_type == "full":
            # Full backup: both database and config
            # Create database backup
            db_filename = f"backup_database_{timestamp}.sql"
            db_filepath = os.path.join(backup_dir, db_filename)
            subprocess.run(
                [
                    "pg_dump",
                    "-h", "db",
                    "-U", "postgres",
                    "-d", "webapp",
                    "-f", db_filepath
                ],
                check=True,
                env={**os.environ, "PGPASSWORD": "postgres"}
            )

            # Create config backup
            config_filename = f"backup_config_{timestamp}.json"
            config_filepath = os.path.join(backup_dir, config_filename)
            create_config_backup(config_filepath)

            # Copy both files to file shares
            db_share_destinations = copy_to_file_shares(db_filepath, db_filename)
            config_share_destinations = copy_to_file_shares(config_filepath, config_filename)

            # Combine file share destinations
            file_share_destinations = []
            if db_share_destinations:
                file_share_destinations.extend([f"DB: {dest}" for dest in db_share_destinations])
            if config_share_destinations:
                file_share_destinations.extend([f"Config: {dest}" for dest in config_share_destinations])

            # Use database file as primary filepath for record
            filepath = db_filepath
            filename = db_filename
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid backup type. Must be 'database', 'config', or 'full'"
            )

        # Get file size
        file_size = os.path.getsize(filepath)

        # Copy to file shares if configured (for database and config backups only)
        # Full backup already handled above
        if backup_data.backup_type != "full":
            file_share_destinations = copy_to_file_shares(filepath, filename)
        # file_share_destinations already set for full backups

        # Create backup record
        backup_record = Backup(
            filename=filename,
            backup_type=backup_data.backup_type,
            file_size=file_size,
            created_by=current_admin.id,
            status="completed"
        )

        db.add(backup_record)
        await db.commit()
        await db.refresh(backup_record)

        # Log the action with file share info
        log_details = {
            "backup_id": backup_record.id,
            "file_size": file_size,
            "primary_location": filepath
        }
        if file_share_destinations:
            log_details["file_shares"] = file_share_destinations

        await log_action(
            db, "INFO", f"Backup created: {filename}",
            user_id=current_admin.id, action="backup_created",
            details=log_details,
            ip_address=request.client.host
        )

        return backup_record

    except subprocess.CalledProcessError as e:
        # Log the error
        await log_action(
            db, "ERROR", f"Backup creation failed: {str(e)}",
            user_id=current_admin.id, action="backup_failed",
            ip_address=request.client.host
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backup creation failed: {str(e)}"
        )


@router.get("/backups/{backup_id}/download")
async def download_backup(
    backup_id: int,
    password: Optional[str] = None,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Download a backup file, optionally encrypted with password."""
    # Get backup record
    result = await db.execute(select(Backup).where(Backup.id == backup_id))
    backup = result.scalar_one_or_none()

    if not backup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup not found"
        )

    # Construct file path
    filepath = os.path.join(backup_settings.backup_dir, backup.filename)

    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup file not found on disk"
        )

    # If password provided, encrypt the file first
    if password:
        try:
            encrypted_filepath = encrypt_file(filepath, password)
            download_filepath = encrypted_filepath
            download_filename = f"{backup.filename}.encrypted"

            # Log the action
            await log_action(
                db, "INFO", f"Backup {backup.filename} downloaded (encrypted)",
                user_id=current_admin.id, action="backup_download",
                details={"backup_id": backup_id, "encrypted": True}
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Encryption failed: {str(e)}"
            )
    else:
        download_filepath = filepath
        download_filename = backup.filename

        # Log the action
        await log_action(
            db, "INFO", f"Backup {backup.filename} downloaded",
            user_id=current_admin.id, action="backup_download",
            details={"backup_id": backup_id, "encrypted": False}
        )

    # Return file for download
    return FileResponse(
        path=download_filepath,
        filename=download_filename,
        media_type="application/octet-stream"
    )


@router.post("/backups/restore")
async def restore_backup(
    backup_file: UploadFile = File(...),
    password: Optional[str] = None,
    create_snapshot: bool = True,
    request: Request = None,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Restore database from uploaded backup file with automatic snapshot creation."""
    temp_dir = backup_settings.backup_dir
    os.makedirs(temp_dir, exist_ok=True)

    # Save uploaded file
    temp_filepath = os.path.join(temp_dir, f"restore_temp_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.sql")
    snapshot_filename = None
    snapshot_backup_id = None

    try:
        # Step 1: Create snapshot of current database before restoring
        if create_snapshot:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            snapshot_filename = f"snapshot_before_restore_{timestamp}.sql"
            snapshot_filepath = os.path.join(backup_settings.backup_dir, snapshot_filename)

            # Create snapshot backup
            snapshot_result = subprocess.run(
                [
                    "pg_dump",
                    "-h", "db",
                    "-U", "postgres",
                    "-d", "webapp",
                    "-f", snapshot_filepath
                ],
                check=True,
                env={**os.environ, "PGPASSWORD": "postgres"},
                capture_output=True,
                text=True
            )

            if snapshot_result.returncode != 0:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to create snapshot backup: {snapshot_result.stderr}"
                )

            # Get file size and create backup record
            snapshot_file_size = os.path.getsize(snapshot_filepath)
            snapshot_record = Backup(
                filename=snapshot_filename,
                backup_type="snapshot",
                file_size=snapshot_file_size,
                created_by=current_admin.id,
                status="completed"
            )
            db.add(snapshot_record)
            await db.commit()
            await db.refresh(snapshot_record)
            snapshot_backup_id = snapshot_record.id

            # Log snapshot creation
            await log_action(
                db, "INFO", f"Snapshot backup created before restore: {snapshot_filename}",
                user_id=current_admin.id, action="snapshot_created",
                details={
                    "backup_id": snapshot_backup_id,
                    "file_size": snapshot_file_size,
                    "reason": "pre-restore snapshot"
                },
                ip_address=request.client.host if request else None
            )

        # Step 2: Write uploaded file to disk
        with open(temp_filepath, 'wb') as f:
            content = await backup_file.read()
            f.write(content)

        # Step 3: If file is encrypted, decrypt it first
        restore_filepath = temp_filepath
        if password or temp_filepath.endswith('.encrypted'):
            if not password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Password required for encrypted backup"
                )

            try:
                restore_filepath = decrypt_file(temp_filepath, password)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )

        # Step 4: Restore database using psql
        result = subprocess.run(
            [
                "psql",
                "-h", "db",
                "-U", "postgres",
                "-d", "webapp",
                "-f", restore_filepath
            ],
            env={**os.environ, "PGPASSWORD": "postgres"},
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            # Restore failed - inform user about snapshot
            error_msg = f"Database restore failed: {result.stderr}"
            if snapshot_filename:
                error_msg += f"\n\nA snapshot backup was created before the restore attempt: {snapshot_filename} (ID: {snapshot_backup_id}). You can use this to restore to the previous state."
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )

        # Step 5: Log successful restore
        await log_action(
            db, "WARNING", f"Database restored from uploaded backup",
            user_id=current_admin.id, action="backup_restored",
            details={
                "filename": backup_file.filename,
                "encrypted": bool(password),
                "snapshot_created": create_snapshot,
                "snapshot_id": snapshot_backup_id if create_snapshot else None
            },
            ip_address=request.client.host if request else None
        )

        response_data = {
            "message": "Database restored successfully",
            "filename": backup_file.filename
        }

        if snapshot_filename:
            response_data["snapshot"] = {
                "id": snapshot_backup_id,
                "filename": snapshot_filename,
                "message": "A snapshot of the previous database state was created and can be used to roll back if needed"
            }

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Restore failed: {str(e)}"
        if snapshot_filename:
            error_msg += f"\n\nA snapshot backup was created: {snapshot_filename} (ID: {snapshot_backup_id})"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )
    finally:
        # Clean up temporary files
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        if password and restore_filepath != temp_filepath and os.path.exists(restore_filepath):
            os.remove(restore_filepath)


@router.get("/system-info")
async def get_system_info(
    current_user: User = Depends(require_permission("system:read"))
):
    """Get system information"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            "cpu_usage": f"{cpu_percent}%",
            "memory_usage": f"{memory.percent}%",
            "memory_total": f"{memory.total / (1024**3):.2f} GB",
            "memory_available": f"{memory.available / (1024**3):.2f} GB",
            "disk_usage": f"{disk.percent}%",
            "disk_total": f"{disk.total / (1024**3):.2f} GB",
            "disk_free": f"{disk.free / (1024**3):.2f} GB"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system info: {str(e)}"
        )


@router.get("/version")
async def get_version(
    current_admin: User = Depends(get_current_admin_user)
):
    """Get current application version and check for updates."""
    try:
        # Get current version
        current_version = APP_VERSION

        # Check for latest version from GitHub
        latest_version = None
        update_available = False

        try:
            import requests
            response = requests.get(
                "https://api.github.com/repos/your-org/web-platform/releases/latest",
                timeout=5
            )
            if response.status_code == 200:
                release_data = response.json()
                latest_version = release_data.get("tag_name", "").lstrip("v")

                # Compare versions
                if latest_version and latest_version != current_version:
                    update_available = True
        except Exception as e:
            print(f"Failed to check for updates: {e}")

        return {
            "current_version": current_version,
            "latest_version": latest_version,
            "update_available": update_available,
            "github_repo": "your-org/web-platform"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get version info: {str(e)}"
        )


@router.get("/releases")
async def get_all_releases(
    current_admin: User = Depends(get_current_admin_user)
):
    """Get all available releases from GitHub."""
    try:
        import requests
        response = requests.get(
            "https://api.github.com/repos/your-org/web-platform/releases",
            timeout=10
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to fetch releases from GitHub: {response.status_code}"
            )

        releases = response.json()
        release_list = []

        for release in releases:
            version = release.get("tag_name", "").lstrip("v")
            release_list.append({
                "version": version,
                "name": release.get("name", version),
                "published_at": release.get("published_at", ""),
                "body": release.get("body", "No release notes available"),
                "prerelease": release.get("prerelease", False),
                "is_current": version == APP_VERSION
            })

        return {
            "current_version": APP_VERSION,
            "releases": release_list
        }
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to connect to GitHub: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch releases: {str(e)}"
        )


@router.post("/update")
async def trigger_update(
    update_request: UpdateRequest,
    request: Request,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger application update to a specific version.
    Works with Docker-based deployments by updating the image tag and restarting containers.
    Creates a snapshot backup before the update for safety.
    """
    try:
        target_version = update_request.version

        # Log the update initiation
        await log_action(
            db, "WARNING", f"Application update to version {target_version} initiated",
            user_id=current_admin.id, action="update_initiated",
            ip_address=request.client.host if request else None
        )

        # Create automatic backup before update
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        snapshot_filename = f"snapshot_before_update_{target_version}_{timestamp}.sql"
        snapshot_filepath = os.path.join(backup_settings.backup_dir, snapshot_filename)

        # Create database snapshot
        snapshot_result = subprocess.run(
            [
                "pg_dump",
                "-h", "db",
                "-U", "postgres",
                "-d", "webapp",
                "-f", snapshot_filepath
            ],
            check=True,
            env={**os.environ, "PGPASSWORD": "postgres"},
            capture_output=True,
            text=True
        )

        if snapshot_result.returncode != 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create snapshot backup: {snapshot_result.stderr}"
            )

        # Get file size and create backup record
        snapshot_file_size = os.path.getsize(snapshot_filepath)
        snapshot_record = Backup(
            filename=snapshot_filename,
            backup_type="snapshot",
            file_size=snapshot_file_size,
            created_by=current_admin.id,
            status="completed"
        )
        db.add(snapshot_record)
        await db.commit()
        await db.refresh(snapshot_record)

        # Create update script that can be run from host or inside container (if Docker socket mounted)
        # Save to backups directory so it's accessible from host
        update_script_path = os.path.join(backup_settings.backup_dir, f"update_to_{target_version}.sh")

        with open(update_script_path, 'w') as f:
            f.write(f"""#!/bin/bash
# Web Platformlication Update Script
# Target Version: {target_version}
# Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC
#
# USAGE:
#   From host machine: cd /path/to/my-web-app && bash backups/update_to_{target_version}.sh
#
# This script will:
#   1. Update docker-compose.yml to use version v{target_version}
#   2. Pull the new Docker image
#   3. Run any pending database migrations
#   4. Recreate the web container with the new version
#   5. Rollback automatically if anything fails

set -e

TARGET_VERSION="{target_version}"
IMAGE_TAG="v${{TARGET_VERSION}}"
COMPOSE_FILE="docker-compose.yml"

echo "========================================="
echo "Web Platform Update Script"
echo "Target Version: ${{TARGET_VERSION}}"
echo "========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "ERROR: docker-compose.yml not found in current directory"
    echo "Please run this script from the my-web-app directory:"
    echo "  cd /path/to/my-web-app && bash backups/update_to_{target_version}.sh"
    exit 1
fi

# Check if docker and docker-compose are available
if ! command -v docker &> /dev/null; then
    echo "ERROR: docker command not found. Please install Docker."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
    echo "ERROR: docker-compose not found. Please install docker-compose."
    exit 1
fi

# Use docker-compose or docker compose
DOCKER_COMPOSE="docker-compose"
if ! command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
fi

echo "Step 1: Backing up docker-compose.yml..."
cp docker-compose.yml docker-compose.yml.backup

echo "Step 2: Updating image tag to ${{IMAGE_TAG}}..."
# Update image tag in docker-compose.yml
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s|image: your-org/web-platform:v[0-9.]*|image: your-org/web-platform:${{IMAGE_TAG}}|g" docker-compose.yml
else
    # Linux
    sed -i "s|image: your-org/web-platform:v[0-9.]*|image: your-org/web-platform:${{IMAGE_TAG}}|g" docker-compose.yml
fi

echo "Step 3: Pulling Docker image your-org/web-platform:${{IMAGE_TAG}}..."
if ! docker pull your-org/web-platform:${{IMAGE_TAG}}; then
    echo "ERROR: Failed to pull image. Version ${{TARGET_VERSION}} may not exist on Docker Hub."
    echo "Restoring backup..."
    mv docker-compose.yml.backup docker-compose.yml
    exit 1
fi

echo "Step 4: Running database migrations..."
if [ -d "./migrations" ]; then
    for migration_file in ./migrations/*.sql; do
        if [ -f "$migration_file" ]; then
            echo "  Applying: $(basename $migration_file)"
            docker exec webapp-db psql -U postgres -d webapp < "$migration_file" 2>&1 | grep -v "already exists" | grep -v "duplicate" || true
        fi
    done
    echo "  Migrations complete"
else
    echo "  No migrations directory found, skipping"
fi

echo "Step 5: Restarting web container with new version..."
$DOCKER_COMPOSE up -d --no-deps --force-recreate web

echo "Step 6: Waiting for application to start..."
sleep 5

# Check if container is running
if docker ps --filter "name=webapp-web" --filter "status=running" | grep -q webapp-web; then
    echo ""
    echo "========================================="
    echo "SUCCESS! Update complete"
    echo "Application is now running version ${{TARGET_VERSION}}"
    echo "========================================="
    echo ""
    echo "Backup file saved: docker-compose.yml.backup"
    echo "You can remove it once you've verified the update: rm docker-compose.yml.backup"
    exit 0
else
    echo ""
    echo "========================================="
    echo "ERROR: Container failed to start"
    echo "========================================="
    echo ""
    echo "Rolling back to previous version..."
    mv docker-compose.yml.backup docker-compose.yml
    $DOCKER_COMPOSE up -d --no-deps web
    echo "Rollback complete. Please check the logs: docker logs webapp-web"
    exit 1
fi
""")

        # Make script executable
        os.chmod(update_script_path, 0o755)

        # Determine if we can auto-update (check if docker socket is accessible)
        can_auto_update = os.path.exists("/var/run/docker.sock")

        update_script_name = f"update_to_{target_version}.sh"

        if can_auto_update:
            # Try to execute update automatically
            try:
                # Execute update script in background
                log_file_path = os.path.join(backup_settings.backup_dir, f"update_{target_version}.log")
                subprocess.Popen(
                    ["/bin/bash", update_script_path],
                    stdout=open(log_file_path, "w"),
                    stderr=subprocess.STDOUT,
                    start_new_session=True
                )

                # Log successful update trigger
                await log_action(
                    db, "WARNING", f"Automatic update to version {target_version} initiated. Snapshot backup: {snapshot_filename}",
                    user_id=current_admin.id, action="update_auto_triggered",
                    details={"snapshot_id": snapshot_record.id, "target_version": target_version, "update_script": update_script_name},
                    ip_address=request.client.host if request else None
                )

                return {
                    "message": f"Update to version {target_version} initiated. Application will restart automatically in a few moments.",
                    "target_version": target_version,
                    "update_mode": "automatic",
                    "update_log": f"backups/update_{target_version}.log",
                    "snapshot": {
                        "id": snapshot_record.id,
                        "filename": snapshot_filename,
                        "message": "A snapshot backup was created before the update"
                    }
                }
            except Exception as e:
                # Fall back to manual mode if auto-update fails
                can_auto_update = False

        # Manual update mode
        if not can_auto_update:
            # Log manual update preparation
            await log_action(
                db, "INFO", f"Update script generated for version {target_version}. Manual execution required.",
                user_id=current_admin.id, action="update_manual_prepared",
                details={"snapshot_id": snapshot_record.id, "target_version": target_version, "update_script": update_script_name},
                ip_address=request.client.host if request else None
            )

            # Get the absolute path hint for the user
            backup_dir_hint = backup_settings.backup_dir.replace("/app/", "")

            return {
                "message": f"Update prepared for version {target_version}. Please run the update script manually.",
                "target_version": target_version,
                "update_mode": "manual",
                "instructions": [
                    "A snapshot backup has been created for safety.",
                    f"To complete the update, run this command from your my-web-app directory:",
                    f"  bash {backup_dir_hint}/{update_script_name}",
                    "",
                    "The script will:",
                    "  1. Update docker-compose.yml to use the new version",
                    "  2. Pull the new Docker image",
                    "  3. Run database migrations",
                    "  4. Restart the application",
                    "  5. Rollback automatically if anything fails"
                ],
                "update_script": update_script_name,
                "snapshot": {
                    "id": snapshot_record.id,
                    "filename": snapshot_filename,
                    "message": "A snapshot backup was created before the update"
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Update failed: {str(e)}"
        )


@router.get("/update-status")
async def get_update_status(
    current_admin: User = Depends(get_current_admin_user)
):
    """Get the status of the last update operation."""
    try:
        # Check if update script is running
        result = subprocess.run(
            ["pgrep", "-f", "update_app.sh"],
            capture_output=True,
            text=True
        )

        is_updating = result.returncode == 0

        # Check if update log exists
        update_log_path = "/tmp/update_app.log"
        log_output = ""
        if os.path.exists(update_log_path):
            with open(update_log_path, 'r') as f:
                log_output = f.read()

        return {
            "is_updating": is_updating,
            "log_output": log_output,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get update status: {str(e)}"
        )


# ─── Certificate Management ───────────────────────────────────────────────────

CERTS_DIR = Path(os.getenv("CERTS_DIR", "/app/certs"))


def _parse_pem_cert(pem_bytes: bytes) -> dict:
    """Parse a PEM certificate and return human-readable metadata."""
    from cryptography import x509
    cert = x509.load_pem_x509_certificate(pem_bytes)
    now = datetime.utcnow()
    try:
        expires = cert.not_valid_after_utc.replace(tzinfo=None)
        not_before = cert.not_valid_before_utc.replace(tzinfo=None)
    except AttributeError:
        # Fallback for older cryptography versions
        expires = cert.not_valid_after
        not_before = cert.not_valid_before
    return {
        "subject": cert.subject.rfc4514_string(),
        "issuer": cert.issuer.rfc4514_string(),
        "not_valid_before": not_before.isoformat(),
        "not_valid_after": expires.isoformat(),
        "days_remaining": (expires - now).days,
        "is_expired": now > expires,
        "serial_number": str(cert.serial_number),
    }


@router.get("/certs")
async def get_cert_status(
    current_admin: User = Depends(get_current_admin_user),
):
    """Return TLS certificate status from /app/certs/cert.pem."""
    cert_path = CERTS_DIR / "cert.pem"
    if not cert_path.exists():
        return {"present": False}
    try:
        info = _parse_pem_cert(cert_path.read_bytes())
        return {"present": True, **info}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to parse certificate: {exc}")


@router.post("/certs/upload")
async def upload_cert(
    cert_file: UploadFile = File(...),
    key_file: UploadFile = File(None),
    passphrase: str = None,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    """Upload a TLS certificate (PEM, CRT, or PFX/P12) and optional private key."""
    CERTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = (cert_file.filename or "").lower()
    cert_bytes = await cert_file.read()

    # Size sanity check (max 64 KB)
    if len(cert_bytes) > 65536:
        raise HTTPException(status_code=400, detail="Certificate file too large (max 64 KB)")

    if filename.endswith((".pfx", ".p12")):
        # Convert PKCS#12 to PEM
        try:
            from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption
            pwd = passphrase.encode() if passphrase else None
            private_key, certificate, _ = pkcs12.load_key_and_certificates(cert_bytes, pwd)
            cert_pem = certificate.public_bytes(Encoding.PEM)
            key_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption()) if private_key else None
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to parse PFX: {exc}")
    elif filename.endswith((".pem", ".crt", ".cer")):
        cert_pem = cert_bytes
        key_pem = (await key_file.read()) if key_file else None
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use .pem, .crt, .pfx, or .p12")

    # Validate the certificate is parseable
    try:
        info = _parse_pem_cert(cert_pem)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid certificate: {exc}")

    # Write files
    (CERTS_DIR / "cert.pem").write_bytes(cert_pem)
    if key_pem:
        (CERTS_DIR / "key.pem").write_bytes(key_pem)

    await log_action(
        db, "INFO", "TLS certificate uploaded",
        user_id=current_admin.id, action="cert_uploaded",
        details={"subject": info["subject"], "expires": info["not_valid_after"]},
        ip_address=request.client.host if request else None,
    )
    return {"message": "Certificate uploaded successfully", "cert_info": {"present": True, **info}}


@router.post("/certs/renew")
async def trigger_cert_renewal(
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    """Signal Caddy to reload its configuration / renew certificates via the admin API."""
    import httpx
    caddy_admin = os.getenv("CADDY_ADMIN_URL", "http://caddy:2019")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(f"{caddy_admin}/load", content=b"{}", headers={"Content-Type": "application/json"})
        await log_action(
            db, "INFO", "Certificate renewal triggered via Caddy admin API",
            user_id=current_admin.id, action="cert_renew",
            ip_address=request.client.host if request else None,
        )
        return {"message": "Certificate renewal triggered", "caddy_status": resp.status_code}
    except Exception as exc:
        return {
            "message": f"Could not reach Caddy admin API ({caddy_admin}). Renewal may need to be triggered manually.",
            "error": str(exc),
        }


@router.delete("/certs")
async def remove_custom_cert(
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    """Remove the custom certificate from /app/certs. Caddy will fall back to ACME."""
    removed = []
    for name in ("cert.pem", "key.pem"):
        path = CERTS_DIR / name
        if path.exists():
            path.unlink()
            removed.append(name)
    await log_action(
        db, "WARNING", "Custom TLS certificate removed",
        user_id=current_admin.id, action="cert_removed",
        details={"removed_files": removed},
        ip_address=request.client.host if request else None,
    )
    return {"message": f"Removed: {', '.join(removed) if removed else 'nothing to remove'}"}
