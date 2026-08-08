"""OrbitCast API — CRUD, refresh, RSS, live status polling."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import config
import db
import feeds as feed_svc
import broker as jobqueue
import rss
from migrate import SCHEMA

app = FastAPI(title="OrbitCast API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    return obj


class CreateFeedBody(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    topic_prompt: str = Field(min_length=1, max_length=4000)
    schedule_minutes: int = Field(default=60, ge=5, le=10080)


@app.on_event("startup")
def startup() -> None:
    with db.db() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)


@app.get("/health")
@app.get("/status")
def health() -> dict:
    try:
        with db.db() as conn:
            db.fetchone(conn, "SELECT 1 AS n")
    except Exception as exc:
        return {"ok": False, "db": False, "error": str(exc)}
    return {
        "ok": True,
        "db": True,
        "queue_depth": jobqueue.queue_depth(),
        "cover_url": config.COVER_URL,
        "public_api_url": config.PUBLIC_API_URL,
    }


@app.get("/")
def root() -> dict:
    return {
        "name": "OrbitCast",
        "tagline": "Podcasts that don't go stale.",
        "docs": "/docs",
        "feeds": "/feeds",
        "metrics": "/metrics",
    }


@app.get("/metrics")
def metrics() -> dict:
    return _jsonable(feed_svc.metrics())


@app.get("/feeds")
def list_feeds() -> list:
    return _jsonable(feed_svc.list_feeds())


@app.post("/feeds", status_code=201)
def create_feed(body: CreateFeedBody) -> dict:
    feed = feed_svc.create_feed(body.title, body.topic_prompt, body.schedule_minutes)
    return _jsonable(feed)


@app.get("/feeds/{feed_id}")
def get_feed(feed_id: str) -> dict:
    feed = feed_svc.get_feed(feed_id)
    if not feed:
        raise HTTPException(404, "feed not found")
    episodes = feed_svc.list_episodes(feed_id)
    return _jsonable({"feed": feed, "episodes": episodes})


@app.post("/feeds/{feed_id}/refresh", status_code=201)
def refresh_feed(feed_id: str) -> dict:
    try:
        episode = feed_svc.refresh_feed(feed_id)
    except KeyError:
        raise HTTPException(404, "feed not found") from None
    return _jsonable(episode)


@app.get("/feeds/{feed_id}/episodes")
def list_episodes(feed_id: str) -> list:
    if not feed_svc.get_feed(feed_id):
        raise HTTPException(404, "feed not found")
    return _jsonable(feed_svc.list_episodes(feed_id))


@app.post("/episodes/{episode_id}/retry", status_code=201)
def retry_episode(episode_id: str) -> dict:
    try:
        ep = feed_svc.retry_episode(episode_id)
    except KeyError:
        raise HTTPException(404, "episode not found") from None
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None
    return _jsonable(ep)


@app.get("/feed/{slug}.xml")
def podcast_feed(slug: str) -> Response:
    feed = feed_svc.get_feed_by_slug(slug)
    if not feed:
        raise HTTPException(404, "feed not found")
    episodes = feed_svc.completed_episodes(str(feed["id"]))
    xml = rss.build_feed_xml(feed, episodes)
    return Response(content=xml, media_type="application/rss+xml")
