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
from pathlib import Path

from config import DEFAULT_SHIP_MODE_SUITABILITY
from modules.scoring import score_routes

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


# Canadian provinces appear in the dataset (Country/Region == "Canada", 200 rows).
# STATUS: PROVISIONAL / UNVERIFIED. Searches of NRCan and Statistics Canada material
# found no authoritative per-province centroid table (StatCan publishes
# population-weighted "representative points", a different definition). Only
# Ontario's value could be cross-checked: it equals the midpoint of Ontario's
# bounding box (~50.0, -86.0), whereas a news-reported calculated centre lies
# nearer Hornepayne. The rest are approximate area-centre values entered by the
# developer, rounded to 1 decimal degree. Sensitivity test: moving the most
# extreme province (Newfoundland and Labrador) by ~100 miles changes any route
# score by at most 1.4 points. Details: docs/DATA_SOURCES.md.
CANADA_CENTROIDS_STATUS = "PROVISIONAL"
CANADA_PROVINCE_CENTROIDS = {
    "Alberta": (54.5, -115.0),
    "British Columbia": (53.7, -127.6),
    "Manitoba": (54.8, -98.8),
    "New Brunswick": (46.5, -66.4),
    "Newfoundland and Labrador": (53.1, -57.7),
    "Nova Scotia": (45.0, -63.0),
    "Ontario": (50.0, -86.0),
    "Prince Edward Island": (46.4, -63.2),
    "Quebec": (52.4, -71.8),
    "Saskatchewan": (54.7, -106.0),
}

# One lookup for every location we can place on a map. US states + Canadian provinces.
STATE_CENTROIDS = {**STATE_CENTROIDS, **CANADA_PROVINCE_CENTROIDS}


# Two-letter codes for the US choropleth (the map draws US states only).
US_STATE_ABBREVIATIONS = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC",
    "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL",
    "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA",
    "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN",
    "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
    "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR",
    "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA",
    "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
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

PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_CSV_NAME = "Nassau_Candy_Distributor.csv"
# Resolved from this file's location, NOT from the terminal's current folder.
DEFAULT_CSV_PATH = PROJECT_DIR / DEFAULT_CSV_NAME

# Columns the analysis reads. A CSV missing any of them is rejected with a clear message.
REQUIRED_COLUMNS = ["Row ID", "Order ID", "Order Date", "Ship Date", "Ship Mode", "Customer ID", "Country/Region",
                    "City", "State/Province", "Postal Code", "Division", "Region", "Product ID", "Product Name",
                    "Sales", "Units", "Gross Profit", "Cost"]


class DataFileError(Exception):
    """A data-file problem the user can fix. The message says what is wrong and how to fix it."""


def _read_csv(path):
    """Read the CSV, turning missing / empty / unreadable / wrong-schema files into DataFileError."""
    p = Path(path) if path else DEFAULT_CSV_PATH
    if not p.is_absolute() and not p.exists():
        p = PROJECT_DIR / p                       # a bare file name is looked up in the project folder
    fix = (f"Fix: place the original '{DEFAULT_CSV_NAME}' in the project folder ({PROJECT_DIR}) "
           f"and start the app again.")
    if not p.exists():
        raise DataFileError(f"Data file not found: {p}\nExpected file: {DEFAULT_CSV_NAME} in {PROJECT_DIR}.\n{fix}")
    if not p.is_file():
        raise DataFileError(f"The data path is not a file: {p}\n{fix}")
    try:
        df = pd.read_csv(p)
    except pd.errors.EmptyDataError:
        raise DataFileError(f"The data file is empty: {p}\n{fix}") from None
    except (pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise DataFileError(f"The data file could not be read as CSV: {p}\nDetails: {exc}\n{fix}") from None
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise DataFileError(f"The data file is missing required column(s): {', '.join(missing)}\n"
                            f"File: {p}\nRequired columns: {', '.join(REQUIRED_COLUMNS)}\n"
                            f"Found columns: {', '.join(map(str, df.columns))}\n{fix}")
    return df


def load_and_clean(path=None):
    """Load and clean the order data. Raises DataFileError (with a fix) for file problems.

    path: optional CSV path; default is Nassau_Candy_Distributor.csv in the project folder.
    """
    df = _read_csv(path)
    before = len(df)

    for col in ("Sales", "Units"):                # non-numeric text becomes NaN and the row is dropped below
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.drop_duplicates(subset="Row ID")
    df = df.dropna(subset=["Order Date", "Ship Date", "Ship Mode", "State/Province",
                            "Region", "Product Name", "Sales", "Units"])
    df = df[(df["Sales"] > 0) & (df["Units"] > 0)]

    for col in ["Division", "Region", "State/Province", "City", "Ship Mode", "Product Name"]:
        df[col] = df[col].astype(str).str.strip()

    df["Order Date"] = pd.to_datetime(df["Order Date"], format="%d-%m-%Y", errors="coerce")
    df["Ship Date"] = pd.to_datetime(df["Ship Date"], format="%d-%m-%Y", errors="coerce")
    df = df.dropna(subset=["Order Date", "Ship Date"])
    if df.empty:
        raise DataFileError("No usable rows remain after cleaning (rows need valid dates in day-month-year format, "
                            "positive Sales and Units, and no missing key fields).\n"
                            f"Check the contents of {DEFAULT_CSV_NAME}.")

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

    # --- Data-quality flags (flag only; nothing is deleted here) ---------------
    # Missing geography: location not in STATE_CENTROIDS, or factory unmapped.
    # Such rows keep NaN distance and are reported, never silently dropped or zeroed.
    df["Missing Geo"] = df["Route Distance (mi)"].isna()
    # Repeated Order ID + Product ID: may be duplicates OR legitimate order lines,
    # so they are flagged for investigation, not removed.
    df["Repeated Order-Product Line"] = df.duplicated(subset=["Order ID", "Product ID"], keep=False)

    meta = {
        "rows_before": before, "rows_removed": removed, "rows_after": len(df),
        "rows_missing_geo": int(df["Missing Geo"].sum()),
        "unmapped_locations": sorted(df.loc[df["Missing Geo"], "State/Province"].unique()),
        "rows_repeated_order_product": int(df["Repeated Order-Product Line"].sum()),
    }
    return df, meta


# ---------------------------------------------------------------------------
# ROUTE EFFICIENCY SCORE
# ---------------------------------------------------------------------------
# Real lead time is invalid (see module docstring), so routes are scored from the
# two fields that DO validate: distance and ship-mode mix. The scoring maths
# (70% distance / 30% ship-mode by default, configurable) lives in
# modules/scoring.py; the editable assumptions live in config.py.

# Backward-compatible alias for code that imported the old constant.
SHIP_MODE_SPEED_WEIGHT = DEFAULT_SHIP_MODE_SUITABILITY


def route_summary(df, level="Region", include_unscored=False, weights=None,
                  suitability=None, reference_max_distance=None):
    """Route table with the Route Efficiency Score, best first.

    weights                 {"distance": .., "ship_mode": ..}; default 70/30 (config.py).
    suitability             {ship mode: 0-1}; default from config.py (an assumption).
    reference_max_distance  distance that scores 0. Default = longest route in `df`,
                            which makes scores RELATIVE to the rows passed in. Pass a
                            fixed value (e.g. from the full dataset) to keep scores
                            stable while filtering.

    Routes whose distance is unknown (NaN) cannot be scored. By default they are
    EXCLUDED so they can never appear as "least efficient". Use
    `unscored_routes()` to list them, or `include_unscored=True` to append them
    at the end (their score stays NaN, never 0).
    """
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

    # Share of each ship mode on the route, e.g. {"Standard Class": 0.7, "First Class": 0.3}
    mode_mix = df.groupby([route_col])["Ship Mode"].agg(lambda x: x.value_counts(normalize=True).to_dict())
    g["Ship Mode Mix"] = g["Route"].map(mode_mix)

    g = score_routes(g, weights=weights, suitability=suitability,
                     reference_max_distance=reference_max_distance)

    g = g.sort_values("Route Efficiency Proxy Score", ascending=False, na_position="last")
    if not include_unscored:
        g = g[g["Route Efficiency Proxy Score"].notna()]
    return g


def unscored_routes(df, level="Region"):
    """Routes that cannot be scored because their distance is unknown."""
    full = route_summary(df, level, include_unscored=True)
    cols = ["Route", "Factory", "Shipments", "Sales"]
    return full[full["Route Efficiency Proxy Score"].isna()][cols]


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
    # Unknown distance can't be judged -- say so instead of calling it "Normal".
    g.loc[g["Avg Distance (mi)"].isna(), "Bottleneck Risk"] = "Not assessed (no distance)"
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


if __name__ == "__main__":
    try:
        df, meta = load_and_clean()
    except DataFileError as exc:
        raise SystemExit(f"Data problem: {exc}")
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
