-- Migration: Add app configuration table
-- This table stores application-wide settings like app name, branding, etc.

CREATE TABLE IF NOT EXISTS app_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_app_config_key ON app_config(key);

-- Insert default app name if not exists
INSERT INTO app_config (key, value)
VALUES ('app_name', 'Web Platform')
ON CONFLICT (key) DO NOTHING;
