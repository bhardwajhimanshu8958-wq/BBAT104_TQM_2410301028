"""
ui_pages/search_page.py — Search & Filtering view (Q03 Usability Feature 4).

Renders vehicle search directory and multi-criterion session search.
"""

import streamlit as st
from features.search_filters import render_vehicle_search, render_session_search


def render_search_page():
    """Render search tabs for vehicle lookup and session logs."""
    st.title("🔍 Search & Filter Records")
    st.caption("Locate parking sessions and vehicles with multi-field filtering.")

    tab1, tab2 = st.tabs(["🚗 Vehicle Directory Search", "🅿️ Parking Sessions Filter"])
    with tab1:
        render_vehicle_search()
    with tab2:
        render_session_search()


if __name__ == "__main__" or True:
    render_search_page()
