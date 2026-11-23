"""Anomaly Detection: IQR route outliers, duplicates, missing geography, sales/profit and factory-product patterns.

Flags only. No record is deleted or changed; every flag shows the reason and the supporting values.
"""

import streamlit as st

from modules import anomaly_detection as ad
from ui import common

ctx = common.load_page_data()
fdf = ctx["fdf"]

st.title("Anomaly Detection")
st.info("**Flags are prompts for review, not errors.** Simple statistics only (IQR and fixed thresholds). "
        "**No record is ever deleted or modified**; each flag shows why it was raised, and you can open the underlying records.")

with st.expander("How the IQR rule works"):
    st.markdown("""
Sort the values. **Q1** is the value 25% of the way up and **Q3** is 75% of the way up; **IQR = Q3 − Q1**.
The *fences* are **Q1 − 1.5 × IQR** and **Q3 + 1.5 × IQR**. A value outside the fences is *unusual* (not necessarily wrong).
Example: distances 300, 800, 1,500, 2,200, 5,000 → Q1 800, Q3 2,200, IQR 1,400, upper fence 4,300 → 5,000 is flagged.
""")

r = ad.detect_all(fdf)
st.markdown('<p class="block-title">Summary</p>', unsafe_allow_html=True)
common.show_table(r["summary"])

tabs = st.tabs(["📏 Route distance (IQR)", "🧾 Duplicate lines", "📍 Missing geography", "💲 Sales & profit",
                "🏭 Factory / product pattern"])


def show(table, name, key):
    """Show a flagged table (Reason placed next to the identifying columns) with its reasons written out, and a CSV download."""
    if table is None or len(table) == 0:
        st.success("Nothing flagged.")
        return
    columns = list(table.columns)
    if "Reason" in columns:                                   # keep the explanation in view instead of at the far right
        rest = [c for c in columns if c not in ("Anomaly Type", "Reason")]
        columns = rest[:2] + [c for c in ("Anomaly Type", "Reason") if c in columns] + rest[2:]
        reasons = table["Reason"].astype(str)
        first = table[rest[0]].astype(str)
        shown = min(len(table), 6)
        st.markdown(f"**Why these were flagged** ({'all' if len(table) <= shown else f'first {shown} of {len(table):,}'}):")
        for subject, why in list(zip(first, reasons))[:shown]:
            st.markdown(f"- **{subject}:** {why}")
    common.show_table(table[columns].round(2))
    st.download_button("⬇️ Download these flagged records (CSV)", table.to_csv(index=False).encode("utf-8"),
                       file_name=name, mime="text/csv", key=key)


with tabs[0]:
    b = r["route_bounds"]
    st.caption(f"Routes assessed: {b['routes_assessed']} (factory → state/province). Q1 {b['q1']:,.0f} mi · Q3 {b['q3']:,.0f} mi · "
               f"IQR {b['iqr']:,.0f} mi · fences [{b['lower_fence']:,.0f}, {b['upper_fence']:,.0f}] mi. Routes with unknown "
               "distance cannot be assessed.")
    show(r["route_outliers"], "route_distance_outliers.csv", "dl_routes")
    if len(r["route_outliers"]):
        route = st.selectbox("Open the underlying order lines of a flagged route", r["route_outliers"]["Route"], key="an_route")
        lines = ad.records_for_route(fdf, route)
        st.caption(f"{len(lines):,} order line(s) on this route (unchanged records).")
        common.show_table(lines[["Row ID", "Order ID", "Product Name", "Customer ID", "State/Province", "Units", "Sales",
                            "Route Distance (mi)"]])

with tabs[1]:
    d = r["duplicates"]
    if len(d):
        exact = int(d["Identical Values"].sum())
        st.caption(f"{len(d):,} lines share an Order ID + Product ID with another line; **{exact:,} have identical values** "
                   "(likely exact duplicates) and the rest differ (possibly legitimate extra lines). Nothing is removed.")
    show(d, "duplicate_order_lines.csv", "dl_dup")

with tabs[2]:
    show(r["missing_geography"], "missing_geography.csv", "dl_geo")

with tabs[3]:
    st.caption("Unit price and gross margin are compared within each product (IQR; any deviation counts when most lines share "
               "one value), and Gross Profit + Cost is checked against Sales.")
    show(r["sales_profit"], "sales_profit_anomalies.csv", "dl_sales")
    const = r["constant_prices"]
    if len(const):
        st.markdown("**Observation:** these products have a single constant unit price and margin on every line, so price and "
                    "margin outliers cannot occur.")
        common.show_table(const)

with tabs[4]:
    st.markdown("**Product ID prefix vs Division**")
    show(r["factory_product_lines"], "product_division_mismatch.csv", "dl_fp")
    st.markdown("**Very-low-volume factories and products** (below 1% / 0.5% of order lines)")
    show(r["factory_product_summary"], "low_volume_factories_products.csv", "dl_low")
