"""
tqm/tqm_report.py — TQM Summary Report Generator.

Produces a multi-sheet Excel workbook that consolidates all TQM artefacts:
  Sheet 1 — Project Info & CTQ Tree
  Sheet 2 — SIPOC Summary
  Sheet 3 — Defect Checksheet Log
  Sheet 4 — FMEA Matrix
  Sheet 5 — PDCA Cycles
  Sheet 6 — Control Chart Data

Also generates a one-click Streamlit page for Review 3 / final submission.
"""

import os
import streamlit as st
import pandas as pd
from datetime import datetime
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from database.db import query_db
from modules.reports import EXPORTS_DIR

PURPLE = "7B2CBF"
DARK   = "1A0533"
WHITE  = "FFFFFF"
ACCENT = "00B4D8"

CTQ_TREE = [
    ("Billing Accuracy",     "CTQ-01", "Fee Discrepancy Rate",   "< 2%",   "FMEA ID-8, PDCA Cycle 1"),
    ("System Availability",  "CTQ-02", "App Uptime",             "> 99%",  "FMEA ID-9, PDCA Cycle 2"),
    ("Data Integrity",       "CTQ-03", "FK Violation Count",     "0",      "FMEA ID-7, PDCA Cycle 3"),
    ("Slot Accuracy",        "CTQ-04", "Wrong-Type Allocation",  "0/day",  "FMEA ID-5"),
    ("Vehicle Traceability", "CTQ-05", "Orphaned Record Rate",   "0%",     "FMEA ID-11"),
    ("Usability",            "CTQ-06", "Q03 Feature Completion", "5/5",    "Dark Mode, Themes, Dashboard, Search, Calendar"),
]

SIPOC_ROWS = [
    ("Supplier",  "Inputs",                "Process",                "Outputs",                   "Customer"),
    ("Driver",    "Plate, vehicle type",   "Vehicle Entry",          "Session record, slot update","Parking Manager"),
    ("Manager",   "Session ID",            "Vehicle Exit & Billing", "Receipt, slot freed",        "Driver / Finance"),
    ("Admin",     "Slot config",           "Slot Management",        "Available slot count",       "Operations Team"),
    ("Admin",     "Vehicle record",        "Vehicle Registry",       "Registered vehicle list",    "Entry Operators"),
    ("DB Layer",  "Defect observations",   "Checksheet Logging",     "Defect register",            "TQM Analyst"),
    ("TQM Analyst","FMEA risk table",      "Risk Prioritisation",    "Ranked RPN list",            "Engineering Lead"),
    ("TQM Team",  "Before/After metrics",  "PDCA Cycle Execution",   "Improvement evidence",       "Course Evaluator"),
]


def _header_row(ws, row_num: int, values: list, bg: str = PURPLE, fg: str = WHITE):
    """Write a styled header row into an openpyxl worksheet."""
    fill   = PatternFill("solid", fgColor=bg)
    font   = Font(bold=True, color=fg, size=11)
    align  = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for col, val in enumerate(values, start=1):
        cell = ws.cell(row=row_num, column=col, value=val)
        cell.fill, cell.font, cell.alignment = fill, font, align


def _auto_width(ws, max_w: int = 55):
    for col in ws.columns:
        max_len = max((len(str(c.value)) for c in col if c.value is not None), default=10)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 4, max_w)


def _section_title(ws, row: int, text: str, cols: int):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=cols)
    c = ws.cell(row=row, column=1, value=text)
    c.font = Font(bold=True, color=ACCENT, size=13)
    c.fill = PatternFill("solid", fgColor=DARK)
    c.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[row].height = 22


def generate_tqm_excel() -> str:
    """Build and save the full TQM summary workbook. Returns the file path."""
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    fname = os.path.join(
        EXPORTS_DIR,
        f"TQM_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    )

    with pd.ExcelWriter(fname, engine="openpyxl") as writer:
        wb = writer.book

        # ── Sheet 1: Project Info & CTQ Tree ─────────────────────────────────
        df_ctq = pd.DataFrame(CTQ_TREE,
                              columns=["Quality Dimension", "CTQ ID",
                                       "Measurable CTQ", "Target", "Evidence / Tool"])
        df_ctq.to_excel(writer, sheet_name="CTQ Tree", index=False)
        ws1 = writer.sheets["CTQ Tree"]
        _header_row(ws1, 1, list(df_ctq.columns))
        _auto_width(ws1)

        # ── Sheet 2: SIPOC ────────────────────────────────────────────────────
        df_sipoc = pd.DataFrame(SIPOC_ROWS[1:], columns=list(SIPOC_ROWS[0]))
        df_sipoc.to_excel(writer, sheet_name="SIPOC", index=False)
        ws2 = writer.sheets["SIPOC"]
        _header_row(ws2, 1, list(SIPOC_ROWS[0]))
        _auto_width(ws2)

        # ── Sheet 3: Defect Log ───────────────────────────────────────────────
        defects = query_db("SELECT * FROM defects ORDER BY date_found DESC")
        df_def  = pd.DataFrame(defects) if defects else pd.DataFrame()
        df_def.to_excel(writer, sheet_name="Defect Checksheet", index=False)
        ws3 = writer.sheets["Defect Checksheet"]
        if not df_def.empty:
            _header_row(ws3, 1, list(df_def.columns))
        _auto_width(ws3)

        # ── Sheet 4: FMEA ─────────────────────────────────────────────────────
        fmea  = query_db("SELECT * FROM fmea ORDER BY rpn DESC")
        df_fm = pd.DataFrame(fmea) if fmea else pd.DataFrame()
        df_fm.to_excel(writer, sheet_name="FMEA Matrix", index=False)
        ws4 = writer.sheets["FMEA Matrix"]
        if not df_fm.empty:
            _header_row(ws4, 1, list(df_fm.columns))
        _auto_width(ws4)

        # ── Sheet 5: PDCA ─────────────────────────────────────────────────────
        pdca  = query_db("SELECT * FROM pdca ORDER BY cycle_no ASC")
        df_pc = pd.DataFrame(pdca) if pdca else pd.DataFrame()
        df_pc.to_excel(writer, sheet_name="PDCA Cycles", index=False)
        ws5 = writer.sheets["PDCA Cycles"]
        if not df_pc.empty:
            _header_row(ws5, 1, list(df_pc.columns))
        _auto_width(ws5)

        # ── Sheet 6: Control Chart Data ───────────────────────────────────────
        rev = query_db(
            """SELECT date(exit_time) AS Day,
                      COUNT(*) AS Sessions,
                      ROUND(SUM(fee),2) AS Revenue
               FROM parking_sessions
               WHERE status='Completed' AND fee IS NOT NULL AND exit_time IS NOT NULL
               GROUP BY Day ORDER BY Day ASC"""
        )
        df_rev = pd.DataFrame(rev) if rev else pd.DataFrame()
        if not df_rev.empty:
            import numpy as np
            mu  = df_rev["Revenue"].mean()
            sig = df_rev["Revenue"].std(ddof=1)
            df_rev["X̄ (Mean)"] = round(mu, 2)
            df_rev["UCL (+3σ)"] = round(mu + 3 * sig, 2)
            df_rev["LCL (-3σ)"] = round(max(0, mu - 3 * sig), 2)
            df_rev["Status"] = df_rev["Revenue"].apply(
                lambda v: "OOC ⚠️" if (v > mu + 3 * sig or v < max(0, mu - 3 * sig)) else "OK ✓"
            )
        df_rev.to_excel(writer, sheet_name="Control Chart Data", index=False)
        ws6 = writer.sheets["Control Chart Data"]
        if not df_rev.empty:
            _header_row(ws6, 1, list(df_rev.columns))
        _auto_width(ws6)

    return fname


# ─── Renderer ────────────────────────────────────────────────────────────────

def render_tqm_report() -> None:
    """Render the TQM Summary Report page."""
    st.title("📄 TQM Project Summary Report")
    st.caption("One-click export of all TQM artefacts for Review 3 / final submission.")

    st.markdown(
        """
        ### 📦 Report Contents
        | Sheet | Contents |
        |:---|:---|
        | **CTQ Tree** | 6 Critical-to-Quality parameters with measurable targets |
        | **SIPOC** | Supplier → Input → Process → Output → Customer matrix |
        | **Defect Checksheet** | Full defect log from quality observations |
        | **FMEA Matrix** | 12 failure modes ranked by RPN (Severity × Occurrence × Detection) |
        | **PDCA Cycles** | 3 completed improvement cycles with before/after metrics |
        | **Control Chart Data** | Daily revenue with X̄, UCL, LCL and in/out-of-control status |

        ---
        """
    )

    # Project Banner
    st.info(
        "**BBAT104 — Fundamentals of Total Quality Management**  \n"
        "🎓 **Student**: Himanshu Bhardwaj &nbsp;|&nbsp; **Roll No**: 2410301028 &nbsp;|&nbsp; "
        "**Section**: B.Tech CSE Sec A  \n"
        "🏛️ **System**: Smart Parking Management System  \n"
        "🎯 **Quality Goal**: Q03 — Improve Usability (Dark Mode, Custom Themes, Dashboard, Search, Calendar)"
    )

    # Quick Stats
    fmea_count = len(query_db("SELECT 1 FROM fmea") or [])
    pdca_count = len(query_db("SELECT 1 FROM pdca") or [])
    def_count  = len(query_db("SELECT 1 FROM defects") or [])
    sess_count = len(query_db("SELECT 1 FROM parking_sessions WHERE status='Completed'") or [])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("FMEA Entries",       fmea_count)
    c2.metric("PDCA Cycles",        pdca_count)
    c3.metric("Defects Logged",     def_count)
    c4.metric("Completed Sessions", sess_count)

    st.markdown("---")

    if st.button("🏗️ Generate Full TQM Report (Excel)", use_container_width=True, type="primary"):
        with st.spinner("Compiling all TQM artefacts into Excel workbook..."):
            try:
                fpath = generate_tqm_excel()
                with open(fpath, "rb") as f:
                    st.download_button(
                        "⬇️ Download TQM_Report.xlsx",
                        data=f.read(),
                        file_name=os.path.basename(fpath),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                st.success(f"Report generated: `{os.path.basename(fpath)}`")
                st.balloons()
            except Exception as e:
                st.error(f"Error generating report: {e}")
