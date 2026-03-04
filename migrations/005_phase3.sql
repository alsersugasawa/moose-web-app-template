-- Phase 3: Developer Experience
-- Feature flags table

CREATE TABLE IF NOT EXISTS feature_flags (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(255),
    is_enabled  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_feature_flags_name ON feature_flags(name);

-- Seed default flags
INSERT INTO feature_flags (name, description, is_enabled) VALUES
    ('registration', 'Allow new user self-registration',    true),
    ('oauth_login',  'Allow OAuth2 social login',           true),
    ('api_keys',     'Allow users to generate API keys',    true),
    ('invitations',  'Allow admins to create invitations',  true)
ON CONFLICT (name) DO NOTHING;
