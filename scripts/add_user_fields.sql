-- Add missing user profile fields to users table
-- Ensures new bot features have the required columns.
ALTER TABLE IF EXISTS users
    ADD COLUMN IF NOT EXISTS thread_id VARCHAR NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS first_name VARCHAR,
    ADD COLUMN IF NOT EXISTS last_name VARCHAR,
    ADD COLUMN IF NOT EXISTS username VARCHAR,
    ADD COLUMN IF NOT EXISTS onboarding_complete BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS plan VARCHAR NOT NULL DEFAULT 'free',
    ADD COLUMN IF NOT EXISTS org_id INTEGER,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
