#!/usr/bin/env python3
"""Upload Step Zero assets to object storage. Run once after first deploy."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import boto3
from botocore.client import Config
from mutagen.mp3 import MP3

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def client():
    endpoint = os.environ["S3_ENDPOINT"]
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ["S3_ACCESS_KEY"],
        aws_secret_access_key=os.environ["S3_SECRET_KEY"],
        region_name=os.environ.get("S3_REGION", "us-east-1"),
        config=Config(s3={"addressing_style": "path"}),
    )


def public_url(key: str) -> str:
    endpoint = os.environ["S3_ENDPOINT"].rstrip("/")
    bucket = os.environ["S3_BUCKET"]
    return f"{endpoint}/{bucket}/{key}"


def upload(key: str, path: Path, content_type: str) -> str:
    c = client()
    bucket = os.environ["S3_BUCKET"]
    with path.open("rb") as fh:
        c.put_object(
            Bucket=bucket,
            Key=key,
            Body=fh,
            ContentType=content_type,
        )
    url = public_url(key)
    print(f"uploaded {path.name} -> {url}")
    return url


def main() -> int:
    required = ["S3_ENDPOINT", "S3_ACCESS_KEY", "S3_SECRET_KEY", "S3_BUCKET"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        print("missing env:", ", ".join(missing), file=sys.stderr)
        return 1

    mp3 = ASSETS / "step0.mp3"
    cover = ASSETS / "cover.jpg"
    if not mp3.exists() or not cover.exists():
        print("missing assets under", ASSETS, file=sys.stderr)
        return 1

    audio_url = upload("step0/intro.mp3", mp3, "audio/mpeg")
    cover_url = upload("step0/cover.jpg", cover, "image/jpeg")
    duration = round(MP3(mp3).info.length)
    bytes_len = mp3.stat().st_size

    print("---")
    print(f"AUDIO_URL={audio_url}")
    print(f"COVER_URL={cover_url}")
    print(f"AUDIO_BYTES={bytes_len}")
    print(f"DURATION_SECONDS={duration}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
