"""
tqm/pareto.py — Pareto Chart Generator (TQM Tool 3).

Generates the 80/20 Pareto analysis from defects table data.
Saves the chart to docs/ and exports/ as PNG.

Why Pareto? The Pareto Principle (80/20 rule) states that ~80% of defects
arise from ~20% of causes. Identifying the 'vital few' defect types
allows focused improvement effort to yield maximum quality gain.
"""

import os
import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from database.db import query_db

DOCS_DIR    = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
EXPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")


def generate_pareto_data() -> pd.DataFrame:
    """Query defect counts grouped by defect_type and compute cumulative %."""
    rows = query_db(
        """SELECT defect_type, COUNT(*) as count
           FROM defects
           GROUP BY defect_type
           ORDER BY count DESC"""
    )
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["cum_count"] = df["count"].cumsum()
    df["cum_pct"]   = (df["cum_count"] / df["count"].sum()) * 100
    return df


def save_pareto_chart(chart_color: str = "#00b4d8", save_png: bool = True) -> str | None:
    """Generate and save the Pareto bar+line chart. Returns path to saved PNG or None."""
    df = generate_pareto_data()
    if df.empty:
        return None

    fig, ax1 = plt.subplots(figsize=(10, 5), facecolor="#0d1b2a")
    ax1.set_facecolor("#1b2a3b")

    # Bars for defect frequency
    ax1.bar(df["defect_type"], df["count"], color=chart_color, alpha=0.85,
            edgecolor="none", label="Defect Count")
    ax1.set_ylabel("Defect Frequency", color=chart_color, fontweight="bold", fontsize=10)
    ax1.tick_params(axis="x", rotation=45, colors="#ccc", labelsize=8)
    ax1.tick_params(axis="y", colors="#ccc")
    ax1.spines[:].set_color("#333")

    # Cumulative % line
    ax2 = ax1.twinx()
    ax2.plot(df["defect_type"], df["cum_pct"], color="#E65100", marker="o",
             linewidth=2.5, markersize=5, label="Cumulative %")
    ax2.axhline(80, color="#D32F2F", linestyle="--", linewidth=1.5, label="80% Cutoff")
    ax2.set_ylabel("Cumulative Percentage (%)", color="#E65100", fontweight="bold", fontsize=10)
    ax2.set_ylim(0, 110)
    ax2.tick_params(colors="#E65100")
    ax2.spines[:].set_color("#333")

    # Title & Legend
    plt.title("Pareto Analysis — Parking System Defect Distribution",
              color="#e0f4ff", fontsize=12, fontweight="bold", pad=15)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=9,
               labelcolor="#fff", facecolor="none", edgecolor="#555",
               loc="upper right")
    fig.tight_layout()

    # Save
    path = None
    if save_png:
        os.makedirs(DOCS_DIR, exist_ok=True)
        os.makedirs(EXPORTS_DIR, exist_ok=True)
        path = os.path.join(EXPORTS_DIR, "pareto_chart.png")
        plt.savefig(path, dpi=180, bbox_inches="tight")
        # Also copy to docs/
        import shutil
        shutil.copy(path, os.path.join(DOCS_DIR, "pareto_chart.png"))

    return fig, path


def render_pareto() -> None:
    """Render the full Pareto analysis page."""
    st.title("📉 Pareto Analysis (80/20 Rule)")
    st.caption("Identify the 'vital few' defect categories driving 80% of quality problems.")
    st.markdown(
        """
        > **Why Pareto?** The 80/20 principle guides targeted corrective action — rather than
        > treating all defects equally, it pinpoints the handful of root causes that deliver the
        > greatest quality improvement return per unit of effort.
        """
    )

    df = generate_pareto_data()
    if df.empty:
        st.info("No defect data available. Log defects via the Checksheet first.")
        return

    col_chart, col_table = st.columns([3, 2])

    with col_chart:
        result = save_pareto_chart(save_png=True)
        if result:
            fig, _ = result
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

    with col_table:
        st.subheader("Frequency Distribution Table")
        display_df = df[["defect_type", "count", "cum_pct"]].copy()
        display_df["cum_pct"] = display_df["cum_pct"].round(1)
        st.dataframe(
            display_df,
            column_config={
                "defect_type": "Defect Category",
                "count": "Frequency",
                "cum_pct": st.column_config.NumberColumn("Cumulative %", format="%.1f%%"),
            },
            hide_index=True,
            use_container_width=True,
        )

        # Vital few identification
        vital_few = df[df["cum_pct"] <= 80]
        st.info(
            f"**Vital Few**: {len(vital_few)} defect type(s) account for ≥80% of all quality issues.  \n"
            + "\n".join(f"• {r['defect_type']}" for _, r in vital_few.iterrows())
        )
