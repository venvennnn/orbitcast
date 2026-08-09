# OrbitCast
**Podcasts that don't go stale.** Type any topic → research → script → TTS → public MP3 → real RSS podcast feed. A cron keeps every active feed alive.

> Live Application: https://web-13d.sea1.zerops.app
 
> Live API: https://api-13d-8000.sea1.zerops.app

## TL;DR for judges
1. OrbitCast turns any topic into a living podcast: type a prompt once, get a real RSS feed that researches, writes, voices, and publishes episodes by itself.
2. Not another audio generator — the novelty is memory: each episode reads the previous scripts and covers only what *changed*, and if nothing episode-worthy happened, it logs a skip instead of publishing filler.
3. Output is standard RSS, so it plays in Apple Podcasts, AntennaPod, or any podcast app — no custom player, no account, no lock-in.
4. Seven Zerops services in one project: nginx web, FastAPI api, managed PostgreSQL, managed Valkey, a Python worker, a cron service, and S3 object storage, talking over the private network with only web/api public.
5. The pipeline is the product: cron enqueues due feeds → Valkey → worker BRPOPs → one Claude call (with built-in web search) writes a change-aware script → TTS → public MP3 in object storage → Apple-valid RSS.
6. Every stage updates Postgres, so the dashboard shows live chips (researching → writing → voicing → publishing) and failed jobs surface with the error and a retry — no silent zombies.
7. Flagship feed, **MSME Credit Pulse**, comes from my day job as an SME-lending data scientist: RBI circulars and credit data turned into a five-minute daily briefing, public sources cited in the show notes.
8. Deployed with ZCP on night one; every service carries its own `zerops.yaml`, so the whole topology is reproducible from this repo.
9. Engineering calls I'll happily defend: public-read bucket over expiring presigned URLs, a ten-line BRPOP loop over Celery, TTS behind one function with a wired fallback — full log in `DECISIONS.md`.
10. It's been publishing unattended since Saturday night — subscribe to the feed and by the time you finish judging, there'll be an episode that proves it.

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
## Secrets
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
Multi-source ingestion (GitHub/RSS/papers), personalized multi-topic briefings, source monitoring, two-host dialogue TTS, "Ask the podcast" over episode history.
