"""
NewsAPI.org client for LocalLens.

Free tier: 100 requests/day, headlines endpoint.
Handles rate limiting, pagination, and normalization to Article dataclass.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from config import settings
from data.supabase_client import Article


class NewsAPIClientError(Exception):
    """Raised on NewsAPI errors (rate limit, auth failure, etc.)."""

    pass


class NewsAPIClient:
    """Wrapper for NewsAPI.org with retry logic and exponential backoff."""

    BASE_URL = "https://newsapi.org/v2"

    def __init__(self) -> None:
        self._api_key = settings.newsapi_key
        self._session = requests.Session()
        self._session.headers.update({"X-Api-Key": self._api_key})
        self._max_retries = 3

    def _request_with_retry(
        self, endpoint: str, params: dict[str, Any], retries: int = 0
    ) -> dict[str, Any]:
        """Make a GET request with exponential backoff on failure."""
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            resp = self._session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            if data.get("status") == "error":
                raise NewsAPIClientError(data.get("message", "Unknown API error"))
            return data
        except requests.exceptions.RequestException as e:
            if retries < self._max_retries:
                wait = 2 ** (retries + 1)
                time.sleep(wait)
                return self._request_with_retry(endpoint, params, retries + 1)
            raise NewsAPIClientError(str(e)) from e

    def _article_to_dataclass(
        self,
        item: dict[str, Any],
        source_level: str,
        locale: str,
    ) -> Article:
        """Normalize a NewsAPI article dict to our Article dataclass."""
        return Article(
            url=item.get("url", ""),
            title=item.get("title", ""),
            body=item.get("description") or item.get("content") or "",
            source=item.get("source", {}).get("name", "NewsAPI"),
            source_level=source_level,
            locale=locale,
            published_at=item.get("publishedAt", datetime.now(timezone.utc).isoformat()),
        )

    def get_global_headlines(
        self, locale: str = "san-diego-ca", page_size: int = 20
    ) -> list[Article]:
        """Fetch top global/national headlines.

        Uses 'general' category to get broad coverage.
        """
        params: dict[str, Any] = {
            "category": "general",
            "pageSize": min(page_size, 100),
            "language": "en",
        }
        data = self._request_with_retry("top-headlines", params)
        articles: list[dict[str, Any]] = data.get("articles", [])
        return [
            self._article_to_dataclass(a, "global", locale) for a in articles
        ]

    def get_headlines_by_category(
        self,
        category: str,
        locale: str = "san-diego-ca",
        page_size: int = 20,
    ) -> list[Article]:
        """Fetch headlines by category.

        Categories: business, entertainment, general, health, science,
        sports, technology.
        """
        params: dict[str, Any] = {
            "category": category,
            "pageSize": min(page_size, 100),
            "language": "en",
        }
        data = self._request_with_retry("top-headlines", params)
        articles = data.get("articles", [])
        return [
            self._article_to_dataclass(a, "global", locale) for a in articles
        ]

    def search_everything(
        self,
        query: str,
        locale: str = "san-diego-ca",
        from_days_ago: int = 7,
        page_size: int = 20,
    ) -> list[Article]:
        """Search all articles matching a query."""
        from_date = (
            datetime.now(timezone.utc) - timedelta(days=from_days_ago)
        ).strftime("%Y-%m-%d")
        params: dict[str, Any] = {
            "q": query,
            "from": from_date,
            "pageSize": min(page_size, 100),
            "language": "en",
            "sortBy": "publishedAt",
        }
        data = self._request_with_retry("everything", params)
        articles = data.get("articles", [])
        return [
            self._article_to_dataclass(a, "global", locale) for a in articles
        ]
