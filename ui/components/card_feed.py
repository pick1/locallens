"""
Card feed component for LocalLens Streamlit UI.

Renders the ranked feed of connection cards with:
- Sort by recency × relevance
- Topic filtering support
- Empty state when no connections available
- Loading state during async operations
"""

from __future__ import annotations

from typing import Any, Callable

import streamlit as st

from ui.components.connection_card import render_connection_card


def render_card_feed(
    connections: list[dict[str, Any]],
    selected_topics: list[str] | None = None,
    on_deep_dive: Callable[[str], None] | None = None,
    loading: bool = False,
) -> None:
    """Render the connection card feed.

    Args:
        connections: List of connection dicts to display.
        selected_topics: If provided, filter cards to only those topics.
        on_deep_dive: Callback for "Go Deeper" button clicks.
        loading: Whether data is currently being fetched.
    """
    if loading:
        _render_loading()
        return

    # Apply topic filter if active
    if selected_topics:
        filtered = [
            c for c in connections
            if any(t in (c.get("topics", []) or []) for t in selected_topics)
        ]
    else:
        filtered = list(connections)

    if not filtered:
        _render_empty(
            has_filters=bool(selected_topics),
            has_connections=bool(connections),
        )
        return

    # Render each card
    for idx, connection in enumerate(filtered):
        render_connection_card(
            connection,
            key=f"card_{idx}_{connection.get('id', idx)}",
            on_deep_dive=on_deep_dive,
        )


def _render_loading() -> None:
    """Show loading state while connections are being fetched."""
    st.markdown(
        """
        <div class="empty-state">
            <h3>🔍 Scanning for connections...</h3>
            <p>Analyzing global and local news for {locale}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.spinner("")


def _render_empty(has_filters: bool, has_connections: bool) -> None:
    """Show empty state message."""
    if has_filters:
        st.markdown(
            """
            <div class="empty-state">
                <h3>🔍 No matching connections</h3>
                <p>Try selecting different topic filters or switching locales.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    elif not has_connections:
        st.markdown(
            """
            <div class="empty-state">
                <h3>🌐 No connections yet</h3>
                <p>The news ingestion pipeline hasn't run yet for this locale.
                New connections will appear here once articles are analyzed.
                This process runs every 6 hours.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
