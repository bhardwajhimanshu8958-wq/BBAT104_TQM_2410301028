"""
features/dashboard.py — Dashboard Overview KPIs and charts (Q03-3).

Provides:
- render_dashboard(): the full dashboard page with KPI cards, charts, and
  a recent activity table.

Why a dashboard? A key CTQ is "situational awareness" — the operator must
see occupancy and revenue at a glance without running queries manually.
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")

from modules.slots import get_all_slots, get_utilization
from modules.billing import revenue_today, revenue_by_day
from modules.vehicles import count_vehicles_today
from modules.sessions import get_recent_activity, get_active_sessions
from features.theme import get_chart_color


def _kpi_card(col, label: str, value: str, delta: str = "") -> None:
    """Render a single KPI metric card in the given column."""
    col.metric(label=label, value=value, delta=delta or None)


def render_dashboard() -> None:
    """Render the full Dashboard Overview page."""
    st.title("📊 Dashboard Overview")
    st.caption("Real-time parking metrics — refreshes on every page load.")

    # ── KPI row ──────────────────────────────────────────────────────────────
    util   = get_utilization()
    rev    = revenue_today()
    veh_td = count_vehicles_today()

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    _kpi_card(c1, "Total Slots",    str(util["total"]))
    _kpi_card(c2, "Occupied",       str(util["occupied"]))
    _kpi_card(c3, "Available",      str(util["available"]))
    _kpi_card(c4, "Utilization",    f"{util['utilization_pct']}%")
    _kpi_card(c5, "Today Revenue",  f"₹{rev:,.2f}")
    _kpi_card(c6, "Vehicles Today", str(veh_td))

    st.markdown("---")

    # ── Charts row ───────────────────────────────────────────────────────────
    chart_col, _, rev_col = st.columns([5, 1, 5])
    color = get_chart_color()

    # Occupancy by zone
    with chart_col:
        st.subheader("🏙️ Occupancy by Zone")
        slots = get_all_slots()
        if slots:
            df = pd.DataFrame(slots)
            zone_occ = df.groupby(["zone", "status"]).size().unstack(fill_value=0)
            fig, ax = plt.subplots(figsize=(5, 3))
            fig.patch.set_alpha(0)
            ax.set_facecolor("none")
            zone_occ.plot(kind="bar", ax=ax, color=[color, "#444", "#888"],
                          edgecolor="none", width=0.6)
            ax.set_xlabel("Zone", color="#aaa")
            ax.set_ylabel("Slots", color="#aaa")
            ax.tick_params(colors="#aaa", rotation=0)
            ax.spines[:].set_color("#333")
            ax.legend(fontsize=8, labelcolor="#aaa", facecolor="none", edgecolor="none")
            plt.tight_layout()
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
        else:
            st.info("No slot data yet.")

    # Revenue by day
    with rev_col:
        st.subheader("💰 Revenue (Last 14 Days)")
        rev_data = revenue_by_day(days=14)
        if rev_data:
            df_rev = pd.DataFrame(rev_data)
            fig2, ax2 = plt.subplots(figsize=(5, 3))
            fig2.patch.set_alpha(0)
            ax2.set_facecolor("none")
            ax2.plot(df_rev["day"], df_rev["total"], color=color, marker="o",
                     linewidth=2, markersize=5)
            ax2.fill_between(df_rev["day"], df_rev["total"],
                             alpha=0.15, color=color)
            ax2.set_xlabel("Date", color="#aaa", fontsize=8)
            ax2.set_ylabel("₹ Revenue", color="#aaa", fontsize=8)
            ax2.tick_params(colors="#aaa", labelsize=7, rotation=30)
            ax2.spines[:].set_color("#333")
            plt.tight_layout()
            st.pyplot(fig2, use_container_width=True)
            plt.close(fig2)
        else:
            st.info("No completed sessions yet.")

    st.markdown("---")

    # ── Recent activity ───────────────────────────────────────────────────────
    st.subheader("🕐 Recent Activity")
    recent = get_recent_activity(limit=10)
    if recent:
        df_act = pd.DataFrame(recent)
        df_act = df_act[["session_id","plate_no","owner_name","slot_code",
                          "entry_time","exit_time","fee","status"]]
        df_act.columns = ["ID","Plate","Owner","Slot","Entry","Exit","Fee (₹)","Status"]
        st.dataframe(df_act, use_container_width=True, hide_index=True)
    else:
        st.info("No sessions recorded yet.")
