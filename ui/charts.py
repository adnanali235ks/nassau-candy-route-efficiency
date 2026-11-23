"""Plotly figure builders for the dashboard (draw only; all numbers come from modules/)."""

import plotly.graph_objects as go

from modules.route_analysis import destination_summary
from ui.common import ACCENT, PRIMARY

_SHORT_COLOR = "#8e6bb0"


def build_route_map(table):
    """Factory -> destination-centroid lines on a North America map.

    `table` needs: Factory, Factory Lat/Lon, State/Province, Dest Lat/Lon,
    Avg Distance (mi), Shipments, Long Distance. Rows without coordinates are skipped.
    """
    t = table.dropna(subset=["Factory Lat", "Factory Lon", "Dest Lat", "Dest Lon"])
    fig = go.Figure()

    # One trace per class (long / shorter). Lines are separated by None so one trace draws many lines.
    for is_long, color, name in ((False, _SHORT_COLOR, "Shorter routes"), (True, ACCENT, "Long-distance routes")):
        sub = t[t["Long Distance"] == is_long]
        lats, lons = [], []
        for f_lat, f_lon, d_lat, d_lon in zip(sub["Factory Lat"], sub["Factory Lon"],
                                              sub["Dest Lat"], sub["Dest Lon"]):
            lats += [f_lat, d_lat, None]
            lons += [f_lon, d_lon, None]
        fig.add_trace(go.Scattergeo(lat=lats, lon=lons, mode="lines", name=f"{name} ({len(sub)})",
                                    line=dict(width=1.3, color=color), opacity=0.55, hoverinfo="skip"))

    # Destination centroids, sized by orders. Hover says clearly these are centroids.
    dest = destination_summary(t)
    fig.add_trace(go.Scattergeo(
        lat=dest["Dest Lat"], lon=dest["Dest Lon"], mode="markers", name="Destination centroid",
        marker=dict(size=(dest["Orders"] ** 0.5).clip(lower=3, upper=22), color=PRIMARY, opacity=0.75,
                    line=dict(width=0.5, color="white")),
        customdata=dest[["State/Province", "Orders", "Avg Distance (mi)"]].to_numpy(),
        hovertemplate="<b>%{customdata[0]}</b> (centroid, not a customer location)<br>"
                      "Orders: %{customdata[1]:,}<br>Avg straight-line distance: %{customdata[2]:,.0f} mi<extra></extra>"))

    # Factories
    fac = t.drop_duplicates("Factory")
    fig.add_trace(go.Scattergeo(
        lat=fac["Factory Lat"], lon=fac["Factory Lon"], mode="markers+text", name="Factory",
        text=fac["Factory"], textposition="top center", textfont=dict(color="#1b1b1b", size=12),
        marker=dict(size=13, symbol="diamond", color="#2E8B57", line=dict(width=1, color="white")),
        hovertemplate="<b>%{text}</b><br>Factory location<extra></extra>"))

    fig.update_geos(scope="north america", lataxis_range=[22, 62], lonaxis_range=[-135, -50],
                    showcountries=True, showsubunits=True, countrycolor="#bbbbbb", subunitcolor="#dddddd",
                    landcolor="#f6f3f8", showland=True, showocean=True, oceancolor="#dce8f2",
                    showlakes=True, lakecolor="#dce8f2", bgcolor="rgba(0,0,0,0)")
    # Colours are set explicitly (the page uses theme=None for this chart) so the map looks the
    # same in light and dark mode: pale map on a transparent page, with a legend that stays readable.
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=560, paper_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h", yanchor="bottom", y=0.0, xanchor="left", x=0.0,
                                  bgcolor="rgba(255,255,255,0.85)", font=dict(color="#1b1b1b")))
    return fig
