"""Object storage upload — explicit Content-Type audio/mpeg."""

from __future__ import annotations

from pathlib import Path

import boto3
from botocore.client import Config

import config


def s3():
    return boto3.client(
        "s3",
        endpoint_url=config.S3_ENDPOINT,
        aws_access_key_id=config.S3_ACCESS_KEY,
        aws_secret_access_key=config.S3_SECRET_KEY,
        region_name=config.S3_REGION,
        config=Config(s3={"addressing_style": "path"}),
    )


def public_url(key: str) -> str:
    return f"{config.S3_ENDPOINT.rstrip('/')}/{config.S3_BUCKET}/{key}"


def upload_file(path: Path, key: str, content_type: str) -> str:
    with path.open("rb") as fh:
        s3().put_object(
            Bucket=config.S3_BUCKET,
            Key=key,
            Body=fh,
            ContentType=content_type,
        )
    return public_url(key)
