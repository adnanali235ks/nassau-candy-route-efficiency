"""Reports: generate the PDF report, the Excel workbook and CSV exports for a selected scenario."""

import io
import zipfile
from datetime import datetime

import streamlit as st

from modules.optimization import HYPOTHETICAL_NOTICE
from modules.reporting import build_report_data
from ui import common
from ui.scenario_controls import scenario_form
from utils.report_generator import make_csv_exports, make_excel, make_pdf

ctx = common.load_page_data()
fdf, df, meta = ctx["fdf"], ctx["df"], ctx["meta"]

st.title("Reports")
st.caption("Generate a professional PDF report, a nine-sheet Excel workbook, and CSV exports. Reports cover the rows matching the "
           "sidebar filters and include the generation time and the scenario assumptions below.")
st.warning(HYPOTHETICAL_NOTICE)

st.markdown('<p class="block-title">1 · Scenario for the optimization sections</p>', unsafe_allow_html=True)
scenario = scenario_form("rep", "Report scenario", {"limit": True, "headroom": 20})
st.caption("Estimated costs are included only if you enter a rate, and are always labelled as estimates. "
           "Split order-line allocations appear as explicit rows in the Excel and CSV files.")

st.markdown('<p class="block-title">2 · Generate</p>', unsafe_allow_html=True)
if st.button("Generate reports", type="primary", key="rep_generate"):
    with st.spinner("Building the report…"):
        data = build_report_data(fdf, scenario, ctx["weights"], ctx["suitability"], meta=meta, total_rows=len(df),
                                 reference_distances=common.get_reference_distances(), generated_at=datetime.now())
        files = make_csv_exports(data)
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as z:
            for name, blob in files.items():
                z.writestr(name, blob)
        st.session_state["report_bundle"] = {
            "stamp": data["generated_at"], "scenario": scenario.name, "assumptions": data["scenario_text"],
            "status": data["scenario_result"]["status"], "message": data["scenario_result"]["message"],
            "pdf": make_pdf(data), "xlsx": make_excel(data), "zip": zip_buf.getvalue(), "csv": files,
            "rows": data["rows_in_report"], "recs": len(data["recommendations"]),
            "flags": len(data["anomaly_overview"])}

bundle = st.session_state.get("report_bundle")
if bundle:
    st.success(f"Reports generated {bundle['stamp']} for scenario **{bundle['scenario']}** "
               f"({bundle['rows']:,} rows, {bundle['recs']} recommendations, {bundle['flags']:,} anomaly flags).")
    st.caption("Assumptions used: " + bundle["assumptions"])
    if bundle["status"] != "OPTIMAL":
        st.error(f"This scenario has no valid plan ({bundle['status']}): {bundle['message']} "
                 "Optimization sections of the reports explain this instead of showing an allocation.")
    stamp = bundle["stamp"].replace(":", "").replace(" ", "_").replace("-", "")
    d1, d2, d3 = st.columns(3)
    d1.download_button("⬇️ PDF report", bundle["pdf"], file_name=f"route_analytics_report_{stamp}.pdf",
                       mime="application/pdf", key="dl_pdf")
    d2.download_button("⬇️ Excel workbook (9 sheets)", bundle["xlsx"], file_name=f"route_analytics_{stamp}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_xlsx")
    d3.download_button("⬇️ All CSV exports (ZIP)", bundle["zip"], file_name=f"route_analytics_csv_{stamp}.zip",
                       mime="application/zip", key="dl_zip")
    with st.expander("Individual CSV files"):
        for name, blob in bundle["csv"].items():
            st.download_button(f"⬇️ {name}", blob, file_name=name, mime="text/csv", key=f"dl_{name}")
else:
    st.info("Choose the scenario above, then press **Generate reports**.")
