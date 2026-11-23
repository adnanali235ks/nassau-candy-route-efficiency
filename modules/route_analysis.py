"""
Executive-level calculations: KPIs, distributions and rule-based business insights.

Pure pandas/NumPy, no Streamlit. Every function takes the (filtered) order-line
table produced by route_core.load_and_clean() and/or a scored route table from
route_core.route_summary().

"Shipment" = a distinct Order ID. Verified on this dataset: each order has exactly
one ship mode, factory, state and customer (see tests/test_pipeline.py).
"""

import numpy as np
import pandas as pd

from route_core import FACTORIES, STATE_CENTROIDS

# Reporting threshold for the "long distance" insight. A presentation choice, NOT a
# service-level limit from the business.
LONG_DISTANCE_MILES = 1500

SCORE_COL = "Route Efficiency Proxy Score"


def executive_kpis(fdf, routes):
    """Headline numbers. `routes` must be a scored route table (unscored rows excluded or NaN)."""
    orders = fdf.drop_duplicates("Order ID")               # one row per order -> per-order averages
    scored = routes[routes[SCORE_COL].notna()]
    if len(scored) and scored["Shipments"].sum() > 0:
        # Weighted average: routes with more orders count proportionally more.
        overall = float(np.average(scored[SCORE_COL], weights=scored["Shipments"]))
    else:
        overall = float("nan")
    return {
        "total_orders": int(fdf["Order ID"].nunique()),                      # dataset observation
        "total_sales": float(fdf["Sales"].sum()),                            # dataset observation
        "customers": int(fdf["Customer ID"].nunique()),                      # dataset observation
        "factories": int(fdf["Factory"].nunique()),                          # via product->factory map (assumption)
        "avg_distance_mi": float(orders["Route Distance (mi)"].mean()),      # calculated; NaN rows skipped
        "overall_efficiency": overall,                                       # calculated
        "scored_routes": int(len(scored)),
        "unscored_routes": int(len(routes) - len(scored)),
    }


def ship_mode_distribution(fdf):
    """Orders and share per ship mode (distinct Order IDs; shares add up to 100%)."""
    counts = fdf.groupby("Ship Mode")["Order ID"].nunique().rename("Orders").reset_index()
    counts["Share %"] = 100 * counts["Orders"] / counts["Orders"].sum()
    return counts.sort_values("Orders", ascending=False)


def factory_sales(fdf):
    """Sales, orders and average distance per factory."""
    g = fdf.groupby("Factory").agg(Sales=("Sales", "sum"), Orders=("Order ID", "nunique"),
                                   Avg_Distance=("Route Distance (mi)", "mean")).reset_index()
    g = g.rename(columns={"Avg_Distance": "Avg Distance (mi)"})
    g["Sales Share %"] = 100 * g["Sales"] / g["Sales"].sum()
    return g.sort_values("Sales", ascending=False)


def best_and_worst_routes(routes, n=5):
    """(best n, worst n) of the SCORED routes. Unscored routes can never appear in either."""
    scored = routes[routes[SCORE_COL].notna()].sort_values(SCORE_COL, ascending=False)
    return scored.head(n), scored.tail(n).iloc[::-1]         # worst first


def business_insights(fdf, routes, long_distance_miles=LONG_DISTANCE_MILES):
    """Plain-language findings derived from the numbers. Each has a 'why' explaining its basis."""
    insights = []
    orders = fdf.drop_duplicates("Order ID")
    total_orders = len(orders)
    total_sales = fdf["Sales"].sum()

    # 1. Sales concentration
    fs = factory_sales(fdf)
    if len(fs) and total_sales > 0:
        top = fs.iloc[0]
        insights.append({
            "title": "Sales are concentrated in one factory" if top["Sales Share %"] >= 50 else "Sales are spread across factories",
            "text": f"{top['Factory']} accounts for {top['Sales Share %']:.0f}% of sales (${top['Sales']:,.0f}).",
            "why": "Factory sales ÷ total sales in the current filter. Factory comes from the product→factory map.",
        })

    # 2. Long-distance exposure
    known = orders["Route Distance (mi)"].dropna()
    if len(known):
        share = 100 * (known > long_distance_miles).mean()
        insights.append({
            "title": "Share of orders travelling a long way",
            "text": f"{share:.0f}% of orders travel more than {long_distance_miles:,} straight-line miles.",
            "why": f"Orders with distance above {long_distance_miles:,} mi ÷ orders with a known distance. "
                   "The threshold is a reporting choice, not a business limit.",
        })

    # 3. Ship-mode mix
    dist = ship_mode_distribution(fdf)
    if len(dist):
        top_mode = dist.iloc[0]
        insights.append({
            "title": "Dominant ship mode",
            "text": f"{top_mode['Ship Mode']} carries {top_mode['Share %']:.0f}% of orders.",
            "why": "Orders per ship mode ÷ total orders (each order has exactly one mode).",
        })

    # 4. Weakest high-volume route
    scored = routes[routes[SCORE_COL].notna()]
    if len(scored):
        busy = scored[scored["Shipments"] >= scored["Shipments"].median()]
        worst = busy.sort_values(SCORE_COL).iloc[0]
        insights.append({
            "title": "Weakest high-volume route",
            "text": f"{worst['Route']} has {int(worst['Shipments']):,} orders, an average distance of "
                    f"{worst['Avg Distance (mi)']:,.0f} mi and a score of {worst[SCORE_COL]:.1f}.",
            "why": "Lowest-scoring route among those with at least the median number of orders. "
                   "Worth investigating; the score is a proxy, not proof of a problem.",
        })

    # 5. Data coverage caveats
    unscored = int(len(routes) - len(scored))
    repeated = int(fdf["Repeated Order-Product Line"].sum()) if "Repeated Order-Product Line" in fdf else 0
    canada_share = 100 * (fdf["Country/Region"] == "Canada").mean() if len(fdf) else 0
    insights.append({
        "title": "Data caveats",
        "text": f"{unscored} route(s) are unscored; {repeated:,} order lines repeat an Order ID + Product ID "
                f"(flagged for review, not removed); {canada_share:.0f}% of rows are Canadian, using provisional "
                "province centroids.",
        "why": "Counted directly from the filtered data.",
    })
    return insights


# ---------------------------------------------------------------------------
# Geographic helpers (Part D)
# ---------------------------------------------------------------------------


def route_map_table(routes):
    """Attach map endpoints to a STATE-level route table.

    Adds Factory Lat/Lon (factory location) and Dest Lat/Lon (the CENTROID of the
    state/province, not any customer's address). Rows whose location is unknown
    keep NaN coordinates; the map skips them and the page reports how many.
    """
    t = routes.copy()
    t["Factory Lat"] = t["Factory"].map(lambda f: FACTORIES.get(f, (np.nan, np.nan))[0])
    t["Factory Lon"] = t["Factory"].map(lambda f: FACTORIES.get(f, (np.nan, np.nan))[1])
    t["Dest Lat"] = t["State/Province"].map(lambda s: STATE_CENTROIDS.get(s, (np.nan, np.nan))[0])
    t["Dest Lon"] = t["State/Province"].map(lambda s: STATE_CENTROIDS.get(s, (np.nan, np.nan))[1])
    return t


def long_distance_threshold(distances, percentile=75):
    """Distance (miles) above which a route counts as "long": a percentile of the known distances.

    Example: distances 300, 800, 1500, 2200 -> 75th percentile = 1675 -> only 2200 is long.
    Returns NaN when there are no known distances.
    """
    known = pd.Series(distances, dtype="float64").dropna()
    return float(np.percentile(known, percentile)) if len(known) else float("nan")


def flag_long_routes(table, threshold):
    """Add a boolean 'Long Distance' column. Unknown distance is never flagged (it is simply unknown)."""
    t = table.copy()
    t["Long Distance"] = t["Avg Distance (mi)"] > threshold      # NaN > x is False
    return t


def destination_summary(table):
    """One row per destination: orders (summed over factories) and order-weighted mean distance."""
    t = table.dropna(subset=["Avg Distance (mi)"]).copy()
    t["_dist_x_orders"] = t["Avg Distance (mi)"] * t["Shipments"]
    g = t.groupby(["State/Province", "Dest Lat", "Dest Lon"], as_index=False).agg(
        Orders=("Shipments", "sum"), _dist=("_dist_x_orders", "sum"), Sales=("Sales", "sum"))
    g["Avg Distance (mi)"] = g["_dist"] / g["Orders"]
    return g.drop(columns="_dist")
