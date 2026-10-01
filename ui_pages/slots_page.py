"""
ui_pages/slots_page.py — Parking slot inventory management (CRUD).

Enforces slot business constraints, allows filtering by zone and status,
and displays slot allocations in real time.
"""

import streamlit as st
from modules.slots import (
    get_all_slots,
    get_utilization,
    create_slot,
    update_slot,
    delete_slot,
    set_slot_status,
)
from config import SLOT_TYPES, SLOT_STATUSES, ZONES


def render_slots_page():
    """Render slot management view, creation form, and status updates."""
    st.title("🅿️ Parking Slot Management")
    st.caption("Inventory, allocation control, and status tracking for all bays.")

    util = get_utilization()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Bays", util["total"])
    c2.metric("Available", util["available"])
    c3.metric("Occupied", util["occupied"])
    c4.metric("Maintenance", util["maintenance"])

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📋 View & Filter Slots", "➕ Add New Slot", "⚙️ Slot Actions"])

    with tab1:
        st.subheader("Current Slot Inventory")
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            zone_filter = st.selectbox("Filter by Zone", ["All"] + ZONES, index=0)
        with f_col2:
            type_filter = st.selectbox("Filter by Type", ["All"] + SLOT_TYPES, index=0)
        with f_col3:
            status_filter = st.selectbox("Filter by Status", ["All"] + SLOT_STATUSES, index=0)

        zf = None if zone_filter == "All" else zone_filter
        tf = None if type_filter == "All" else type_filter
        sf = None if status_filter == "All" else status_filter

        slots = get_all_slots(zone=zf, slot_type=tf, status=sf)
        st.write(f"Showing **{len(slots)}** slots matching criteria.")

        if slots:
            st.dataframe(
                slots,
                column_config={
                    "slot_id": "ID",
                    "slot_code": "Slot Code",
                    "zone": "Zone",
                    "slot_type": "Vehicle Type",
                    "status": "Current Status",
                },
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("No slots found matching the selected filters.")

    with tab2:
        st.subheader("Register a New Parking Bay")
        with st.form("add_slot_form", clear_on_submit=True):
            s_code = st.text_input("Slot Code (e.g., A-101, B-201)").strip().upper()
            s_zone = st.selectbox("Zone", ZONES)
            s_type = st.selectbox("Slot Classification", SLOT_TYPES)
            s_status = st.selectbox("Initial Status", SLOT_STATUSES, index=0)
            submitted = st.form_submit_button("Add Slot", use_container_width=True)

            if submitted:
                if not s_code:
                    st.error("Slot code cannot be empty.")
                else:
                    try:
                        new_id = create_slot(s_code, s_zone, s_type, s_status)
                        st.success(f"Slot **{s_code}** created successfully (ID #{new_id})!")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Error creating slot: {e}")

    with tab3:
        st.subheader("Update Slot Status / Maintenance")
        all_s = get_all_slots()
        slot_map = {f"{s['slot_code']} ({s['zone']} - {s['slot_type']}) [{s['status']}]": s for s in all_s}
        selected_slot_label = st.selectbox("Select Slot", list(slot_map.keys()) if slot_map else ["None"])

        if slot_map and selected_slot_label != "None":
            target = slot_map[selected_slot_label]
            col_u1, col_u2 = st.columns(2)

            with col_u1:
                st.write(f"**Selected Slot**: `{target['slot_code']}` | **Current Status**: `{target['status']}`")
                new_st = st.selectbox("Set Status", SLOT_STATUSES, index=SLOT_STATUSES.index(target["status"]))
                if st.button("Update Status"):
                    if target["status"] == "Occupied" and new_st != "Occupied":
                        st.warning("Slot is currently Occupied by an active session. Exit vehicle first.")
                    else:
                        set_slot_status(target["slot_id"], new_st)
                        st.success(f"Slot {target['slot_code']} status updated to {new_st}!")
                        st.rerun()

            with col_u2:
                st.write("**Danger Zone**")
                if st.button("🗑️ Delete Slot", type="secondary"):
                    try:
                        delete_slot(target["slot_id"])
                        st.success(f"Slot {target['slot_code']} deleted successfully!")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Cannot delete slot: {e}")


if __name__ == "__main__" or True:
    render_slots_page()
