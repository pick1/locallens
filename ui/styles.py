"""
Application-wide CSS styles for LocalLens Streamlit UI.

Defines a clean, modern design system with:
- Dark header bar
- Card-style connection cards
- Consistent spacing and typography
- Mobile-friendly layout
"""

from __future__ import annotations

import streamlit as st

STYLES = """
<style>
    /* ── Global ─────────────────────────────────────────── */
    .main .block-container {
        max-width: 900px;
        padding-top: 1rem;
        padding-bottom: 2rem;
    }

    /* ── Header ─────────────────────────────────────────── */
    .locallens-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        color: white;
        padding: 1.2rem 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .locallens-header h1 {
        margin: 0;
        font-size: 1.5rem;
        font-weight: 700;
        color: white;
    }
    .locallens-header span {
        font-size: 0.85rem;
        opacity: 0.8;
    }

    /* ── Card styling for st.container block ────────────── */
    .card-wrapper {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        transition: box-shadow 0.2s ease;
    }
    .card-wrapper:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .card-mechanism {
        font-size: 0.9rem;
        color: #374151;
        line-height: 1.5;
        margin: 0.5rem 0 0.75rem 0;
    }

    /* ── Confidence Badge ───────────────────────────────── */
    .badge {
        display: inline-block;
        font-size: 0.7rem;
        font-weight: 600;
        padding: 0.15rem 0.5rem;
        border-radius: 999px;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        margin-right: 0.4rem;
    }
    .badge-high { background: #d1fae5; color: #065f46; }
    .badge-medium { background: #fef3c7; color: #92400e; }
    .badge-low { background: #fee2e2; color: #991b1b; }
    .badge-sensitive { background: #ede9fe; color: #5b21b6; }
    .badge-scoop { background: #dbeafe; color: #1e40af; }

    /* ── Neighborhoods Tag ───────────────────────────────── */
    .neighborhoods-tag {
        font-size: 0.8rem;
        color: #4b5563;
        margin-bottom: 0.5rem;
        padding: 0.2rem 0;
    }

    /* ── Scoop Angle Box (expanded) ──────────────────────── */
    .scoop-angle-box {
        background: #f0f5ff;
        border-left: 3px solid #3b82f6;
        border-radius: 4px;
        padding: 0.6rem 0.8rem;
        margin: 0.75rem 0;
        font-size: 0.85rem;
        color: #1e3a8a;
        line-height: 1.5;
    }

    /* ── Topic Tags ─────────────────────────────────────── */
    .topic-tag {
        display: inline-block;
        font-size: 0.7rem;
        padding: 0.15rem 0.5rem;
        border-radius: 6px;
        background: #f3f4f6;
        color: #374151;
        margin-right: 0.3rem;
        margin-bottom: 0.3rem;
    }

    /* ── Disclaimer ─────────────────────────────────────── */
    .disclaimer {
        font-size: 0.75rem;
        color: #9ca3af;
        font-style: italic;
        padding: 0.5rem;
        border-top: 1px solid #f3f4f6;
        margin-top: 1rem;
    }

    /* ── Empty State ────────────────────────────────────── */
    .empty-state {
        text-align: center;
        padding: 3rem 1rem;
        color: #9ca3af;
    }
    .empty-state h3 {
        color: #6b7280;
        margin-bottom: 0.5rem;
    }

    /* ── Spinner/loading ────────────────────────────────── */
    .stSpinner > div {
        border-color: #1a1a2e !important;
    }

    /* ── Mobile tweaks ──────────────────────────────────── */
    @media (max-width: 640px) {
        .card-wrapper {
            padding: 0.9rem;
        }
        .locallens-header h1 {
            font-size: 1.2rem;
        }
    }
</style>
"""


def apply_styles() -> None:
    """Inject application CSS into the Streamlit page."""
    st.markdown(STYLES, unsafe_allow_html=True)


def render_header(locale_display: str) -> None:
    """Render the app header bar.

    Args:
        locale_display: Human-readable locale name (e.g. "San Diego, CA").
    """
    st.markdown(
        f"""
        <div class="locallens-header">
            <h1>🔍 LocalLens</h1>
            <span>📍 {locale_display}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
