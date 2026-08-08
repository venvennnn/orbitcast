"""TTS — edge-tts primary, OpenAI fallback behind synthesize()."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import config

log = logging.getLogger("orbitcast.tts")


async def _edge(text: str, out: Path) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, config.TTS_VOICE)
    await communicate.save(str(out))


def _openai(text: str, out: Path) -> None:
    from openai import OpenAI

    if not config.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set for TTS fallback")
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    # Keep under ~4000 chars per request for tts-1
    chunk = text[:4000]
    with client.audio.speech.with_streaming_response.create(
        model="tts-1",
        voice="nova",
        input=chunk,
        response_format="mp3",
    ) as response:
        response.stream_to_file(out)


def synthesize(text: str, out: Path) -> Path:
    """Return path to an MP3. Tries edge-tts, then OpenAI."""
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        asyncio.run(_edge(text, out))
        if out.exists() and out.stat().st_size > 0:
            return out
        raise RuntimeError("edge-tts produced empty file")
    except Exception as exc:
        log.warning("edge-tts failed (%s) — falling back to OpenAI TTS", exc)
        _openai(text, out)
        if not out.exists() or out.stat().st_size == 0:
            raise RuntimeError("OpenAI TTS produced empty file") from exc
        return out
