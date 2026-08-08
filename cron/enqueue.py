"""Cron tick — enqueue refresh for active feeds past schedule_minutes."""

from __future__ import annotations

import logging
import sys

import db
import broker as jobqueue

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("orbitcast.cron")


def tick() -> int:
    with db.db() as conn:
        due = db.fetchall(
            conn,
            """
            SELECT * FROM feeds
            WHERE active = TRUE
              AND (
                last_generated_at IS NULL
                OR last_generated_at < NOW() - (schedule_minutes || ' minutes')::interval
              )
            """,
        )
        enqueued = 0
        for feed in due:
            ep = db.fetchone(
                conn,
                """
                INSERT INTO episodes (feed_id, status, stage)
                VALUES (%s, 'queued', 'queued')
                RETURNING *
                """,
                (str(feed["id"]),),
            )
            assert ep
            db.execute(
                conn,
                "UPDATE feeds SET last_generated_at = NOW() WHERE id = %s",
                (str(feed["id"]),),
            )
            # skipable: prefix → worker may return skipped when nothing new
            jobqueue.enqueue(f"skipable:{ep['id']}")
            enqueued += 1
            log.info("enqueued feed=%s episode=%s", feed["slug"], ep["id"])
    log.info("cron tick done — enqueued %s", enqueued)
    return enqueued


if __name__ == "__main__":
    try:
        tick()
    except Exception:
        log.exception("cron tick failed")
        sys.exit(1)
