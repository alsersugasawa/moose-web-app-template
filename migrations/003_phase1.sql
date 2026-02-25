-- Migration: Phase 1 features
-- Date: 2026-02-20
-- Description: Email verification, password reset, OAuth 2.0, TOTP, session management

-- ─── Email verification fields on users ──────────────────────────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE NOT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verification_token VARCHAR(128);
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verification_expires TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_users_email_verification_token
    ON users(email_verification_token)
    WHERE email_verification_token IS NOT NULL;

-- ─── OAuth 2.0 fields on users ────────────────────────────────────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_provider VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS oauth_user_id VARCHAR(255);

CREATE UNIQUE INDEX IF NOT EXISTS uq_oauth_provider_user
    ON users(oauth_provider, oauth_user_id)
    WHERE oauth_provider IS NOT NULL AND oauth_user_id IS NOT NULL;

-- ─── TOTP fields on users ─────────────────────────────────────────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(64);
ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN DEFAULT FALSE NOT NULL;

-- ─── Password reset tokens ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token       VARCHAR(128) UNIQUE NOT NULL,
    expires_at  TIMESTAMP NOT NULL,
    used        BOOLEAN DEFAULT FALSE NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_prt_token   ON password_reset_tokens(token);
CREATE INDEX IF NOT EXISTS idx_prt_user_id ON password_reset_tokens(user_id);

-- ─── User sessions (active session management + JWT revocation) ───────────────
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS user_sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    jti         UUID UNIQUE NOT NULL,
    device_info VARCHAR(512),
    ip_address  VARCHAR(50),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_used   TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at  TIMESTAMP NOT NULL,
    is_revoked  BOOLEAN DEFAULT FALSE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_us_user_id    ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_us_jti        ON user_sessions(jti);
CREATE INDEX IF NOT EXISTS idx_us_active     ON user_sessions(expires_at, is_revoked)
    WHERE is_revoked = FALSE;

-- ─── Mark existing admin users as email-verified (bootstrapping) ──────────────
UPDATE users SET email_verified = TRUE WHERE is_admin = TRUE;
