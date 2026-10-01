"""
ui_pages/reports_page.py — Excel Export and Reporting interface.

Provides styled .xlsx downloads for parking sessions, daily revenue audits,
and the vehicle registry using pandas and openpyxl (FR-19).
"""

import os
import streamlit as st
from modules.reports import export_sessions, export_revenue, export_vehicles


def render_reports_page():
    """Render the report generation and download interface."""
    st.title("📥 Operational Reports & Data Export")
    st.caption("Generate formatted Excel (.xlsx) workbooks with styled headers and auto-column fitting.")

    st.info("💡 All generated spreadsheets comply with TQM reporting standards and include formatted column widths and header styling.")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.subheader("📋 Parking Sessions")
        st.write("Complete audit log of all parking entries, exits, durations, and fee charges.")
        if st.button("Generate Sessions Excel", use_container_width=True):
            with st.spinner("Generating workbook..."):
                fpath = export_sessions()
                with open(fpath, "rb") as f:
                    st.download_button(
                        label="⬇️ Download sessions.xlsx",
                        data=f.read(),
                        file_name=os.path.basename(fpath),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                st.success("Report ready!")

    with c2:
        st.subheader("💰 Revenue Summary")
        st.write("Day-by-day aggregate collection, completed sessions count, and financial turnover.")
        if st.button("Generate Revenue Excel", use_container_width=True):
            with st.spinner("Generating workbook..."):
                fpath = export_revenue()
                with open(fpath, "rb") as f:
                    st.download_button(
                        label="⬇️ Download revenue.xlsx",
                        data=f.read(),
                        file_name=os.path.basename(fpath),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                st.success("Report ready!")

    with c3:
        st.subheader("🚗 Vehicle Register")
        st.write("Full directory of registered vehicles, owners, contact details, and categories.")
        if st.button("Generate Vehicles Excel", use_container_width=True):
            with st.spinner("Generating workbook..."):
                fpath = export_vehicles()
                with open(fpath, "rb") as f:
                    st.download_button(
                        label="⬇️ Download vehicles.xlsx",
                        data=f.read(),
                        file_name=os.path.basename(fpath),
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                st.success("Report ready!")


if __name__ == "__main__" or True:
    render_reports_page()
