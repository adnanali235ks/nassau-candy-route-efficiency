"""
Nassau Candy Distributor — Factory-to-Customer Shipping Route Efficiency Analysis
Core analysis engine.

IMPORTANT DATA QUALITY NOTE (read this before trusting any lead-time number):
The `Ship Date` field in this dataset does not behave as a genuine shipment
record relative to `Order Date`. Computed lead times average ~1,300 days,
with no meaningful difference across Ship Modes (Same Day shipments show the
same "lead time" as Standard Class). This means Ship Date was almost
certainly populated independently of Order Date upstream, and CANNOT be used
to compute real shipping lead time, delay frequency, or a time-based route
efficiency score.

This module still computes the raw lead-time field (for transparency /
documentation purposes), but the dashboard and report explicitly flag it as
unreliable and use a distance + volume based "Route Efficiency Proxy"
instead, built only from fields that validate correctly:
  - Ship Mode (categorical, valid)
  - Factory -> Customer approximate distance (derived from coordinates, valid)
  - Order/shipment volume per route (valid)
"""

import pandas as pd
import numpy as np
from math import radians, sin, cos, sqrt, atan2

# ---------------------------------------------------------------------------
# REFERENCE DATA (from project brief)
# ---------------------------------------------------------------------------

FACTORIES = {
    "Lot's O' Nuts":      (32.881893, -111.768036),
    "Wicked Choccy's":    (32.076176, -81.088371),
    "Sugar Shack":        (48.119140, -96.181150),
    "Secret Factory":     (41.446333, -90.565487),
    "The Other Factory":  (35.117500, -89.971107),
}

PRODUCT_FACTORY_MAP = {
    "Wonka Bar - Nutty Crunch Surprise": "Lot's O' Nuts",
    "Wonka Bar - Fudge Mallows":         "Lot's O' Nuts",
    "Wonka Bar -Scrumdiddlyumptious":    "Lot's O' Nuts",
    "Wonka Bar - Milk Chocolate":        "Wicked Choccy's",
    "Wonka Bar - Triple Dazzle Caramel": "Wicked Choccy's",
    "Laffy Taffy":                       "Sugar Shack",
    "SweeTARTS":                         "Sugar Shack",
    "Nerds":                             "Sugar Shack",
    "Fun Dip":                           "Sugar Shack",
    "Fizzy Lifting Drinks":              "Sugar Shack",
    "Everlasting Gobstopper":            "Secret Factory",
    "Hair Toffee":                       "The Other Factory",
    "Lickable Wallpaper":                "Secret Factory",
    "Wonka Gum":                         "Secret Factory",
    "Kazookles":                         "The Other Factory",
}

STATE_CENTROIDS = {
    "Alabama": (32.806671, -86.791130), "Alaska": (61.370716, -152.404419),
    "Arizona": (33.729759, -111.431221), "Arkansas": (34.969704, -92.373123),
    "California": (36.116203, -119.681564), "Colorado": (39.059811, -105.311104),
    "Connecticut": (41.597782, -72.755371), "Delaware": (39.318523, -75.507141),
    "District of Columbia": (38.897438, -77.026817), "Florida": (27.766279, -81.686783),
    "Georgia": (33.040619, -83.643074), "Hawaii": (21.094318, -157.498337),
    "Idaho": (44.240459, -114.478828), "Illinois": (40.349457, -88.986137),
    "Indiana": (39.849426, -86.258278), "Iowa": (42.011539, -93.210526),
    "Kansas": (38.526600, -96.726486), "Kentucky": (37.668140, -84.670067),
    "Louisiana": (31.169546, -91.867805), "Maine": (44.693947, -69.381927),
    "Maryland": (39.063946, -76.802101), "Massachusetts": (42.230171, -71.530106),
    "Michigan": (43.326618, -84.536095), "Minnesota": (45.694454, -93.900192),
    "Mississippi": (32.741646, -89.678696), "Missouri": (38.456085, -92.288368),
    "Montana": (46.921925, -110.454353), "Nebraska": (41.125370, -98.268082),
    "Nevada": (38.313515, -117.055374), "New Hampshire": (43.452492, -71.563896),
    "New Jersey": (40.298904, -74.521011), "New Mexico": (34.840515, -106.248482),
    "New York": (42.165726, -74.948051), "North Carolina": (35.630066, -79.806419),
    "North Dakota": (47.528912, -99.784012), "Ohio": (40.388783, -82.764915),
    "Oklahoma": (35.565342, -96.928917), "Oregon": (44.572021, -122.070938),
    "Pennsylvania": (40.590752, -77.209755), "Rhode Island": (41.680893, -71.511780),
    "South Carolina": (33.856892, -80.945007), "South Dakota": (44.299782, -99.438828),
    "Tennessee": (35.747845, -86.692345), "Texas": (31.054487, -97.563461),
    "Utah": (40.150032, -111.862434), "Vermont": (44.045876, -72.710686),
    "Virginia": (37.769337, -78.169968), "Washington": (47.400902, -121.490494),
    "West Virginia": (38.491226, -80.954456), "Wisconsin": (44.268543, -89.616508),
    "Wyoming": (42.755966, -107.302490),
}


def haversine_miles(lat1, lon1, lat2, lon2):
    R = 3958.8
    p1, p2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlmb = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(p1) * cos(p2) * sin(dlmb / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


# ---------------------------------------------------------------------------
# LOAD & CLEAN
# ---------------------------------------------------------------------------

def load_and_clean(path="Nassau_Candy_Distributor.csv"):
    df = pd.read_csv(path)
    before = len(df)

    df = df.drop_duplicates(subset="Row ID")
    df = df.dropna(subset=["Order Date", "Ship Date", "Ship Mode", "State/Province",
                            "Region", "Product Name", "Sales", "Units"])
    df = df[(df["Sales"] > 0) & (df["Units"] > 0)]

    for col in ["Division", "Region", "State/Province", "City", "Ship Mode", "Product Name"]:
        df[col] = df[col].astype(str).str.strip()

    df["Order Date"] = pd.to_datetime(df["Order Date"], format="%d-%m-%Y", errors="coerce")
    df["Ship Date"] = pd.to_datetime(df["Ship Date"], format="%d-%m-%Y", errors="coerce")
    df = df.dropna(subset=["Order Date", "Ship Date"])

    # Raw lead time -- computed for transparency, but flagged unreliable (see module docstring)
    df["Raw Lead Time (days)"] = (df["Ship Date"] - df["Order Date"]).dt.days
    df.loc[df["Raw Lead Time (days)"] < 0, "Raw Lead Time (days)"] = np.nan

    removed = before - len(df)

    # Factory mapping
    df["Factory"] = df["Product Name"].map(PRODUCT_FACTORY_MAP)
    df["Factory Lat"] = df["Factory"].map(lambda f: FACTORIES.get(f, (np.nan, np.nan))[0])
    df["Factory Lon"] = df["Factory"].map(lambda f: FACTORIES.get(f, (np.nan, np.nan))[1])

    def get_centroid(state):
        return STATE_CENTROIDS.get(state, (np.nan, np.nan))
    cust_lat, cust_lon = zip(*df["State/Province"].map(get_centroid))
    df["Customer Lat"] = cust_lat
    df["Customer Lon"] = cust_lon

    def calc_dist(row):
        if pd.isna(row["Factory Lat"]) or pd.isna(row["Customer Lat"]):
            return np.nan
        return haversine_miles(row["Factory Lat"], row["Factory Lon"],
                                row["Customer Lat"], row["Customer Lon"])
    df["Route Distance (mi)"] = df.apply(calc_dist, axis=1)

    # Route definitions
    df["Route (Factory-Region)"] = df["Factory"] + " -> " + df["Region"]
    df["Route (Factory-State)"] = df["Factory"] + " -> " + df["State/Province"]

    meta = {"rows_before": before, "rows_removed": removed, "rows_after": len(df)}
    return df, meta


# ---------------------------------------------------------------------------
# ROUTE EFFICIENCY PROXY
# ---------------------------------------------------------------------------
# Since real lead time is invalid, we build a defensible "Route Efficiency
# Proxy Score" (0-100, higher = more efficient) from the two fields that DO
# validate: shorter distance per shipment, and ship-mode mix (Same Day/First
# Class shipments are assumed faster service tiers regardless of the broken
# date field, since that's what the category itself represents).

SHIP_MODE_SPEED_WEIGHT = {"Same Day": 1.00, "First Class": 0.85, "Second Class": 0.6, "Standard Class": 0.4}


def route_summary(df, level="Region"):
    route_col = "Route (Factory-Region)" if level == "Region" else "Route (Factory-State)"
    geo_col = "Region" if level == "Region" else "State/Province"

    g = df.groupby([route_col, "Factory", geo_col]).agg(
        Shipments=("Order ID", "nunique"),
        Units=("Units", "sum"),
        Sales=("Sales", "sum"),
        Avg_Distance=("Route Distance (mi)", "mean"),
        Raw_Avg_Lead_Time=("Raw Lead Time (days)", "mean"),
    ).reset_index().rename(columns={route_col: "Route", "Avg_Distance": "Avg Distance (mi)",
                                      "Raw_Avg_Lead_Time": "Raw Avg Lead Time (days) [UNRELIABLE]"})

    # Dominant ship mode + speed-weight per route
    mode_mix = df.groupby([route_col])["Ship Mode"].agg(lambda x: x.value_counts(normalize=True).to_dict())
    g["Ship Mode Mix"] = g["Route"].map(mode_mix)
    g["Speed Weight"] = g["Ship Mode Mix"].apply(
        lambda d: sum(SHIP_MODE_SPEED_WEIGHT.get(m, 0.5) * share for m, share in d.items())
    )

    # Efficiency proxy: shorter distance + higher speed-weight = more efficient
    max_dist = g["Avg Distance (mi)"].max()
    g["Distance Score"] = 100 * (1 - (g["Avg Distance (mi)"] / max_dist))
    g["Route Efficiency Proxy Score"] = (0.6 * g["Distance Score"] + 0.4 * (g["Speed Weight"] * 100)).round(1)

    return g.sort_values("Route Efficiency Proxy Score", ascending=False)


def ship_mode_summary(df):
    g = df.groupby("Ship Mode").agg(
        Shipments=("Order ID", "nunique"),
        Units=("Units", "sum"),
        Sales=("Sales", "sum"),
        Avg_Distance=("Route Distance (mi)", "mean"),
        Raw_Avg_Lead_Time=("Raw Lead Time (days)", "mean"),
    ).reset_index().rename(columns={"Avg_Distance": "Avg Distance (mi)",
                                      "Raw_Avg_Lead_Time": "Raw Avg Lead Time (days) [UNRELIABLE]"})
    total = g["Shipments"].sum()
    g["Share of Shipments %"] = g["Shipments"] / total * 100
    order = ["Same Day", "First Class", "Second Class", "Standard Class"]
    g["sort_key"] = g["Ship Mode"].apply(lambda m: order.index(m) if m in order else 99)
    return g.sort_values("sort_key").drop(columns="sort_key")


def geo_bottleneck_summary(df):
    """Volume + distance based bottleneck view by region/state (no time claims)."""
    g = df.groupby(["Region", "State/Province"]).agg(
        Shipments=("Order ID", "nunique"),
        Sales=("Sales", "sum"),
        Avg_Distance=("Route Distance (mi)", "mean"),
    ).reset_index().rename(columns={"Avg_Distance": "Avg Distance (mi)"})
    # Flag high-volume + high-distance = candidate bottleneck (cost/complexity risk)
    vol_median = g["Shipments"].median()
    dist_median = g["Avg Distance (mi)"].median()
    g["Bottleneck Risk"] = np.where(
        (g["Shipments"] >= vol_median) & (g["Avg Distance (mi)"] >= dist_median),
        "High Volume + Long Distance",
        "Normal"
    )
    return g.sort_values("Shipments", ascending=False)


def factory_route_footprint(df):
    g = df.groupby("Factory").agg(
        Shipments=("Order ID", "nunique"),
        States_Served=("State/Province", "nunique"),
        Regions_Served=("Region", "nunique"),
        Sales=("Sales", "sum"),
        Avg_Distance=("Route Distance (mi)", "mean"),
    ).reset_index().rename(columns={"Avg_Distance": "Avg Distance (mi)"})
    return g.sort_values("Shipments", ascending=False)


def ship_mode_by_route_level(df, level="Region"):
    geo_col = "Region" if level == "Region" else "State/Province"
    g = df.groupby([geo_col, "Ship Mode"]).agg(Shipments=("Order ID", "nunique")).reset_index()
    return g


if __name__ == "__main__":
    df, meta = load_and_clean()
    print("Cleaning summary:", meta)
    print("\nRaw lead time sanity check (should look broken):")
    print(df["Raw Lead Time (days)"].describe())
    print(df.groupby("Ship Mode")["Raw Lead Time (days)"].mean())

    route_summary(df, "Region").to_csv("route_summary_region.csv", index=False)
    route_summary(df, "State/Province").to_csv("route_summary_state.csv", index=False)
    ship_mode_summary(df).to_csv("ship_mode_summary.csv", index=False)
    geo_bottleneck_summary(df).to_csv("geo_bottleneck_summary.csv", index=False)
    factory_route_footprint(df).to_csv("factory_route_footprint.csv", index=False)
    df.to_csv("processed_routes.csv", index=False)
    print("\nAll processed files written.")
