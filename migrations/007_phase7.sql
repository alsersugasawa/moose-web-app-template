-- Phase 7: File Storage

CREATE TABLE IF NOT EXISTS stored_files (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename      VARCHAR(255) NOT NULL,
    content_type  VARCHAR(100),
    size_bytes    INTEGER NOT NULL,
    s3_key        VARCHAR(1024) NOT NULL,
    thumbnail_key VARCHAR(1024),
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_stored_files_user_id ON stored_files(user_id);
