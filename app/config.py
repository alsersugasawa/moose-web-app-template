"""Application configuration for backup locations and settings."""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class BackupSettings(BaseSettings):
    """Backup configuration settings."""

    # Primary backup directory (local disk)
    # Default to /app/backups which the container has write access to
    backup_dir: str = os.getenv("BACKUP_DIR", "/app/backups")

    # SMB/CIFS file share settings
    smb_enabled: bool = os.getenv("SMB_BACKUP_ENABLED", "false").lower() == "true"
    smb_host: Optional[str] = os.getenv("SMB_HOST", None)
    smb_share: Optional[str] = os.getenv("SMB_SHARE", None)
    smb_username: Optional[str] = os.getenv("SMB_USERNAME", None)
    smb_password: Optional[str] = os.getenv("SMB_PASSWORD", None)
    smb_mount_point: str = os.getenv("SMB_MOUNT_POINT", "/mnt/smb_backups")

    # NFS file share settings
    nfs_enabled: bool = os.getenv("NFS_BACKUP_ENABLED", "false").lower() == "true"
    nfs_host: Optional[str] = os.getenv("NFS_HOST", None)
    nfs_export: Optional[str] = os.getenv("NFS_EXPORT", None)
    nfs_mount_point: str = os.getenv("NFS_MOUNT_POINT", "/mnt/nfs_backups")

    # Backup retention
    backup_retention_days: int = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
backup_settings = BackupSettings()
