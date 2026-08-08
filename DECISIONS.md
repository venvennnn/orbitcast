# OrbitCast — DECISIONS

Running log for judge-prep and the build post. Newest first.

## 2026-08-08 — First real episode shipped end-to-end

- **ANTHROPIC_API_KEY** set at project scope; worker research+script works (`claude-haiku-4-5` + web_search).
- **edge-tts:** pin `7.2.8` (7.0.2 → Microsoft WS 403). Running worker must be restarted after vendor upgrade or it keeps the old module in memory.
- **OpenAI TTS fallback** still unwired until `OPENAI_API_KEY` is provided — optional insurance.
- **First completed episode:** “Weekend tech news” → 77s MP3 public `audio/mpeg`, RSS enclosure live.

## 2026-08-08 — MVP architecture locked

- **Queue contract:** API/manual refresh LPUSH plain `episode_id` → worker `force=True`. Cron LPUSH `skipable:<id>` → worker may mark `skipped`.
- **No Celery:** Valkey BRPOP loop on `worker` (`orbitcast:jobs`).
- **TTS:** `synthesize()` = edge-tts → OpenAI TTS fallback.
- **LLM:** Anthropic `claude-haiku-4-5` + `web_search_20250305` in one call; JSON `{title,description,script}` or `{skip,reason}`.
- **RSS:** hand-built XML (not feedgen) for Apple enclosure/itunes control; cover reused from Step Zero public object.
- **Dashboard:** vanilla JS + Tailwind CDN on `web`; polls `/feeds` + `/metrics` every 2s.
- **Secrets:** `ANTHROPIC_API_KEY` (+ optional `OPENAI_API_KEY`) as project env — required before real episodes generate.

## 2026-08-08 — Step Zero PASSED (AntennaPod)

- **Client:** AntennaPod — subscribe-by-URL + play succeeded on live feed.
- **Feed:** `https://api-13d-8000.sea1.zerops.app/feed/orbitcast-step0.xml`
- **Meaning:** RSS + public object-storage MP3 path is de-risked. Build the product on this base; do not reopen the enclosure/URL strategy unless a validator or Apple Podcasts rejects something specific.
- **Demo note:** use a **fresh slug** for the live judging subscribe (apps cache feeds hard).

## 2026-08-08 — Step Zero unblocked (infra + feed live)

- **Public API:** `https://api-13d-8000.sea1.zerops.app`
- **Enclosure:** `https://storage-sea1.zerops.io/5lhkq-objectstorage/step0/intro.mp3` — `Content-Type: audio/mpeg`, `Accept-Ranges: bytes`, ~9s edge-tts.
- **Cover:** 1400×1400 JPEG hardcoded for all feeds until per-feed art.
- **Gotcha:** first deploy needed explicit `zerops_subdomain enable`.
- **edge-tts:** works; keep OpenAI TTS as `synthesize()` fallback.

## 2026-08-08 — Step Zero kickoff

- **Product name (working):** OrbitCast — living podcast feeds from a topic, on Zerops.
- **Bootstrap mode:** `simple` for `api` / `web` / `worker` / `cron` — hackathon needs durable public HTTPS through judging, not a transient `dev` container.
- **Service map (PRD §4):** `web` (nginx) · `api` (python@3.12 FastAPI) · `db` (postgresql@18) · `queue` (valkey@7.2) · `worker` (python) · `cron` (python + crontab later) · `objectstorage` (S3/MinIO, public-read).
- **Object storage hostname:** existing `objectstorage` (not `storage`) — keep name; wire as `${objectstorage_*}`.
- **Bucket policy:** `public-read` required so enclosure URLs never expire (no presigned URLs). Verify Content-Type `audio/mpeg` on upload.
- **Step Zero order:** isolate RSS-in-real-app before CRUD/queue. Hardcoded FastAPI RSS + one uploaded MP3.
- **TTS probe:** `edge-tts` (en-US-JennyNeural) generated the Step Zero sample on ZCP — primary path looks viable; OpenAI TTS remains wired fallback later.
- **No Celery:** Valkey `BRPOP` loop on `worker` (Sunday).
- **No React build:** vanilla JS + Tailwind CDN on `web` (Sunday afternoon).
- **Auth:** hardcode `user_id = 1` / localStorage UUID — out of scope.
