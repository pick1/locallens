"""
Deep dive modal component for LocalLens Streamlit UI.

Implements a full-analysis modal overlay triggered by the "Go Deeper" button
on any connection card. Shows:
- Timeline of the global story (5-7 key events)
- Named local stakeholders
- Historical precedents
- Suggested local sources
- Related connection cards
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from agents.deep_dive_agent import (
    DeepDiveContent,
    DeepDiveAgent,
    extract_stakeholders,
)

# ── Seed deep-dive content for demo mode ──────────────────────────────────

SEED_DEEP_DIVES: dict[str, dict[str, Any]] = {
    "seed-1": {
        "timeline": [
            {"date": "Mar 2024", "event": "Strait of Hormuz tensions escalate after Iranian seizure of commercial vessel"},
            {"date": "Apr 2024", "event": "US deploys additional naval assets to the Persian Gulf"},
            {"date": "May 2024", "event": "Iranian-backed Houthi attacks on Red Sea shipping intensify"},
            {"date": "Jun 2024", "event": "US Congress holds hearings on Iran strategy"},
            {"date": "Jul 2024", "event": "Diplomatic backchannel talks mediated by Oman reported"},
            {"date": "Aug 2024", "event": "IRGC conducts military exercises near Hormuz"},
            {"date": "Sep 2024", "event": "Oil prices spike 12% on supply disruption fears"},
        ],
        "stakeholders": [
            "Council on American-Islamic Relations (CAIR) San Diego",
            "Islamic Center of San Diego",
            "Somali Family Service of San Diego",
            "International Rescue Committee San Diego",
            "San Diego County Office of Immigrant and Refugee Affairs",
            "El Cajon City Council",
            "San Diego Police Department — Hate Crime Unit",
            "UCSD Center for Muslim-American Studies",
        ],
        "historical_precedents": [
            {"event": "Post-9/11 anti-Muslim backlash (2001)", "local_impact": "San Diego saw a 300% increase in hate incidents; CAIR San Diego established support hotline"},
            {"event": "Trump travel ban executive order (2017)", "local_impact": "San Diego International Airport saw protests; local Yemeni community in El Cajon directly affected by visa suspension"},
            {"event": "Iran nuclear deal withdrawal (2018)", "local_impact": "Iranian-American community in San Diego reported increased anxiety; local businesses with Iran trade links affected"},
        ],
        "suggested_sources": [
            "Voice of San Diego — immigration and community beat",
            "San Diego Union-Tribune — military and foreign affairs coverage",
            "KPBS — local community impact reporting",
            "CAIR San Diego newsletter",
            "San Diego County Grand Jury reports on hate incidents",
        ],
        "related_themes": [
            "Immigration and refugee resettlement",
            "Hate crime monitoring and prevention",
            "Military-diplomatic policy and local communities",
        ],
    },
    "seed-2": {
        "timeline": [
            {"date": "Jan 2024", "event": "California Sierra Nevada snowpack measured at 80% of normal"},
            {"date": "Mar 2024", "event": "Drought conditions worsen; snowpack drops to 60%"},
            {"date": "May 2024", "event": "Governor Newsom issues drought preparedness executive order"},
            {"date": "Jul 2024", "event": "Lake Mead levels drop to critical threshold"},
            {"date": "Aug 2024", "event": "Bureau of Reclamation announces Colorado River Tier 2 shortage"},
            {"date": "Sep 2024", "event": "San Diego County Water Authority activates drought contingency plan"},
            {"date": "Oct 2024", "event": "Imperial Irrigation District announces voluntary fallowing program"},
        ],
        "stakeholders": [
            "San Diego County Water Authority",
            "Imperial Irrigation District",
            "Metropolitan Water District of Southern California",
            "San Diego City Council — Environment Committee",
            "Farm Bureau of Imperial Valley",
            "California Department of Water Resources",
            "UCSD Scripps Institution of Oceanography",
            "San Diego Coastkeeper",
        ],
        "historical_precedents": [
            {"event": "2012-2016 California drought", "local_impact": "San Diego imposed mandatory 16% water use reduction; desalination plant in Carlsbad accelerated"},
            {"event": "2021 Colorado River Basin Tier 1 shortage", "local_impact": "Imperial Valley farmers received $150/acre-foot fallowing payments; Arizona bore larger cuts"},
            {"event": "1991 drought emergency", "local_impact": "San Diego considered water recycling mandates; led to Pure Water San Diego program"},
        ],
        "suggested_sources": [
            "San Diego County Water Authority — drought updates",
            "Imperial Valley Press — agricultural coverage",
            "CalMatters — California water policy",
            "KPBS — environment and climate reporting",
            "Water Education Foundation — Colorado River news",
        ],
        "related_themes": [
            "Climate adaptation and infrastructure",
            "Agricultural policy and rural communities",
            "Urban water conservation",
        ],
    },
    "seed-3": {
        "timeline": [
            {"date": "Mar 2025", "event": "Federal port automation rules announced by DOT"},
            {"date": "Apr 2025", "event": "ILWU raises concerns about job displacement"},
            {"date": "May 2025", "event": "Port of Los Angeles announces phased automation plan"},
            {"date": "Jun 2025", "event": "Cargo diversion to smaller ports begins"},
            {"date": "Jul 2025", "event": "Port of San Diego reports 15% cargo volume increase"},
            {"date": "Aug 2025", "event": "ILWU Local 29 San Diego holds negotiations with port authority"},
            {"date": "Sep 2025", "event": "Federal mediation requested in automation labor dispute"},
        ],
        "stakeholders": [
            "Port of San Diego",
            "ILWU Local 29",
            "San Diego Regional Chamber of Commerce",
            "San Diego Maritime Terminal operators",
            "US Maritime Administration (MARAD)",
            "San Diego City Council — Economic Development Committee",
            "California Air Resources Board (emissions from redirected cargo)",
        ],
        "historical_precedents": [
            {"event": "2002 West Coast port lockout", "local_impact": "San Diego port experienced 2-week shutdown; local manufacturers shifted to air freight"},
            {"event": "2015 ILWU contract negotiations", "local_impact": "Port congestion led to some cargo diversion to San Diego; temporary labor shortages"},
            {"event": "Panama Canal expansion 2016", "local_impact": "Shifted some East Coast cargo away from West Coast; San Diego saw modest throughput decline"},
        ],
        "suggested_sources": [
            "Port of San Diego — news releases",
            "ILWU Local 29 — labor updates",
            "Journal of Commerce — maritime industry coverage",
            "San Diego Union-Tribune — business and economy",
            "FreightWaves — logistics and supply chain",
        ],
        "related_themes": [
            "Automation and workforce transition",
            "Port infrastructure and trade",
            "Labor relations and collective bargaining",
        ],
    },
}


def render_deep_dive_modal(connection_id: str) -> None:
    """Open a Streamlit dialog with the full deep-dive analysis.

    Args:
        connection_id: The ID of the connection to analyze.
    """
    @st.dialog("🔍 Deep Dive Analysis", width="large")
    def _modal(conn_id: str):
        # Try to find the connection in session state
        connection = _find_connection(conn_id)
        if not connection:
            st.error("Connection not found. It may have expired.")
            return

        # Try to get cached deep dive content
        cache_key = f"deep_dive_{conn_id}"
        if cache_key in st.session_state:
            content = st.session_state[cache_key]
        else:
            # Generate or use seed content
            content = _get_deep_dive_content(conn_id, connection)
            if content:
                st.session_state[cache_key] = content

        if not content:
            st.warning("Unable to generate deep-dive analysis. Using basic article information.")
            _render_basic(connection)
            return

        _render_deep_dive(content, connection)

    _modal(connection_id)


def _find_connection(conn_id: str) -> dict[str, Any] | None:
    """Find a connection by ID in session state connections."""
    connections = st.session_state.get("connections", [])
    for conn in connections:
        if conn.get("id") == conn_id:
            return conn
    return None


def _get_deep_dive_content(
    conn_id: str, connection: dict[str, Any]
) -> DeepDiveContent | None:
    """Get deep-dive content, using seed data or generating via agent."""
    # Check for seed content
    if conn_id in SEED_DEEP_DIVES:
        seed = SEED_DEEP_DIVES[conn_id]
        return DeepDiveContent(
            timeline=seed["timeline"],
            stakeholders=seed["stakeholders"],
            historical_precedents=seed["historical_precedents"],
            suggested_sources=seed["suggested_sources"],
            related_themes=seed["related_themes"],
        )

    # Fall back to NER-based extraction from available text
    combined_text = (
        connection.get("card_body", "")
        + " "
        + connection.get("mechanism_text", "")
    )
    stakeholders = extract_stakeholders(combined_text)

    return DeepDiveContent(
        timeline=[
            {"date": "Recent", "event": connection.get("card_title", "")},
        ],
        stakeholders=stakeholders or ["Local community organizations"],
        historical_precedents=[],
        suggested_sources=[],
        related_themes=connection.get("topics", []),
    )


def _render_deep_dive(content: DeepDiveContent, connection: dict[str, Any]) -> None:
    """Render the full deep-dive analysis content."""
    # Header with connection info
    st.markdown(f"### {connection.get('card_title', '')}")
    st.markdown(
        f"""
        <div style="font-size:0.85rem; color:#6b7280; margin-bottom:1rem;">
            Confidence: <span class="badge badge-{connection.get('confidence', 'low')}">
            {connection.get('confidence', 'low').upper()}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Mechanism summary
    st.markdown("#### 🔗 Connection Mechanism")
    st.markdown(connection.get("mechanism_text", ""))

    # Timeline
    if content.timeline:
        st.markdown("#### 📅 Timeline")
        for event in content.timeline:
            st.markdown(
                f"""<div style="display:flex; gap:1rem; margin-bottom:0.4rem;">
                    <span style="font-weight:600; min-width:100px; color:#1a1a2e;">
                        {event.get('date', '')}
                    </span>
                    <span>{event.get('event', '')}</span>
                </div>""",
                unsafe_allow_html=True,
            )

    # Stakeholders
    if content.stakeholders:
        st.markdown("#### 🏛️ Local Stakeholders")
        cols = st.columns(2)
        half = len(content.stakeholders) // 2 + len(content.stakeholders) % 2
        for i, stakeholder in enumerate(content.stakeholders):
            col_idx = 0 if i < half else 1
            with cols[col_idx]:
                st.markdown(f"- {stakeholder}")

    # Historical precedents
    if content.historical_precedents:
        st.markdown("#### 📜 Historical Precedents")
        for precedent in content.historical_precedents:
            with st.container():
                st.markdown(f"**{precedent.get('event', '')}**")
                st.markdown(f"_{precedent.get('local_impact', '')}_")
                st.markdown("---")

    # Suggested sources
    if content.suggested_sources:
        st.markdown("#### 📰 Suggested Local Sources")
        for source in content.suggested_sources:
            st.markdown(f"- {source}")

    # Related themes
    if content.related_themes:
        st.markdown("#### 🔄 Related Themes")
        theme_str = " ".join(
            f'<span style="display:inline-block; font-size:0.8rem; '
            f'padding:0.1rem 0.5rem; background:#f3f4f6; border-radius:6px; '
            f'margin:0.2rem;">{t}</span>'
            for t in content.related_themes
        )
        st.markdown(theme_str, unsafe_allow_html=True)

    # Disclaimer
    st.markdown(
        """
        <div class="disclaimer">
            ⚠️ AI-synthesized analysis. Verify all information with original sources.
            No personally identifiable information is stored.
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_basic(connection: dict[str, Any]) -> None:
    """Fallback: render basic connection info without deep-dive."""
    st.markdown(f"### {connection.get('card_title', '')}")
    st.markdown(connection.get("card_body", ""))
    st.markdown(
        f"**Mechanism:** {connection.get('mechanism_text', '')}"
    )
