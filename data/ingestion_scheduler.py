"""
Ingestion scheduler for LocalLens.

Runs periodic news ingestion jobs via APScheduler.
Designed to run inside the Streamlit process (acceptable for MVP on single dyno).

Limitation: ingestion stops when no user is running the app.
Documented — should be promoted to a separate worker dyno for production.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler

from config import settings

logger = logging.getLogger(__name__)


class IngestionScheduler:
    """Manages periodic ingestion of news articles from all sources."""

    def __init__(self) -> None:
        self._scheduler = BackgroundScheduler(daemon=True)
        self._ingestion_fn: Callable[[], int] | None = None
        self._last_run: str | None = None
        self._last_count: int = 0

    @property
    def last_run(self) -> str | None:
        return self._last_run

    @property
    def last_count(self) -> int:
        return self._last_count

    def configure(
        self,
        ingestion_fn: Callable[[str], int],
        locale: str = "",
        interval_hours: int = 6,
    ) -> None:
        """Configure the ingestion job.

        Args:
            ingestion_fn: Callable that takes a locale slug and returns
                count of new articles ingested.
            locale: Default locale slug to ingest for.
            interval_hours: How often to run ingestion.
        """
        self._ingestion_fn = ingestion_fn
        locale_to_use = locale or settings.default_locale

        def _run_ingestion() -> None:
            try:
                logger.info("Starting scheduled ingestion for %s", locale_to_use)
                count = ingestion_fn(locale_to_use)
                self._last_run = datetime.now(timezone.utc).isoformat()
                self._last_count = count
                logger.info("Ingestion complete: %d new articles", count)
            except Exception:
                logger.exception("Ingestion job failed")

        self._scheduler.add_job(
            _run_ingestion,
            "interval",
            hours=interval_hours,
            id="news_ingestion",
            name="News Ingestion",
            next_run_time=None,  # don't run on start; call run_once() first
        )

    def run_once(self) -> int:
        """Immediately run the ingestion job (called on app startup)."""
        if self._ingestion_fn is None:
            logger.warning("Ingestion not configured — skipping run_once")
            return 0
        try:
            logger.info("Running initial ingestion...")
            count = self._ingestion_fn(settings.default_locale)
            self._last_run = datetime.now(timezone.utc).isoformat()
            self._last_count = count
            logger.info("Initial ingestion complete: %d new articles", count)
            return count
        except Exception:
            logger.exception("Initial ingestion failed")
            return 0

    def start(self) -> None:
        """Start the background scheduler."""
        if not self._scheduler.get_job("news_ingestion"):
            logger.warning("Ingestion not configured — scheduler not started")
            return
        self._scheduler.start()
        logger.info("Ingestion scheduler started")

    def stop(self) -> None:
        """Shut down the scheduler gracefully."""
        self._scheduler.shutdown(wait=False)
        logger.info("Ingestion scheduler stopped")
