"""
Connection Discovery Agent — Headline monitoring for local impact.

This agent fetches global and national headlines, then uses the locale
profile to assess which stories are likely to have local impact.
No local articles needed — the locale profile IS the local context.

The goal: identify stories that will affect the city BEFORE local
journalists report on the local angle.
"""

from __future__ import annotations

import logging
from typing import Any

from config import settings

logger = logging.getLogger(__name__)


class RelevanceScorer:
    """Scores how relevant a global/national headline is to a locale.

    Uses the locale profile (demographics, economy, geography, infrastructure)
    to assess whether a story likely has local impact. In production this
    uses a lightweight LLM call; in demo mode it uses keyword heuristics.
    """

    def __init__(self, llm_client: Any | None = None) -> None:
        self._llm = llm_client

    def score_relevance(
        self,
        headline: dict[str, Any],
        locale_profile: dict[str, Any],
    ) -> float:
        """Score a headline's likely local relevance for a locale.

        Args:
            headline: Dict with title, body, source, published_at.
            locale_profile: Rich locale context profile.

        Returns:
            Relevance score 0.0–1.0. Threshold for action > 0.5.
        """
        title = (headline.get("title") or "").lower()
        body = (headline.get("body") or "").lower()
        combined = f"{title} {body}"

        if self._llm and self._llm.available:
            return self._llm_score(headline, locale_profile)

        return self._heuristic_score(combined, locale_profile)

    _STOP_WORDS: set[str] = {
        "a", "an", "the", "of", "in", "on", "at", "to", "for",
        "and", "or", "with", "by", "is", "are", "was", "were",
        "be", "been", "being", "has", "have", "had", "do", "does",
        "did", "will", "would", "could", "should", "may", "might",
        "shall", "can", "its", "it's", "their", "our", "your",
        "this", "that", "these", "those", "from", "about",
    }

    def _heuristic_score(
        self, text: str, profile: dict[str, Any]
    ) -> float:
        """Quick keyword-based relevance heuristic for demo mode.

        Weighs hits against key dimensions from the locale profile.
        Checks: employers/industries (0.25 each), demographics/issues (0.15),
        geography/military/infrastructure (0.1 each).
        Filters out common stop words from multi-word phrases.
        """
        score = 0.0
        signals = 0

        # Check against key industries and employers
        employers = profile.get("major_employers", [])
        industries = profile.get("key_industries", [])
        for item in employers + industries:
            keywords = [w for w in item.lower().split() if w not in self._STOP_WORDS and len(w) >= 3]
            if not keywords:
                continue
            if any(kw in text for kw in keywords):
                score += 0.25
                signals += 1

        # Check against demographic keywords
        demo_text = str(profile.get("demographics", {})).lower()
        for term in demo_text.split(", "):
            term = term.strip().split(":")[0] if ":" in term else term.strip()
            if term and len(term) > 3 and term not in self._STOP_WORDS and term in text:
                score += 0.15
                signals += 1

        # Check against active local issues
        issues = profile.get("active_local_issues", [])
        for issue in issues:
            keywords = [w for w in issue.lower().split() if w not in self._STOP_WORDS]
            if not keywords:
                continue
            if any(kw in text for kw in keywords):
                score += 0.15
                signals += 1

        # Check against geography info
        geo = profile.get("geography", {})
        for val in geo.values():
            if isinstance(val, str) and val.lower() in text:
                score += 0.1
                signals += 1

        # Check against military installations
        mil = profile.get("military", {})
        for val in mil.values():
            if isinstance(val, str) and val.lower() in text:
                score += 0.1
                signals += 1

        # Check against infrastructure
        infra = profile.get("infrastructure", {})
        for val in infra.values():
            if isinstance(val, str) and val.lower() in text:
                score += 0.1
                signals += 1

        # Normalize
        result = min(score, 1.0)
        return result

    def _llm_score(
        self,
        headline: dict[str, Any],
        profile: dict[str, Any],
    ) -> float:
        """Use an LLM to score relevance.

        Constructs a structured prompt with headline details and locale
        context, then asks for a relevance score and reasoning.
        """
        prompt = (
            f"Global/National Headline: {headline.get('title', '')}\n\n"
            f"Summary: {(headline.get('body', '') or '')[:2000]}\n\n"
            f"Locale: {profile.get('display_name', 'Unknown')}\n"
            f"Demographics: {profile.get('demographics', {})}\n"
            f"Key industries: {', '.join(profile.get('key_industries', []))}\n"
            f"Major employers: {', '.join(profile.get('major_employers', []))}\n"
            f"Geography: {profile.get('geography', {})}\n"
            f"Infrastructure: {profile.get('infrastructure', {})}\n"
            f"Active local issues: {', '.join(profile.get('active_local_issues', []))}\n\n"
            f"On a scale of 0.0 to 1.0, how likely is this global/national "
            f"story to have a real, measurable impact on this locale? "
            f"Consider economic links, demographic connections, geographic "
            f"factors, supply chain effects, policy ripple effects, and "
            f"public health implications.\n\n"
            f"Respond with ONLY a single float between 0 and 1."
        )
        try:
            result = self._llm.generate(prompt, temperature=0.1, max_tokens=10)
            return max(0.0, min(1.0, float(result.strip())))
        except (ValueError, TypeError, AttributeError):
            return 0.0


class HeadlineMonitorAgent:
    """Monitors global/national headlines and identifies locally relevant stories.

    The agent:
    1. Fetches recent global/national headlines from Supabase
    2. For each headline, scores relevance using the locale profile
    3. Returns ranked list of headlines likely to have local impact
    """

    def __init__(self, supabase_client: Any | None = None) -> None:
        self._db = supabase_client
        self._scorer = RelevanceScorer()

    def discover(
        self,
        locale: str,
        locale_profile: dict[str, Any],
        hours: int = 24,
        max_headlines: int = 50,
    ) -> list[dict[str, Any]]:
        """Find global/national headlines relevant to the locale.

        Args:
            locale: Locale slug.
            locale_profile: Rich locale context dict.
            hours: Lookback window for headlines.
            max_headlines: Max headlines to evaluate.

        Returns:
            List of relevant headline dicts, sorted by relevance score,
            each with an added 'relevance_score' key.
        """
        logger.info(
            "Monitoring headlines for %s (lookback: %dh)",
            locale,
            hours,
        )

        headlines: list[dict[str, Any]] = []
        if self._db:
            headlines.extend(self._db.get_articles_by_level("global", hours=hours))
            headlines.extend(self._db.get_articles_by_level("national", hours=hours))
        else:
            logger.info("No database — discovery requires headline ingestion first")

        if not headlines:
            logger.info("No headlines to evaluate")
            return []

        logger.info("Scoring %d headlines for local relevance", len(headlines))

        # Score each headline
        scored: list[dict[str, Any]] = []
        for h in headlines[:max_headlines]:
            score = self._scorer.score_relevance(h, locale_profile)
            if score >= 0.35:  # low threshold for broad discovery
                h["relevance_score"] = round(score, 3)
                scored.append(h)

        scored.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        logger.info(
            "Found %d relevant headlines (top score: %.2f)",
            len(scored),
            scored[0]["relevance_score"] if scored else 0,
        )

        return scored
