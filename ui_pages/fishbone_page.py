"""
ui_pages/fishbone_page.py — Ishikawa Fishbone Diagram UI (TQM Tool 4).

Visualizes root causes categorized into People, Process, Software Code, and Infrastructure.
"""

import streamlit as st
from database.db import query_db


def render_fishbone_page():
    """Render Ishikawa cause-and-effect categories and defect breakdown."""
    st.title("🐟 Ishikawa Fishbone Diagram")
    st.caption("Cause-and-effect root cause taxonomy across People, Process, Software, and Infrastructure.")

    categories = ["People", "Process", "Software Code", "Infrastructure"]
    cols = st.columns(4)

    for idx, cat in enumerate(categories):
        with cols[idx]:
            st.markdown(f"#### 🏷️ {cat}")
            defects = query_db(
                "SELECT defect_type, description FROM defects WHERE fishbone_category = ?",
                (cat,),
            )
            if defects:
                for d in defects:
                    st.markdown(f"- **{d['defect_type']}**: {d['description']}")
            else:
                st.caption("No defects logged in this branch.")

    st.markdown("---")
    st.info("💡 High-resolution vector Fishbone diagrams are generated during Phase 5 using matplotlib.")


if __name__ == "__main__" or True:
    render_fishbone_page()
