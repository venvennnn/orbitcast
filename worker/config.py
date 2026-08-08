"""OrbitCast shared config — env-driven, no hardcoded secrets."""

from __future__ import annotations

import os


def env(name: str, default: str | None = None) -> str:
    val = os.environ.get(name, default)
    if val is None or val == "":
        raise RuntimeError(f"missing required env: {name}")
    return val


def env_opt(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


DATABASE_URL = os.environ.get("DATABASE_URL", "")
REDIS_URL = os.environ.get("REDIS_URL", "")
QUEUE_KEY = os.environ.get("QUEUE_KEY", "orbitcast:jobs")

S3_ENDPOINT = env_opt("S3_ENDPOINT").rstrip("/")
S3_ACCESS_KEY = env_opt("S3_ACCESS_KEY")
S3_SECRET_KEY = env_opt("S3_SECRET_KEY")
S3_BUCKET = env_opt("S3_BUCKET")
S3_REGION = env_opt("S3_REGION", "us-east-1")

PUBLIC_API_URL = env_opt("PUBLIC_API_URL", "https://api-13d-8000.sea1.zerops.app").rstrip("/")
COVER_URL = env_opt(
    "COVER_URL",
    f"{S3_ENDPOINT}/{S3_BUCKET}/step0/cover.jpg" if S3_ENDPOINT and S3_BUCKET else "",
)

ANTHROPIC_API_KEY = env_opt("ANTHROPIC_API_KEY")
OPENAI_API_KEY = env_opt("OPENAI_API_KEY")
ANTHROPIC_MODEL = env_opt("ANTHROPIC_MODEL", "claude-haiku-4-5")
TTS_VOICE = env_opt("TTS_VOICE", "en-US-JennyNeural")

HARDCODED_USER_ID = 1
