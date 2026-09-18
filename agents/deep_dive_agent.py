"""
Deep Dive Agent — generates comprehensive analysis for a connection card.

Input: connection_id
Process:
1. Fetch source articles and connection record from Supabase
2. Web search for historical precedents (Tavily API, if configured)
3. Extract named local stakeholders via spaCy NER
4. Synthesize full deep-dive markdown via GPT-4o
Output: structured DeepDiveContent with timeline, stakeholders, precedents, sources
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from config import settings
from llm_client import get_llm_client

logger = logging.getLogger(__name__)


# ── Structured Output ─────────────────────────────────────────────────────


class DeepDiveContent(BaseModel):
    """Full deep-dive analysis for a connection card."""

    timeline: list[dict[str, str]] = Field(
        description="List of 5-7 key events in the global story, each with 'date' and 'event' keys"
    )
    stakeholders: list[str] = Field(
        description="Named local stakeholders likely affected (organizations, city departments, community groups)"
    )
    historical_precedents: list[dict[str, str]] = Field(
        description="Similar past events and what happened locally, each with 'event' and 'local_impact' keys"
    )
    suggested_sources: list[str] = Field(
        description="Suggested local sources to follow for ongoing coverage"
    )
    related_themes: list[str] = Field(
        description="Related local themes this connection touches on"
    )


# ── Deep Dive Prompt ──────────────────────────────────────────────────────

DEEP_DIVE_SYSTEM_PROMPT = """You are a senior research analyst for LocalLens. Your job is to produce
a comprehensive "deep dive" analysis for a connection between a global/national story
and its predicted local impact.

Since this analysis is AI-generated (scooping local media), base your deep dive on:
1. The global/national headline and its body text
2. The AI-generated impact analysis text
3. The locale profile (demographics, economy, infrastructure, geography)

Produce a structured analysis with:
1. A timeline of the global story (5-7 key events with dates)
2. Named local stakeholders likely affected
3. Historical precedents from similar past events
4. Suggested local sources for ongoing coverage
5. Related local themes

When discussing politically sensitive topics, present multiple perspectives
and avoid attributing intent to named political figures."""

DEEP_DIVE_PROMPT = """Produce a deep-dive analysis for this predicted local impact:

## Global/National Headline
Title: {global_title}
Source: {global_source}
Published: {global_date}
Body: {global_body}

## AI-Generated Local Impact Analysis
{impact_analysis}

## Connection Confidence Assessment
Confidence: {confidence}
Mechanism: {mechanism}
Topics: {topics}

## Locale Profile
{locale_context}

## Historical Context
{historical_context}

Generate a comprehensive deep-dive analysis. Since the local impact analysis
is AI-generated (a "scoop" prediction), be explicit about what is grounded
in the global article vs. inferred from the locale profile."""


# ── NER Extraction ─────────────────────────────────────────────────────────


def extract_stakeholders(text: str) -> list[str]:
    """Extract named organizations and entities using spaCy.

    Falls back to basic keyword extraction if spaCy model is unavailable.
    """
    try:
        import spacy
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            # spaCy model not downloaded — skip NER
            logger.warning("spaCy en_core_web_sm not available — skipping NER")
            return _fallback_extract_stakeholders(text)

        doc = nlp(text[:10000])  # limit for performance
        orgs = set()
        govt_entities = set()

        for ent in doc.ents:
            if ent.label_ == "ORG":
                orgs.add(ent.text)
            elif ent.label_ in ("GPE", "LAW"):
                govt_entities.add(ent.text)

        # Prioritize entities appearing multiple times
        combined = list(orgs) + list(govt_entities)
        return combined[:15]  # top 15 stakeholders
    except Exception:
        logger.exception("spaCy NER failed — using fallback")
        return _fallback_extract_stakeholders(text)


def _fallback_extract_stakeholders(text: str) -> list[str]:
    """Basic keyword-based stakeholder extraction when spaCy unavailable."""
    import re
    # Common entity patterns: capitalized phrases
    candidates = re.findall(
        r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", text
    )
    # Filter out common non-entities
    skip = {"The", "When", "What", "This", "That", "There", "These", "Those", "While"}
    filtered = [
        c for c in candidates
        if c.split()[0] not in skip
    ]
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for c in filtered:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique[:15]


# ── Deep Dive Agent ────────────────────────────────────────────────────────


class DeepDiveAgent:
    """Generates comprehensive deep-dive analysis for a connection."""

    def __init__(self) -> None:
        self._llm = get_llm_client()

    def generate_deep_dive(
        self,
        connection: dict[str, Any],
        global_article: dict[str, Any],
        local_article: dict[str, Any] | None = None,
        locale_profile: dict[str, Any] | None = None,
    ) -> DeepDiveContent | None:
        """Generate a full deep-dive analysis.

        Args:
            connection: The connection record dict.
            global_article: The global/national article dict.
            local_article: Optional local article dict (may be None in scoop mode).
            locale_profile: Optional locale profile dict.

        Returns:
            DeepDiveContent with structured analysis, or None on failure.
        """
        # Step 1: Web search for historical context (Tavily, if available)
        historical_context = self._search_historical_context(
            global_article.get("title", ""),
        )

        # Step 2: Build locale context string
        locale_context = ""
        if locale_profile:
            locale_context = json.dumps(
                {
                    "name": locale_profile.get("display_name", ""),
                    "demographics": locale_profile.get("demographics", {}),
                    "economy": locale_profile.get("economy", {}),
                    "industries": locale_profile.get("key_industries", []),
                    "employers": locale_profile.get("major_employers", []),
                    "geography": locale_profile.get("geography", {}),
                    "infrastructure": locale_profile.get("infrastructure", {}),
                    "military": locale_profile.get("military", {}),
                    "issues": locale_profile.get("active_local_issues", []),
                    "community": locale_profile.get("community_organizations", []),
                },
                indent=2,
            )

        # Step 3: Use the AI-generated impact analysis as the "local" content
        impact_analysis = (
            f"Card Title: {connection.get('card_title', '')}\n\n"
            f"Body: {connection.get('card_body', '')}\n\n"
            f"Mechanism: {connection.get('mechanism_text', '')}\n\n"
            f"Scoop Angle: {connection.get('scoop_angle', '')}\n\n"
            f"Neighborhoods Affected: {connection.get('neighborhoods_affected', '')}"
        )

        # Step 4: Generate deep-dive via LLM
        prompt = DEEP_DIVE_PROMPT.format(
            global_title=global_article.get("title", "Untitled"),
            global_source=global_article.get("source", "Unknown"),
            global_date=global_article.get("published_at", ""),
            global_body=global_article.get("body", "")[:4000],
            impact_analysis=impact_analysis,
            confidence=connection.get("confidence", "unknown"),
            mechanism=connection.get("mechanism_text", ""),
            topics=", ".join(connection.get("topics", [])),
            locale_context=locale_context,
            historical_context=historical_context,
        )

        try:
            result = self._llm.generate_structured(
                prompt=prompt,
                response_model=DeepDiveContent,
                system_prompt=DEEP_DIVE_SYSTEM_PROMPT,
                temperature=0.4,  # slightly higher for creative synthesis
            )
        except Exception:
            logger.exception("Deep dive LLM call failed")
            return None

        # Step 4: NER-based stakeholder extraction from global + impact text
        impact_text = connection.get("card_body", "") or ""
        global_body = global_article.get("body", "") or ""
        combined_text = f"{global_body} {impact_text}"
        ner_stakeholders = extract_stakeholders(combined_text)
        if ner_stakeholders:
            # Merge LLM-identified stakeholders with NER findings
            all_stakeholders = list(set(result.stakeholders + ner_stakeholders))
            result.stakeholders = all_stakeholders[:20]

        logger.info("Deep dive generated for connection %s", connection.get("id", "unknown"))
        return result

    def _search_historical_context(
        self, global_title: str
    ) -> str:
        """Search for historical precedents via Tavily API.

        Falls back gracefully if Tavily is not configured.
        """
        if not settings.tavily_api_key:
            return "No historical search available (Tavily API key not configured)."

        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=settings.tavily_api_key)
            query = f"similar past events to {global_title} and impact on local communities"
            response = client.search(query=query, max_results=3)
            results = response.get("results", [])
            if not results:
                return "No relevant historical precedents found."
            return "\n".join(
                f"- {r.get('title', '')}: {r.get('content', '')[:200]}"
                for r in results
            )
        except ImportError:
            logger.warning("tavily-python not installed")
            return "Historical search unavailable."
        except Exception:
            logger.exception("Tavily search failed")
            return "Historical search encountered an error."
