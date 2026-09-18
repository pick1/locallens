"""
Connection card component for LocalLens Streamlit UI.

Renders a single connection card showing:
- Global story → mechanism → local impact
- Source badges and confidence indicator
- "Go Deeper" button for full analysis
- AI-generated content disclaimer
"""

from __future__ import annotations

from typing import Any, Callable

import streamlit as st


def render_connection_card(
    connection: dict[str, Any],
    key: str,
    on_deep_dive: Callable[[str], None] | None = None,
) -> None:
    """Render a single connection card.

    Uses Streamlit-native components where possible, with targeted
    unsafe_allow_html for badges and topic tags that need custom styling.

    Args:
        connection: Connection dict with keys: card_title, mechanism_text,
            card_body, confidence, topics, id, global_source, local_source.
        key: Unique key for Streamlit widget scoping.
        on_deep_dive: Optional callback for the "Go Deeper" button.
    """
    card_title = connection.get("card_title", "Untitled Connection")
    mechanism = connection.get("mechanism_text", "")
    confidence = connection.get("confidence", "low")
    topics = connection.get("topics", [])
    is_sensitive = connection.get("is_sensitive", False)
    conn_id = connection.get("id", key)
    scoop_angle = connection.get("scoop_angle", "")
    neighborhoods = connection.get("neighborhoods_affected", "")
    local_source = connection.get("local_source", "")

    # Open card wrapper
    st.markdown('<div class="card-wrapper">', unsafe_allow_html=True)

    # ── Card title (Streamlit-native heading) ──────────────────────
    st.subheader(card_title, anchor=False)

    # ── Badge row ──────────────────────────────────────────────────
    confidence_class = (
        f"badge-{confidence}"
        if confidence in ("high", "medium", "low")
        else "badge-low"
    )
    badge_parts = [
        f'<span class="badge {confidence_class}">'
        f"{_escape_html(confidence.upper())}"
        f"</span>"
    ]
    # Add "Scoop" badge for AI-generated original analysis
    if "AI-generated" in local_source or scoop_angle:
        badge_parts.append(
            '<span class="badge badge-scoop">'
            "&#x1F300; Scoop</span>"
        )
    if is_sensitive:
        badge_parts.append(
            '<span class="badge badge-sensitive">'
            "&#x2696;&#xFE0F; Multiple perspectives</span>"
        )
    st.markdown(
        f'<div style="margin-bottom: 0.6rem;">{" ".join(badge_parts)}</div>',
        unsafe_allow_html=True,
    )

    # ── Topic tags ─────────────────────────────────────────────────
    if topics:
        topic_html = " ".join(
            f'<span class="topic-tag">{_escape_html(t)}</span>' for t in topics
        )
        st.markdown(
            f'<div style="margin-bottom: 0.5rem;">{topic_html}</div>',
            unsafe_allow_html=True,
        )

    # ── Location tag ───────────────────────────────────────────────
    if neighborhoods:
        st.markdown(
            f'<div class="neighborhoods-tag">&#x1F4CD; Affects: {_escape_html(neighborhoods)}</div>',
            unsafe_allow_html=True,
        )

    # ── Mechanism text ─────────────────────────────────────────────
    if mechanism:
        st.markdown(
            f'<p class="card-mechanism">{_escape_html(mechanism)}</p>',
            unsafe_allow_html=True,
        )

    # ── Expandable card body ───────────────────────────────────────
    card_body = connection.get("card_body", "")
    with st.expander("Read full analysis"):
        st.markdown(
            f'<div style="font-size:0.9rem; line-height:1.6; color:#374151;">'
            f"{_escape_html(card_body).replace(chr(10), '<br>')}"
            f"</div>",
            unsafe_allow_html=True,
        )
        # Scoop angle
        if scoop_angle:
            st.markdown(
                f'<div class="scoop-angle-box">'
                f"<strong>&#x1F4A1; Original Analysis:</strong> "
                f"{_escape_html(scoop_angle)}"
                f"</div>",
                unsafe_allow_html=True,
            )
        # Source attribution
        st.markdown(
            f'<div style="margin-top:0.75rem; font-size:0.8rem; color:#6b7280;">'
            f"<strong>Global source:</strong> "
            f"{_escape_html(connection.get('global_source', 'Global'))}"
            f"<br>"
            f"<strong>Local impact:</strong> "
            f"{_escape_html(local_source)}"
            f"</div>"
            f'<div class="disclaimer">'
            f"&#x26A0;&#xFE0F; AI-synthesized analysis based on source articles. "
            f"Verify with original sources."
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── "Go Deeper" button ────────────────────────────────────────
    if on_deep_dive:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.button(
                "🔍 Go Deeper",
                key=f"deep_dive_{key}",
                type="secondary",
                use_container_width=True,
                on_click=on_deep_dive,
                args=(conn_id,),
            )

    # Close card wrapper
    st.markdown("</div>", unsafe_allow_html=True)


def _escape_html(text: str) -> str:
    """Escape HTML special characters.

    Args:
        text: Raw text to escape.

    Returns:
        Text safe for insertion into HTML content.
    """
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )
