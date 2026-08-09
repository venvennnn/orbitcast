"""Research + script via Anthropic + web_search — one call, JSON out."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import config

log = logging.getLogger("orbitcast.research")


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_text(message) -> str:
    parts = []
    for block in message.content:
        if hasattr(block, "text"):
            parts.append(block.text)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts)


def generate_episode(
    topic: str,
    prior_scripts: list[str],
    *,
    force: bool,
    recap_previous: bool = True,
) -> dict[str, Any]:
    """
    Returns {title, description, script} or {skip: true, reason}.
    force=True (manual refresh) never returns skip.
    When prior episodes exist and recap_previous=True, script MUST open with
    ~20 seconds of spoken recap of the previous episode, then new material.
    """
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    from anthropic import Anthropic

    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

    episode_number = len(prior_scripts) + 1
    prior = "\n\n---\n\n".join(prior_scripts[-3:]) if prior_scripts else "(no prior episodes)"
    skip_rule = (
        "You MUST produce an episode. Never return skip."
        if force
        else (
            "If nothing episode-worthy has changed since prior episodes, "
            'return JSON {"skip": true, "reason": "..."} instead.'
        )
    )

    if prior_scripts and recap_previous:
        structure = f"""This is episode #{episode_number} in an ongoing series.

Script STRUCTURE (required):
1) OPENING RECAP (~20 seconds spoken, about 45–55 words): briefly summarize what the PREVIOUS episode covered (use the most recent prior script). Start like "Last time we covered…" — do not invent details that weren't in that script.
2) BRIDGE (one sentence): "Here's what's new since then…"
3) NEW MATERIAL (the rest): only what's changed / new since prior episodes. Do not rehash the recap.

Total spoken length target: about 110–180 seconds.
"""
    elif prior_scripts:
        structure = """Prior episodes exist, but recap is disabled for this feed.
Open with what changed since last time, then report only what's new. Target ~90–150 seconds.
"""
    else:
        structure = """This is episode #1 — no prior recap.
Write a self-contained briefing (~90–150 seconds).
"""

    prompt = f"""You are writing a conversational single-host podcast briefing.

Topic / standing brief:
{topic}

Prior episode scripts (most recent last; use for change-awareness and optional recap):
{prior}

{structure}

{skip_rule}

Use web search to find current information. Then respond with ONLY valid JSON (no markdown fences):
{{
  "title": "short episode title",
  "description": "1-2 sentence show notes",
  "script": "spoken script for a single host. Natural speech, no stage directions, no bullet lists."
}}
"""

    message = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=4096,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
        messages=[{"role": "user", "content": prompt}],
    )

    raw = _extract_text(message)
    if not raw:
        raw = str(message.content)
    cleaned = _strip_fences(raw)

    match = re.search(r"\{[\s\S]*\}", cleaned)
    if not match:
        raise RuntimeError(f"model returned no JSON: {cleaned[:500]}")
    data = json.loads(match.group(0))

    if data.get("skip"):
        if force:
            log.warning("model tried to skip on forced run — requesting forced script")
            message = client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=4096,
                tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
                messages=[
                    {"role": "user", "content": prompt},
                    {
                        "role": "user",
                        "content": (
                            "Do NOT skip. Produce the JSON with title, description, and script now. "
                            "If sources are thin, brief on the standing topic with what is known. "
                            "Keep the required recap structure if this is episode 2+."
                        ),
                    },
                ],
            )
            cleaned = _strip_fences(_extract_text(message))
            match = re.search(r"\{[\s\S]*\}", cleaned)
            if not match:
                raise RuntimeError(f"forced re-prompt returned no JSON: {cleaned[:500]}")
            data = json.loads(match.group(0))
            if data.get("skip"):
                raise RuntimeError("model refused to generate on forced refresh")
        else:
            return {"skip": True, "reason": data.get("reason") or "nothing new"}

    for key in ("title", "description", "script"):
        if not data.get(key):
            raise RuntimeError(f"missing field in model JSON: {key}")
    return data
