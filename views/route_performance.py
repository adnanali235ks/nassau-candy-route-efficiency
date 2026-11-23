"""Route Performance: route leaderboard, ship-mode comparison and state drill-down.

(These are the three analysis tabs of the original single-page dashboard, kept
intact and moved here. The original geographic tab is now on Geographic Analysis.)
"""

import plotly.express as px
import streamlit as st

from route_core import ship_mode_summary
from ui import common
from ui.common import GOOD, RISK, ACCENT

ctx = common.load_page_data()
fdf, weights, suitability = ctx["fdf"], ctx["weights"], ctx["suitability"]

st.title("Route Performance")
st.caption("How efficient is each factory-to-destination route, and how does ship mode differ? "
           "Efficiency is a **calculated score** built partly on **assumptions** (see Scoring settings).")
common.data_quality_banner()

tab_routes, tab_modes, tab_drill = st.tabs(["🏆 Route efficiency", "📦 Ship mode comparison", "🔎 State drill-down"])

# ---------------------------------------------------------------------------
with tab_routes:
    st.markdown('<p class="block-title">Route Performance Leaderboard</p>', unsafe_allow_html=True)
    st.caption(f"Route Efficiency Score = {weights['distance']:.0%} Distance Score + {weights['ship_mode']:.0%} "
               "Ship-Mode Score (0–100, higher = more efficient). Only routes with a known distance are scored.")
    level = st.radio("Route granularity", ["Region", "State/Province"], horizontal=True)
    rs = common.scored_routes(fdf, level, weights, suitability)

    colA, colB = st.columns(2)
    with colA:
        st.markdown("**Top 10 most efficient routes**")
        fig = px.bar(rs.head(10).sort_values("Route Efficiency Proxy Score"),
                     x="Route Efficiency Proxy Score", y="Route", orientation="h",
                     color_discrete_sequence=[GOOD], labels={"Route Efficiency Proxy Score": "Route Efficiency Score"})
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, width="stretch")
    with colB:
        st.markdown("**Bottom 10 least efficient routes**")
        fig2 = px.bar(rs.tail(10).sort_values("Route Efficiency Proxy Score"),
                      x="Route Efficiency Proxy Score", y="Route", orientation="h",
                      color_discrete_sequence=[RISK], labels={"Route Efficiency Proxy Score": "Route Efficiency Score"})
        fig2.update_layout(margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig2, width="stretch")

    st.markdown('<p class="block-title">Full Route Table (scored routes only)</p>', unsafe_allow_html=True)
    st.caption("Distance Points + Ship-Mode Points = Route Efficiency Score, so each score can be explained.")
    common.show_table(
        rs[["Route", "Factory", "Shipments", "Sales", "Avg Distance (mi)", "Distance Points",
            "Ship-Mode Points", "Route Efficiency Proxy Score"]].round(2)
        .rename(columns={"Route Efficiency Proxy Score": "Route Efficiency Score"}),
        max_height=820)                      # Region level has 20 routes: show them all without an inner scroll bar

    unscored = common.scored_routes(fdf, level, weights, suitability, include_unscored=True)
    unscored = unscored[unscored["Route Efficiency Proxy Score"].isna()][["Route", "Factory", "Shipments", "Sales"]]
    if not unscored.empty:
        with st.expander(f"Unscored routes ({len(unscored)}) — excluded from rankings"):
            st.caption("These routes have no known distance, so no score can be calculated. "
                       "They are not ranked and are not treated as zero.")
            common.show_table(unscored.round(2))

# ---------------------------------------------------------------------------
with tab_modes:
    st.markdown('<p class="block-title">Ship Mode Comparison</p>', unsafe_allow_html=True)
    sm = ship_mode_summary(fdf)
    colA, colB = st.columns(2)
    with colA:
        st.caption("Share of orders by ship mode (distinct Order IDs; each order has exactly one mode).")
        fig = px.pie(sm, names="Ship Mode", values="Shipments", hole=0.45,
                     color_discrete_sequence=px.colors.sequential.Purples_r)
        fig.update_traces(textinfo="percent+label")
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
        st.plotly_chart(fig, width="stretch")
    with colB:
        fig2 = px.bar(sm, x="Ship Mode", y="Avg Distance (mi)", color_discrete_sequence=[ACCENT])
        fig2.update_layout(margin=dict(l=10, r=10, t=30, b=10), title="Avg. distance by ship mode (valid metric)")
        st.plotly_chart(fig2, width="stretch")

    st.markdown("**Cost-time tradeoff (descriptive only — time axis is unreliable, shown for transparency)**")
    fig3 = px.bar(sm, x="Ship Mode", y="Raw Avg Lead Time (days) [UNRELIABLE]", color_discrete_sequence=[RISK])
    fig3.update_layout(margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig3, width="stretch")
    st.caption("All four bars are nearly identical — this is the data quality issue, not a real finding. "
               "A working shipment log would show Same Day ≈ 0–1 days and a clear staircase up to Standard Class.")
    common.show_table(sm.round(2))

# ---------------------------------------------------------------------------
with tab_drill:
    st.markdown('<p class="block-title">State / Province Drill-Down</p>', unsafe_allow_html=True)
    chosen_state = st.selectbox("Choose a state or province", options=sorted(fdf["State/Province"].unique()))
    sdf = fdf[fdf["State/Province"] == chosen_state]

    c1, c2, c3 = st.columns(3)
    c1.metric("Orders", f"{sdf['Order ID'].nunique():,}")
    c2.metric("Total Sales", f"${sdf['Sales'].sum():,.0f}")
    c3.metric("Avg. Distance", f"{sdf['Route Distance (mi)'].mean():,.0f} mi")

    colA, colB = st.columns(2)
    with colA:
        fig = px.pie(sdf, names="Factory", values="Sales", hole=0.4, title="Sales by Supplying Factory")
        fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, width="stretch")
    with colB:
        # Count distinct orders per ship mode (a numeric value; Order ID itself is text).
        mode_counts = sdf.groupby("Ship Mode")["Order ID"].nunique().reset_index(name="Orders")
        fig2 = px.pie(mode_counts, names="Ship Mode", values="Orders", hole=0.4,
                      title="Orders by Ship Mode (distinct Order IDs)")
        fig2.update_layout(margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig2, width="stretch")

    st.markdown("**Order-line records for this state/province**")
    common.show_table(
        sdf[["Order ID", "Order Date", "Ship Mode", "Factory", "Product Name", "Sales", "Route Distance (mi)"]]
        .sort_values("Order Date", ascending=False).head(200))
    st.caption("Showing up to 200 most recent matching order lines. Order-level Ship Date is intentionally "
               "omitted given the data quality finding above.")
