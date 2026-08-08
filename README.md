# OrbitCast

**Podcasts that don't go stale.** Type any topic → research → script → TTS → public MP3 → real RSS podcast feed. A cron keeps every active feed alive.

> Zerops Challenge · Aug 8–9, 2026  
> Live dashboard: https://web-13d.sea1.zerops.app  
> Live API: https://api-13d-8000.sea1.zerops.app

## How Zerops is used

| Service | Zerops piece | Job |
|---|---|---|
| `web` | Runtime (nginx) | Dashboard — vanilla JS + Tailwind CDN |
| `api` | Runtime (Python FastAPI) | CRUD, polling, RSS, refresh trigger |
| `db` | Managed PostgreSQL | feeds, episodes |
| `queue` | Managed Valkey | job broker (`BRPOP` / `LPUSH`) |
| `worker` | Runtime (Python) | research → script → TTS → upload |
| `cron` | Runtime + crontab | enqueue refresh per active feed |
| `objectstorage` | Object storage (S3/MinIO) | public MP3s + cover art |

Internal traffic on the private network; only `web` / `api` are public. Object storage uses a **public-read** bucket policy and direct object URLs (no expiring presigned URLs).

## Architecture (product loop)

1. Create a feed (or cron selects due active feeds).
2. Insert `episodes` row `status=queued` → `LPUSH orbitcast:jobs`.
3. Worker `BRPOP`s → stages: researching → writing → voicing → publishing.
4. Anthropic (`claude-haiku-4-5` + web_search) returns JSON script (change-aware vs last episodes; cron may `skip`).
5. `synthesize()` = **edge-tts** (pinned) with **OpenAI TTS** fallback.
6. Upload MP3 with `Content-Type: audio/mpeg` → mark completed.
7. `GET /feed/{slug}.xml` serves Apple-compatible RSS.

Manual `POST /feeds/{id}/refresh` always forces generation (demo-safe).

## Secrets (never commit)

Set as **Zerops project env** (not in git):

| Key | Required | Used by |
|---|---|---|
| `ANTHROPIC_API_KEY` | yes | worker research/script |
| `OPENAI_API_KEY` | optional | TTS fallback if edge-tts flakes |

Everything else is `${service_var}` wiring in each service's `zerops.yaml`.

## Repo layout

```
api/       FastAPI + RSS + feed CRUD
worker/    BRPOP pipeline
cron/      enqueue tick (crontab */5)
web/       dashboard
import.yaml
```

Each runtime folder has its own `zerops.yaml` (setup name = hostname). Deploy from that folder via Zerops / `zcli`.

## Local-ish smoke

Against a live project:

```bash
curl https://api-13d-8000.sea1.zerops.app/health
curl -X POST https://api-13d-8000.sea1.zerops.app/feeds \
  -H 'Content-Type: application/json' \
  -d '{"title":"Demo","topic_prompt":"…","schedule_minutes":60}'
```

## AI disclosure

Built with Cursor / ZCP agents on Zerops. Episode scripts: Anthropic Claude + web_search. Voice: edge-tts (Microsoft endpoint) with optional OpenAI TTS fallback. Dashboard / API / worker orchestration: human-directed AI-assisted implementation.

## Roadmap (not built)

Multi-source ingestion (GitHub/RSS/papers), personalized multi-topic briefings, source monitoring, two-host dialogue TTS, “Ask the podcast” over episode history.
