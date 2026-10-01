"""
tqm/pdca.py — PDCA Cycle Tracker (TQM Tool 5).

Records improvement cycles (Plan → Do → Check → Act) with before/after
metric comparison so the team can quantify the improvement delta.

Why PDCA? The Plan-Do-Check-Act (Deming) cycle is the foundational TQM
continuous-improvement model. Logging each cycle creates an auditable
improvement history with measurable outcomes.
"""

import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from database.db import query_db, execute_db


# ─── Seed ───────────────────────────────────────────────────────────────────

def seed_pdca_if_empty() -> None:
    """Seed 3 completed PDCA cycles if table is empty."""
    if query_db("SELECT 1 FROM pdca LIMIT 1"):
        return

    cycles = [
        (1,
         "Plan — Billing Accuracy\n"
         "Defect: Free-minute deduction had an off-by-one error causing overcharges on short stays.\n"
         "Target: Reduce billing discrepancy rate from 12% to <2%.",
         "Do — Code Fix\n"
         "Revised calculate_fee() to use strict > comparison on free_minutes.\n"
         "Added Poka-Yoke: calculate_fee raises ValueError for negative amounts.\n"
         "Wrote explicit pytest: calculate_fee('Car',10)==20.0 verified.",
         "Check — Test Results\n"
         "Unit test suite: 7/7 passed. Billing discrepancy rate: 0% in 30-session regression.\n"
         "User acceptance: 3/3 test users confirmed receipt accuracy.",
         "Act — Standardise\n"
         "Merged fix to main branch. Added billing unit test to CI gate.\n"
         "Added to ERROR_LOG.md as Lesson Learned. Updated FMEA ID-8 to Resolved.",
         "Billing Discrepancy Rate (%)", 12.0, 0.0),

        (2,
         "Plan — UI Crash on Empty DB\n"
         "Defect: App crashed on fresh install with 'NoneType not iterable' when no slots exist.\n"
         "Target: Eliminate all None-check crashes; app must start without demo data.",
         "Do — Guard All Queries\n"
         "Added 'if rows else []' guard after every query_db() call across all ui_pages/.\n"
         "Added 'if df.empty: st.info(...)' to all DataFrames that depended on live data.",
         "Check — Smoke Tests\n"
         "test_ui_smoke.py ran 3 AppTest smoke tests on empty DB; all passed.\n"
         "Empty-state placeholder messages verified on 5 pages.",
         "Act — Standardise\n"
         "Created coding standard: every query must have a None guard. Added to README.\n"
         "Updated FMEA ID-9 to Resolved.",
         "Empty-DB Crash Count", 5.0, 0.0),

        (3,
         "Plan — FK Constraint Enforcement\n"
         "Defect: SQLite FKs not enforced by default; orphaned sessions possible after slot delete.\n"
         "Target: Ensure PRAGMA foreign_keys=ON is active for every connection.",
         "Do — DB Layer Fix\n"
         "Added PRAGMA foreign_keys = ON to get_connection() in database/db.py.\n"
         "Added cascade delete test for parking_sessions in test_crud_operations.py.",
         "Check — Test Results\n"
         "FK violation test confirmed: INSERT into parking_sessions with invalid slot_id raises OperationalError.\n"
         "All 7 pytest tests pass post-fix.",
         "Act — Standardise\n"
         "Documented in schema.sql comment: FK must always be enabled at connection level.\n"
         "Updated FMEA ID-7 to Resolved.",
         "FK Violations Possible (binary)", 1.0, 0.0),
    ]

    for (cycle_no, plan, do, check, act, metric, before, after) in cycles:
        execute_db(
            """INSERT INTO pdca (cycle_no, plan, do_action, check_result, act_decision,
               metric_name, before_value, after_value)
               VALUES (?,?,?,?,?,?,?,?)""",
            (cycle_no, plan, do, check, act, metric, before, after),
        )


# ─── CRUD ────────────────────────────────────────────────────────────────────

def get_all_pdca() -> list[dict]:
    return query_db("SELECT * FROM pdca ORDER BY cycle_no ASC")


def add_pdca_cycle(plan: str, do_action: str, check_result: str, act_decision: str,
                   metric_name: str, before_value: float, after_value: float) -> int:
    """Insert a new PDCA cycle. Returns the new pdca_id."""
    max_cycle = query_db("SELECT MAX(cycle_no) as m FROM pdca")
    cycle_no = (max_cycle[0]["m"] or 0) + 1
    return execute_db(
        """INSERT INTO pdca (cycle_no, plan, do_action, check_result, act_decision,
           metric_name, before_value, after_value)
           VALUES (?,?,?,?,?,?,?,?)""",
        (cycle_no, plan, do_action, check_result, act_decision,
         metric_name, before_value, after_value),
    )


# ─── Charts ──────────────────────────────────────────────────────────────────

def _improvement_bar_chart(df: pd.DataFrame):
    """Generate before/after improvement bar chart."""
    fig, ax = plt.subplots(figsize=(9, 4), facecolor="#0d1b2a")
    ax.set_facecolor("#1b2a3b")
    x = range(len(df))
    w = 0.35
    ax.bar([xi - w / 2 for xi in x], df["before_value"], width=w,
           label="Before", color="#e63946", alpha=0.85)
    ax.bar([xi + w / 2 for xi in x], df["after_value"], width=w,
           label="After", color="#2a9d8f", alpha=0.85)
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"Cycle {r['cycle_no']}\n{r['metric_name'][:25]}"
                        for _, r in df.iterrows()], color="#ccc", fontsize=8)
    ax.set_ylabel("Metric Value", color="#aaa")
    ax.tick_params(colors="#aaa")
    ax.spines[:].set_color("#333")
    ax.legend(labelcolor="#fff", facecolor="none", edgecolor="#555", fontsize=9)
    plt.title("PDCA Before vs After Metric Comparison",
              color="#e0f4ff", fontsize=11, fontweight="bold", pad=12)
    fig.tight_layout()
    return fig


def _pdca_wheel(phase: str = "Act"):
    """Draw a PDCA wheel (pie segments) highlighting the current phase."""
    phases    = ["Plan", "Do", "Check", "Act"]
    colors    = {"Plan": "#00b4d8", "Do": "#2a9d8f", "Check": "#f4a261", "Act": "#9d4edd"}
    alpha     = [1.0 if p == phase else 0.35 for p in phases]

    fig, ax   = plt.subplots(figsize=(4, 4), facecolor="#0d1b2a")
    wedges, _ = ax.pie([1, 1, 1, 1],
                       colors=[colors[p] for p in phases],
                       startangle=90,
                       counterclock=False,
                       wedgeprops={"edgecolor": "#0d1b2a", "linewidth": 3})
    for w, a in zip(wedges, alpha):
        w.set_alpha(a)

    for i, p in enumerate(phases):
        angle = 90 - (i * 90) - 45
        import math
        rx = 0.6 * math.cos(math.radians(angle))
        ry = 0.6 * math.sin(math.radians(angle))
        ax.text(rx, ry, p, ha="center", va="center",
                color="#fff", fontsize=11, fontweight="bold")

    ax.text(0, 0, "PDCA", ha="center", va="center",
            color="#e0f4ff", fontsize=10, fontweight="bold")
    ax.set_facecolor("#0d1b2a")
    ax.set_title(f"Current Phase: {phase}", color="#e0f4ff", fontsize=9, pad=8)
    plt.tight_layout()
    return fig


# ─── Renderer ────────────────────────────────────────────────────────────────

def render_pdca() -> None:
    """Render the PDCA Cycle Tracker page."""
    seed_pdca_if_empty()

    st.title("🔄 PDCA Continuous Improvement Cycles")
    st.caption("Deming's Plan-Do-Check-Act cycle tracker for measurable quality improvements.")
    st.markdown(
        """
        > **Why PDCA?** TQM is sustained by iterative improvement rather than one-time fixes.
        > Each logged PDCA cycle provides an auditable record of problem, action, result, and
        > standardisation — forming the backbone of continuous improvement culture.
        """
    )

    rows = get_all_pdca()
    df   = pd.DataFrame(rows) if rows else pd.DataFrame()

    tab_overview, tab_chart, tab_new = st.tabs(["📋 Cycle Log", "📊 Improvement Chart", "➕ Log New Cycle"])

    with tab_overview:
        if df.empty:
            st.info("No PDCA cycles recorded.")
        else:
            for _, row in df.iterrows():
                with st.expander(
                    f"🔄 Cycle {int(row['cycle_no'])} — {row['metric_name']}  "
                    f"  ({row['date']})",
                    expanded=False,
                ):
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        phases = ["Plan", "Do", "Check", "Act"]
                        cols = st.columns(4)
                        fields = ["plan", "do_action", "check_result", "act_decision"]
                        icons = ["📋", "⚙️", "✅", "🚀"]
                        colors = ["#00b4d8", "#2a9d8f", "#f4a261", "#9d4edd"]
                        for i, (ph, col) in enumerate(zip(phases, cols)):
                            with col:
                                st.markdown(
                                    f"<div style='border-left:3px solid {colors[i]};padding-left:8px'>"
                                    f"<b>{icons[i]} {ph}</b></div>",
                                    unsafe_allow_html=True,
                                )
                                st.caption(str(row[fields[i]])[:300])
                    with c2:
                        fig = _pdca_wheel("Act")
                        st.pyplot(fig, use_container_width=True)
                        plt.close(fig)

                        delta = row["after_value"] - row["before_value"]
                        direction = "↓" if delta < 0 else ("↑" if delta > 0 else "→")
                        st.metric(
                            label=row["metric_name"][:30],
                            value=f"{row['after_value']:.1f}",
                            delta=f"{delta:.1f} {direction}",
                            delta_color="normal" if delta > 0 else "inverse",
                        )

    with tab_chart:
        if df.empty:
            st.info("Log at least one cycle to see the chart.")
        else:
            fig = _improvement_bar_chart(df)
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

    with tab_new:
        st.subheader("Log a New PDCA Cycle")
        with st.form("new_pdca_form"):
            col1, col2 = st.columns(2)
            plan         = col1.text_area("📋 Plan — Problem & Target", height=120)
            do_action    = col2.text_area("⚙️ Do — Actions Taken", height=120)
            check_result = col1.text_area("✅ Check — Results & Evidence", height=120)
            act_decision = col2.text_area("🚀 Act — Standardise / Escalate", height=120)
            metric_name  = st.text_input("Metric Being Measured")
            col_b, col_a = st.columns(2)
            before_val   = col_b.number_input("Metric Value BEFORE", min_value=0.0, step=0.1)
            after_val    = col_a.number_input("Metric Value AFTER", min_value=0.0, step=0.1)
            submitted    = st.form_submit_button("💾 Save PDCA Cycle", use_container_width=True)

        if submitted:
            if not all([plan, do_action, check_result, act_decision, metric_name]):
                st.error("All fields are required.")
            else:
                add_pdca_cycle(plan, do_action, check_result, act_decision,
                               metric_name, before_val, after_val)
                st.success("PDCA cycle logged successfully!")
                st.rerun()
