"""Schema migration — idempotent."""

from __future__ import annotations

import db

SCHEMA = """
CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$ BEGIN
  CREATE TYPE episode_status AS ENUM ('queued', 'processing', 'completed', 'failed', 'skipped');
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS feeds (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  topic_prompt TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  schedule_minutes INT NOT NULL DEFAULT 60,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  last_generated_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS episodes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  feed_id UUID NOT NULL REFERENCES feeds(id) ON DELETE CASCADE,
  title TEXT,
  description TEXT,
  script TEXT,
  audio_url TEXT,
  audio_bytes BIGINT,
  duration_seconds INT,
  status episode_status NOT NULL DEFAULT 'queued',
  stage TEXT,
  error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_episodes_feed_created ON episodes (feed_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feeds_active_schedule ON feeds (active, last_generated_at);
"""


if __name__ == "__main__":
    with db.db() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
    print("migrate ok")
