"""Executive Overview: headline KPIs, summary charts, best/worst routes and insights."""

import plotly.express as px
import streamlit as st

from modules.route_analysis import (executive_kpis, ship_mode_distribution, factory_sales,
                                    best_and_worst_routes, business_insights, SCORE_COL)
from ui import common
from ui.common import GOOD, RISK, PRIMARY

ctx = common.load_page_data()
fdf, weights, suitability = ctx["fdf"], ctx["weights"], ctx["suitability"]

st.title("Executive Overview")
st.caption("A one-page summary of the network. Small labels under each number say where it comes from: "
           "*dataset* (read from the CSV), *calculated* (derived by our code) or *assumption*.")
common.data_quality_banner()

# Region-level routes: ~20 routes that all have meaningful volume (state-level routes include many tiny ones).
routes = common.scored_routes(fdf, "Region", weights, suitability, include_unscored=True)
kpi = executive_kpis(fdf, routes)

# --- KPI row ---------------------------------------------------------------
cols = st.columns(6)
common.metric_card(cols[0], "Orders", f"{kpi['total_orders']:,}", "dataset · distinct Order IDs")
common.metric_card(cols[1], "Total sales", f"${kpi['total_sales']:,.0f}", "dataset")
common.metric_card(cols[2], "Factories", f"{kpi['factories']}", "assumption · product→factory map")
common.metric_card(cols[3], "Customers", f"{kpi['customers']:,}", "dataset · distinct Customer IDs")
common.metric_card(cols[4], "Avg distance", f"{kpi['avg_distance_mi']:,.0f} mi", "calculated · straight-line, per order")
eff = kpi["overall_efficiency"]
common.metric_card(cols[5], "Route efficiency", "n/a" if eff != eff else f"{eff:.1f} / 100",
                   "calculated · order-weighted score")
common.provisional_note()
if kpi["unscored_routes"]:
    st.caption(f"{kpi['unscored_routes']} route(s) have no known distance and are excluded from the efficiency figure.")

# --- Charts ----------------------------------------------------------------
st.markdown("")
left, right = st.columns(2)
with left:
    st.markdown('<p class="block-title">Ship-mode distribution</p>', unsafe_allow_html=True)
    st.caption("Share of orders by ship mode (dataset).")
    dist = ship_mode_distribution(fdf)
    fig = px.pie(dist, names="Ship Mode", values="Orders", hole=0.5,
                 color_discrete_sequence=px.colors.sequential.Purples_r)
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
    st.plotly_chart(fig, width="stretch")
with right:
    st.markdown('<p class="block-title">Sales by factory</p>', unsafe_allow_html=True)
    st.caption("Total sales of the products each factory makes (dataset, via the product→factory map).")
    fs = factory_sales(fdf)
    fig = px.bar(fs.sort_values("Sales"), x="Sales", y="Factory", orientation="h",
                 color_discrete_sequence=[PRIMARY], hover_data={"Orders": True, "Avg Distance (mi)": ":.0f"})
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, width="stretch")

# --- Best / worst routes ---------------------------------------------------
st.markdown('<p class="block-title">Best and worst scored routes</p>', unsafe_allow_html=True)
st.caption(f"Region-level routes ranked by Route Efficiency Score ({weights['distance']:.0%} distance + "
           f"{weights['ship_mode']:.0%} ship-mode; calculated, partly assumption-based). Unscored routes are never ranked.")
best, worst = best_and_worst_routes(routes, n=5)
c1, c2 = st.columns(2)
for col, table, title, color in ((c1, best, "Top 5", GOOD), (c2, worst, "Bottom 5", RISK)):
    with col:
        st.markdown(f"**{title}**")
        fig = px.bar(table.sort_values(SCORE_COL), x=SCORE_COL, y="Route", orientation="h",
                     color_discrete_sequence=[color], range_x=[0, 100],
                     hover_data={"Shipments": True, "Avg Distance (mi)": ":.0f"})
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Route Efficiency Score")
        st.plotly_chart(fig, width="stretch")

# --- Insights --------------------------------------------------------------
st.markdown('<p class="block-title">Business insights</p>', unsafe_allow_html=True)
st.caption("Rule-based observations computed from the current filter. They describe the data; "
           "they are not operational recommendations.")
for item in business_insights(fdf, routes):
    st.markdown(f"**{item['title']}.** {item['text']}")
    st.caption(f"Why: {item['why']}")
