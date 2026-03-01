-- Migration: Phase 2 — User Management & Access Control
-- Date: 2026-02-24
-- Description: RBAC roles, user profile fields, API keys, invitations

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── Roles table ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS roles (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(50) UNIQUE NOT NULL,
    permissions JSONB NOT NULL DEFAULT '[]',
    description VARCHAR(255),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_roles_name ON roles(name);

-- Seed default roles (idempotent)
INSERT INTO roles (name, permissions, description) VALUES
    ('viewer',  '[]',                                              'Read-only access to own data'),
    ('editor',  '[]',                                              'Can edit own content'),
    ('manager', '["users:read","logs:read","system:read"]',        'Team management permissions')
ON CONFLICT (name) DO NOTHING;

-- ─── RBAC: role FK on users ───────────────────────────────────────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS role_id INTEGER REFERENCES roles(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_users_role_id ON users(role_id) WHERE role_id IS NOT NULL;

-- ─── Profile fields on users ─────────────────────────────────────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS bio         TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_path VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone    VARCHAR(50) DEFAULT 'UTC';
ALTER TABLE users ADD COLUMN IF NOT EXISTS language    VARCHAR(10) DEFAULT 'en';

-- ─── API keys table ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS api_keys (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name       VARCHAR(100) NOT NULL,
    key_hash   VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(10) NOT NULL,
    scopes     JSONB NOT NULL DEFAULT '[]',
    last_used  TIMESTAMP,
    expires_at TIMESTAMP,
    is_active  BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_api_keys_user_id    ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_prefix ON api_keys(key_prefix);

-- ─── Invitations table ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS invitations (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token      VARCHAR(64) UNIQUE NOT NULL,
    email      VARCHAR(100),
    created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    used_by    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    used_at    TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_invitations_token      ON invitations(token);
CREATE INDEX IF NOT EXISTS idx_invitations_created_by ON invitations(created_by);
CREATE INDEX IF NOT EXISTS idx_invitations_unused     ON invitations(expires_at, used_at)
    WHERE used_at IS NULL;
