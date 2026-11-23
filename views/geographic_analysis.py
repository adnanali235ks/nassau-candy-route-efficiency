"""Geographic Analysis: factory-to-destination map, distance comparison, shipment density."""

import plotly.express as px
import streamlit as st

from modules.route_analysis import route_map_table, long_distance_threshold, flag_long_routes
from route_core import US_STATE_ABBREVIATIONS, geo_bottleneck_summary
from ui import common
from ui.charts import build_route_map
from ui.common import ACCENT, PRIMARY

ctx = common.load_page_data()
fdf, weights, suitability = ctx["fdf"], ctx["weights"], ctx["suitability"]

st.title("Geographic Analysis")
st.caption("Where does each factory ship, and which routes are unusually long?")
st.info(
    "**How to read the map.** Each line joins a factory to the **centroid (geographic centre) of a state or "
    "province** — not to any customer's real location. Distances are **straight-line (great-circle) miles**, "
    "not road distance; real driving routes are longer. Canadian province centroids are **provisional**."
)

# State/province-level routes (one line per factory -> destination) with map coordinates.
routes = common.scored_routes(fdf, "State/Province", weights, suitability, include_unscored=True)
table = route_map_table(routes)

tab_map, tab_dist, tab_density = st.tabs(["🗺️ Route map", "📏 Distance comparison", "📍 Shipment density & bottlenecks"])

# ---------------------------------------------------------------------------
with tab_map:
    c1, c2, c3 = st.columns([2, 1, 1])
    factories = c1.multiselect("Factories", sorted(table["Factory"].unique()),
                               default=sorted(table["Factory"].unique()), key="geo_factories")
    # Default 100 so Canadian routes (low volume, ranked ~58th and below) are visible without touching the slider.
    top_n = c2.slider("Routes shown (top N by orders)", 5, max(10, len(table)), min(100, len(table)), key="geo_topn")
    percentile = c3.slider("Long-distance = top …% of routes", 5, 50, 25, step=5, key="geo_pct",
                           help="A route is 'long-distance' if its average distance is above this percentile of "
                                "all known route distances (25 → above the 75th percentile).")

    threshold = long_distance_threshold(table["Avg Distance (mi)"], 100 - percentile)
    table = flag_long_routes(table, threshold)
    only_long = st.checkbox(f"Show only long-distance routes (> {threshold:,.0f} mi)", key="geo_only_long")

    view = table[table["Factory"].isin(factories)]
    if only_long:
        view = view[view["Long Distance"]]
    view = view.sort_values("Shipments", ascending=False).head(top_n)
    undrawable = int(view[["Dest Lat", "Factory Lat"]].isna().any(axis=1).sum())

    if view.empty:
        st.warning("No routes match these map settings.")
    else:
        st.plotly_chart(build_route_map(view), width="stretch", theme=None)
    st.caption(f"Showing {len(view)} route(s). Long-distance threshold: **{threshold:,.0f} mi** "
               f"(calculated from the data; a display setting, not a business limit)."
               + (f" {undrawable} route(s) lack coordinates and are not drawn." if undrawable else ""))

# ---------------------------------------------------------------------------
with tab_dist:
    st.markdown('<p class="block-title">Longest routes</p>', unsafe_allow_html=True)
    st.caption("Average straight-line distance per factory → state/province route (calculated). "
               "Routes with unknown distance are excluded here and listed below if any exist.")
    known = table.dropna(subset=["Avg Distance (mi)"]).sort_values("Avg Distance (mi)", ascending=False)
    top = known.head(15).sort_values("Avg Distance (mi)")
    fig = px.bar(top, x="Avg Distance (mi)", y="Route", orientation="h", color="Long Distance",
                 color_discrete_map={True: ACCENT, False: PRIMARY}, hover_data={"Shipments": True})
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), legend_title_text="Long-distance")
    st.plotly_chart(fig, width="stretch")

    st.markdown('<p class="block-title">Distance by destination</p>', unsafe_allow_html=True)
    common.show_table(known[["Route", "Factory", "State/Province", "Shipments", "Avg Distance (mi)", "Long Distance"]]
                 .round(1))
    missing = table[table["Avg Distance (mi)"].isna()]
    if not missing.empty:
        st.warning(f"{len(missing)} route(s) have unknown distance (location not in the reference table): "
                   + ", ".join(missing["Route"].head(8)))

# ---------------------------------------------------------------------------
with tab_density:
    st.markdown('<p class="block-title">Shipment Density & Bottleneck Risk</p>', unsafe_allow_html=True)
    geo = geo_bottleneck_summary(fdf)

    geo["abbrev"] = geo["State/Province"].map(US_STATE_ABBREVIATIONS)
    geo_map = geo.dropna(subset=["abbrev"])
    n_non_us = len(geo) - len(geo_map)
    if n_non_us:
        st.caption(f"The US map shows US states only. {n_non_us} non-US location(s) (Canadian provinces) "
                   "are included in the table below but not on this map; see the Route map tab for them.")
    fig = px.choropleth(geo_map, locations="abbrev", locationmode="USA-states", color="Shipments",
                        scope="usa", color_continuous_scale="Purples",
                        hover_data={"State/Province": True, "Avg Distance (mi)": ":.0f", "Sales": ":.0f"})
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, width="stretch")

    flagged = geo[geo["Bottleneck Risk"] == "High Volume + Long Distance"]
    st.error(
        f"⚠️ **{len(flagged)} locations flagged as High Volume + Long Distance** (above-median order volume AND "
        f"above-median average distance): candidates for a closer look. "
        f"{', '.join(flagged['State/Province'].head(8))}{'...' if len(flagged) > 8 else ''}")
    common.show_table(geo[["Region", "State/Province", "Shipments", "Sales", "Avg Distance (mi)", "Bottleneck Risk"]]
                 .round(2))
