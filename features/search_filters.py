"""
features/search_filters.py — Search and filter UI for vehicles and sessions (Q03-4).

Provides:
- render_vehicle_search(): filterable vehicle table.
- render_session_search(): filterable session table with date range.

Why search filters? A CTQ target is "filter response < 2 seconds on 1,000 records".
All filtering is pushed to SQLite (server-side) rather than loading all rows
into memory first.
"""

import streamlit as st
import pandas as pd
from modules.sessions import get_all_sessions
from modules.vehicles import get_all_vehicles
from config import VEHICLE_TYPES, SESSION_STATUSES


def render_vehicle_search() -> None:
    """Render the vehicle search panel with live-filter controls."""
    st.subheader("🔍 Search Vehicles")

    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        search_text = st.text_input("Search by plate or owner name", key="vsearch_text",
                                    placeholder="e.g. UK07 or Rajesh")
    with col2:
        vtype_filter = st.selectbox("Vehicle Type", ["All"] + VEHICLE_TYPES,
                                    key="vsearch_type")
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✖ Clear", key="vsearch_clear"):
            st.session_state.vsearch_text = ""
            st.session_state.vsearch_type = "All"
            st.rerun()

    vtype = vtype_filter if vtype_filter != "All" else None
    rows  = get_all_vehicles(vehicle_type=vtype, search=search_text or None)

    st.caption(f"**{len(rows)} result(s) found**")

    if rows:
        df = pd.DataFrame(rows)
        df = df[["vehicle_id","plate_no","owner_name","phone","vehicle_type","created_at"]]
        df.columns = ["ID","Plate","Owner","Phone","Type","Registered At"]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No vehicles match the current filters.")


def render_session_search() -> None:
    """Render the session search panel with comprehensive filter controls."""
    st.subheader("🔍 Search Sessions")

    row1 = st.columns([2, 2, 2, 2])
    row2 = st.columns([2, 2, 1])

    with row1[0]:
        plate  = st.text_input("Plate Number", key="ss_plate", placeholder="e.g. UK07AB")
    with row1[1]:
        owner  = st.text_input("Owner Name",   key="ss_owner", placeholder="e.g. Rajesh")
    with row1[2]:
        slot   = st.text_input("Slot Code",    key="ss_slot",  placeholder="e.g. A-C-01")
    with row1[3]:
        status = st.selectbox("Status", ["All"] + SESSION_STATUSES, key="ss_status")

    with row2[0]:
        from_date = st.date_input("From Date", value=None, key="ss_from")
    with row2[1]:
        to_date   = st.date_input("To Date",   value=None, key="ss_to")
    with row2[2]:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✖ Clear Filters", key="ss_clear"):
            for k in ["ss_plate","ss_owner","ss_slot","ss_status","ss_from","ss_to"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    rows = get_all_sessions(
        status    = status if status != "All" else None,
        plate     = plate  or None,
        owner     = owner  or None,
        slot_code = slot   or None,
        from_date = str(from_date) if from_date else None,
        to_date   = str(to_date)   if to_date   else None,
    )

    st.caption(f"**{len(rows)} result(s) found**")

    if rows:
        df = pd.DataFrame(rows)
        df = df[["session_id","plate_no","owner_name","vehicle_type",
                 "slot_code","zone","entry_time","exit_time","fee","status"]]
        df.columns = ["ID","Plate","Owner","Type","Slot","Zone","Entry","Exit","Fee (₹)","Status"]
        df["Fee (₹)"] = df["Fee (₹)"].apply(lambda x: f"₹{x:,.2f}" if x else "—")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No sessions match the current filters.")
