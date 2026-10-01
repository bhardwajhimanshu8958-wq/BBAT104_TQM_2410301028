"""
ui_pages/vehicles_page.py — Vehicle Registry management (CRUD).

Allows registration of incoming vehicles, phone/plate verification,
and vehicle profile management.
"""

import streamlit as st
from modules.vehicles import (
    get_all_vehicles,
    create_vehicle,
    update_vehicle,
    delete_vehicle,
    get_vehicle_by_plate,
)
from modules.validation import validate_plate, validate_phone, validate_non_empty
from config import VEHICLE_TYPES


def render_vehicles_page():
    """Render vehicle registration interface, directory search, and records."""
    st.title("🚙 Vehicle Registry")
    st.caption("Registered vehicle database, owner contacts, and vehicle type classifications.")

    tab1, tab2, tab3 = st.tabs(["🔍 Directory & Search", "➕ Register Vehicle", "✏️ Edit / Manage"])

    with tab1:
        st.subheader("Registered Vehicle Records")
        c_search, c_filter = st.columns([2, 1])
        with c_search:
            search_query = st.text_input("Search by Plate Number or Owner Name", placeholder="e.g. UK07 or Sharma")
        with c_filter:
            type_filter = st.selectbox("Vehicle Type Filter", ["All"] + VEHICLE_TYPES)

        tf = None if type_filter == "All" else type_filter
        sq = search_query.strip() if search_query else None

        vehicles = get_all_vehicles(vehicle_type=tf, search=sq)
        st.write(f"Showing **{len(vehicles)}** vehicle(s).")

        if vehicles:
            st.dataframe(
                vehicles,
                column_config={
                    "vehicle_id": "ID",
                    "plate_no": "Plate Number",
                    "owner_name": "Owner Name",
                    "phone": "Phone Number",
                    "vehicle_type": "Classification",
                    "created_at": "Registration Date",
                },
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("No vehicles match the query.")

    with tab2:
        st.subheader("New Vehicle Registration (Poka-Yoke Protected)")
        with st.form("register_vehicle_form", clear_on_submit=True):
            plate = st.text_input("License Plate Number (e.g., UK07AB1234)").strip().upper()
            owner = st.text_input("Owner / Driver Full Name").strip()
            phone = st.text_input("Mobile Phone (10 digits)").strip()
            v_type = st.selectbox("Vehicle Category", VEHICLE_TYPES)

            submitted = st.form_submit_button("Register Vehicle", use_container_width=True)

            if submitted:
                # Poka-Yoke validations
                ok_plate, msg_plate = validate_plate(plate)
                ok_owner, msg_owner = validate_non_empty(owner, "Owner Name")
                ok_phone, msg_phone = validate_phone(phone)

                if not ok_plate:
                    st.error(f"❌ {msg_plate}")
                elif not ok_owner:
                    st.error(f"❌ {msg_owner}")
                elif not ok_phone:
                    st.error(f"❌ {msg_phone}")
                else:
                    try:
                        v_id = create_vehicle(plate, owner, phone, v_type)
                        st.success(f"✅ Vehicle **{plate}** ({v_type}) registered successfully! (ID #{v_id})")
                        st.rerun()
                    except ValueError as e:
                        st.error(f"❌ {e}")
                    except Exception as e:
                        st.error(f"System Error: {e}")

    with tab3:
        st.subheader("Edit or Remove Vehicle")
        vehicles_all = get_all_vehicles()
        v_map = {f"{v['plate_no']} — {v['owner_name']} ({v['vehicle_type']})": v for v in vehicles_all}
        selected_label = st.selectbox("Select Vehicle", list(v_map.keys()) if v_map else ["None"])

        if v_map and selected_label != "None":
            target = v_map[selected_label]
            with st.form("edit_vehicle_form"):
                new_owner = st.text_input("Owner Name", value=target["owner_name"])
                new_phone = st.text_input("Phone Number", value=target["phone"])
                new_type = st.selectbox("Vehicle Type", VEHICLE_TYPES, index=VEHICLE_TYPES.index(target["vehicle_type"]))
                update_btn = st.form_submit_button("Save Changes")

                if update_btn:
                    ok_owner, msg_owner = validate_non_empty(new_owner, "Owner Name")
                    ok_phone, msg_phone = validate_phone(new_phone)
                    if not ok_owner:
                        st.error(msg_owner)
                    elif not ok_phone:
                        st.error(msg_phone)
                    else:
                        update_vehicle(target["vehicle_id"], target["plate_no"], new_owner, new_phone, new_type)
                        st.success(f"Vehicle {target['plate_no']} updated successfully!")
                        st.rerun()

            if st.button("🗑️ Delete Vehicle Record", type="secondary"):
                try:
                    delete_vehicle(target["vehicle_id"])
                    st.success(f"Vehicle {target['plate_no']} removed from system.")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Cannot delete vehicle: {e}")


if __name__ == "__main__" or True:
    render_vehicles_page()
