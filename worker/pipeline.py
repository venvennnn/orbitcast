"""Episode pipeline: research → script → TTS → upload."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from mutagen.mp3 import MP3

import db
import research
import storage
import tts

log = logging.getLogger("orbitcast.pipeline")


def _set_stage(conn, episode_id: str, stage: str, status: str = "processing") -> None:
    db.execute(
        conn,
        "UPDATE episodes SET status = %s::episode_status, stage = %s, error = NULL WHERE id = %s",
        (status, stage, episode_id),
    )


def process_episode(episode_id: str, *, force: bool = False) -> None:
    with db.db() as conn:
        ep = db.fetchone(conn, "SELECT * FROM episodes WHERE id = %s", (episode_id,))
        if not ep:
            log.error("episode %s not found", episode_id)
            return
        feed = db.fetchone(conn, "SELECT * FROM feeds WHERE id = %s", (ep["feed_id"],))
        if not feed:
            log.error("feed missing for episode %s", episode_id)
            return

        # Manual refresh rows are always force; cron-created rows allow skip.
        # Heuristic: if caller says force OR episode was created via refresh path
        # (we stamp force via stage marker). Default: allow skip unless force.
        prior = db.fetchall(
            conn,
            """
            SELECT script FROM episodes
            WHERE feed_id = %s AND status = 'completed' AND script IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 3
            """,
            (str(feed["id"]),),
        )
        prior_scripts = [r["script"] for r in prior if r.get("script")]

        try:
            _set_stage(conn, episode_id, "researching")
            conn.commit()

            _set_stage(conn, episode_id, "writing")
            conn.commit()

            result = research.generate_episode(
                feed["topic_prompt"],
                prior_scripts,
                force=force,
            )

            if result.get("skip"):
                db.execute(
                    conn,
                    """
                    UPDATE episodes
                    SET status = 'skipped', stage = 'skipped',
                        error = %s, title = 'Skipped', description = %s
                    WHERE id = %s
                    """,
                    (result.get("reason"), result.get("reason"), episode_id),
                )
                conn.commit()
                log.info("episode %s skipped: %s", episode_id, result.get("reason"))
                return

            db.execute(
                conn,
                """
                UPDATE episodes
                SET title = %s, description = %s, script = %s, stage = 'voicing'
                WHERE id = %s
                """,
                (result["title"], result["description"], result["script"], episode_id),
            )
            conn.commit()

            with tempfile.TemporaryDirectory() as tmp:
                mp3_path = Path(tmp) / f"{episode_id}.mp3"
                tts.synthesize(result["script"], mp3_path)
                duration = int(round(MP3(mp3_path).info.length))
                audio_bytes = mp3_path.stat().st_size

                _set_stage(conn, episode_id, "publishing")
                conn.commit()

                key = f"episodes/{feed['id']}/{episode_id}.mp3"
                audio_url = storage.upload_file(mp3_path, key, "audio/mpeg")

            db.execute(
                conn,
                """
                UPDATE episodes
                SET status = 'completed', stage = 'published',
                    audio_url = %s, audio_bytes = %s, duration_seconds = %s, error = NULL
                WHERE id = %s
                """,
                (audio_url, audio_bytes, duration, episode_id),
            )
            db.execute(
                conn,
                "UPDATE feeds SET last_generated_at = NOW() WHERE id = %s",
                (str(feed["id"]),),
            )
            conn.commit()
            log.info("episode %s completed → %s", episode_id, audio_url)

        except Exception as exc:
            log.exception("episode %s failed", episode_id)
            db.execute(
                conn,
                """
                UPDATE episodes
                SET status = 'failed', stage = 'failed', error = %s
                WHERE id = %s
                """,
                (str(exc)[:2000], episode_id),
            )
            conn.commit()
