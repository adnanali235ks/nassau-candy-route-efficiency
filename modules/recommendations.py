"""
Smart Recommendations: explainable, rule-based. No AI, no external services.

Each rule is: IF a measured value crosses a documented threshold THEN emit a recommendation that states
  Why (the rule in words), Rule (the exact threshold), and Supporting Values (the numbers that triggered it).

Basis labels:  "Dataset" = counted straight from the data, "Calculated" = derived from the data,
               "Hypothetical" = depends on simulation assumptions (eligibility / capacity).
Recommendations are prompts to INVESTIGATE; none is an operational instruction.
No Streamlit code here.
"""

import pandas as pd

import route_core as rc
from modules.anomaly_detection import detect_all
from modules.route_analysis import LONG_DISTANCE_MILES   # one shared definition of a "long" shipment

# Documented thresholds (change here, and the wording of every recommendation follows)
DISTANCE_CONTRIBUTOR_SHARE = 0.05       # route contributing >= 5% of all unit-miles
WIDE_REACH_SHARE = 0.50                 # factory shipping >= 50% of its units farther than LONG_DISTANCE_MILES
HIGH_VOLUME_ORDERS = 100                # outlier route with at least this many orders is "High" priority
SAVING_HIGH, SAVING_MEDIUM = 0.02, 0.005   # share of total unit-miles a reassignment could save
TOP_N_REASSIGNMENTS = 5

_PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}
COLUMNS = ["ID", "Category", "Priority", "Basis", "Title", "Recommendation", "Why", "Rule", "Supporting Values"]


def _fmt(values):
    return "; ".join(f"{k}: {v}" for k, v in values.items())


def _rec(category, priority, basis, title, recommendation, why, rule, values):
    return {"Category": category, "Priority": priority, "Basis": basis, "Title": title,
            "Recommendation": recommendation, "Why": why, "Rule": rule, "Supporting Values": _fmt(values)}


# ---------------------------------------------------------------------------
# Rule families
# ---------------------------------------------------------------------------
def long_distance_recommendations(df, anomalies):
    """1a. IQR outlier routes; 1b. routes that contribute a large share of all unit-miles."""
    recs = []
    out = anomalies["route_outliers"]
    b = anomalies["route_bounds"]
    long_routes = out[out["Direction"] == "unusually long"] if "Direction" in out.columns else out.iloc[0:0]
    for _, r in long_routes.iterrows():
        orders = int(r["Shipments"])
        recs.append(_rec(
            "Long-distance route", "High" if orders >= HIGH_VOLUME_ORDERS else "Low", "Calculated",
            f"Unusually long route: {r['Route']}",
            "Investigate whether this route can be served from a closer factory or consolidated.",
            f"Its average straight-line distance is above the upper IQR fence for all routes.",
            f"Route average distance > Q3 + {b['multiplier']:g} x IQR (= {b['upper_fence']:,.0f} mi); "
            f"High priority if >= {HIGH_VOLUME_ORDERS} orders",
            {"Average distance": f"{r['Avg Distance (mi)']:,.0f} mi", "Orders": orders, "Q1": f"{b['q1']:,.0f} mi",
             "Q3": f"{b['q3']:,.0f} mi", "Upper fence": f"{b['upper_fence']:,.0f} mi"}))

    valid = df.dropna(subset=["Route Distance (mi)"]).copy()
    valid["Unit-Miles"] = valid["Units"] * valid["Route Distance (mi)"]
    total = valid["Unit-Miles"].sum()
    if total > 0:
        by_route = valid.groupby("Route (Factory-State)").agg(
            UM=("Unit-Miles", "sum"), Units=("Units", "sum"), Orders=("Order ID", "nunique"),
            Dist=("Route Distance (mi)", "mean")).reset_index()
        by_route["Share"] = by_route["UM"] / total
        contributors = by_route[by_route["Share"] >= DISTANCE_CONTRIBUTOR_SHARE].sort_values("Share", ascending=False)
        for _, r in contributors.iterrows():
            recs.append(_rec(
                "Long-distance route", "Medium", "Calculated", f"Large distance contributor: {r['Route (Factory-State)']}",
                "Review whether the volume on this route could be served from a nearer factory (see the hypothetical "
                "reassignments).",
                "This single route accounts for a large share of all unit-miles shipped.",
                f"Route unit-miles >= {100 * DISTANCE_CONTRIBUTOR_SHARE:g}% of total unit-miles",
                {"Share of unit-miles": f"{100 * r['Share']:.1f}%", "Unit-miles": f"{r['UM']:,.0f}", "Units": f"{int(r['Units']):,}",
                 "Orders": f"{int(r['Orders']):,}", "Average distance": f"{r['Dist']:,.0f} mi"}))
    return recs


def reassignment_recommendations(scenario_result):
    """2. HYPOTHETICAL alternative factories, from the optimiser's changed demand cells, summarised per product."""
    if scenario_result is None:
        return []
    if scenario_result["status"] != "OPTIMAL":
        return [_rec("Alternative factory allocation", "Low", "Hypothetical", "Optimizer scenario has no valid plan",
                     "Adjust the scenario assumptions (capacity or eligibility) before drawing conclusions.",
                     "The selected scenario could not be solved, so no reassignment can be suggested.",
                     "Solver status is not OPTIMAL",
                     {"Status": scenario_result["status"], "Detail": scenario_result["message"]})]
    cmp = scenario_result["comparison"]
    changed = cmp["changed_cells"]
    total = cmp["baseline_unit_miles"]
    if changed.empty or total <= 0:
        return []
    by_product = changed.groupby("Product Name").agg(
        Saved=("Unit-Miles Saved", "sum"), Cells=("Cell", "count"), Units=("Units Moved", "sum")).reset_index()
    by_product = by_product.sort_values("Saved", ascending=False).head(TOP_N_REASSIGNMENTS)
    alloc = scenario_result["allocation"]
    recs = []
    for _, r in by_product.iterrows():
        product = r["Product Name"]
        share = r["Saved"] / total
        if share <= 0:
            continue
        target = (alloc[alloc["Product Name"] == product].groupby("Factory")["Units"].sum().sort_values(ascending=False))
        target_text = ", ".join(f"{f} ({u:,.0f} units)" for f, u in target.head(3).items())
        current = rc.PRODUCT_FACTORY_MAP.get(product, "unknown")
        priority = "High" if share >= SAVING_HIGH else ("Medium" if share >= SAVING_MEDIUM else "Low")
        recs.append(_rec(
            "Alternative factory allocation", priority, "Hypothetical",
            f"Hypothetical: serve {product} from nearer factories",
            f"If {product} (currently made at {current}) could also be made elsewhere, the simulation would serve it from "
            f"{target_text}. Investigate whether that is operationally possible.",
            "The optimizer found nearer eligible factories for several state/province demand cells of this product.",
            f"Ranked by unit-miles saved; High if saving >= {100 * SAVING_HIGH:g}% of total unit-miles, "
            f"Medium if >= {100 * SAVING_MEDIUM:g}%",
            {"Unit-miles saved": f"{r['Saved']:,.0f}", "Share of total unit-miles": f"{100 * share:.1f}%",
             "Demand cells changed": int(r["Cells"]), "Units moved": f"{r['Units']:,.0f}",
             "Scenario": scenario_result["name"]}))
    return recs


def capacity_recommendations(unconstrained_units, capacities):
    """3. HYPOTHETICAL: factories whose unconstrained-plan volume would exceed the hypothetical capacity."""
    recs = []
    if not capacities:
        return recs
    for factory, cap in capacities.items():
        units = float(unconstrained_units.get(factory, 0.0))
        if cap is not None and units > cap + 1e-9:
            over = units - cap
            pct = 100 * over / cap if cap > 0 else float("inf")
            recs.append(_rec(
                "Factory capacity", "High" if (cap == 0 or pct >= 100) else "Medium", "Hypothetical",
                f"Hypothetical overload: {factory}",
                "The nearest-factory plan would overload this factory; treat the unconstrained savings as an upper "
                "bound and test realistic capacities.",
                "When every demand cell is sent to its nearest factory, this factory's volume exceeds the hypothetical "
                "capacity assumption.",
                "Unconstrained-plan units > hypothetical capacity; High if over by >= 100% (or capacity is 0)",
                {"Unconstrained-plan units": f"{units:,.0f}", "Hypothetical capacity": f"{cap:,}",
                 "Excess units": f"{over:,.0f}", "Over capacity by": "n/a (capacity 0)" if cap == 0 else f"{pct:.0f}%"}))
    return recs


def geography_recommendations(df):
    """4. Unusual geographical pattern: factories that ship much of their volume a long way."""
    recs = []
    valid = df.dropna(subset=["Route Distance (mi)"])
    for factory, g in valid.groupby("Factory"):
        units = g["Units"].sum()
        if units <= 0:
            continue
        far = g.loc[g["Route Distance (mi)"] > LONG_DISTANCE_MILES, "Units"].sum()
        share = far / units
        if share >= WIDE_REACH_SHARE:
            weighted_avg = float((g["Units"] * g["Route Distance (mi)"]).sum() / units)
            recs.append(_rec(
                "Geographic pattern", "High" if share >= 0.75 else "Medium", "Calculated",
                f"Wide-reach factory: {factory}",
                "Review whether this factory's customer footprint is intended, or whether regional supply would be shorter.",
                "A large share of this factory's units ships farther than the long-distance threshold.",
                f"Share of units shipped > {LONG_DISTANCE_MILES:,} mi is >= {100 * WIDE_REACH_SHARE:g}%; High if >= 75%",
                {"Units shipped over threshold": f"{100 * share:.0f}%", "Units": f"{units:,.0f}",
                 "Unit-weighted avg distance": f"{weighted_avg:,.0f} mi",
                 "States/provinces served": int(g["State/Province"].nunique()),
                 "Farthest destination": f"{g['Route Distance (mi)'].max():,.0f} mi"}))
    return recs


def data_quality_recommendations(df, anomalies):
    """5. Data-quality issues, taken from the anomaly detectors and known data caveats."""
    recs = []
    dup = anomalies["duplicates"]
    exact = int(dup["Identical Values"].sum()) if len(dup) else 0
    other = len(dup) - exact
    if exact:
        recs.append(_rec("Data quality", "High", "Dataset", "Possible exact duplicate order lines",
                         "Verify with the data owner whether these lines are duplicates before relying on sales or unit totals. "
                         "No record has been removed.",
                         "Lines share Order ID + Product ID and every compared value (sales, units, profit, cost, ship mode, dates).",
                         "Same Order ID + Product ID and identical values on all compared fields",
                         {"Lines involved": f"{exact:,}", "Sales on these lines": f"${dup.loc[dup['Identical Values'], 'Sales'].sum():,.2f}"}))
    if other:
        recs.append(_rec("Data quality", "Medium", "Dataset", "Repeated Order ID + Product ID with different values",
                         "Check whether these are legitimate additional order lines. No record has been removed.",
                         "Lines share Order ID + Product ID but differ in sales, units or other values.",
                         "Same Order ID + Product ID, at least one compared value differs", {"Lines involved": f"{other:,}"}))
    geo = anomalies["missing_geography"]
    if len(geo):
        recs.append(_rec("Data quality", "High", "Dataset", "Records with missing geographical information",
                         "Complete the location fields or extend the reference table; these records are excluded from "
                         "distance metrics and the optimizer.",
                         "Location fields are blank or the state/province centroid or factory is unknown.",
                         "Any blank location field, unknown centroid or unmapped factory",
                         {"Records": len(geo), "Units excluded": f"{geo['Units'].sum():,.0f}"}))
    canada = df[df["Country/Region"] == "Canada"]
    if len(canada) and rc.CANADA_CENTROIDS_STATUS == "PROVISIONAL":
        recs.append(_rec("Data quality", "Medium", "Calculated", "Canadian distances use provisional centroids",
                         "Verify the province centroid coordinates against an authoritative source before presenting "
                         "Canadian distances as exact.",
                         "No authoritative centroid table was found; values are approximate.",
                         "Canadian rows exist and centroid status is PROVISIONAL",
                         {"Canadian order lines": len(canada), "Share of lines": f"{100 * len(canada) / len(df):.1f}%"}))
    mism = anomalies["factory_product_lines"]
    if len(mism):
        names = ", ".join(sorted(mism["Product Name"].unique()))
        recs.append(_rec("Data quality", "Low", "Dataset", "Product ID prefix disagrees with Division",
                         "Confirm the product's division or ID with the data owner.",
                         "The 3-letter Product ID prefix implies a different division than the Division column.",
                         "Product ID prefix (CHO/SUG/OTH) not equal to Division", {"Lines": len(mism), "Products": names}))
    low = anomalies["factory_product_summary"]
    low_fac = low[low["Kind"] == "Factory"] if len(low) else low
    if len(low_fac):
        recs.append(_rec("Data quality", "Low", "Dataset", "Very-low-volume factories",
                         "Interpret factory comparisons and optimizer results for these factories with care; see "
                         "docs/SUGAR_SHACK_INVESTIGATION.md.",
                         "These factories have too few order lines for stable comparisons.",
                         "Factory share of order lines below 1%",
                         {"Factories": ", ".join(low_fac["Subject"]), "Shares": ", ".join(f"{s:.2f}%" for s in low_fac["Share of lines %"])}))
    const = anomalies.get("constant_prices", pd.DataFrame())
    if len(const):
        recs.append(_rec("Data quality", "Low", "Dataset", "Prices and margins never vary within a product",
                         "Treat sales and profit patterns with caution: the data contains no price variation to analyse.",
                         "Every line of these products has the same unit price and margin.",
                         "One distinct unit price and margin across >= 8 lines of a product", {"Products": len(const)}))
    return recs


# ---------------------------------------------------------------------------
# Everything at once
# ---------------------------------------------------------------------------
def generate_recommendations(df, anomalies=None, scenario_result=None, unconstrained_units=None, capacities=None):
    """Run all rule families. Returns a DataFrame (COLUMNS), High priority first, with stable IDs."""
    anomalies = detect_all(df) if anomalies is None else anomalies
    recs = (long_distance_recommendations(df, anomalies) + reassignment_recommendations(scenario_result)
            + (capacity_recommendations(unconstrained_units, capacities) if unconstrained_units is not None else [])
            + geography_recommendations(df) + data_quality_recommendations(df, anomalies))
    if not recs:
        return pd.DataFrame(columns=COLUMNS)
    table = pd.DataFrame(recs)
    table["_p"] = table["Priority"].map(_PRIORITY_ORDER)
    table = table.sort_values(["_p", "Category"], kind="stable").drop(columns="_p").reset_index(drop=True)
    table.insert(0, "ID", [f"R{i:02d}" for i in range(1, len(table) + 1)])
    return table[COLUMNS]
