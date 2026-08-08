"""Valkey / Redis job broker — LPUSH / BRPOP, ~zero config."""

from __future__ import annotations

import redis

import config


def client() -> redis.Redis:
    if not config.REDIS_URL:
        raise RuntimeError("REDIS_URL not set")
    return redis.Redis.from_url(config.REDIS_URL, decode_responses=True)


def enqueue(episode_id: str) -> None:
    client().lpush(config.QUEUE_KEY, episode_id)


def queue_depth() -> int:
    try:
        return int(client().llen(config.QUEUE_KEY))
    except Exception:
        return -1
