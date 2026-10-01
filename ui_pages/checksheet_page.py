"""
ui_pages/checksheet_page.py — Defect Checksheet UI (TQM Tool 1).

Allows operators to log defects, inspect defect logs, and update status.
"""

import streamlit as st
from database.db import query_db, execute_db
from datetime import datetime


def render_checksheet_page():
    """Render the defect checksheet and logging interface."""
    st.title("📋 TQM Defect Checksheet")
    st.caption("Structured defect data collection for quality control and root cause analysis.")

    tab1, tab2 = st.tabs(["📊 Defect Log", "➕ Log New Defect"])

    with tab1:
        st.subheader("Logged Defects Register")
        defects = query_db("SELECT * FROM defects ORDER BY defect_id DESC")
        if defects:
            st.dataframe(
                defects,
                column_config={
                    "defect_id": "ID",
                    "date_found": "Date",
                    "module": "Module",
                    "description": "Description",
                    "fishbone_category": "Ishikawa Category",
                    "defect_type": "Defect Type",
                    "severity": "Severity (1-10)",
                    "status": "Status",
                    "resolution": "Resolution Notes",
                    "is_demo": "Demo Data",
                },
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("No defects logged yet.")

    with tab2:
        st.subheader("Report Quality Observation")
        with st.form("new_defect_form", clear_on_submit=True):
            d_module = st.selectbox("Affected Module", ["Entry", "Exit", "Slots", "Vehicles", "Billing", "UI"])
            d_cat = st.selectbox("Fishbone Category", ["People", "Process", "Software Code", "Infrastructure"])
            d_type = st.selectbox("Defect Classification", [
                "Long Queue (> 30s)",
                "Slot Allocation Mismatch",
                "Incorrect Tariff Calculation",
                "UI Render Glitch",
                "Validation Error Ignored",
                "Barcode / Plate Scanner Failure",
                "Hardware Gate Delay",
            ])
            d_desc = st.text_area("Detailed Description of Defect / Anomaly").strip()
            d_sev = st.slider("Severity Rating (1 = Minor, 10 = Critical / System Down)", 1, 10, 5)
            submitted = st.form_submit_button("Submit Defect to Checksheet", use_container_width=True)

            if submitted:
                if not d_desc:
                    st.error("Please provide a description.")
                else:
                    today = datetime.now().strftime("%Y-%m-%d")
                    execute_db(
                        """INSERT INTO defects (date_found, module, description, fishbone_category, defect_type, severity, status, is_demo)
                           VALUES (?,?,?,?,?,?,'Open',0)""",
                        (today, d_module, d_desc, d_cat, d_type, d_sev),
                    )
                    st.success("Defect recorded in Checksheet!")
                    st.rerun()


if __name__ == "__main__" or True:
    render_checksheet_page()
