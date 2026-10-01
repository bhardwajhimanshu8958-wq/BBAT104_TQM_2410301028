"""
app.py — Main application entry point for the Smart Parking Management System.

Built for BBAT104 Fundamentals of Total Quality Management.
Student: Himanshu Bhardwaj (Roll No. 2410301028, B.Tech CSE Sec A)
Quality Goal: Q03 — Improve Usability (Dark Mode, Custom Themes, Dashboard, Search Filters, Calendar)
"""

import streamlit as st
from database.db import init_db, query_db
from database.seed import (
    seed_tariff,
    seed_slots,
    seed_vehicles,
    seed_settings,
    seed_defects,
)
from tqm.fmea import seed_fmea_if_empty
from tqm.pdca import seed_pdca_if_empty
from features.theme import apply_theme, render_theme_sidebar


def ensure_database():
    """Ensure database tables exist and are seeded on initial launch."""
    init_db()
    slots_count = query_db("SELECT COUNT(*) as c FROM slots")
    if not slots_count or slots_count[0]["c"] == 0:
        seed_tariff()
        seed_slots()
        seed_vehicles()
        seed_settings()
        seed_defects()
    # Seed TQM modules independently (safe to call even if partially seeded)
    seed_fmea_if_empty()
    seed_pdca_if_empty()


# Initialize database schema and initial data
ensure_database()

# Configure page layout and browser metadata
st.set_page_config(
    page_title="TQM Parking System | Q03 Usability",
    page_icon="🅿️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply dynamic CSS variables for dark/light mode and selected palette
apply_theme()

# Sidebar: Theme customizer and student course info
render_theme_sidebar()
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style="font-size: 0.85rem; line-height: 1.4; color: var(--text);">
        <b>BBAT104 TQM Project</b><br>
        👤 <b>Student</b>: Himanshu Bhardwaj<br>
        🆔 <b>Roll No</b>: 2410301028 (Sec A)<br>
        🎯 <b>Goal</b>: Q03 Usability Excellence<br>
        🏛️ <b>System</b>: Parking Management
    </div>
    """,
    unsafe_allow_html=True,
)

# Navigation definition with st.Page and st.navigation (Streamlit >= 1.36)
pages = {
    "Operations": [
        st.Page("ui_pages/home.py", title="Home & Overview", icon="🏠", default=True),
        st.Page("ui_pages/entry_exit_page.py", title="Entry & Exit Operations", icon="🚗"),
        st.Page("ui_pages/slots_page.py", title="Parking Slot Manager", icon="🅿️"),
        st.Page("ui_pages/vehicles_page.py", title="Vehicle Registry", icon="🚙"),
    ],
    "Q03 Usability Suite": [
        st.Page("ui_pages/dashboard_page.py", title="Executive Dashboard", icon="📊"),
        st.Page("ui_pages/search_page.py", title="Search & Filter Records", icon="🔍"),
        st.Page("ui_pages/calendar_page.py", title="Monthly Calendar View", icon="📅"),
        st.Page("ui_pages/reports_page.py", title="Excel Reports & Export", icon="📥"),
    ],
    "TQM Quality Control": [
        st.Page("ui_pages/checksheet_page.py", title="Defect Checksheet", icon="📋"),
        st.Page("ui_pages/fmea_page.py", title="FMEA Risk Audit", icon="⚠️"),
        st.Page("ui_pages/pareto_page.py", title="Pareto 80/20 Analysis", icon="📉"),
        st.Page("ui_pages/fishbone_page.py", title="Ishikawa Fishbone", icon="🐟"),
        st.Page("ui_pages/pdca_page.py", title="PDCA Improvement Cycles", icon="🔄"),
        st.Page("ui_pages/control_chart_page.py", title="SPC Control Chart", icon="📈"),
        st.Page("ui_pages/tqm_report_page.py", title="TQM Summary Report", icon="📄"),
    ],
}

router = st.navigation(pages)
router.run()
