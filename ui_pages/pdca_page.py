"""
ui_pages/pdca_page.py — Plan-Do-Check-Act (PDCA) Continuous Improvement Log (TQM Tool 5).

Displays documented PDCA cycles, before/after metrics, and Kaizen improvements.
"""

import streamlit as st
from database.db import query_db


def render_pdca_page():
    """Render the PDCA cycle history and performance delta comparisons."""
    st.title("🔄 Plan-Do-Check-Act (PDCA) Kaizen Log")
    st.caption("Structured Deming cycles for iterative system optimization.")

    rows = query_db("SELECT * FROM pdca ORDER BY cycle_no ASC")
    if rows:
        for r in rows:
            with st.expander(f"🔄 PDCA Cycle #{r['cycle_no']}: {r['plan'][:60]}... ({r['date']})", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**📋 Plan**: {r['plan']}")
                    st.markdown(f"**⚡ Do (Action)**: {r['do_action']}")
                with c2:
                    st.markdown(f"**🔍 Check (Results)**: {r['check_result']}")
                    st.markdown(f"**🎯 Act (Standardization)**: {r['act_decision']}")

                st.markdown("---")
                mc1, mc2, mc3 = st.columns(3)
                mc1.metric("Metric", r["metric_name"])
                mc2.metric("Baseline (Before)", r["before_value"])
                delta_val = float(r["after_value"]) - float(r["before_value"]) if isinstance(r["after_value"], (int, float)) else None
                mc3.metric("Optimized (After)", r["after_value"], delta=f"{delta_val:+.1f}" if delta_val is not None else None)
    else:
        st.info("PDCA cycles will be populated during Phase 5 continuous improvement.")


if __name__ == "__main__" or True:
    render_pdca_page()
