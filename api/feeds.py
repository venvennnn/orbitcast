"""Feed / episode domain operations."""

from __future__ import annotations

import re
import uuid
from typing import Any

import db
import broker as jobqueue


def _slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")[:48] or "feed"
    return f"{s}-{uuid.uuid4().hex[:6]}"


def list_feeds() -> list[dict[str, Any]]:
    with db.db() as conn:
        feeds = db.fetchall(
            conn,
            """
            SELECT f.*,
              (SELECT COUNT(*) FROM episodes e WHERE e.feed_id = f.id) AS episode_count,
              (SELECT COUNT(*) FROM episodes e WHERE e.feed_id = f.id AND e.status = 'completed') AS completed_count,
              (SELECT e.status FROM episodes e WHERE e.feed_id = f.id ORDER BY e.created_at DESC LIMIT 1) AS latest_status,
              (SELECT e.stage FROM episodes e WHERE e.feed_id = f.id ORDER BY e.created_at DESC LIMIT 1) AS latest_stage,
              (SELECT e.error FROM episodes e WHERE e.feed_id = f.id ORDER BY e.created_at DESC LIMIT 1) AS latest_error,
              (SELECT e.id FROM episodes e WHERE e.feed_id = f.id ORDER BY e.created_at DESC LIMIT 1) AS latest_episode_id
            FROM feeds f
            ORDER BY f.created_at DESC
            """,
        )
        return feeds


def get_feed(feed_id: str) -> dict[str, Any] | None:
    with db.db() as conn:
        return db.fetchone(conn, "SELECT * FROM feeds WHERE id = %s", (feed_id,))


def get_feed_by_slug(slug: str) -> dict[str, Any] | None:
    with db.db() as conn:
        return db.fetchone(conn, "SELECT * FROM feeds WHERE slug = %s", (slug,))


def create_feed(title: str, topic_prompt: str, schedule_minutes: int = 60) -> dict[str, Any]:
    slug = _slugify(title)
    schedule_minutes = max(5, min(schedule_minutes, 10080))
    with db.db() as conn:
        feed = db.fetchone(
            conn,
            """
            INSERT INTO feeds (title, topic_prompt, slug, schedule_minutes, active)
            VALUES (%s, %s, %s, %s, TRUE)
            RETURNING *
            """,
            (title, topic_prompt, slug, schedule_minutes),
        )
        assert feed
        episode = _insert_queued(conn, str(feed["id"]))
        db.execute(
            conn,
            "UPDATE feeds SET last_generated_at = NOW() WHERE id = %s",
            (str(feed["id"]),),
        )
        jobqueue.enqueue(str(episode["id"]))  # plain id → worker force=True
        feed["latest_episode_id"] = episode["id"]
        return feed


def list_episodes(feed_id: str) -> list[dict[str, Any]]:
    with db.db() as conn:
        return db.fetchall(
            conn,
            "SELECT * FROM episodes WHERE feed_id = %s ORDER BY created_at DESC",
            (feed_id,),
        )


def completed_episodes(feed_id: str) -> list[dict[str, Any]]:
    with db.db() as conn:
        return db.fetchall(
            conn,
            """
            SELECT * FROM episodes
            WHERE feed_id = %s AND status = 'completed' AND audio_url IS NOT NULL
            ORDER BY created_at DESC
            """,
            (feed_id,),
        )


def _insert_queued(conn, feed_id: str) -> dict[str, Any]:
    ep = db.fetchone(
        conn,
        """
        INSERT INTO episodes (feed_id, status, stage)
        VALUES (%s, 'queued', 'queued')
        RETURNING *
        """,
        (feed_id,),
    )
    assert ep
    return ep


def refresh_feed(feed_id: str) -> dict[str, Any]:
    """Manual refresh — always force generation (never skip)."""
    with db.db() as conn:
        feed = db.fetchone(conn, "SELECT * FROM feeds WHERE id = %s", (feed_id,))
        if not feed:
            raise KeyError("feed not found")
        episode = _insert_queued(conn, feed_id)
        db.execute(
            conn,
            "UPDATE feeds SET last_generated_at = NOW() WHERE id = %s",
            (feed_id,),
        )
    jobqueue.enqueue(str(episode["id"]))
    return episode


def retry_episode(episode_id: str) -> dict[str, Any]:
    with db.db() as conn:
        ep = db.fetchone(conn, "SELECT * FROM episodes WHERE id = %s", (episode_id,))
        if not ep:
            raise KeyError("episode not found")
        if ep["status"] not in ("failed", "skipped"):
            raise ValueError("only failed/skipped episodes can be retried")
        db.execute(
            conn,
            """
            UPDATE episodes
            SET status = 'queued', stage = 'queued', error = NULL
            WHERE id = %s
            """,
            (episode_id,),
        )
        ep = db.fetchone(conn, "SELECT * FROM episodes WHERE id = %s", (episode_id,))
    assert ep
    jobqueue.enqueue(str(episode_id))
    return ep


def metrics() -> dict[str, Any]:
    with db.db() as conn:
        row = db.fetchone(
            conn,
            """
            SELECT
              (SELECT COUNT(*) FROM feeds WHERE active) AS active_feeds,
              (SELECT COUNT(*) FROM episodes) AS episodes_total,
              (SELECT COUNT(*) FROM episodes WHERE status = 'completed') AS episodes_completed,
              (SELECT COUNT(*) FROM episodes WHERE status = 'failed') AS episodes_failed,
              (SELECT COUNT(*) FROM episodes WHERE status = 'processing') AS episodes_processing,
              (SELECT COUNT(*) FROM episodes WHERE status = 'queued') AS episodes_queued,
              (SELECT COUNT(*) FROM episodes WHERE status = 'skipped') AS episodes_skipped
            """,
        )
    return {
        **(row or {}),
        "queue_depth": jobqueue.queue_depth(),
    }
