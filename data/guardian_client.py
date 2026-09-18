"""
The Guardian API client for LocalLens.

Free tier: no rate limit for non-commercial use.
Handles pagination, retry, and normalization to Article dataclass.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from config import settings
from data.supabase_client import Article


class GuardianClientError(Exception):
    pass


class GuardianClient:
    """Wrapper for The Guardian Open Platform API."""

    BASE_URL = "https://content.guardianapis.com"

    def __init__(self) -> None:
        self._api_key = settings.guardian_api_key
        self._session = requests.Session()
        self._max_retries = 3

    def _request_with_retry(
        self, params: dict[str, Any], retries: int = 0
    ) -> dict[str, Any]:
        """Make a GET request with exponential backoff."""
        params["api-key"] = self._api_key
        try:
            resp = self._session.get(
                f"{self.BASE_URL}/search",
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            return data
        except requests.exceptions.RequestException as e:
            if retries < self._max_retries:
                wait = 2 ** (retries + 1)
                time.sleep(wait)
                return self._request_with_retry(params, retries + 1)
            raise GuardianClientError(str(e)) from e

    def _item_to_article(
        self, item: dict[str, Any], source_level: str, locale: str
    ) -> Article:
        """Normalize a Guardian API result to our Article dataclass."""
        fields = item.get("fields", {})
        return Article(
            url=item.get("webUrl", ""),
            title=item.get("webTitle", ""),
            body=fields.get("bodyText") or fields.get("trailText") or "",
            source="The Guardian",
            source_level=source_level,
            locale=locale,
            published_at=item.get(
                "webPublicationDate",
                datetime.now(timezone.utc).isoformat(),
            ),
        )

    def get_world_news(
        self,
        locale: str = "san-diego-ca",
        page_size: int = 20,
        page: int = 1,
    ) -> list[Article]:
        """Fetch world/international news from The Guardian."""
        params: dict[str, Any] = {
            "section": "world",
            "page-size": min(page_size, 50),
            "page": page,
            "order-by": "newest",
            "show-fields": "bodyText,trailText",
        }
        data = self._request_with_retry(params)
        results = data.get("response", {}).get("results", [])
        return [
            self._item_to_article(r, "global", locale) for r in results
        ]

    def get_us_news(
        self,
        locale: str = "san-diego-ca",
        page_size: int = 20,
        page: int = 1,
    ) -> list[Article]:
        """Fetch US national news."""
        params: dict[str, Any] = {
            "section": "us-news",
            "page-size": min(page_size, 50),
            "page": page,
            "order-by": "newest",
            "show-fields": "bodyText,trailText",
        }
        data = self._request_with_retry(params)
        results = data.get("response", {}).get("results", [])
        return [
            self._item_to_article(r, "national", locale) for r in results
        ]

    def search(
        self,
        query: str,
        locale: str = "san-diego-ca",
        from_days_ago: int = 7,
        page_size: int = 20,
    ) -> list[Article]:
        """Search Guardian articles by keyword."""
        from_date = (
            datetime.now(timezone.utc) - timedelta(days=from_days_ago)
        ).strftime("%Y-%m-%d")
        params: dict[str, Any] = {
            "q": query,
            "from-date": from_date,
            "page-size": min(page_size, 50),
            "order-by": "relevance",
            "show-fields": "bodyText,trailText",
        }
        data = self._request_with_retry(params)
        results = data.get("response", {}).get("results", [])
        return [
            self._item_to_article(r, "national", locale) for r in results
        ]
