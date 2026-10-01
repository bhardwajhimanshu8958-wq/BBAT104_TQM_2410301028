"""
tqm/control_chart.py — Statistical Process Control (SPC) Control Chart (TQM Tool 6).

Generates X-bar and UCL/LCL control limits from daily fee revenue data
to detect out-of-control processes using the Western Electric rules.

Why Control Charts? SPC control charts distinguish between:
  - Common cause variation (normal process noise)
  - Special cause variation (signals of abnormal process behaviour)
This allows the team to react only when truly warranted, preventing
over-adjustment (tampering) while catching real quality escapes.

Control Limit Formulas (3-sigma):
  Mean (X̄)  = average of all daily revenues
  σ          = sample standard deviation
  UCL        = X̄ + 3σ
  LCL        = max(0, X̄ − 3σ)   (revenue cannot be negative)
"""

import os
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from database.db import query_db, execute_db
from datetime import date, timedelta
import random

EXPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")
DOCS_DIR    = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")


# ─── Data Access ─────────────────────────────────────────────────────────────

def get_daily_revenue() -> pd.DataFrame:
    """Aggregate completed session fees by date. Returns DataFrame[date, revenue]."""
    rows = query_db(
        """SELECT date(exit_time) AS day, ROUND(SUM(fee),2) AS revenue
           FROM parking_sessions
           WHERE status = 'Completed' AND fee IS NOT NULL AND exit_time IS NOT NULL
           GROUP BY day
           ORDER BY day ASC"""
    )
    if not rows:
        return pd.DataFrame(columns=["day", "revenue"])
    df = pd.DataFrame(rows)
    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce").fillna(0)
    return df


def seed_demo_revenue_if_needed() -> None:
    """If fewer than 20 completed sessions exist, insert 30 days of demo sessions."""
    count = query_db("SELECT COUNT(*) AS c FROM parking_sessions WHERE status='Completed'")
    if count and count[0]["c"] >= 20:
        return

    # Pull first vehicle and first slot from DB
    vehicles = query_db("SELECT vehicle_id, vehicle_type FROM vehicles LIMIT 3")
    slots    = query_db("SELECT slot_id FROM slots WHERE status != 'Maintenance' LIMIT 3")
    if not vehicles or not slots:
        return

    base_date = date.today() - timedelta(days=31)
    random.seed(42)
    for i in range(30):
        day = base_date + timedelta(days=i)
        # 3-8 sessions per day
        for _ in range(random.randint(3, 8)):
            veh  = random.choice(vehicles)
            slot = random.choice(slots)
            entry_h  = random.randint(8, 17)
            entry_m  = random.randint(0, 59)
            duration = random.randint(30, 240)   # minutes
            entry_dt = f"{day} {entry_h:02d}:{entry_m:02d}:00"
            exit_dt  = (
                pd.Timestamp(entry_dt) + pd.Timedelta(minutes=duration)
            ).strftime("%Y-%m-%d %H:%M:%S")
            rate  = {"Car": 2.0, "Bike": 1.0, "EV": 3.0}.get(veh["vehicle_type"], 2.0)
            free  = {"Car": 10,  "Bike": 5,   "EV": 15}.get(veh["vehicle_type"], 10)
            mins  = max(0, duration - free)
            fee   = round(20.0 + (mins / 60) * rate * 10, 2)

            execute_db(
                """INSERT INTO parking_sessions
                   (vehicle_id, slot_id, entry_time, exit_time, fee, status)
                   VALUES (?,?,?,?,?,'Completed')""",
                (veh["vehicle_id"], slot["slot_id"], entry_dt, exit_dt, fee),
            )


# ─── Chart Generation ─────────────────────────────────────────────────────────

def compute_control_limits(df: pd.DataFrame) -> dict:
    """Compute X̄, UCL, LCL and flag out-of-control points."""
    rev    = df["revenue"].values
    mean   = float(np.mean(rev))
    std    = float(np.std(rev, ddof=1)) if len(rev) > 1 else 0.0
    ucl    = mean + 3 * std
    lcl    = max(0.0, mean - 3 * std)
    flags  = [(r > ucl or r < lcl) for r in rev]
    return {"mean": mean, "ucl": ucl, "lcl": lcl, "std": std, "flags": flags}


def generate_control_chart(df: pd.DataFrame, limits: dict):
    """Generate and return a matplotlib control chart figure."""
    fig, ax = plt.subplots(figsize=(13, 5), facecolor="#0d1b2a")
    ax.set_facecolor("#1b2a3b")

    x = range(len(df))
    rev = df["revenue"].values

    # Data points — colour by in/out of control
    in_ctrl  = [v for v, f in zip(rev, limits["flags"]) if not f]
    out_ctrl = [v for v, f in zip(rev, limits["flags"]) if f]
    xi_in    = [i for i, f in enumerate(limits["flags"]) if not f]
    xi_out   = [i for i, f in enumerate(limits["flags"]) if f]

    ax.plot(x, rev, color="#00b4d8", linewidth=1.8, alpha=0.8, zorder=2)
    ax.scatter(xi_in,  in_ctrl,  color="#2a9d8f", s=40, zorder=3, label="In-Control")
    ax.scatter(xi_out, out_ctrl, color="#e63946", s=70, zorder=4,
               marker="^", label="Out-of-Control ⚠️")

    # Control lines
    ax.axhline(limits["mean"], color="#f4d03f", linewidth=2.0,
               linestyle="-",  label=f"X̄ = ₹{limits['mean']:.2f}")
    ax.axhline(limits["ucl"],  color="#e63946", linewidth=1.5,
               linestyle="--", label=f"UCL = ₹{limits['ucl']:.2f}")
    ax.axhline(limits["lcl"],  color="#e63946", linewidth=1.5,
               linestyle="--", label=f"LCL = ₹{limits['lcl']:.2f}")

    # Shaded ±1σ band
    ax.fill_between(x, limits["mean"] - limits["std"],
                    limits["mean"] + limits["std"],
                    color="#f4d03f", alpha=0.08, label="±1σ Band")
    ax.fill_between(x, limits["ucl"], limits["lcl"],
                    color="#e63946", alpha=0.05)

    ax.set_xticks(list(x))
    ax.set_xticklabels(df["day"].tolist(), rotation=45, ha="right",
                       color="#aaa", fontsize=7)
    ax.set_ylabel("Daily Revenue (₹)", color="#aaa", fontsize=10)
    ax.tick_params(colors="#aaa")
    ax.spines[:].set_color("#333")
    ax.legend(fontsize=8, labelcolor="#ddd", facecolor="none",
              edgecolor="#555", loc="upper left")
    plt.title("SPC X-bar Control Chart — Daily Parking Revenue",
              color="#e0f4ff", fontsize=12, fontweight="bold", pad=14)
    fig.tight_layout()
    return fig


# ─── Renderer ────────────────────────────────────────────────────────────────

def render_control_chart() -> None:
    """Render the SPC Control Chart page."""
    seed_demo_revenue_if_needed()

    st.title("📈 SPC Control Chart — Statistical Process Control")
    st.caption("X-bar chart with 3σ UCL/LCL to separate common-cause from special-cause variation.")
    st.markdown(
        """
        > **Why SPC?** Control charts tell us *when* to act on process variation.
        > Points inside UCL/LCL are **common-cause** (leave alone — don't tamper).
        > Points **outside** are **special-cause** signals requiring investigation.
        >
        > **Formula**: UCL = X̄ + 3σ &nbsp;|&nbsp; LCL = max(0, X̄ − 3σ)
        """
    )

    df = get_daily_revenue()
    if df.empty or len(df) < 5:
        st.warning("Not enough completed session data to draw a meaningful control chart. "
                   "Run the app for a few days or add demo sessions.")
        return

    limits = compute_control_limits(df)
    out_count = sum(limits["flags"])

    # KPI strip
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Process Mean (X̄)", f"₹{limits['mean']:.2f}")
    kpi2.metric("Std Dev (σ)",       f"₹{limits['std']:.2f}")
    kpi3.metric("UCL (X̄+3σ)",       f"₹{limits['ucl']:.2f}")
    kpi4.metric("Out-of-Control Pts",f"{out_count}",
                delta=f"{out_count} signal(s)", delta_color="inverse" if out_count > 0 else "off")

    # Chart
    fig = generate_control_chart(df, limits)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

    # Interpretation
    st.markdown("---")
    if out_count == 0:
        st.success("✅ **Process in control** — all data points lie within ±3σ. "
                   "No special-cause variation detected.")
    else:
        st.error(
            f"⚠️ **{out_count} out-of-control point(s)** detected outside 3σ limits. "
            "Investigate for special causes (unusual events, tariff changes, system outages)."
        )
        ooc_days = df[limits["flags"]]["day"].tolist()
        st.write("**Out-of-control dates:**", ", ".join(str(d) for d in ooc_days))

    # Data table
    with st.expander("📋 Raw Daily Revenue Data"):
        display = df.copy()
        display["Status"] = ["🔴 OOC" if f else "🟢 OK" for f in limits["flags"]]
        display["revenue"] = display["revenue"].apply(lambda v: f"₹{v:.2f}")
        st.dataframe(display, hide_index=True, use_container_width=True)

    # PNG Save
    if st.button("💾 Save Chart as PNG", use_container_width=True):
        fig2 = generate_control_chart(df, limits)
        os.makedirs(EXPORTS_DIR, exist_ok=True)
        os.makedirs(DOCS_DIR, exist_ok=True)
        path = os.path.join(EXPORTS_DIR, "control_chart.png")
        plt.savefig(path, dpi=180, bbox_inches="tight")
        import shutil
        shutil.copy(path, os.path.join(DOCS_DIR, "control_chart.png"))
        plt.close(fig2)
        st.success(f"Saved to `{path}` and `docs/control_chart.png`")
