"""
Sidebar component for LocalLens Streamlit UI.

Contains:
- Locale switcher (dropdown)
- Topic filter (multi-select checkboxes)
- About section
- Connection refresh button
"""

from __future__ import annotations

from typing import Callable

import streamlit as st

from config import settings

TOPIC_CATEGORIES = [
    "Economy",
    "Environment",
    "Community & Demographics",
    "Public Health",
    "Policy",
    "Infrastructure",
]

VIEW_OPTIONS = ["📰 Feed", "🗂️ Archive"]


def render_sidebar(
    current_locale: str,
    on_locale_change: Callable[[str], None] | None = None,
    on_refresh: Callable[[], None] | None = None,
) -> list[str]:
    """Render the sidebar with navigation, locale switcher, and topic filters.

    Args:
        current_locale: Currently selected locale slug.
        on_locale_change: Callback when locale is switched.
        on_refresh: Callback for the refresh button.

    Returns:
        List of selected topic filter strings (empty = all topics).
    """
    with st.sidebar:
        st.markdown("## 🔍 LocalLens")
        st.markdown("Connecting global stories to local impact.")
        st.divider()

        # ── Navigation: Feed / Archive ────────────────────────
        st.markdown("### 📑 View")
        current_view = st.session_state.get("_current_view", "feed")
        new_view = st.radio(
            "Select view",
            options=VIEW_OPTIONS,
            index=0 if current_view == "feed" else 1,
            key="nav_view",
            label_visibility="collapsed",
            horizontal=True,
        )
        selected_view = "archive" if "Archive" in new_view else "feed"
        if selected_view != current_view:
            st.session_state["_current_view"] = selected_view
            st.rerun()

        st.divider()

        # ── Locale Switcher ──────────────────────────────────
        st.markdown("### 📍 Location")

        # Build locale options as (slug, display name) pairs
        locale_options = dict(settings.supported_locales)

        selected_display = locale_options.get(
            current_locale, "San Diego, CA"
        )

        new_display = st.selectbox(
            "Select a city/region",
            options=list(locale_options.values()),
            index=list(locale_options.keys()).index(current_locale)
            if current_locale in locale_options
            else 0,
            key="locale_selector",
        )

        # Convert display name back to slug
        new_locale = current_locale
        for slug, display in locale_options.items():
            if display == new_display:
                new_locale = slug
                break

        if new_locale != current_locale and on_locale_change:
            on_locale_change(new_locale)

        st.divider()

        # ── Topic Filters + Refresh (Feed view only) ──────────
        selected_topics = []
        if selected_view == "feed":
            st.markdown("### 🏷️ Topics")

            for topic in TOPIC_CATEGORIES:
                if st.checkbox(topic, value=True, key=f"topic_{topic}"):
                    selected_topics.append(topic)

            # "Select All / None" helpers
            col1, col2 = st.columns(2)
            with col1:
                if st.button("All", use_container_width=True, key="topic_all"):
                    _set_all_topics(True)
                    st.rerun()
            with col2:
                if st.button("None", use_container_width=True, key="topic_none"):
                    _set_all_topics(False)
                    st.rerun()

            st.divider()

            # ── Refresh ────────────────────────────────────────
            st.markdown("### 🔄 Refresh")
            if st.button(
                "🔄 Refresh Connections",
                use_container_width=True,
                type="primary",
            ):
                if on_refresh:
                    on_refresh()

            # Show last refresh time
            last_refresh = st.session_state.get("last_refresh_time")
            if last_refresh:
                st.caption(f"Last updated: {last_refresh}")

        st.divider()

        # ── About ────────────────────────────────────────────
        st.markdown("### ℹ️ About")
        st.markdown(
            """
            **LocalLens** connects global and national news to their
            impact on local communities.

            Powered by AI analysis of news sources. Every connection card
            is AI-synthesized and linked to its source articles.

            *No user accounts. No tracking. No PII stored.*
            """
        )

        # Cache indicator
        cached_count = st.session_state.get("_cached_pairs_count", 0)
        if cached_count > 0:
            st.caption(f"{cached_count} cached article pairs analyzed")

    return selected_topics


def _set_all_topics(value: bool) -> None:
    """Set all topic checkboxes to the same value."""
    for topic in TOPIC_CATEGORIES:
        st.session_state[f"topic_{topic}"] = value
