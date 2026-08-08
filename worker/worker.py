"""OrbitCast worker — bare BRPOP loop against Valkey."""

from __future__ import annotations

import logging
import signal
import sys
import time

import redis

import config
import db
import pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("orbitcast.worker")

_running = True


def _stop(*_args) -> None:
    global _running
    _running = False


def main() -> int:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    if not config.REDIS_URL:
        log.error("REDIS_URL missing")
        return 1
    if not config.DATABASE_URL:
        log.error("DATABASE_URL missing")
        return 1

    r = redis.Redis.from_url(config.REDIS_URL, decode_responses=True)
    log.info("worker listening on %s", config.QUEUE_KEY)

    while _running:
        try:
            item = r.brpop(config.QUEUE_KEY, timeout=5)
            if not item:
                continue
            _, episode_id = item
            log.info("picked %s", episode_id)

            # Force generation if this episode has no prior completed siblings
            # OR if any 'force' flag — manual refresh always wants audio.
            # Manual refresh inserts queued rows after user action; we force
            # whenever the feed has been touched via refresh by checking
            # whether last_generated_at was just stamped AND we prefer force
            # for all non-cron jobs. Simplest honest rule: force=True always
            # for BRPOP jobs created by API refresh; cron sets ORBITCAST_ALLOW_SKIP.
            # We encode allow-skip by pushing "skipable:<id>" from cron and plain id from API.
            force = True
            if episode_id.startswith("skipable:"):
                force = False
                episode_id = episode_id.split(":", 1)[1]

            pipeline.process_episode(episode_id, force=force)
        except redis.ConnectionError as exc:
            log.error("redis connection error: %s — retry in 3s", exc)
            time.sleep(3)
        except Exception:
            log.exception("worker loop error")
            time.sleep(1)

    log.info("worker stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
