"""
Nassau Candy Distributor — Factory-to-Customer Shipping Route Efficiency Dashboard
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from route_core import (
    load_and_clean, route_summary, ship_mode_summary, geo_bottleneck_summary,
    factory_route_footprint, FACTORIES
)

st.set_page_config(page_title="Nassau Candy | Route Efficiency", page_icon="🚚", layout="wide")

PRIMARY, ACCENT, GOOD, RISK, NEUTRAL = "#5B2C6F", "#E67E22", "#2E8B57", "#C0392B", "#7f8c8d"

st.markdown(f"""
<style>
.metric-card {{ background:#faf7fc; border:1px solid #e8dff0; border-radius:10px; padding:14px 18px; text-align:center;}}
.metric-card h3 {{ margin:0; font-size:13px; color:{NEUTRAL}; font-weight:600; text-transform:uppercase; letter-spacing:.03em;}}
.metric-card p {{ margin:4px 0 0 0; font-size:26px; font-weight:700; color:{PRIMARY};}}
.block-title {{ font-size:22px; font-weight:700; color:{PRIMARY}; margin-bottom:0px;}}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def get_data():
    return load_and_clean()


df, meta = get_data()

# ---------------------------------------------------------------------------
# SIDEBAR FILTERS
# ---------------------------------------------------------------------------
st.sidebar.title("🚚 Nassau Candy")
st.sidebar.caption("Factory-to-Customer Shipping Route Efficiency")

min_date, max_date = df["Order Date"].min(), df["Order Date"].max()
date_range = st.sidebar.date_input("Order date range", value=(min_date, max_date),
                                    min_value=min_date, max_value=max_date)

regions = st.sidebar.multiselect("Region", options=sorted(df["Region"].unique()),
                                  default=sorted(df["Region"].unique()))
states = st.sidebar.multiselect("State/Province (optional)", options=sorted(df["State/Province"].unique()))
ship_modes = st.sidebar.multiselect("Ship Mode", options=sorted(df["Ship Mode"].unique()),
                                     default=sorted(df["Ship Mode"].unique()))
dist_threshold = st.sidebar.slider("Minimum route distance (mi)", 0, 2000, 0, step=50)

st.sidebar.markdown("---")
st.sidebar.caption(f"Rows loaded: **{meta['rows_after']:,}**")

mask = (df["Region"].isin(regions)) & (df["Ship Mode"].isin(ship_modes)) & (df["Route Distance (mi)"] >= dist_threshold)
if states:
    mask &= df["State/Province"].isin(states)
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    mask &= (df["Order Date"] >= start) & (df["Order Date"] <= end)

fdf = df[mask]
if fdf.empty:
    st.warning("No shipments match the current filters.")
    st.stop()

# ---------------------------------------------------------------------------
# DATA QUALITY BANNER (always visible)
# ---------------------------------------------------------------------------
st.warning(
    "⚠️ **Data quality finding:** the `Ship Date` field in this dataset does not track `Order Date` "
    "the way a real shipment record should — computed lead time averages ~1,300 days and shows "
    "**no difference between Same Day and Standard Class shipping**, which is impossible for genuine "
    "fulfillment data. We therefore do **not** report lead time, delay frequency, or a time-based "
    "efficiency score as real findings anywhere in this dashboard. Instead, the **Route Efficiency "
    "Proxy Score** below is built only from validated fields: shipping distance and ship-mode mix. "
    "We recommend the data engineering team audit the ETL pipeline that populates `Ship Date` before "
    "it is used for any SLA or delivery-performance reporting."
)

# ---------------------------------------------------------------------------
# HEADER KPIs
# ---------------------------------------------------------------------------
st.title("Factory-to-Customer Shipping Route Efficiency")
st.caption("Nassau Candy Distributor — interactive logistics analytics")

total_shipments = fdf["Order ID"].nunique()
avg_dist = fdf["Route Distance (mi)"].mean()
n_states = fdf["State/Province"].nunique()
n_routes = fdf["Route (Factory-State)"].nunique()

c1, c2, c3, c4 = st.columns(4)
for col, label, val in zip([c1, c2, c3, c4],
    ["Shipments", "Avg. Route Distance", "States Served", "Active Routes"],
    [f"{total_shipments:,}", f"{avg_dist:,.0f} mi", f"{n_states}", f"{n_routes}"]):
    col.markdown(f'<div class="metric-card"><h3>{label}</h3><p>{val}</p></div>', unsafe_allow_html=True)

st.markdown("")
tabs = st.tabs(["🏆 Route Efficiency Overview", "🗺️ Geographic Shipping Map",
                "📦 Ship Mode Comparison", "🔎 Route Drill-Down"])

# ---------------------------------------------------------------------------
# TAB 1 — ROUTE EFFICIENCY OVERVIEW
# ---------------------------------------------------------------------------
with tabs[0]:
    st.markdown('<p class="block-title">Route Performance Leaderboard</p>', unsafe_allow_html=True)
    st.caption("Route Efficiency Proxy Score = 60% distance score + 40% ship-mode speed-weight. Higher = more efficient.")

    level = st.radio("Route granularity", ["Region", "State/Province"], horizontal=True)
    rs = route_summary(fdf, level)

    colA, colB = st.columns(2)
    with colA:
        st.markdown("**Top 10 most efficient routes**")
        fig = px.bar(rs.head(10).sort_values("Route Efficiency Proxy Score"),
                      x="Route Efficiency Proxy Score", y="Route", orientation="h",
                      color_discrete_sequence=[GOOD])
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    with colB:
        st.markdown("**Bottom 10 least efficient routes**")
        fig2 = px.bar(rs.tail(10).sort_values("Route Efficiency Proxy Score"),
                       x="Route Efficiency Proxy Score", y="Route", orientation="h",
                       color_discrete_sequence=[RISK])
        fig2.update_layout(margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<p class="block-title">Full Route Table</p>', unsafe_allow_html=True)
    st.dataframe(
        rs[["Route", "Factory", "Shipments", "Sales", "Avg Distance (mi)", "Route Efficiency Proxy Score"]]
        .round(2), use_container_width=True, hide_index=True,
    )

# ---------------------------------------------------------------------------
# TAB 2 — GEOGRAPHIC SHIPPING MAP
# ---------------------------------------------------------------------------
with tabs[1]:
    st.markdown('<p class="block-title">Shipment Density & Bottleneck Risk by State</p>', unsafe_allow_html=True)
    geo = geo_bottleneck_summary(fdf)

    # State abbreviation map for choropleth
    state_abbrev = {
        "Alabama": "AL","Alaska": "AK","Arizona": "AZ","Arkansas": "AR","California": "CA",
        "Colorado": "CO","Connecticut": "CT","Delaware": "DE","District of Columbia": "DC",
        "Florida": "FL","Georgia": "GA","Hawaii": "HI","Idaho": "ID","Illinois": "IL",
        "Indiana": "IN","Iowa": "IA","Kansas": "KS","Kentucky": "KY","Louisiana": "LA",
        "Maine": "ME","Maryland": "MD","Massachusetts": "MA","Michigan": "MI","Minnesota": "MN",
        "Mississippi": "MS","Missouri": "MO","Montana": "MT","Nebraska": "NE","Nevada": "NV",
        "New Hampshire": "NH","New Jersey": "NJ","New Mexico": "NM","New York": "NY",
        "North Carolina": "NC","North Dakota": "ND","Ohio": "OH","Oklahoma": "OK","Oregon": "OR",
        "Pennsylvania": "PA","Rhode Island": "RI","South Carolina": "SC","South Dakota": "SD",
        "Tennessee": "TN","Texas": "TX","Utah": "UT","Vermont": "VT","Virginia": "VA",
        "Washington": "WA","West Virginia": "WV","Wisconsin": "WI","Wyoming": "WY",
    }
    geo["abbrev"] = geo["State/Province"].map(state_abbrev)
    geo_map = geo.dropna(subset=["abbrev"])

    fig = px.choropleth(geo_map, locations="abbrev", locationmode="USA-states",
                         color="Shipments", scope="usa", color_continuous_scale="Purples",
                         hover_data={"State/Province": True, "Avg Distance (mi)": ":.0f", "Sales": ":.0f"})
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<p class="block-title">Factory Locations & Reach</p>', unsafe_allow_html=True)
    fac_df = pd.DataFrame([{"Factory": k, "lat": v[0], "lon": v[1]} for k, v in FACTORIES.items()])
    fig2 = px.scatter_geo(fac_df, lat="lat", lon="lon", text="Factory", scope="usa",
                           color_discrete_sequence=[ACCENT])
    fig2.update_traces(marker=dict(size=16))
    fig2.update_layout(margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig2, use_container_width=True)

    bottleneck_states = geo[geo["Bottleneck Risk"] == "High Volume + Long Distance"]
    st.error(
        f"⚠️ **{len(bottleneck_states)} states flagged as High Volume + Long Distance** "
        f"(above-median shipment volume AND above-median shipping distance) — these are the "
        f"geographic bottleneck candidates worth prioritizing for regional hub or carrier "
        f"optimization: {', '.join(bottleneck_states['State/Province'].head(8))}{'...' if len(bottleneck_states) > 8 else ''}"
    )

    st.dataframe(geo[["Region", "State/Province", "Shipments", "Sales", "Avg Distance (mi)", "Bottleneck Risk"]]
                 .round(2), use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# TAB 3 — SHIP MODE COMPARISON
# ---------------------------------------------------------------------------
with tabs[2]:
    st.markdown('<p class="block-title">Ship Mode Comparison</p>', unsafe_allow_html=True)
    sm = ship_mode_summary(fdf)

    colA, colB = st.columns(2)
    with colA:
        fig = px.pie(sm, names="Ship Mode", values="Shipments", hole=0.45,
                      color_discrete_sequence=px.colors.sequential.Purples_r)
        fig.update_traces(textinfo="percent+label")
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with colB:
        fig2 = px.bar(sm, x="Ship Mode", y="Avg Distance (mi)", color_discrete_sequence=[ACCENT])
        fig2.update_layout(margin=dict(l=10, r=10, t=10, b=10), title="Avg. Distance by Ship Mode (valid metric)")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("**Cost-time tradeoff (descriptive only — time axis is unreliable, shown for transparency)**")
    fig3 = px.bar(sm, x="Ship Mode", y="Raw Avg Lead Time (days) [UNRELIABLE]", color_discrete_sequence=[RISK])
    fig3.update_layout(margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("Notice all four bars are nearly identical — this is the data quality issue, not a real finding. "
               "A working shipment log would show Same Day ≈ 0-1 days and a clear staircase up to Standard Class.")

    st.dataframe(sm.round(2), use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# TAB 4 — ROUTE DRILL-DOWN
# ---------------------------------------------------------------------------
with tabs[3]:
    st.markdown('<p class="block-title">State-Level Drill-Down</p>', unsafe_allow_html=True)
    chosen_state = st.selectbox("Choose a state", options=sorted(fdf["State/Province"].unique()))
    sdf = fdf[fdf["State/Province"] == chosen_state]

    c1, c2, c3 = st.columns(3)
    c1.metric("Shipments", f"{sdf['Order ID'].nunique():,}")
    c2.metric("Total Sales", f"${sdf['Sales'].sum():,.0f}")
    c3.metric("Avg. Distance", f"{sdf['Route Distance (mi)'].mean():,.0f} mi")

    colA, colB = st.columns(2)
    with colA:
        fig = px.pie(sdf, names="Factory", values="Sales", hole=0.4, title="Sales by Supplying Factory")
        fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)
    with colB:
        fig2 = px.pie(sdf, names="Ship Mode", values="Order ID", hole=0.4, title="Shipments by Ship Mode")
        fig2.update_layout(margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("**Order-level shipment records for this state**")
    st.dataframe(
        sdf[["Order ID", "Order Date", "Ship Mode", "Factory", "Product Name", "Sales", "Route Distance (mi)"]]
        .sort_values("Order Date", ascending=False).head(200),
        use_container_width=True, hide_index=True,
    )
    st.caption("Showing up to 200 most recent matching orders. Order-level Ship Date is intentionally omitted "
               "here given the data quality finding above.")

st.markdown("---")
st.caption("Built for Nassau Candy Distributor · Factory-to-Customer Shipping Route Efficiency Analysis")
