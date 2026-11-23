"""
Report content: computes everything the PDF / Excel / CSV reports show, in ONE place, so the three
outputs always agree. No file writing here (see utils/report_generator.py) and no Streamlit code.

Labelling rules used by every report
  * "Dataset" / "Calculated"  = actual data and metrics derived from it
  * "Hypothetical"            = results of the allocation simulation (assumptions, not facts)
  * Estimated cost            = included ONLY when the user supplied a rate, and always called an estimate
"""

from datetime import datetime

import numpy as np
import pandas as pd

import route_core as rc
from modules import scenarios as sc
from modules.anomaly_detection import detect_all
from modules.optimization import split_order_lines
from modules.recommendations import generate_recommendations
from modules.route_analysis import executive_kpis, business_insights, best_and_worst_routes, ship_mode_distribution
from modules.scenarios import Scenario, describe_scenario
from config import DEFAULT_SCORE_WEIGHTS, DEFAULT_SHIP_MODE_SUITABILITY

HYPOTHETICAL_BANNER = ("HYPOTHETICAL SIMULATION: results below depend on assumptions (any factory can make any product, "
                       "optional capacities) and are NOT an operational recommendation or actual factory data.")

LIMITATIONS = [
    "Ship Date does not track Order Date (about 1,300 days for every ship mode), so no delivery-time or delay metric is reported.",
    "Distances are straight-line (great-circle) miles from the factory to a state/province centroid, not road distance and "
    "not the customer's address.",
    "Canadian province centroids are provisional: no authoritative source was found (see docs/DATA_SOURCES.md).",
    "The product-to-factory mapping comes from the project brief; the dataset has no factory column, so it cannot be verified.",
    "The Route Efficiency Score uses assumed weights and ship-mode suitability values; it measures distance and service-tier "
    "mix, not measured speed, cost or quality.",
    "The allocation simulation is hypothetical: it assumes factories can make products the data says they do not, ignores "
    "production cost, quality, inventory and real capacity, and (without capacity limits) is an upper bound on savings.",
    "Estimated transport costs, where shown, equal an illustrative user-entered rate multiplied by unit-miles. They are not "
    "actual costs and are not part of any efficiency score.",
    "Repeated Order ID + Product ID lines are flagged, not removed; sales and unit totals include them.",
    "Every product in the data has a single constant unit price and margin, so price and margin analysis is limited.",
    "Which orders within a demand cell take which factory in the order-line allocation is a bookkeeping rule (Row ID order), "
    "not an optimizer decision.",
]


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------
def factory_performance_table(df):
    """Per-factory actuals and calculated distances (Dataset / Calculated)."""
    known = df.dropna(subset=["Route Distance (mi)"])
    g = df.groupby("Factory").agg(Orders=("Order ID", "nunique"), Customers=("Customer ID", "nunique"),
                                  Units=("Units", "sum"), Sales=("Sales", "sum"), Gross_Profit=("Gross Profit", "sum"),
                                  States_Served=("State/Province", "nunique")).reset_index()
    um = known.assign(UM=known["Units"] * known["Route Distance (mi)"]).groupby("Factory").agg(
        UM=("UM", "sum"), U=("Units", "sum"), Max=("Route Distance (mi)", "max")).reset_index()
    g = g.merge(um, on="Factory", how="left")
    g["Gross Profit %"] = 100 * g["Gross_Profit"] / g["Sales"]
    g["Sales Share %"] = 100 * g["Sales"] / g["Sales"].sum()
    g["Avg Distance per Unit (mi)"] = g["UM"] / g["U"]
    g = g.rename(columns={"Gross_Profit": "Gross Profit", "States_Served": "States/Provinces Served",
                          "Max": "Farthest Destination (mi)"})
    cols = ["Factory", "Orders", "Customers", "Units", "Sales", "Gross Profit", "Gross Profit %", "Sales Share %",
            "States/Provinces Served", "Avg Distance per Unit (mi)", "Farthest Destination (mi)"]
    return g[cols].sort_values("Sales", ascending=False).reset_index(drop=True)


def shipping_mode_table(df):
    """Ship-mode summary WITHOUT the unreliable lead-time column."""
    t = rc.ship_mode_summary(df).drop(columns=[c for c in rc.ship_mode_summary(df).columns if "UNRELIABLE" in c])
    return t.rename(columns={"Shipments": "Orders"}).reset_index(drop=True)


def anomaly_overview(anoms):
    """One flat table of every flagged record/subject: Anomaly Type, Subject, Row ID, Order ID, Reason."""
    frames = []

    def add(table, subject_col=None, subject_fn=None):
        if table is None or len(table) == 0:
            return
        f = pd.DataFrame({"Anomaly Type": table["Anomaly Type"].to_numpy()})
        f["Subject"] = (table[subject_col].to_numpy() if subject_col else subject_fn(table))
        f["Row ID"] = table["Row ID"].to_numpy() if "Row ID" in table else np.nan
        f["Order ID"] = table["Order ID"].to_numpy() if "Order ID" in table else ""
        f["Reason"] = table["Reason"].to_numpy()
        frames.append(f)

    add(anoms["route_outliers"], "Route")
    add(anoms["duplicates"], subject_fn=lambda t: (t["Order ID"].astype(str) + " / " + t["Product ID"].astype(str)).to_numpy())
    add(anoms["missing_geography"], subject_fn=lambda t: t["State/Province"].astype(str).to_numpy())
    add(anoms["sales_profit"], "Product Name")
    add(anoms["factory_product_lines"], "Product Name")
    add(anoms["factory_product_summary"], "Subject")
    if not frames:
        return pd.DataFrame(columns=["Anomaly Type", "Subject", "Row ID", "Order ID", "Reason"])
    return pd.concat(frames, ignore_index=True)


def data_quality_table(df, meta, anoms, total_rows):
    """Key facts about data quality, each with its source label."""
    dup = anoms["duplicates"]
    exact = int(dup["Identical Values"].sum()) if len(dup) else 0
    rows = [
        ("Rows in this report", f"{len(df):,} of {total_rows:,} loaded rows", "Dataset"),
        ("Rows removed during loading", f"{meta['rows_removed']:,}", "Calculated"),
        ("Rows with unknown location", f"{int(df['Missing Geo'].sum()):,}", "Calculated"),
        ("Repeated Order ID + Product ID lines (flagged, kept)", f"{len(dup):,}", "Dataset"),
        ("   of which identical values (likely exact duplicates)", f"{exact:,}", "Dataset"),
        ("Canadian order lines (provisional centroids)", f"{int((df['Country/Region'] == 'Canada').sum()):,}", "Calculated"),
        ("Product ID prefix / Division mismatches", f"{len(anoms['factory_product_lines']):,}", "Dataset"),
        ("Products with one constant unit price and margin", f"{len(anoms['constant_prices']):,}", "Dataset"),
        ("Ship Date reliability", "Unusable for delivery time (about 1,300 days for every ship mode)", "Dataset"),
        ("Product-to-factory mapping", "From the project brief; the CSV has no factory column", "Assumption"),
    ]
    return pd.DataFrame(rows, columns=["Item", "Value", "Basis"])


# ---------------------------------------------------------------------------
# Everything
# ---------------------------------------------------------------------------
def build_report_data(df, scenario=None, weights=None, suitability=None, meta=None, total_rows=None,
                      reference_distances=None, generated_at=None):
    """Compute all report content for the (already filtered) order lines `df`.

    scenario  the selected hypothetical scenario (default: no limits, all factories eligible, no cost rate)
    """
    scenario = scenario or Scenario("Selected scenario")
    weights = weights or dict(DEFAULT_SCORE_WEIGHTS)
    suitability = suitability or dict(DEFAULT_SHIP_MODE_SUITABILITY)
    meta = meta or {"rows_removed": 0}
    total_rows = total_rows or len(df)
    reference = reference_distances or {}
    generated_at = generated_at or datetime.now()

    def routes(level, include_unscored=True):
        return rc.route_summary(df, level, include_unscored=include_unscored, weights=weights, suitability=suitability,
                                reference_max_distance=reference.get(level))

    region_routes = routes("Region")
    state_routes = routes("State/Province")
    kpis = executive_kpis(df, region_routes)
    best, worst = best_and_worst_routes(region_routes, n=5)

    ctx = sc.prepare_context(df)
    result = sc.run_scenario(ctx, scenario)
    free = result if scenario.headroom_pct is None and scenario.eligibility_mode == "all" else \
        sc.run_scenario(ctx, Scenario("Unconstrained", "all"))
    anoms = detect_all(df)
    caps = result.get("capacities")
    unconstrained_units = (free["allocation"].groupby("Factory")["Units"].sum()
                           if free["status"] == "OPTIMAL" else None)
    recs = generate_recommendations(df, anoms, result if result["status"] != "NO DATA" else None,
                                    unconstrained_units, caps)

    order_alloc = pd.DataFrame()
    alloc_note = ""
    if result["status"] == "OPTIMAL" and result.get("integral", True):
        order_alloc = split_order_lines(ctx["valid"], result["allocation"], ctx["distance"])
        n_split = int(order_alloc.loc[order_alloc["Line Split"], "Row ID"].nunique())
        alloc_note = (f"{len(order_alloc):,} rows for {len(ctx['valid']):,} original order lines; {n_split:,} line(s) are "
                      "split across factories and appear on several rows (Line Split = True).")
    elif result["status"] != "OPTIMAL":
        alloc_note = f"No order-line allocation: scenario status is {result['status']}. {result['message']}"

    comparison_table = sc.compare_scenarios(ctx, [result]) if result["status"] != "NO DATA" else pd.DataFrame()
    volumes = sc.factory_volume_table(ctx, [result]) if result["status"] != "NO DATA" else pd.DataFrame()
    changed = (result["comparison"]["changed_cells"] if result.get("comparison") else pd.DataFrame())

    return {
        "generated_at": generated_at.strftime("%Y-%m-%d %H:%M:%S"),
        "scenario": scenario, "scenario_text": describe_scenario(scenario), "scenario_result": result,
        "weights": weights, "suitability": suitability,
        "score_text": (f"Route Efficiency Score = {weights['distance']:.0%} distance + {weights['ship_mode']:.0%} ship-mode "
                       "suitability (assumptions: " + ", ".join(f"{k} {v:g}" for k, v in suitability.items()) + ")"),
        "kpis": kpis, "insights": business_insights(df, region_routes),
        "region_routes": region_routes, "state_routes": state_routes, "best_routes": best, "worst_routes": worst,
        "factory_performance": factory_performance_table(df), "shipping_modes": shipping_mode_table(df),
        "ship_mode_distribution": ship_mode_distribution(df),
        "scenario_comparison": comparison_table, "factory_volumes": volumes, "changed_cells": changed,
        "order_allocations": order_alloc, "order_allocation_note": alloc_note,
        "anomalies": anoms, "anomaly_overview": anomaly_overview(anoms), "recommendations": recs,
        "data_quality": data_quality_table(df, meta, anoms, total_rows),
        "limitations": LIMITATIONS, "hypothetical_banner": HYPOTHETICAL_BANNER,
        "has_cost": scenario.cost_rate is not None, "rows_in_report": len(df), "total_rows": total_rows,
    }
