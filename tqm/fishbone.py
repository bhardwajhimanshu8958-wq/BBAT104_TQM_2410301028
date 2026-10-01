"""
tqm/fishbone.py — Ishikawa Fishbone Diagram Generator (TQM Tool 4).

Generates a cause-and-effect fishbone diagram using matplotlib, grouping
defects from the database into four branches:
    People | Process | Software Code | Infrastructure

Why Fishbone? The Ishikawa diagram visualises the many possible root causes
that contribute to a single effect (quality failure), making it essential for
structured problem analysis before corrective action.
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import streamlit as st
from database.db import query_db

DOCS_DIR    = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs")
EXPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "exports")

CATEGORIES = ["People", "Process", "Software Code", "Infrastructure"]
BRANCH_COLORS = {
    "People":          "#00b4d8",
    "Process":         "#2a9d8f",
    "Software Code":   "#e07a5f",
    "Infrastructure":  "#9d4edd",
}

# Layout positions for the four branches (top-left, top-right, bottom-left, bottom-right)
BRANCH_POSITIONS = {
    "People":          (0.05, 0.75),
    "Process":         (0.05, 0.30),
    "Software Code":   (0.55, 0.75),
    "Infrastructure":  (0.55, 0.30),
}


def _get_causes_by_category() -> dict[str, list[str]]:
    """Fetch defect types per fishbone category from the database."""
    data = {}
    for cat in CATEGORIES:
        rows = query_db(
            "SELECT DISTINCT defect_type FROM defects WHERE fishbone_category = ?",
            (cat,),
        )
        data[cat] = [r["defect_type"] for r in rows]
    return data


def generate_fishbone_chart(effect: str = "Parking System Quality Failure") -> tuple:
    """Generate and return the matplotlib fishbone diagram figure."""
    causes = _get_causes_by_category()

    fig, ax = plt.subplots(figsize=(14, 7), facecolor="#0d1b2a")
    ax.set_facecolor("#0d1b2a")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # Spine (backbone)
    ax.annotate("", xy=(0.92, 0.52), xytext=(0.05, 0.52),
                arrowprops=dict(arrowstyle="-|>", color="#e0f4ff", lw=2.5))

    # Effect box (head of fish)
    effect_box = mpatches.FancyBboxPatch((0.88, 0.44), 0.11, 0.16,
                                         boxstyle="round,pad=0.01",
                                         facecolor="#1b2a3b", edgecolor="#00b4d8",
                                         linewidth=2.5, zorder=5)
    ax.add_patch(effect_box)
    ax.text(0.935, 0.52, effect.replace(" ", "\n"), color="#e0f4ff",
            fontsize=7, fontweight="bold", ha="center", va="center", zorder=6)

    # Branch ribs and causes
    for cat, (bx, by) in BRANCH_POSITIONS.items():
        color = BRANCH_COLORS[cat]
        is_top = by > 0.5

        # Branch label
        ax.text(bx + 0.17, by + (0.08 if is_top else -0.04), cat,
                color=color, fontsize=10, fontweight="bold", ha="center")

        # Rib from branch to spine
        spine_x = 0.35 if bx < 0.4 else 0.72
        rib_angle_y = 0.52
        ax.annotate("", xy=(spine_x, rib_angle_y),
                    xytext=(bx + 0.14, by + (0.00 if is_top else 0.08)),
                    arrowprops=dict(arrowstyle="-", color=color, lw=2.0))

        # Causes as sub-bones
        cat_causes = causes.get(cat, [])
        if not cat_causes:
            cat_causes = ["(no defects logged yet)"]

        for i, cause_text in enumerate(cat_causes[:5]):  # show up to 5 per branch
            cy = by + (0.05 - i * 0.05) if is_top else by + (0.06 + i * 0.05)
            cx_start = bx + 0.03
            cx_end   = bx + 0.28
            ax.plot([cx_start, cx_end], [cy, cy], color=color, lw=1.2, alpha=0.7)
            ax.text(cx_start - 0.01, cy, f"• {cause_text[:35]}",
                    color="#cccccc", fontsize=7, va="center", ha="right")

    plt.title(f"Ishikawa Fishbone: Root Causes of '{effect}'",
              color="#e0f4ff", fontsize=13, fontweight="bold", pad=10)
    fig.tight_layout()
    return fig, causes


def save_fishbone_chart(effect: str = "Parking System Quality Failure") -> str:
    """Save fishbone diagram as PNG and return path."""
    fig, _ = generate_fishbone_chart(effect)
    os.makedirs(DOCS_DIR, exist_ok=True)
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    path = os.path.join(EXPORTS_DIR, "fishbone_diagram.png")
    plt.savefig(path, dpi=180, bbox_inches="tight")
    import shutil
    shutil.copy(path, os.path.join(DOCS_DIR, "fishbone_diagram.png"))
    plt.close(fig)
    return path


def render_fishbone() -> None:
    """Render the Ishikawa fishbone diagram page."""
    st.title("🐟 Ishikawa Fishbone Diagram")
    st.caption("Cause-and-effect root cause analysis grouped by People, Process, Software Code, and Infrastructure.")
    st.markdown(
        """
        > **Why Fishbone?** The Ishikawa diagram helps teams visualize all possible root causes
        > of a problem in a structured way, enabling comprehensive corrective action rather than
        > fixing only the most visible symptom.
        """
    )

    effect = st.text_input("Effect / Problem Statement", value="Parking System Quality Failure")

    fig, causes = generate_fishbone_chart(effect)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

    st.markdown("---")
    st.subheader("Cause Branch Details")
    cols = st.columns(4)
    for idx, cat in enumerate(CATEGORIES):
        with cols[idx]:
            st.markdown(f"**{cat}**")
            cat_causes = causes.get(cat, [])
            if cat_causes:
                for c in cat_causes:
                    st.markdown(f"- {c}")
            else:
                st.caption("No defects logged")

    if st.button("💾 Save Fishbone as PNG", use_container_width=True):
        path = save_fishbone_chart(effect)
        st.success(f"Saved to: `{path}` (also copied to `docs/`)")
