"""
ui_pages/entry_exit_page.py — Vehicle entry and exit operations.

Implements the primary operational flow of the parking system:
- Vehicle Entry: auto-suggests best slot to minimize queue time (CTQ 1).
- Vehicle Exit: calculates fee with grace periods and frees the slot (CTQ 2 & 3).
"""

from datetime import datetime
import streamlit as st
from modules.slots import get_available_slot, get_all_slots
from modules.vehicles import get_all_vehicles, get_vehicle_by_plate, create_vehicle
from modules.sessions import (
    record_entry,
    record_exit,
    get_active_sessions,
    get_active_session_for_vehicle,
)
from modules.billing import calculate_duration_minutes, calculate_fee, get_tariff
from modules.validation import validate_plate, validate_phone, validate_non_empty
from config import VEHICLE_TYPES


def render_entry_exit_page():
    """Render the operational entry and exit management tabs."""
    st.title("🚗 Vehicle Entry & Exit Operations")
    st.caption("Real-time check-in, automated bay allocation, and checkout billing.")

    tab_entry, tab_exit, tab_active = st.tabs(["🟢 Vehicle Entry (Check-In)", "🔴 Vehicle Exit & Billing", "📋 Active Sessions"])

    # ── TAB 1: VEHICLE ENTRY ───────────────────────────────────────────────────
    with tab_entry:
        st.subheader("Process Vehicle Entry")
        st.info("💡 **CTQ Feature**: System automatically identifies vehicle type and recommends the closest available bay to minimize queue time.")

        entry_mode = st.radio("Entry Method", ["Select Registered Vehicle", "Quick-Register & Check-In"], horizontal=True)

        if entry_mode == "Select Registered Vehicle":
            vehicles = get_all_vehicles()
            if not vehicles:
                st.warning("No vehicles registered yet. Switch to Quick-Register.")
            else:
                v_options = {f"{v['plate_no']} ({v['vehicle_type']}) — {v['owner_name']}": v for v in vehicles}
                selected_v_label = st.selectbox("Select Vehicle", list(v_options.keys()))
                v = v_options[selected_v_label]

                # Check if already active
                existing = get_active_session_for_vehicle(v["vehicle_id"])
                if existing:
                    st.error(f"⚠️ Poka-Yoke Alert: Vehicle {v['plate_no']} is already parked in Slot `{existing['slot_code']}` since {existing['entry_time']}.")
                else:
                    # Auto-suggest slot
                    suggested = get_available_slot(v["vehicle_type"])
                    if not suggested:
                        st.error(f"❌ No available bays for vehicle type '{v['vehicle_type']}'. Parking full!")
                    else:
                        st.success(f"🎯 **Recommended Bay**: Slot `{suggested['slot_code']}` (Zone {suggested['zone']}, {suggested['slot_type']})")

                        # Option to override slot
                        avail_slots = get_all_slots(status="Available")
                        slot_choices = {f"{s['slot_code']} ({s['zone']} - {s['slot_type']})": s for s in avail_slots}
                        default_idx = list(slot_choices.keys()).index(f"{suggested['slot_code']} ({suggested['zone']} - {suggested['slot_type']})") if f"{suggested['slot_code']} ({suggested['zone']} - {suggested['slot_type']})" in slot_choices else 0

                        chosen_slot_label = st.selectbox("Assigned Slot Bay", list(slot_choices.keys()), index=default_idx)
                        chosen_slot = slot_choices[chosen_slot_label]

                        if st.button("Confirm Check-In & Issue Entry Slip", type="primary", use_container_width=True):
                            try:
                                sess_id = record_entry(v["vehicle_id"], chosen_slot["slot_id"])
                                st.balloons()
                                st.success(f"✅ Vehicle **{v['plate_no']}** entered successfully! Session ID: #{sess_id}")
                                st.markdown(
                                    f"""
                                    <div style="border: 2px dashed #4CAF50; border-radius: 8px; padding: 15px; margin: 10px 0; background: rgba(76, 175, 80, 0.05);">
                                        <h4 style="margin:0 0 10px 0; color:#4CAF50;">🎟️ ENTRY PASS #{sess_id}</h4>
                                        <p><b>Vehicle Plate:</b> {v['plate_no']} ({v['vehicle_type']})<br>
                                        <b>Owner:</b> {v['owner_name']} | {v['phone']}<br>
                                        <b>Allocated Slot:</b> {chosen_slot['slot_code']} (Zone {chosen_slot['zone']})<br>
                                        <b>Entry Timestamp:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )
                            except ValueError as e:
                                st.error(str(e))

        else:
            # Quick register & check-in
            st.markdown("##### Quick Vehicle Registration + Immediate Entry")
            with st.form("quick_entry_form"):
                q_plate = st.text_input("License Plate (e.g. UK07AB1234)").strip().upper()
                q_owner = st.text_input("Owner Name").strip()
                q_phone = st.text_input("Mobile Phone (10 digits)").strip()
                q_type = st.selectbox("Vehicle Classification", VEHICLE_TYPES)
                submit_quick = st.form_submit_button("Register & Check In", use_container_width=True)

                if submit_quick:
                    ok_p, msg_p = validate_plate(q_plate)
                    ok_o, msg_o = validate_non_empty(q_owner, "Owner Name")
                    ok_ph, msg_ph = validate_phone(q_phone)

                    if not ok_p:
                        st.error(msg_p)
                    elif not ok_o:
                        st.error(msg_o)
                    elif not ok_ph:
                        st.error(msg_ph)
                    else:
                        try:
                            # Auto find slot first
                            suggested = get_available_slot(q_type)
                            if not suggested:
                                st.error(f"❌ Parking full for {q_type}! Cannot admit vehicle.")
                            else:
                                v_rec = get_vehicle_by_plate(q_plate)
                                if not v_rec:
                                    v_id = create_vehicle(q_plate, q_owner, q_phone, q_type)
                                else:
                                    v_id = v_rec["vehicle_id"]
                                sess_id = record_entry(v_id, suggested["slot_id"])
                                st.success(f"✅ Vehicle **{q_plate}** admitted to Slot **{suggested['slot_code']}** (Session #{sess_id})!")
                                st.rerun()
                        except ValueError as e:
                            st.error(str(e))

    # ── TAB 2: VEHICLE EXIT & BILLING ──────────────────────────────────────────
    with tab_exit:
        st.subheader("Process Vehicle Exit & Collect Tariff")
        actives = get_active_sessions()

        if not actives:
            st.info("No active parking sessions at this time. All vehicles have exited.")
        else:
            act_options = {
                f"Session #{s['session_id']} | Plate: {s['plate_no']} | Slot: {s['slot_code']} | Entry: {s['entry_time']}": s
                for s in actives
            }
            selected_act_label = st.selectbox("Select Active Session to Checkout", list(act_options.keys()))
            target_sess = act_options[selected_act_label]

            # Current time and live calculation
            now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            duration_mins = calculate_duration_minutes(target_sess["entry_time"], now_time)
            tariff = get_tariff(target_sess["vehicle_type"])
            fee = calculate_fee(target_sess["vehicle_type"], duration_mins)

            st.markdown("---")
            st.markdown("#### 🧾 Billing Statement Preview")

            b1, b2, b3, b4 = st.columns(4)
            b1.metric("Parked Duration", f"{int(duration_mins)} mins", f"{round(duration_mins/60, 1)} hrs")
            b2.metric("Free Allowance", f"{tariff['free_minutes']} mins")
            b3.metric("Tariff Rate", f"₹{tariff['base_rate']} + ₹{tariff['per_hour_rate']}/hr")
            b4.metric("Total Payable", f"₹{fee:.2f}")

            st.write(
                f"• **Vehicle**: `{target_sess['plate_no']}` ({target_sess['vehicle_type']}) | "
                f"• **Owner**: {target_sess['owner_name']} | "
                f"• **Slot**: `{target_sess['slot_code']}` (Zone {target_sess['zone']})"
            )

            if st.button("💳 Confirm Payment & Complete Exit", type="primary", use_container_width=True):
                try:
                    res = record_exit(target_sess["session_id"], target_sess["vehicle_type"])
                    st.balloons()
                    st.success(f"✅ Exit processed for Session #{target_sess['session_id']}! Slot {target_sess['slot_code']} is now Available.")
                    st.markdown(
                        f"""
                        <div style="border: 2px solid #2196F3; border-radius: 8px; padding: 15px; margin: 10px 0; background: rgba(33, 150, 243, 0.05);">
                            <h4 style="margin:0 0 10px 0; color:#2196F3;">🧾 OFFICIAL PARKING RECEIPT</h4>
                            <p><b>Receipt ID:</b> REC-{target_sess['session_id']}-{datetime.now().strftime('%M%S')}<br>
                            <b>Vehicle:</b> {target_sess['plate_no']} ({target_sess['vehicle_type']})<br>
                            <b>Check-In:</b> {target_sess['entry_time']}<br>
                            <b>Check-Out:</b> {res['exit_time']}<br>
                            <b>Total Duration:</b> {res['duration_minutes']} minutes<br>
                            <h3 style="color:#2196F3; margin: 8px 0 0 0;">Total Amount Paid: ₹{res['fee']:.2f}</h3>
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                except ValueError as e:
                    st.error(str(e))

    # ── TAB 3: ACTIVE SESSIONS MONITOR ─────────────────────────────────────────
    with tab_active:
        st.subheader("Live Parked Vehicles Monitor")
        current_actives = get_active_sessions()
        st.write(f"Currently **{len(current_actives)}** vehicles actively parked in the facility.")

        if current_actives:
            st.dataframe(
                current_actives,
                column_config={
                    "session_id": "ID",
                    "plate_no": "Plate Number",
                    "owner_name": "Driver Name",
                    "vehicle_type": "Type",
                    "slot_code": "Bay Code",
                    "zone": "Zone",
                    "entry_time": "Entry Time",
                    "status": "Session Status",
                },
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("No vehicles currently in the parking lot.")


if __name__ == "__main__" or True:
    render_entry_exit_page()
