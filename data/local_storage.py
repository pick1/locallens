"""
Local SQLite storage for LocalLens — zero-dependency replacement for Supabase.

Provides the same dataclass interface as supabase_client.py but stores
everything in a local SQLite database. Used when no Supabase credentials
are configured.

Schema:
  articles     — ingested news articles (deduplicated by URL)
  connections  — AI-generated connection cards
  locale_profiles — cached locale profile data
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DB_DIR / "locallens.db"


# ── Shared Data Models ────────────────────────────────────────────────────


@dataclass
class Article:
    """Normalized article from any source."""

    url: str
    title: str
    body: str
    source: str = ""
    source_level: str = "global"  # global|national|state|local
    locale: str = "san-diego-ca"
    published_at: str = ""
    id: int | None = None  # populated after insert


@dataclass
class Connection:
    """A connection card linking a global story to local impact."""

    global_article_id: int
    locale: str = "san-diego-ca"
    confidence: str = "medium"  # low|medium|high
    mechanism_text: str = ""
    card_title: str = ""
    card_body: str = ""
    topics: str = "[]"  # JSON list stored as string
    is_sensitive: bool = False
    scoop_angle: str = ""
    neighborhoods_affected: str = ""
    created_at: str = ""
    cached_until: str = ""
    local_article_id: int | None = None
    id: int | None = None


# ── Database Manager ──────────────────────────────────────────────────────


class LocalDatabase:
    """Thread-safe SQLite database for LocalLens."""

    def __init__(self, db_path: str | Path = DB_PATH) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get a thread-local connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self._db_path))
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
        return self._local.conn

    def _init_db(self) -> None:
        """Create tables if they don't exist."""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                body TEXT,
                source TEXT,
                source_level TEXT DEFAULT 'global',
                locale TEXT DEFAULT 'san-diego-ca',
                published_at TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                global_article_id INTEGER REFERENCES articles(id),
                local_article_id INTEGER,
                locale TEXT DEFAULT 'san-diego-ca',
                confidence TEXT DEFAULT 'medium',
                mechanism_text TEXT,
                card_title TEXT,
                card_body TEXT,
                topics TEXT DEFAULT '[]',
                is_sensitive INTEGER DEFAULT 0,
                scoop_angle TEXT DEFAULT '',
                neighborhoods_affected TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                cached_until TEXT
            );

            CREATE TABLE IF NOT EXISTS locale_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                locale_slug TEXT UNIQUE,
                display_name TEXT,
                metro_code TEXT,
                context_json TEXT,
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_articles_level ON articles(source_level);
            CREATE INDEX IF NOT EXISTS idx_articles_locale ON articles(locale);
            CREATE INDEX IF NOT EXISTS idx_connections_locale ON connections(locale);
        """)
        conn.commit()

    # ── Article Operations ─────────────────────────────────────────────────

    def insert_article(self, article: Article) -> Article | None:
        """Insert an article, skipping if URL already exists."""
        conn = self._get_conn()
        try:
            cur = conn.execute(
                """INSERT OR IGNORE INTO articles
                   (url, title, body, source, source_level, locale, published_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    article.url,
                    article.title,
                    article.body,
                    article.source,
                    article.source_level,
                    article.locale,
                    article.published_at,
                ),
            )
            conn.commit()
            if cur.lastrowid:
                article.id = cur.lastrowid
                return article
            return None  # duplicate
        except sqlite3.Error as e:
            logger.error("Failed to insert article: %s", e)
            return None

    def insert_articles(self, articles: list[Article]) -> int:
        """Insert multiple articles. Returns count of new inserts."""
        count = 0
        for article in articles:
            if self.insert_article(article):
                count += 1
        return count

    def get_articles(
        self,
        source_level: str | None = None,
        locale: str | None = None,
        hours: int = 24,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get recent articles with optional filters."""
        conn = self._get_conn()
        conditions = []
        params: list[Any] = []

        if source_level:
            conditions.append("source_level = ?")
            params.append(source_level)
        if locale:
            conditions.append("locale = ?")
            params.append(locale)

        where = " AND ".join(conditions) if conditions else "1=1"
        rows = conn.execute(
            f"""SELECT * FROM articles
                WHERE {where}
                  AND created_at >= datetime('now', ?)
                ORDER BY published_at DESC
                LIMIT ?""",
            params + [f"-{hours} hours", limit],
        ).fetchall()
        return [dict(row) for row in rows]

    def get_articles_by_level(
        self,
        level: str,
        locale: str | None = None,
        hours: int = 24,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch articles by source level, optionally filtered by locale.

        Mirrors SupabaseClient.get_articles_by_level interface for
        compatibility with HeadlineMonitorAgent.
        """
        conn = self._get_conn()
        conditions = ["source_level = ?"]
        params: list[Any] = [level]

        if locale:
            conditions.append("locale = ?")
            params.append(locale)

        where = " AND ".join(conditions)
        rows = conn.execute(
            f"""SELECT * FROM articles
                WHERE {where}
                  AND created_at >= datetime('now', ?)
                ORDER BY published_at DESC
                LIMIT ?""",
            params + [f"-{hours} hours", limit],
        ).fetchall()
        return [dict(row) for row in rows]

    def get_article_by_id(self, article_id: int) -> dict[str, Any] | None:
        """Get a single article by ID."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM articles WHERE id = ?", [article_id]
        ).fetchone()
        return dict(row) if row else None

    def get_article_count(self) -> int:
        """Total articles stored."""
        conn = self._get_conn()
        return conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]

    def get_global_headlines(
        self, hours: int = 24, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get recent global/national headlines for the discovery pipeline."""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT * FROM articles
               WHERE source_level IN ('global', 'national')
                 AND created_at >= datetime('now', ?)
                 AND title != ''
               ORDER BY published_at DESC
               LIMIT ?""",
            [f"-{hours} hours", limit],
        ).fetchall()
        return [dict(row) for row in rows]

    # ── Connection Operations ─────────────────────────────────────────────

    def insert_connection(self, connection: Connection) -> dict[str, Any] | None:
        """Insert a connection card."""
        conn = self._get_conn()
        try:
            topics_json = (
                json.dumps(connection.topics)
                if isinstance(connection.topics, list)
                else connection.topics
            )
            cur = conn.execute(
                """INSERT INTO connections
                   (global_article_id, local_article_id, locale, confidence,
                    mechanism_text, card_title, card_body, topics, is_sensitive,
                    scoop_angle, neighborhoods_affected, cached_until)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    connection.global_article_id,
                    connection.local_article_id,
                    connection.locale,
                    connection.confidence,
                    connection.mechanism_text,
                    connection.card_title,
                    connection.card_body,
                    topics_json,
                    1 if connection.is_sensitive else 0,
                    connection.scoop_angle,
                    connection.neighborhoods_affected,
                    connection.cached_until or "",
                ),
            )
            conn.commit()
            if cur.lastrowid:
                row = conn.execute(
                    "SELECT * FROM connections WHERE id = ?", [cur.lastrowid]
                ).fetchone()
                return dict(row) if row else None
            return None
        except sqlite3.Error as e:
            logger.error("Failed to insert connection: %s", e)
            return None

    def get_connections(
        self, locale: str = "san-diego-ca", limit: int = 20
    ) -> list[dict[str, Any]]:
        """Get connection cards for a locale, newest first."""
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT c.*, a.title as global_title, a.source as global_source
               FROM connections c
               LEFT JOIN articles a ON c.global_article_id = a.id
               WHERE c.locale = ?
               ORDER BY c.created_at DESC
               LIMIT ?""",
            [locale, limit],
        ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            # Parse topics JSON
            if isinstance(d.get("topics"), str):
                try:
                    d["topics"] = json.loads(d["topics"])
                except (json.JSONDecodeError, TypeError):
                    d["topics"] = []
            d["is_sensitive"] = bool(d.get("is_sensitive", False))
            result.append(d)
        return result

    def get_connection_by_id(self, conn_id: int) -> dict[str, Any] | None:
        """Get a single connection by ID."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM connections WHERE id = ?", [conn_id]
        ).fetchone()
        return dict(row) if row else None

    def get_connection_count(self) -> int:
        """Total connections stored."""
        conn = self._get_conn()
        return conn.execute("SELECT COUNT(*) FROM connections").fetchone()[0]

    def search_connections(
        self,
        locale: str = "san-diego-ca",
        topics: list[str] | None = None,
        confidence: str | None = None,
        keyword: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Search connections with optional filters.

        Args:
            locale: Locale slug.
            topics: Filter by topic categories (OR logic).
            confidence: Filter by confidence level (low/medium/high).
            keyword: Search in card_title and card_body (case-insensitive).
            limit: Max results.
            offset: Pagination offset.

        Returns:
            List of connection dicts with global_title and global_source.
        """
        conn = self._get_conn()
        conditions = ["c.locale = ?"]
        params: list[Any] = [locale]

        if confidence:
            conditions.append("c.confidence = ?")
            params.append(confidence)

        if keyword:
            conditions.append(
                "(LOWER(c.card_title) LIKE ? OR LOWER(c.card_body) LIKE ?)"
            )
            kw = f"%{keyword.lower()}%"
            params.append(kw)
            params.append(kw)

        # Topic filter — topics stored as JSON string like '["Economy","Policy"]'
        if topics:
            topic_conditions: list[str] = []
            for t in topics:
                topic_conditions.append("c.topics LIKE ?")
                params.append(f"%{t}%")
            conditions.append(f"({' OR '.join(topic_conditions)})")

        where = " AND ".join(conditions)
        rows = conn.execute(
            f"""SELECT c.*, a.title as global_title, a.source as global_source
                FROM connections c
                LEFT JOIN articles a ON c.global_article_id = a.id
                WHERE {where}
                ORDER BY c.created_at DESC
                LIMIT ? OFFSET ?""",
            params + [limit, offset],
        ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            if isinstance(d.get("topics"), str):
                try:
                    d["topics"] = json.loads(d["topics"])
                except (json.JSONDecodeError, TypeError):
                    d["topics"] = []
            d["is_sensitive"] = bool(d.get("is_sensitive", False))
            result.append(d)
        return result

    # ── Locale Profile Operations ─────────────────────────────────────────

    def upsert_locale_profile(
        self, locale_slug: str, display_name: str, context: dict[str, Any]
    ) -> None:
        """Insert or update a locale profile."""
        conn = self._get_conn()
        conn.execute(
            """INSERT INTO locale_profiles (locale_slug, display_name, context_json, updated_at)
               VALUES (?, ?, ?, datetime('now'))
               ON CONFLICT(locale_slug) DO UPDATE SET
                   display_name = excluded.display_name,
                   context_json = excluded.context_json,
                   updated_at = datetime('now')""",
            [locale_slug, display_name, json.dumps(context)],
        )
        conn.commit()

    def get_locale_profile(
        self, locale_slug: str
    ) -> dict[str, Any] | None:
        """Get a locale profile by slug."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM locale_profiles WHERE locale_slug = ?", [locale_slug]
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        if isinstance(d.get("context_json"), str):
            try:
                d.update(json.loads(d["context_json"]))
            except (json.JSONDecodeError, TypeError):
                pass
        return d

    # ── Maintenance ────────────────────────────────────────────────────────

    def vacuum(self) -> None:
        """Reclaim space."""
        conn = self._get_conn()
        conn.execute("VACUUM")
        conn.commit()

    @property
    def article_count(self) -> int:
        return self.get_article_count()

    @property
    def connection_count(self) -> int:
        return self.get_connection_count()
