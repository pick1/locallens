"""
Local Impact Generator — Generates local impact analysis from global headlines.

This agent takes a global/national headline + locale profile and DIRECTLY
generates a local impact analysis. No local article matching required.

This is the "scoop" capability: producing unique local impact analysis
before traditional media covers the local angle.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from config import settings
from llm_client import get_llm_client

logger = logging.getLogger(__name__)


# ── Structured Output Schema ─────────────────────────────────────────────


class LocalImpactOutput(BaseModel):
    """Structured output from the local impact generator."""

    has_local_impact: bool = Field(
        description="Whether this story has a real, measurable local impact"
    )
    confidence: str = Field(
        description="Confidence level: low, medium, or high"
    )
    card_title: str = Field(
        description="Compelling title combining global story and local angle (max 15 words)"
    )
    mechanism: str = Field(
        description="The causal or contextual mechanism linking the global event to local impact (2-3 sentences)"
    )
    card_body: str = Field(
        description="Full analysis: global context, local impact pathway, specific affected groups/sectors (2-3 paragraphs)"
    )
    neighborhoods_or_groups_affected: list[str] = Field(
        description="Specific San Diego neighborhoods, demographic groups, or business sectors affected"
    )
    topics: list[str] = Field(
        description="Topic categories: subsets of Economy, Environment, Community & Demographics, Public Health, Policy, Infrastructure"
    )
    is_sensitive: bool = Field(
        description="True if topic is politically sensitive (foreign conflicts, immigration, policing, abortion policy)"
    )
    scoop_angle: str = Field(
        description="What makes this analysis original — the angle that local media hasn't yet reported (1 sentence)"
    )


# ── Prompt Templates ──────────────────────────────────────────────────────


IMPACT_GENERATION_SYSTEM_PROMPT = """You are an expert local impact analyst for LocalLens. Your job is to connect global and national news stories to their predicted local impact on a specific US city.

You are NOT summarizing existing local news coverage. You are ORIGINALLY ANALYZING how a global story will affect the city's specific demographics, economy, infrastructure, neighborhoods, and communities.

Key principles:
- Be specific: name actual neighborhoods, companies, organizations, and demographic groups
- Be causal: explain the mechanism clearly — how does the global event lead to local impact?
- Be original: produce analysis that a local journalist would find insightful — your goal is to SCOOP local media by identifying impacts before they're reported
- Be honest: if the connection is weak, say so with low confidence
- For politically sensitive topics, present multiple perspectives

Confidence rubric:
- HIGH: Direct causal chain with named local entities (port policy → Port of SD, federal funding → specific SDG&E project)
- MEDIUM: Plausible mechanism with indirect evidence (tariff changes → price effects on local consumers)
- LOW: Thematic overlap only, speculative or distant link"""


def _build_generation_prompt(
    headline: dict[str, Any],
    locale_profile: dict[str, Any],
) -> str:
    """Build the prompt for local impact generation.

    Args:
        headline: Dict with title, body, source, published_at.
        locale_profile: Rich locale context dict.

    Returns:
        Formatted prompt string.
    """
    # Format locale profile for the prompt
    profile_sections = [
        f"## Locale: {locale_profile.get('display_name', 'Unknown')}",
    ]

    # Demographics
    demo = locale_profile.get("demographics", {})
    if demo:
        demo_lines = "\n".join(f"- {k}: {v}" for k, v in demo.items())
        profile_sections.append(f"\n### Demographics\n{demo_lines}")

    # Economy
    economy = locale_profile.get("economy", {})
    if economy:
        econ_lines = "\n".join(f"- {k}: {v}" for k, v in economy.items())
        profile_sections.append(f"\n### Economy\n{econ_lines}")

    # Key industries
    industries = locale_profile.get("key_industries", [])
    if industries:
        profile_sections.append(f"\n### Key Industries\n" + "\n".join(f"- {i}" for i in industries))

    # Major employers
    employers = locale_profile.get("major_employers", [])
    if employers:
        profile_sections.append(f"\n### Major Employers\n" + "\n".join(f"- {e}" for e in employers))

    # Geography
    geo = locale_profile.get("geography", {})
    if geo:
        geo_lines = "\n".join(f"- {k}: {v}" for k, v in geo.items())
        profile_sections.append(f"\n### Geography & Climate\n{geo_lines}")

    # Infrastructure
    infra = locale_profile.get("infrastructure", {})
    if infra:
        infra_lines = "\n".join(f"- {k}: {v}" for k, v in infra.items())
        profile_sections.append(f"\n### Infrastructure\n{infra_lines}")

    # Government
    govt = locale_profile.get("government_entities", [])
    if govt:
        profile_sections.append(f"\n### Government & Regulation\n" + "\n".join(f"- {g}" for g in govt))

    # Active issues
    issues = locale_profile.get("active_local_issues", [])
    if issues:
        profile_sections.append(f"\n### Active Local Issues\n" + "\n".join(f"- {i}" for i in issues))

    # Military
    military = locale_profile.get("military", {})
    if military:
        mil_lines = "\n".join(f"- {k}: {v}" for k, v in military.items())
        profile_sections.append(f"\n### Military Presence\n{mil_lines}")

    # Community info
    community = locale_profile.get("community_organizations", [])
    if community:
        profile_sections.append(f"\n### Community Organizations\n" + "\n".join(f"- {c}" for c in community))

    profile_text = "\n".join(profile_sections)

    prompt = f"""Analyze the local impact of this global/national story on the specified locale.

## Global/National Headline
Title: {headline.get('title', 'Untitled')}
Source: {headline.get('source', 'Unknown')}
Published: {headline.get('published_at', '')}
Body:
{(headline.get('body', '') or '')[:4000]}

{profile_text}

Determine whether this story has a real, measurable impact on the locale. If it does,
generate a complete local impact analysis. Be specific about which neighborhoods,
demographic groups, business sectors, or government entities are affected.

Your analysis MUST be original — do not reference existing local news coverage.
Produce the kind of insightful analysis that would SCOOP local journalists."""
    return prompt


# ── Local Impact Generator ────────────────────────────────────────────────


class LocalImpactGenerator:
    """Generates local impact analysis from global headlines + locale profile.

    This is the core "scoop" capability — producing original local impact
    analysis that hasn't been reported by local media yet.
    """

    def __init__(self) -> None:
        self._llm = get_llm_client()

    def generate(
        self,
        headline: dict[str, Any],
        locale_profile: dict[str, Any],
    ) -> LocalImpactOutput | None:
        """Generate a local impact analysis from a global headline.

        Args:
            headline: Dict with title, body, source, published_at.
            locale_profile: Rich locale context dict (demographics, economy,
                geography, infrastructure, military, community).

        Returns:
            LocalImpactOutput if impact detected, None otherwise.
        """
        if not self._llm or not self._llm.available:
            logger.warning("No LLM client available — skipping impact generation")
            return None

        prompt = _build_generation_prompt(headline, locale_profile)

        try:
            result_data = self._llm.generate_structured(
                prompt=prompt,
                response_model=LocalImpactOutput,
                system_prompt=IMPACT_GENERATION_SYSTEM_PROMPT,
            )
            if isinstance(result_data, dict):
                # Safety net: LLMs (especially Ollama) sometimes return strings
                # where we expect lists. Coerce common list fields.
                if isinstance(result_data.get("neighborhoods_or_groups_affected"), str):
                    result_data["neighborhoods_or_groups_affected"] = [
                        s.strip() for s in result_data["neighborhoods_or_groups_affected"].split(",")
                        if s.strip()
                    ]
                if isinstance(result_data.get("topics"), str):
                    result_data["topics"] = [
                        s.strip() for s in result_data["topics"].split(",")
                        if s.strip()
                    ]
                result = LocalImpactOutput(**result_data)
            else:
                result = result_data
        except Exception:
            logger.exception("Impact generation failed for headline: %s",
                             headline.get("title", "")[:60])
            return None

        if not result.has_local_impact:
            logger.debug("No local impact: %s", headline.get("title", "")[:60])
            return None

        logger.info(
            "Impact generated: %s (confidence=%s, topics=%s, scoop=%s...)",
            result.card_title[:50],
            result.confidence,
            result.topics,
            result.scoop_angle[:60] if result.scoop_angle else "",
        )
        return result

    def validate(
        self,
        global_article: dict[str, Any],
        local_article: dict[str, Any],
        locale_profile: dict[str, Any] | None = None,
    ) -> LocalImpactOutput | None:
        """Legacy interface — matches old test API.

        In the new architecture this generates impact from the global article
        using the locale profile. The local_article parameter is accepted
        for backward compatibility but is not used for impact generation.

        Args:
            global_article: Dict with title, body, source, published_at.
            local_article: Ignored in new architecture (kept for tests).
            locale_profile: Optional locale context dict.

        Returns:
            LocalImpactOutput if impact detected, None otherwise.
        """
        if not locale_profile:
            return None
        return self.generate(global_article, locale_profile)
