"""
features/theme.py — Dark mode toggle and theme management.

Applies dark mode as CSS variables injected via st.markdown.
Persists user preference in the `settings` database table.
"""

import streamlit as st
from database.db import query_db, execute_db
from config import THEME_PALETTES, DEFAULT_PALETTE, DEFAULT_DARK_MODE


def _get_setting(key: str, default: str) -> str:
    """Read a value from the settings table, or return default."""
    rows = query_db("SELECT value FROM settings WHERE key=?", (key,))
    return rows[0]["value"] if rows else default


def _set_setting(key: str, value: str) -> None:
    """Upsert a key-value pair into the settings table."""
    execute_db(
        "INSERT INTO settings (key,value) VALUES (?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def _build_css(dark: bool) -> str:
    """Generate CSS variable overrides for dark or light mode."""
    if dark:
        bg      = "#0d1b2a"
        surface = "#1b2a3b"
        text    = "#e0f4ff"
        primary = "#00b4d8"
    else:
        bg      = "#f5f7fa"
        surface = "#ffffff"
        text    = "#1a1a2e"
        primary = "#0077b6"

    return f"""
    <style>
    :root {{
        --bg:      {bg};
        --surface: {surface};
        --primary: {primary};
        --text:    {text};
    }}
    .stApp {{
        background-color: var(--bg) !important;
        color: var(--text) !important;
    }}
    section[data-testid="stSidebar"] {{
        background-color: var(--surface) !important;
    }}
    .stButton > button {{
        background-color: var(--primary) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 6px !important;
    }}
    .stButton > button:hover {{
        filter: brightness(1.15) !important;
    }}
    div[data-testid="metric-container"] {{
        background-color: var(--surface) !important;
        border-left: 4px solid var(--primary) !important;
        border-radius: 8px !important;
        padding: 12px !important;
    }}
    </style>
    """


def apply_theme() -> None:
    """Read saved dark mode setting and inject CSS."""
    dark = _get_setting("dark_mode", str(DEFAULT_DARK_MODE)).lower() == "true"
    st.markdown(_build_css(dark), unsafe_allow_html=True)


def render_theme_sidebar() -> None:
    """Render dark mode toggle control in the sidebar."""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎨 Appearance")

    current_dark = _get_setting("dark_mode", str(DEFAULT_DARK_MODE)).lower() == "true"
    new_dark = st.sidebar.toggle("🌙 Dark Mode", value=current_dark)
    if new_dark != current_dark:
        _set_setting("dark_mode", str(new_dark).lower())
        st.rerun()


def get_chart_color() -> str:
    """Return default chart primary colour."""
    return "#00b4d8"
