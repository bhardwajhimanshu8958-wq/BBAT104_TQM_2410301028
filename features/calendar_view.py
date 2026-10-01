"""
features/calendar_view.py — Monthly calendar view of parking activity (Q03-5).

Shows a heat-coloured grid of the current month where each cell's colour
intensity is proportional to that day's revenue.  Clicking a date shows a
detail table of entries/exits for that day.

Why calendar.py + pandas: Python's built-in `calendar` module provides the
month grid structure; pandas aggregates session data by date.  No third-party
calendar widget needed — keeps the stack simple as required.
"""

import calendar
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from modules.sessions import sessions_by_day
from modules.billing import revenue_by_day
from modules.sessions import get_all_sessions


def _hex_blend(intensity: float, color_hex: str) -> str:
    """Return a hex colour blended from transparent to color_hex by intensity (0-1)."""
    r = int(color_hex[1:3], 16)
    g = int(color_hex[3:5], 16)
    b = int(color_hex[5:7], 16)
    # Blend with a dark surface colour (#1b2a3b)
    sr, sg, sb = 27, 42, 59
    br = int(sr + (r - sr) * intensity)
    bg = int(sg + (g - sg) * intensity)
    bb = int(sb + (b - sb) * intensity)
    return f"#{br:02x}{bg:02x}{bb:02x}"


def render_calendar() -> None:
    """Render the monthly calendar view with heat-coloured revenue cells."""
    from features.theme import get_chart_color

    st.title("📅 Calendar View")
    st.caption("Revenue heat-map by day.  Click a date to see its sessions.")

    # ── Month navigation ─────────────────────────────────────────────────────
    today = date.today()
    if "cal_year"  not in st.session_state:
        st.session_state.cal_year  = today.year
    if "cal_month" not in st.session_state:
        st.session_state.cal_month = today.month

    nav_l, nav_c, nav_r = st.columns([1, 3, 1])
    with nav_l:
        if st.button("◀ Prev", key="cal_prev"):
            d = date(st.session_state.cal_year, st.session_state.cal_month, 1) - timedelta(days=1)
            st.session_state.cal_year  = d.year
            st.session_state.cal_month = d.month
            st.rerun()
    with nav_c:
        st.markdown(
            f"<h3 style='text-align:center'>"
            f"{calendar.month_name[st.session_state.cal_month]} {st.session_state.cal_year}"
            f"</h3>",
            unsafe_allow_html=True,
        )
    with nav_r:
        if st.button("Next ▶", key="cal_next"):
            d = date(st.session_state.cal_year, st.session_state.cal_month,
                     calendar.monthrange(st.session_state.cal_year,
                                         st.session_state.cal_month)[1]) + timedelta(days=1)
            st.session_state.cal_year  = d.year
            st.session_state.cal_month = d.month
            st.rerun()

    year  = st.session_state.cal_year
    month = st.session_state.cal_month
    color = get_chart_color()

    # ── Fetch month data ─────────────────────────────────────────────────────
    first_day  = date(year, month, 1)
    last_day   = date(year, month, calendar.monthrange(year, month)[1])
    days_range = (last_day - first_day).days + 1

    from_d = str(first_day)
    to_d   = str(last_day)

    rev_rows     = revenue_by_day(days=365)  # pull all; filter below
    rev_by_date  = {r["day"]: r["total"] for r in rev_rows}
    entry_rows   = sessions_by_day(days=365)
    entry_by_day = {r["day"]: r["entries"] for r in entry_rows}

    max_rev = max(rev_by_date.values(), default=1) or 1

    # ── Build calendar grid ──────────────────────────────────────────────────
    cal = calendar.monthcalendar(year, month)
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    header_html = "".join(
        f"<th style='padding:6px 10px;text-align:center;color:#aaa'>{d}</th>"
        for d in day_names
    )
    rows_html = ""
    for week in cal:
        rows_html += "<tr>"
        for day_num in week:
            if day_num == 0:
                rows_html += "<td style='padding:6px;'></td>"
                continue
            day_str = str(date(year, month, day_num))
            rev     = rev_by_date.get(day_str, 0)
            entries = entry_by_day.get(day_str, 0)
            intensity = min(rev / max_rev, 1.0) if max_rev > 0 else 0
            cell_color = _hex_blend(intensity, color) if rev > 0 else "#1b2a3b"
            is_today   = (day_num == today.day and year == today.year and month == today.month)
            border     = f"2px solid {color}" if is_today else "1px solid #333"
            rows_html += (
                f"<td style='padding:6px;text-align:center;border-radius:8px;"
                f"background:{cell_color};border:{border};min-width:60px;'>"
                f"<b style='color:#fff'>{day_num}</b><br>"
                f"<small style='color:#ccc'>₹{rev:,.0f}</small><br>"
                f"<small style='color:#aaa'>{entries} in</small>"
                f"</td>"
            )
        rows_html += "</tr>"

    table_html = (
        f"<table style='border-collapse:separate;border-spacing:4px;width:100%'>"
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{rows_html}</tbody></table>"
    )
    st.markdown(table_html, unsafe_allow_html=True)

    # ── Day-detail selector ───────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🔎 Day Detail")
    selected_day = st.date_input("Select a date to see its sessions",
                                  value=today, key="cal_detail_day")
    if selected_day:
        day_sessions = get_all_sessions(
            from_date=str(selected_day),
            to_date=str(selected_day),
        )
        if day_sessions:
            df = pd.DataFrame(day_sessions)
            df = df[["session_id","plate_no","owner_name","slot_code",
                     "entry_time","exit_time","fee","status"]]
            df.columns = ["ID","Plate","Owner","Slot","Entry","Exit","Fee (₹)","Status"]
            df["Fee (₹)"] = df["Fee (₹)"].apply(lambda x: f"₹{x:,.2f}" if x else "—")
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info(f"No sessions recorded on {selected_day}.")


# Alias for compatibility with page imports
render_calendar_view = render_calendar
