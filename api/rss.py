"""Apple-grade podcast RSS via feedgen."""

from __future__ import annotations

from datetime import timezone
from email.utils import format_datetime
from typing import Any
from xml.sax.saxutils import escape

import config


def build_feed_xml(feed: dict[str, Any], episodes: list[dict[str, Any]]) -> str:
    """Hand-built RSS with podcast extensions — feedgen can emit Apple-rejected XML; keep control."""
    public = config.PUBLIC_API_URL
    cover = config.COVER_URL
    self_url = f"{public}/feed/{feed['slug']}.xml"
    title = feed["title"]
    description = feed["topic_prompt"]

    items = []
    for ep in episodes:
        if ep["status"] != "completed" or not ep.get("audio_url"):
            continue
        pub = ep["created_at"]
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        duration = ep.get("duration_seconds") or 0
        length = ep.get("audio_bytes") or 0
        items.append(
            f"""    <item>
      <title>{escape(ep.get('title') or 'Episode')}</title>
      <description>{escape(ep.get('description') or '')}</description>
      <guid isPermaLink="false">{ep['id']}</guid>
      <pubDate>{format_datetime(pub)}</pubDate>
      <enclosure url="{escape(ep['audio_url'])}" length="{length}" type="audio/mpeg"/>
      <itunes:duration>{duration}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
      <itunes:image href="{escape(cover)}"/>
    </item>"""
        )

    items_xml = "\n".join(items)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
  xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{escape(title)}</title>
    <link>{escape(public)}</link>
    <description>{escape(description)}</description>
    <language>en-us</language>
    <itunes:author>OrbitCast</itunes:author>
    <itunes:summary>{escape(description)}</itunes:summary>
    <itunes:explicit>false</itunes:explicit>
    <itunes:category text="Technology"/>
    <itunes:image href="{escape(cover)}"/>
    <image>
      <url>{escape(cover)}</url>
      <title>{escape(title)}</title>
      <link>{escape(public)}</link>
    </image>
    <atom:link href="{escape(self_url)}" rel="self" type="application/rss+xml"/>
{items_xml}
  </channel>
</rss>
"""
