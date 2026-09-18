"""Archive page for LocalLens — browse all past connection cards with filters.

Provides a searchable, filterable view of every connection card ever generated.
Filters: keyword search, topic categories, confidence level.
Results show in reverse chronological order with expandable cards.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

import streamlit as st

from data.local_storage import LocalDatabase
from ui.components.sidebar import TOPIC_CATEGORIES

logger = logging.getLogger(__name__)

CONFIDENCE_OPTIONS = ["All", "high", "medium", "low"]


def _get_archive_data(
    locale: str,
    keyword: str | None,
    selected_topics: list[str],
    selected_confidence: str,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    """Fetch connections from the local DB with filters.

    Returns (results, total_count).
    """
    db = LocalDatabase()
    topics = selected_topics if selected_topics else None
    confidence = selected_confidence if selected_confidence != "All" else None
    keyword_str = keyword.strip() if keyword and keyword.strip() else None

    results = db.search_connections(
        locale=locale,
        topics=topics,
        confidence=confidence,
        keyword=keyword_str,
        limit=limit,
        offset=offset,
    )

    # Get total count (same filters, no limit)
    total = len(
        db.search_connections(
            locale=locale,
            topics=topics,
            confidence=confidence,
            keyword=keyword_str,
            limit=10000,
        )
    )
    return results, total


def _render_archive_card(conn: dict[str, Any], on_deep_dive: Callable[[str], None]) -> None:
    """Render a single connection card in archive list view.

    More compact than the feed card — smaller header, no image placeholders.
    """
    card_id = f"conn-{conn['id']}"
    title = conn.get("card_title", "Untitled")
    body = conn.get("card_body", "")
    mechanism = conn.get("mechanism_text", "")
    confidence = conn.get("confidence", "medium")
    topics = conn.get("topics", []) or []
    is_sensitive = conn.get("is_sensitive", False)
    neighborhoods = conn.get("neighborhoods_affected", "")
    created_at = conn.get("created_at", "")
    scoop = conn.get("scoop_angle", "")

    # Confidence badge color
    badge_colors = {
        "high": "#00cc66",
        "medium": "#f0ad4e",
        "low": "#ff6b6b",
    }
    badge_color = badge_colors.get(confidence, "#9ca3af")

    with st.container(border=True):
        # Header row: title + badge
        col_title, col_badge = st.columns([6, 1])
        with col_title:
            st.markdown(f"**{title}**")
        with col_badge:
            st.markdown(
                f"<span style='background:{badge_color}22; color:{badge_color}; "
                f"padding:2px 8px; border-radius:4px; font-size:0.75rem; "
                f"font-weight:600;'>{confidence.upper()}</span>",
                unsafe_allow_html=True,
            )

        # Topics as small tags
        if topics:
            tags = " ".join(
                f"<span style='background:#00ff8822; color:#00ff88; "
                f"padding:1px 6px; border-radius:3px; font-size:0.7rem; "
                f"margin-right:4px;'>{t}</span>"
                for t in topics
            )
            if is_sensitive:
                tags += (
                    "<span style='background:#ff880022; color:#ff8800; "
                    "padding:1px 6px; border-radius:3px; font-size:0.7rem; "
                    "margin-right:4px;'>⚠ Multi-perspective</span>"
                )
            st.markdown(f"<div style='margin:4px 0;'>{tags}</div>", unsafe_allow_html=True)

        # Date and neighborhoods
        info_parts = []
        if created_at:
            try:
                dt = created_at[:10]
                info_parts.append(f"📅 {dt}")
            except Exception:
                pass
        if neighborhoods:
            info_parts.append(f"📍 {neighborhoods[:80]}{'…' if len(neighborhoods) > 80 else ''}")
        if info_parts:
            st.markdown(
                f"<div style='font-size:0.75rem; color:#9ca3af; margin:2px 0 6px;'>"
                f"{' &nbsp;·&nbsp; '.join(info_parts)}</div>",
                unsafe_allow_html=True,
            )

        # Expandable content
        with st.expander("View analysis", expanded=False):
            if mechanism:
                st.markdown(f"**How the connection works**\n\n{mechanism}")
            st.markdown(f"**Full analysis**\n\n{body}")
            if scoop:
                st.markdown(
                    f"<div style='font-size:0.8rem; color:#00aaff; "
                    f"border-left:2px solid #00aaff44; padding-left:8px; "
                    f"margin-top:8px;'><strong>Scoop angle:</strong> {scoop}</div>",
                    unsafe_allow_html=True,
                )

        # Go Deeper button
        if on_deep_dive:
            st.button(
                "🔍 Go Deeper",
                key=f"archive_deep_{conn['id']}",
                on_click=on_deep_dive,
                args=(card_id,),
            )


def render_archive_page(on_deep_dive: Callable[[str], None] | None = None) -> None:
    """Render the archive page with filters and paginated results.

    Args:
        on_deep_dive: Callback for "Go Deeper" button clicks.
    """
    locale = st.session_state.get("locale", "san-diego-ca")

    # ── Filter Bar ────────────────────────────────────────────
    with st.container(border=True):
        filt_col1, filt_col2, filt_col3 = st.columns([3, 2, 2])

        with filt_col1:
            kw = st.text_input(
                "🔍 Search",
                placeholder="Search titles and analysis...",
                key="archive_keyword",
                label_visibility="collapsed",
            )

        with filt_col2:
            conf = st.selectbox(
                "Confidence",
                options=CONFIDENCE_OPTIONS,
                key="archive_confidence",
                label_visibility="collapsed",
            )

        with filt_col3:
            selected_topics = st.multiselect(
                "Topics",
                options=TOPIC_CATEGORIES,
                default=[],
                key="archive_topics",
                placeholder="All topics",
                label_visibility="collapsed",
            )

    # ── Results ───────────────────────────────────────────────
    page_size = 20
    page = st.session_state.get("archive_page", 0)

    results, total = _get_archive_data(
        locale=locale,
        keyword=kw,
        selected_topics=selected_topics,
        selected_confidence=conf,
        limit=page_size,
        offset=page * page_size,
    )

    if not results:
        st.info("No past connection cards found matching your filters.")
        return

    # Result count + page info
    st.markdown(
        f"<div style='font-size:0.85rem; color:#9ca3af; margin-bottom:8px;'>"
        f"<strong>{total}</strong> connection{'s' if total != 1 else ''} found"
        f"{' (showing {}-{})'.format(page * page_size + 1, min((page + 1) * page_size, total)) if total > page_size else ''}"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Render cards
    for conn in results:
        _render_archive_card(conn, on_deep_dive or (lambda _: None))

    # ── Pagination ────────────────────────────────────────────
    if total > page_size:
        col_prev, col_info, col_next = st.columns([1, 3, 1])
        with col_prev:
            if page > 0:
                if st.button("← Previous", use_container_width=True, key="archive_prev"):
                    st.session_state["archive_page"] = page - 1
                    st.rerun()
        with col_info:
            total_pages = (total + page_size - 1) // page_size
            st.markdown(
                f"<div style='text-align:center; color:#9ca3af; font-size:0.85rem; "
                f"padding-top:6px;'>Page {page + 1} of {total_pages}</div>",
                unsafe_allow_html=True,
            )
        with col_next:
            if (page + 1) * page_size < total:
                if st.button("Next →", use_container_width=True, key="archive_next"):
                    st.session_state["archive_page"] = page + 1
                    st.rerun()
