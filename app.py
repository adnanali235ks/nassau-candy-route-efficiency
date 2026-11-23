"""
Nassau Candy Distributor — Supply Chain Route Analytics
Entry point / navigation shell.  Run with:  streamlit run app.py

This file only sets up the page and the left-hand menu. Each page lives in
views/, shared UI helpers in ui/common.py, and all calculations in
route_core.py and modules/ (no Streamlit code there).
"""

import streamlit as st

st.set_page_config(page_title="Nassau Candy | Route Analytics", page_icon="🚚", layout="wide")

from ui.environment import missing_packages, problem_message

# Fail early with a clear message if this Python lacks a required package (instead of an obscure error inside a page).
_missing = missing_packages()
if _missing:
    st.error("### Missing Python packages")
    st.markdown(f"```\n{problem_message(_missing)}\n```")
    st.stop()

st.sidebar.title("🚚 Nassau Candy")
st.sidebar.caption("Supply Chain Route Analytics")

pages = [
    st.Page("views/executive_overview.py", title="Executive Overview", icon="📊", default=True),
    st.Page("views/geographic_analysis.py", title="Geographic Analysis", icon="🗺️"),
    st.Page("views/route_performance.py", title="Route Performance", icon="🏆"),
    st.Page("views/optimization_center.py", title="Optimization Center", icon="🧮"),
    st.Page("views/scenario_simulator.py", title="Scenario Simulator", icon="🎛️"),
    st.Page("views/smart_recommendations.py", title="Smart Recommendations", icon="💡"),
    st.Page("views/anomaly_detection.py", title="Anomaly Detection", icon="🔍"),
    st.Page("views/reports.py", title="Reports", icon="📄"),
]
st.navigation(pages).run()
