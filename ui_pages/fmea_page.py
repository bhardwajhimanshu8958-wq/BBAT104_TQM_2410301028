"""
ui_pages/fmea_page.py — FMEA Risk Audit Matrix UI (TQM Tool 2).

Displays failure modes, calculated RPN (Severity x Occurrence x Detection),
top risks, and mitigation action tracking.
"""

import streamlit as st
from database.db import query_db


def render_fmea_page():
    """Render the FMEA risk assessment matrix and RPN ranking."""
    st.title("⚠️ Failure Mode and Effects Analysis (FMEA)")
    st.caption("Proactive risk assessment and Risk Priority Number (RPN) prioritization.")

    st.markdown(
        """
        > **RPN Formula**: $\\text{RPN} = \\text{Severity (S)} \\times \\text{Occurrence (O)} \\times \\text{Detection (D)}$  
        > Threshold for urgent mitigation: **RPN > 100**
        """
    )

    rows = query_db("SELECT * FROM fmea ORDER BY rpn DESC")
    if rows:
        st.subheader("FMEA Risk Matrix (Sorted by Highest RPN)")
        st.dataframe(
            rows,
            column_config={
                "fmea_id": "ID",
                "process_step": "Process Step",
                "failure_mode": "Failure Mode",
                "effect": "Potential Effect",
                "cause": "Root Cause",
                "severity": "S (1-10)",
                "occurrence": "O (1-10)",
                "detection": "D (1-10)",
                "rpn": st.column_config.NumberColumn("RPN (S×O×D)"),
                "mitigation": "Mitigation Strategy",
                "status": "Action Status",
            },
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("FMEA matrix will be populated during Phase 4 quality audit.")


if __name__ == "__main__" or True:
    render_fmea_page()
