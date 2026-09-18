"""
RSS feed client for LocalLens.

Parses RSS/Atom feeds from global, national, and local sources.
Normalizes all feed entries to the Article dataclass.

Usage:
    client = RSSClient()
    articles = client.parse_feeds()  # all feeds
    global_articles = client.parse_feeds(categories=['global', 'national'])
    local_articles = client.parse_feeds(categories=['local'])
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import feedparser
import requests

# Try to import Article from local_storage first (SQLite mode),
# fall back to supabase_client (cloud mode)
try:
    from data.local_storage import Article
except ImportError:
    from data.supabase_client import Article


# ── Feed Registry ─────────────────────────────────────────────────────────

GLOBAL_FEEDS: list[dict[str, str]] = [
    {
        "name": "BBC World News",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "level": "global",
    },
    {
        "name": "BBC US & Canada",
        "url": "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",
        "level": "global",
    },
    {
        "name": "BBC Business",
        "url": "https://feeds.bbci.co.uk/news/business/rss.xml",
        "level": "global",
    },
    {
        "name": "The Guardian — US News",
        "url": "https://www.theguardian.com/us-news/rss",
        "level": "global",
    },
    {
        "name": "The Guardian — World News",
        "url": "https://www.theguardian.com/world/rss",
        "level": "global",
    },
]

NATIONAL_FEEDS: list[dict[str, str]] = [
    {
        "name": "NPR News",
        "url": "https://feeds.npr.org/1001/rss.xml",
        "level": "national",
    },
    {
        "name": "NBC News",
        "url": "https://feeds.nbcnews.com/nbcnews/public/news",
        "level": "national",
    },
    {
        "name": "CBS News",
        "url": "https://www.cbsnews.com/latest/rss/main",
        "level": "national",
    },
]

LOCAL_SAN_DIEGO_FEEDS: list[dict[str, str]] = [
    {
        "name": "Voice of San Diego",
        "url": "https://voiceofsandiego.org/feed/",
        "level": "local",
    },
    {
        "name": "San Diego Union-Tribune",
        "url": "https://www.sandiegouniontribune.com/feed/",
        "level": "local",
    },
    {
        "name": "KPBS News",
        "url": "https://www.kpbs.org/feeds/news/rss",
        "level": "local",
    },
]

STATE_FEEDS: list[dict[str, str]] = [
    {
        "name": "CalMatters",
        "url": "https://calmatters.org/feed/",
        "level": "state",
    },
]

# Convenience grouping
ALL_FEEDS = GLOBAL_FEEDS + NATIONAL_FEEDS + STATE_FEEDS + LOCAL_SAN_DIEGO_FEEDS
LEVEL_MAP: dict[str, list[dict[str, str]]] = {
    "global": GLOBAL_FEEDS,
    "national": NATIONAL_FEEDS,
    "state": STATE_FEEDS,
    "local": LOCAL_SAN_DIEGO_FEEDS,
}


class RSSClientError(Exception):
    pass


class RSSClient:
    """Parse RSS/Atom feeds and normalize to Article dataclass."""

    def __init__(
        self,
        locale: str = "san-diego-ca",
    ) -> None:
        self._locale = locale
        self._session = requests.Session()
        self._session.headers.update(
            {"User-Agent": "LocalLens/1.0 (news intelligence aggregator)"}
        )

    def _fetch_feed(self, feed_url: str) -> str:
        """Fetch raw feed XML with retry."""
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                resp = self._session.get(feed_url, timeout=15)
                resp.raise_for_status()
                return resp.text
            except requests.exceptions.RequestException:
                if attempt < max_retries:
                    time.sleep(2**attempt)
                    continue
                raise RSSClientError(
                    f"Failed to fetch feed: {feed_url}"
                ) from None
        return ""  # unreachable

    def _entry_to_article(
        self,
        entry: dict[str, Any],
        source_name: str,
        source_level: str,
    ) -> Article | None:
        """Normalize a feedparser entry to Article."""
        # Extract best available URL
        link = entry.get("link", "")
        if isinstance(link, dict):
            link = link.get("href", "")
        if not link:
            return None

        # Extract published time
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        if published:
            try:
                published_dt = datetime(*published[:6], tzinfo=timezone.utc)
                published_str = published_dt.isoformat()
            except (TypeError, ValueError):
                published_str = datetime.now(timezone.utc).isoformat()
        else:
            published_str = datetime.now(timezone.utc).isoformat()

        # Build body from summary/content
        body = entry.get("summary", "")
        if not body and "content" in entry:
            content_list = entry.get("content", [])
            if content_list:
                body = content_list[0].get("value", "")

        # Strip HTML tags for cleaner body text
        if body:
            import re

            body = re.sub(r"<[^>]+>", "", body)
            body = re.sub(r"\s+", " ", body).strip()[:5000]

        return Article(
            url=link.strip(),
            title=entry.get("title", "").strip(),
            body=body,
            source=source_name,
            source_level=source_level,
            locale=self._locale,
            published_at=published_str,
        )

    def parse_feeds(
        self,
        categories: list[str] | None = None,
    ) -> list[Article]:
        """Parse feeds from specified categories and return articles.

        Args:
            categories: List of feed level categories to fetch.
                Options: 'global', 'national', 'state', 'local'.
                Defaults to all categories.

        Returns:
            List of Article dataclass instances.
        """
        feeds_to_parse: list[dict[str, str]] = []
        if categories:
            for cat in categories:
                feeds_to_parse.extend(LEVEL_MAP.get(cat, []))
        else:
            feeds_to_parse = ALL_FEEDS

        articles: list[Article] = []
        for feed_info in feeds_to_parse:
            try:
                raw_xml = self._fetch_feed(feed_info["url"])
                parsed = feedparser.parse(raw_xml)
                for entry in parsed.entries:
                    article = self._entry_to_article(
                        entry,
                        feed_info["name"],
                        feed_info["level"],
                    )
                    if article:
                        articles.append(article)
            except RSSClientError:
                continue  # skip failed feeds
        return articles
