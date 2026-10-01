"""
ui_pages/pareto_page.py — Pareto 80/20 Analysis UI (TQM Tool 3).

Renders Pareto charts of defects to isolate the 'vital few' from the 'trivial many'.
"""

import streamlit as st
from database.db import query_db
import pandas as pd
import matplotlib.pyplot as plt
from features.theme import get_chart_color


def render_pareto_page():
    """Render the Pareto analysis chart and defect frequency distribution."""
    st.title("📉 Pareto Analysis (80/20 Rule)")
    st.caption("Identify the 'vital few' defect categories driving the majority of operational problems.")

    rows = query_db(
        """SELECT defect_type, COUNT(*) as count 
           FROM defects 
           GROUP BY defect_type 
           ORDER BY count DESC"""
    )

    if not rows:
        st.info("No defect data available to plot Pareto chart. Log defects via Checksheet first.")
        return

    df = pd.DataFrame(rows)
    df["cum_count"] = df["count"].cumsum()
    df["cum_pct"] = (df["cum_count"] / df["count"].sum()) * 100

    c_left, c_right = st.columns([3, 2])

    with c_left:
        fig, ax1 = plt.subplots(figsize=(8, 5))
        chart_col = get_chart_color()

        ax1.bar(df["defect_type"], df["count"], color=chart_col, alpha=0.85, label="Defect Count")
        ax1.set_ylabel("Defect Frequency", color=chart_col, fontweight="bold")
        ax1.tick_params(axis="x", rotation=45)

        ax2 = ax1.twinx()
        ax2.plot(df["defect_type"], df["cum_pct"], color="#E65100", marker="o", linewidth=2.5, label="Cumulative %")
        ax2.axhline(80, color="#D32F2F", linestyle="--", linewidth=1.5, label="80% Cutoff Line")
        ax2.set_ylabel("Cumulative Percentage (%)", color="#E65100", fontweight="bold")
        ax2.set_ylim(0, 105)

        plt.title("Pareto Distribution of Parking System Defects", fontsize=12, fontweight="bold", pad=15)
        fig.tight_layout()
        st.pyplot(fig)

    with c_right:
        st.subheader("Pareto Frequency Table")
        st.dataframe(
            df[["defect_type", "count", "cum_pct"]],
            column_config={
                "defect_type": "Defect Category",
                "count": "Frequency",
                "cum_pct": st.column_config.NumberColumn("Cumulative %", format="%.1f%%"),
            },
            hide_index=True,
            use_container_width=True,
        )


if __name__ == "__main__" or True:
    render_pareto_page()
