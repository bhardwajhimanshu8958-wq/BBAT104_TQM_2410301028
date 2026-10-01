"""
ui_pages/home.py — Executive home and operational overview page.

Displays student project identification, TQM quality goals (Q03),
live operational metrics, and quick navigation actions.
"""

import streamlit as st
from modules.slots import get_utilization, get_all_slots
from modules.sessions import get_active_sessions, get_recent_activity
from modules.vehicles import get_all_vehicles


def render_home_page():
    """Render the main home page with KPIs, CTQ objectives, and slot layout."""
    st.title("🅿️ Smart Parking Management System")
    st.caption("BBAT104 Fundamentals of Total Quality Management | Academic Session 2026-27")

    # Student & Project banner
    st.info(
        "🎓 **Student**: Himanshu Bhardwaj | **Roll No**: 2410301028 | **Section**: B.Tech CSE Sec A  \n"
        "🎯 **TQM Focus**: Minimize Entry Queue Times & Maximize Space Utilization  \n"
        "⭐ **Assigned Quality Goal**: **Q03: Improve Usability** (Dark Mode, Themes, Dashboard, Search & Calendar)"
    )

    # Operational KPIs
    util = get_utilization()
    active_sessions = get_active_sessions()
    all_vehicles = get_all_vehicles()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Slots", util["total"])
    with c2:
        st.metric("Occupied Bays", util["occupied"], delta=f"{util['utilization_pct']}% Utilized")
    with c3:
        st.metric("Available Bays", util["available"])
    with c4:
        st.metric("Active Sessions", len(active_sessions))

    st.markdown("---")

    # Strategic CTQ Alignment & Operational Status
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("🎯 Critical to Quality (CTQ) Parameters")
        st.markdown(
            """
            - **CTQ 1: Rapid Entry Flow (< 30s)**: Automated slot recommendation matching vehicle type.
            - **CTQ 2: Capacity Optimization (> 80%)**: Real-time zone-wise slot tracking and allocation.
            - **CTQ 3: Zero-Defect Billing**: Transparent tariff calculation with free-tier grace periods.
            - **CTQ 4: Poka-Yoke Mistake Proofing**: Rejection of duplicate entries and malformed plates.
            - **CTQ 5: Usability (Q03)**: Seamless navigation, dark mode, custom palettes, search & calendar.
            """
        )

    with col_right:
        st.subheader("🗺️ Live Zone Occupancy")
        slots = get_all_slots()
        zones = {}
        for s in slots:
            z = s.get("zone", "General")
            zones.setdefault(z, {"total": 0, "occupied": 0, "available": 0, "maintenance": 0})
            zones[z]["total"] += 1
            stt = s.get("status", "Available")
            if stt == "Occupied":
                zones[z]["occupied"] += 1
            elif stt == "Maintenance":
                zones[z]["maintenance"] += 1
            else:
                zones[z]["available"] += 1

        for z, data in sorted(zones.items()):
            pct = round((data["occupied"] / data["total"] * 100), 1) if data["total"] else 0
            st.write(f"**Zone {z}**: {data['occupied']}/{data['total']} Occupied ({pct}%)")
            st.progress(pct / 100.0)

    st.markdown("---")
    st.subheader("🕒 Recent Activity")
    recent = get_recent_activity(5)
    if recent:
        st.dataframe(
            recent,
            column_config={
                "session_id": "ID",
                "plate_no": "Plate",
                "owner_name": "Owner",
                "slot_code": "Slot",
                "entry_time": "Entry Time",
                "exit_time": "Exit Time",
                "fee": st.column_config.NumberColumn("Fee (₹)", format="₹%.2f"),
                "status": "Status",
            },
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.write("No parking activity recorded yet.")


if __name__ == "__main__" or True:
    render_home_page()
