"""
tqm/checksheet.py — Defect Checksheet and Data Collection module (TQM Tool 1).

Provides structured data collection for quality control observations,
defect severity scoring (1-10), and status lifecycle tracking.

Why Checksheet? In TQM, defect logging at the gemba (place of action)
is the prerequisite for all quantitative root cause analysis (Pareto & Fishbone).
"""

from datetime import datetime
import streamlit as st
import pandas as pd
from database.db import query_db, execute_db
from config import FISHBONE_CATEGORIES, DEFECT_STATUSES, DEFECT_SEVERITIES


def log_defect(module: str, description: str, fishbone_category: str,
               defect_type: str, severity: int, is_demo: int = 0) -> int:
    """Insert a new quality defect record into the database."""
    if fishbone_category not in FISHBONE_CATEGORIES:
        raise ValueError(f"Invalid category '{fishbone_category}'. Must be one of {FISHBONE_CATEGORIES}")
    if severity < 1 or severity > 10:
        raise ValueError("Severity must be an integer between 1 and 10.")

    today = datetime.now().strftime("%Y-%m-%d")
    sql = """
        INSERT INTO defects (date_found, module, description, fishbone_category, defect_type, severity, status, is_demo)
        VALUES (?, ?, ?, ?, ?, ?, 'Open', ?)
    """
    return execute_db(sql, (today, module, description.strip(), fishbone_category, defect_type.strip(), severity, is_demo))


def get_all_defects(module: str = None, category: str = None, status: str = None) -> list[dict]:
    """Retrieve defect records with optional filtering."""
    sql = "SELECT * FROM defects WHERE 1=1"
    params = []
    if module:
        sql += " AND module = ?"
        params.append(module)
    if category:
        sql += " AND fishbone_category = ?"
        params.append(category)
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY defect_id DESC"
    return query_db(sql, tuple(params))


def update_defect_status(defect_id: int, new_status: str, resolution: str = "") -> None:
    """Update defect status (Open, In Progress, Resolved) and resolution remarks."""
    if new_status not in DEFECT_STATUSES:
        raise ValueError(f"Invalid status '{new_status}'. Must be one of {DEFECT_STATUSES}")
    execute_db(
        "UPDATE defects SET status = ?, resolution = ? WHERE defect_id = ?",
        (new_status, resolution.strip(), defect_id),
    )


def get_defect_summary() -> dict:
    """Return summary metrics for defect tracking."""
    rows = query_db("SELECT status, COUNT(*) as cnt FROM defects GROUP BY status")
    counts = {r["status"]: r["cnt"] for r in rows}
    total = sum(counts.values())
    return {
        "total": total,
        "open": counts.get("Open", 0),
        "in_progress": counts.get("In Progress", 0),
        "resolved": counts.get("Resolved", 0),
    }


def render_checksheet() -> None:
    """Render the full interactive defect checksheet UI."""
    st.title("📋 TQM Defect Checksheet")
    st.caption("Standardized defect recording for continuous quality improvement (Kaizen).")

    summary = get_defect_summary()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Defect Log", summary["total"])
    c2.metric("Open Anomalies", summary["open"], delta="Action Required" if summary["open"] > 0 else "Clear")
    c3.metric("Under Investigation", summary["in_progress"])
    c4.metric("Resolved / Closed", summary["resolved"])

    st.markdown("---")
    tab_log, tab_new, tab_manage = st.tabs(["📊 Defect Audit Table", "➕ Log Observation", "⚙️ Status Updates"])

    with tab_log:
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            mod_f = st.selectbox("Filter Module", ["All", "Entry", "Exit", "Slots", "Vehicles", "Billing", "UI", "DB"])
        with col_f2:
            cat_f = st.selectbox("Filter Ishikawa Branch", ["All"] + FISHBONE_CATEGORIES)
        with col_f3:
            stat_f = st.selectbox("Filter Status", ["All"] + DEFECT_STATUSES)

        mf = None if mod_f == "All" else mod_f
        cf = None if cat_f == "All" else cat_f
        sf = None if stat_f == "All" else stat_f

        defects = get_all_defects(module=mf, category=cf, status=sf)
        st.caption(f"**{len(defects)}** defect record(s) matching criteria.")

        if defects:
            df = pd.DataFrame(defects)
            st.dataframe(
                df,
                column_config={
                    "defect_id": "ID",
                    "date_found": "Date",
                    "module": "Module",
                    "description": "Observation Description",
                    "fishbone_category": "Category",
                    "defect_type": "Defect Type",
                    "severity": st.column_config.NumberColumn("Severity (1-10)"),
                    "status": "Current Status",
                    "resolution": "Resolution Notes",
                    "is_demo": st.column_config.CheckboxColumn("Demo Data"),
                },
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("No defect records found matching the active filters.")

    with tab_new:
        st.subheader("Log Quality Observation / Defect")
        with st.form("log_defect_form", clear_on_submit=True):
            f_module = st.selectbox("System Module", ["Entry", "Exit", "Slots", "Vehicles", "Billing", "UI", "DB"])
            f_cat = st.selectbox("Ishikawa Fishbone Branch", FISHBONE_CATEGORIES)
            f_type = st.selectbox("Defect Type Classification", [
                "Queue Delay (> 30s)",
                "Slot Allocation Mismatch",
                "Incorrect Tariff Calculation",
                "UI Render Glitch",
                "Validation Error Ignored",
                "Hardware / Barcode Scanner Glitch",
                "Database Timeout",
            ])
            f_desc = st.text_area("Detailed Symptom & Failure Description").strip()
            f_sev = st.slider("Defect Severity Rating (1 = Minor UI anomaly, 10 = Critical System Block)", 1, 10, 5)
            f_demo = st.checkbox("Mark as Demo Record (is_demo = 1)", value=False)

            if st.form_submit_button("Record Defect to Checksheet", use_container_width=True):
                if not f_desc:
                    st.error("Please enter a detailed description of the defect.")
                else:
                    new_id = log_defect(f_module, f_desc, f_cat, f_type, f_sev, is_demo=1 if f_demo else 0)
                    st.success(f"✅ Defect #{new_id} recorded in Checksheet!")
                    st.rerun()

    with tab_manage:
        st.subheader("Update Defect Status & Resolution")
        all_d = get_all_defects()
        if not all_d:
            st.info("No defects available to update.")
        else:
            d_options = {f"#{d['defect_id']} [{d['status']}] {d['module']} - {d['defect_type']}": d for d in all_d}
            selected_d_label = st.selectbox("Select Defect to Update", list(d_options.keys()))
            target_d = d_options[selected_d_label]

            st.write(f"**Description**: {target_d['description']}")
            st.write(f"**Severity**: {target_d['severity']}/10 | **Category**: {target_d['fishbone_category']}")

            new_stat = st.selectbox("Update Status", DEFECT_STATUSES, index=DEFECT_STATUSES.index(target_d["status"]))
            new_res = st.text_area("Resolution / Root Cause Notes", value=target_d["resolution"] or "")

            if st.button("Save Defect Status", type="primary"):
                update_defect_status(target_d["defect_id"], new_stat, new_res)
                st.success(f"Defect #{target_d['defect_id']} updated to {new_stat}!")
                st.rerun()
