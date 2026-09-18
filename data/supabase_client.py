"""
Supabase + pgvector client for LocalLens.

Handles article storage, connection records, locale profiles,
and vector similarity search via pgvector.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
from supabase import Client, create_client

from config import settings


# ── Shared Data Models ────────────────────────────────────────────────────


@dataclass
class Article:
    """Normalized article from any source."""

    url: str
    title: str
    body: str
    source: str
    source_level: str  # global | national | state | local
    locale: str  # slug like "san-diego-ca"
    published_at: str  # ISO-8601
    created_at: str = ""
    embedding: list[float] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class Connection:
    """A discovered connection between a global story and local impact.

    In the new "scoop" architecture, local_article_id is optional because
    impact is generated directly from the global headline + locale profile,
    not by matching to an existing local article.
    """

    global_article_id: str
    locale: str
    confidence: str  # low | medium | high
    mechanism_text: str
    card_title: str
    card_body: str
    topics: list[str]
    local_article_id: str = ""  # optional — set when matching a local article
    created_at: str = ""
    cached_until: str = ""
    id: str = ""
    scoop_angle: str = ""
    neighborhoods_affected: str = ""


@dataclass
class LocaleProfile:
    """Context profile for a locale used by AI agents.

    Contains rich, hyper-local context used by the AI to generate
    original local impact analysis from global headlines.
    """

    locale_slug: str
    display_name: str
    metro_code: str
    demographics: dict[str, Any]
    major_employers: list[str]
    key_industries: list[str]
    government_entities: list[str]
    active_local_issues: list[str]
    economy: dict[str, Any]  # GDP, major sectors, trade data
    geography: dict[str, Any]  # region, climate, water sources, border
    infrastructure: dict[str, Any]  # port, airport, transit, energy
    military: dict[str, Any]  # bases, personnel, economic impact


# ── Supabase Client ────────────────────────────────────────────────────────


class SupabaseClient:
    """Wrapper around Supabase with pgvector support."""

    def __init__(self) -> None:
        self._client: Client = create_client(
            settings.supabase_url,
            settings.supabase_key,
        )

    @property
    def client(self) -> Client:
        return self._client

    # ── Articles ──────────────────────────────────────────────────────────

    def insert_article(self, article: Article) -> dict[str, Any] | None:
        """Insert a single article, skipping duplicates by URL."""
        existing = (
            self._client.table("articles")
            .select("id")
            .eq("url", article.url)
            .execute()
        )
        if existing.data:
            return None  # deduplicated

        article.created_at = datetime.now(timezone.utc).isoformat()
        data = self._client.table("articles").insert(article.to_dict()).execute()
        return data.data[0] if data.data else None

    def insert_articles_batch(self, articles: list[Article]) -> int:
        """Batch insert articles, returns count of new articles."""
        count = 0
        for article in articles:
            if self.insert_article(article) is not None:
                count += 1
        return count

    def get_articles_by_level(
        self,
        level: str,
        locale: str | None = None,
        hours: int = 24,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch articles by source level, optionally filtered by locale."""
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        query = (
            self._client.table("articles")
            .select("*")
            .eq("source_level", level)
            .gte("published_at", cutoff)
            .order("published_at", desc=True)
            .limit(limit)
        )
        if locale:
            query = query.eq("locale", locale)
        result = query.execute()
        return result.data or []

    def get_article_by_id(self, article_id: str) -> dict[str, Any] | None:
        result = (
            self._client.table("articles")
            .select("*")
            .eq("id", article_id)
            .execute()
        )
        return result.data[0] if result.data else None

    # ── Embeddings ────────────────────────────────────────────────────────

    def get_unembedded_articles(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get articles that don't have embeddings yet."""
        result = (
            self._client.table("articles")
            .select("*")
            .is_("embedding", "null")
            .limit(limit)
            .execute()
        )
        return result.data or []

    def update_embedding(
        self, article_id: str, embedding: list[float]
    ) -> None:
        self._client.table("articles").update(
            {"embedding": embedding}
        ).eq("id", article_id).execute()

    def search_similar_local(
        self,
        global_embedding: list[float],
        locale: str,
        threshold: float = 0.35,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for local articles similar to a global article embedding.

        Uses cosine similarity via pgvector.
        """
        # pgvector cosine distance: 1 - cosine_similarity
        # So threshold 0.35 similarity = distance 0.65
        distance_threshold = 1.0 - threshold
        result = (
            self._client.rpc(
                "match_articles",
                {
                    "query_embedding": embedding,
                    "match_threshold": distance_threshold,
                    "match_count": limit,
                    "filter_locale": locale,
                    "filter_level": "local",
                },
            ).execute()
        )
        return result.data or []

    # ── Connections ───────────────────────────────────────────────────────

    def insert_connection(self, connection: Connection) -> dict[str, Any]:
        connection.created_at = datetime.now(timezone.utc).isoformat()
        connection.cached_until = (
            datetime.now(timezone.utc) + timedelta(hours=settings.cache_hours)
        ).isoformat()
        data = self._client.table("connections").insert(
            asdict(connection)
        ).execute()
        return data.data[0]

    def get_connections_for_locale(
        self, locale: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Get cached connections for a locale, ordered by recency."""
        now = datetime.now(timezone.utc).isoformat()
        result = (
            self._client.table("connections")
            .select("*")
            .eq("locale", locale)
            .gte("cached_until", now)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    def get_connection_by_id(self, conn_id: str) -> dict[str, Any] | None:
        result = (
            self._client.table("connections")
            .select("*")
            .eq("id", conn_id)
            .execute()
        )
        return result.data[0] if result.data else None

    def get_connections_by_topic(
        self, locale: str, topics: list[str], limit: int = 20
    ) -> list[dict[str, Any]]:
        """Get connections filtered by topic categories."""
        now = datetime.now(timezone.utc).isoformat()
        # Supabase supports array containment with @> operator
        result = (
            self._client.table("connections")
            .select("*")
            .eq("locale", locale)
            .gte("cached_until", now)
            .contains("topics", topics)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    # ── Locale Profiles ──────────────────────────────────────────────────

    def get_locale_profile(self, locale_slug: str) -> dict[str, Any] | None:
        result = (
            self._client.table("locale_profiles")
            .select("*")
            .eq("locale_slug", locale_slug)
            .execute()
        )
        return result.data[0] if result.data else None

    def upsert_locale_profile(self, profile: LocaleProfile) -> dict[str, Any]:
        data = asdict(profile)
        result = (
            self._client.table("locale_profiles")
            .upsert(data, on_conflict="locale_slug")
            .execute()
        )
        return result.data[0]
