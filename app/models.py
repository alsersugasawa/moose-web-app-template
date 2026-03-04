import uuid as uuid_module
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, JSON, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    permissions = Column(JSONB, nullable=False, default=list)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    permissions = Column(JSON, nullable=True)
    last_login = Column(DateTime, nullable=True)
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Phase 1: Email verification
    email_verified = Column(Boolean, default=False, nullable=False)
    email_verification_token = Column(String(128), nullable=True, index=True)
    email_verification_expires = Column(DateTime, nullable=True)

    # Phase 1: OAuth 2.0
    oauth_provider = Column(String(50), nullable=True)
    oauth_user_id = Column(String(255), nullable=True)

    # Phase 1: TOTP
    totp_secret = Column(String(64), nullable=True)
    totp_enabled = Column(Boolean, default=False, nullable=False)

    # Phase 2: RBAC
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True, index=True)
    role = relationship("Role", back_populates="users")

    # Phase 2: Profile
    display_name = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    avatar_path = Column(String(255), nullable=True)
    timezone = Column(String(50), nullable=True, default="UTC")
    language = Column(String(10), nullable=True, default="en")

    __table_args__ = (
        UniqueConstraint("oauth_provider", "oauth_user_id", name="uq_oauth_provider_user"),
    )


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100))
    details = Column(JSON, nullable=True)
    ip_address = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)


class Backup(Base):
    __tablename__ = "backups"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    backup_type = Column(String(50), nullable=False)
    file_size = Column(Integer)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="completed")
    created_at = Column(DateTime, default=datetime.utcnow)


class AppConfig(Base):
    __tablename__ = "app_config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(128), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", backref="password_reset_tokens")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    jti = Column(UUID(as_uuid=True), unique=True, nullable=False, index=True, default=uuid_module.uuid4)
    device_info = Column(String(512), nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)

    user = relationship("User", backref="sessions")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    key_hash = Column(String(255), nullable=False)
    key_prefix = Column(String(10), nullable=False, index=True)
    scopes = Column(JSONB, nullable=False, default=list)
    last_used = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", backref="api_keys")


class Invitation(Base):
    __tablename__ = "invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid_module.uuid4)
    token = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(100), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    used_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    used_at = Column(DateTime, nullable=True)

    creator = relationship("User", foreign_keys=[created_by], backref="created_invitations")
    consumer = relationship("User", foreign_keys=[used_by])


class FeatureFlag(Base):
    """Phase 3: Database-backed feature on/off switches."""
    __tablename__ = "feature_flags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    is_enabled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
