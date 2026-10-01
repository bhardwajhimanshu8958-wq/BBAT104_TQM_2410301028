"""
features/theme.py — Dark mode toggle and custom colour-theme management.

Applies a chosen palette as CSS variables injected via st.markdown.
Persists user preferences in the `settings` database table.
Includes live color preview swatches in the sidebar and coordinates chart palettes.
"""

import streamlit as st
from database.db import query_db, execute_db
from config import THEME_PALETTES, DEFAULT_PALETTE, DEFAULT_DARK_MODE, PALETTE_NAMES


# ─── Persistence helpers ─────────────────────────────────────────────────────

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


# ─── CSS injection ───────────────────────────────────────────────────────────

def _build_css(palette: dict, dark: bool) -> str:
    """Generate CSS variable overrides for the selected palette and mode."""
    if dark:
        bg      = palette["bg"]
        surface = palette["surface"]
        text    = palette["text"]
    else:
        bg      = "#f5f7fa"
        surface = "#ffffff"
        text    = "#1a1a2e"

    primary = palette["primary"]

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
    .dataframe thead tr th {{
        background-color: var(--primary) !important;
        color: #ffffff !important;
    }}
    </style>
    """


def apply_theme() -> None:
    """Read saved theme settings and inject CSS. Call once at app startup."""
    dark = _get_setting("dark_mode", str(DEFAULT_DARK_MODE)).lower() == "true"
    palette_name = _get_setting("palette", DEFAULT_PALETTE)
    palette = THEME_PALETTES.get(palette_name, THEME_PALETTES[DEFAULT_PALETTE])
    st.markdown(_build_css(palette, dark), unsafe_allow_html=True)


# ─── Sidebar controls ────────────────────────────────────────────────────────

def render_theme_sidebar() -> None:
    """Render dark mode toggle and palette selector with live swatches in the sidebar."""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎨 Appearance & Themes")

    # Dark mode toggle
    current_dark = _get_setting("dark_mode", str(DEFAULT_DARK_MODE)).lower() == "true"
    new_dark = st.sidebar.toggle("🌙 Dark Mode", value=current_dark)
    if new_dark != current_dark:
        _set_setting("dark_mode", str(new_dark).lower())
        st.rerun()

    # Palette selector (5 palettes: Ocean, Forest, Sunset, Royal, Slate)
    current_palette = _get_setting("palette", DEFAULT_PALETTE)
    new_palette = st.sidebar.selectbox(
        "🖌️ Colour Theme Palette",
        options=PALETTE_NAMES,
        index=PALETTE_NAMES.index(current_palette) if current_palette in PALETTE_NAMES else 0,
    )
    if new_palette != current_palette:
        _set_setting("palette", new_palette)
        st.rerun()

    # Live swatch preview
    p = THEME_PALETTES[new_palette]
    st.sidebar.markdown(
        f"""
        <div style="display:flex;gap:6px;margin-top:6px;align-items:center;">
          <span style="font-size:0.8rem;color:var(--text);margin-right:4px;">Swatch:</span>
          <div style="width:20px;height:20px;border-radius:4px;background:{p['bg']};border:1px solid #777;" title="Background: {p['bg']}"></div>
          <div style="width:20px;height:20px;border-radius:4px;background:{p['surface']};border:1px solid #777;" title="Surface: {p['surface']}"></div>
          <div style="width:20px;height:20px;border-radius:4px;background:{p['primary']};border:1px solid #777;" title="Primary: {p['primary']}"></div>
          <div style="width:20px;height:20px;border-radius:4px;background:{p['text']};border:1px solid #777;" title="Text: {p['text']}"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_chart_color() -> str:
    """Return the current palette's chart colour for matplotlib/seaborn plots."""
    palette_name = _get_setting("palette", DEFAULT_PALETTE)
    palette = THEME_PALETTES.get(palette_name, THEME_PALETTES[DEFAULT_PALETTE])
    return palette["chart"]
