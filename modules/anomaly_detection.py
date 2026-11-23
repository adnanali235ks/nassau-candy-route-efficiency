"""
Rule-based anomaly detection. Simple statistics only (IQR and fixed, documented thresholds): no ML.

Every detector returns a DataFrame of FLAGGED records with the columns
    "Anomaly Type", "Reason" (plain language), plus identifying and supporting-value columns.
Nothing is deleted, corrected or modified: the input DataFrame is only read.

IQR rule (Tukey fences), in simple terms
  sort the values; Q1 = value 25% of the way up, Q3 = value 75% of the way up; IQR = Q3 - Q1
  lower fence = Q1 - 1.5 * IQR,  upper fence = Q3 + 1.5 * IQR
  a value outside the fences is flagged as "unusual" (not necessarily wrong).
  Example: 300, 800, 1500, 2200, 5000 -> Q1 800, Q3 2200, IQR 1400, upper fence 4300 -> 5000 is flagged.
"""

import numpy as np
import pandas as pd

import route_core as rc

IQR_MULTIPLIER = 1.5
MIN_GROUP_SIZE_FOR_IQR = 8          # per-product statistics need at least this many lines
LOW_VOLUME_FACTORY_SHARE = 0.01     # factory with < 1% of order lines
LOW_VOLUME_PRODUCT_SHARE = 0.005    # product with < 0.5% of order lines
_PRODUCT_ID_PREFIX = {"CHO": "Chocolate", "SUG": "Sugar", "OTH": "Other"}


def iqr_bounds(values, multiplier=IQR_MULTIPLIER):
    """Return (q1, q3, iqr, lower_fence, upper_fence) of the non-missing values (NaNs if too few)."""
    v = pd.Series(values, dtype="float64").dropna()
    if len(v) < 4:
        return (np.nan,) * 5
    q1, q3 = np.percentile(v, [25, 75])
    iqr = q3 - q1
    return q1, q3, iqr, q1 - multiplier * iqr, q3 + multiplier * iqr


# ---------------------------------------------------------------------------
# 1. IQR route-distance outliers
# ---------------------------------------------------------------------------
def route_distance_outliers(df, level="State/Province", multiplier=IQR_MULTIPLIER):
    """Routes (factory -> state/province or region) whose average distance is outside the IQR fences.

    Returns (flagged_routes, bounds). Routes with unknown distance cannot be assessed and are not flagged.
    """
    summary = rc.route_summary(df, level, include_unscored=True)[
        ["Route", "Factory", "Shipments", "Units", "Avg Distance (mi)"]]
    known = summary.dropna(subset=["Avg Distance (mi)"]).copy()
    q1, q3, iqr, lower, upper = iqr_bounds(known["Avg Distance (mi)"], multiplier)
    bounds = {"q1": q1, "q3": q3, "iqr": iqr, "lower_fence": lower, "upper_fence": upper,
              "multiplier": multiplier, "routes_assessed": int(len(known))}
    if np.isnan(upper):
        return known.iloc[0:0].assign(**{"Anomaly Type": [], "Reason": []}), bounds
    high = known["Avg Distance (mi)"] > upper
    low = known["Avg Distance (mi)"] < lower
    flagged = known[high | low].copy()
    flagged["Anomaly Type"] = "Route distance outlier (IQR)"
    flagged["Direction"] = np.where(flagged["Avg Distance (mi)"] > upper, "unusually long", "unusually short")
    flagged["Fence (mi)"] = np.where(flagged["Avg Distance (mi)"] > upper, upper, lower)
    flagged["Reason"] = flagged.apply(
        lambda r: (f"Average distance {r['Avg Distance (mi)']:,.0f} mi is {r['Direction']}: outside the IQR "
                   f"fence of {r['Fence (mi)']:,.0f} mi (Q1 {q1:,.0f}, Q3 {q3:,.0f}, multiplier {multiplier:g}) "
                   f"across {bounds['routes_assessed']} routes."), axis=1)
    return flagged.sort_values("Avg Distance (mi)", ascending=False).reset_index(drop=True), bounds


def records_for_route(df, route_label, level="State/Province"):
    """The underlying order lines of one route, for inspection (a filtered copy; nothing changes)."""
    col = "Route (Factory-Region)" if level == "Region" else "Route (Factory-State)"
    return df[df[col] == route_label].copy()


# ---------------------------------------------------------------------------
# 2. Duplicate order lines
# ---------------------------------------------------------------------------
def duplicate_order_lines(df):
    """Lines that share an Order ID + Product ID with at least one other line.

    "Identical values" (same Sales, Units, Gross Profit, Cost, Ship Mode, Dates) is a likely exact duplicate;
    "Different values" may be a legitimate extra order line. Neither is removed.
    """
    key = ["Order ID", "Product ID"]
    dup = df[df.duplicated(subset=key, keep=False)].copy()
    if dup.empty:
        return dup.assign(**{"Anomaly Type": [], "Reason": []})
    compare = ["Sales", "Units", "Gross Profit", "Cost", "Ship Mode", "Order Date", "Ship Date"]
    dup["Group Size"] = dup.groupby(key)["Row ID"].transform("count")
    distinct_values = dup.groupby(key)[compare].transform(lambda s: s.nunique(dropna=False)).max(axis=1)
    dup["Identical Values"] = distinct_values == 1
    dup["Anomaly Type"] = np.where(dup["Identical Values"], "Duplicate order line (identical values)",
                                   "Repeated Order ID + Product ID (different values)")
    dup["Reason"] = np.where(
        dup["Identical Values"],
        "Order ID + Product ID appears " + dup["Group Size"].astype(str) + " times with identical Sales, Units, "
        "Gross Profit, Cost, Ship Mode and dates: likely an exact duplicate (not removed).",
        "Order ID + Product ID appears " + dup["Group Size"].astype(str) + " times with different values: "
        "possibly a legitimate extra order line, needs checking (not removed).")
    cols = ["Row ID", "Order ID", "Product ID", "Product Name", "Customer ID", "State/Province", "Sales", "Units",
            "Group Size", "Identical Values", "Anomaly Type", "Reason"]
    return dup[cols].sort_values(["Order ID", "Product ID", "Row ID"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 3. Missing geographical information
# ---------------------------------------------------------------------------
def missing_geography(df):
    """Lines with a blank location field, an unknown state/province centroid, or an unmapped factory."""
    reasons = pd.DataFrame(index=df.index)
    for col in ["State/Province", "City", "Postal Code", "Region", "Country/Region"]:
        if col in df:
            reasons[f"Blank {col}"] = df[col].isna() | (df[col].astype(str).str.strip() == "")
    reasons["Unknown state/province centroid"] = df["Customer Lat"].isna() | df["Customer Lon"].isna()
    reasons["Product has no mapped factory"] = df["Factory"].isna()
    flagged_mask = reasons.any(axis=1)
    out = df.loc[flagged_mask, ["Row ID", "Order ID", "Product Name", "Customer ID", "Country/Region",
                                "State/Province", "City", "Postal Code", "Sales", "Units"]].copy()
    if out.empty:
        return out.assign(**{"Anomaly Type": [], "Reason": []})
    out["Anomaly Type"] = "Missing geographical information"
    out["Reason"] = reasons.loc[flagged_mask].apply(
        lambda r: "; ".join(c for c in reasons.columns if r[c]) + ". Distance cannot be calculated; the record is excluded "
                  "from distance metrics and the optimizer, never treated as 0 miles.", axis=1)
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 4. Sales and gross-profit patterns
# ---------------------------------------------------------------------------
def sales_profit_anomalies(df, multiplier=IQR_MULTIPLIER):
    """Unusual unit price or margin (IQR within each product), and gross profit that does not add up."""
    d = df.copy()
    d["Unit Price"] = d["Sales"] / d["Units"]
    d["Margin %"] = 100 * d["Gross Profit"] / d["Sales"]
    findings = []
    for product, g in d.groupby("Product Name"):
        if len(g) < MIN_GROUP_SIZE_FOR_IQR:
            continue
        for metric, label in (("Unit Price", "unit price"), ("Margin %", "gross margin %")):
            q1, q3, iqr, lower, upper = iqr_bounds(g[metric], multiplier)
            if np.isnan(upper):
                continue
            if iqr == 0:
                # Most lines share one value, so the fences collapse onto it: ANY different value is unusual.
                lower = upper = float(np.median(g[metric]))
                bad = g[~np.isclose(g[metric], lower, atol=1e-9)]
            else:
                bad = g[(g[metric] > upper) | (g[metric] < lower)]
            for idx, r in bad.iterrows():
                findings.append({"index": idx, "Anomaly Type": f"Unusual {label} for product (IQR)",
                                 "Reason": (f"{label.capitalize()} {r[metric]:,.2f} is outside {product}'s IQR range "
                                            f"[{lower:,.2f}, {upper:,.2f}] (Q1 {q1:,.2f}, Q3 {q3:,.2f}, "
                                            f"{len(g)} lines).")})
    mismatch = ~np.isclose(d["Gross Profit"] + d["Cost"], d["Sales"], atol=0.02)
    for idx in d.index[mismatch]:
        findings.append({"index": idx, "Anomaly Type": "Gross Profit + Cost does not equal Sales",
                         "Reason": f"Gross Profit {d.at[idx, 'Gross Profit']:,.2f} + Cost {d.at[idx, 'Cost']:,.2f} = "
                                   f"{d.at[idx, 'Gross Profit'] + d.at[idx, 'Cost']:,.2f}, but Sales is {d.at[idx, 'Sales']:,.2f}."})
    for idx in d.index[d["Gross Profit"] < 0]:
        findings.append({"index": idx, "Anomaly Type": "Negative gross profit",
                         "Reason": f"Gross Profit is {d.at[idx, 'Gross Profit']:,.2f} (a loss on this line)."})
    cols = ["Row ID", "Order ID", "Product Name", "Factory", "Sales", "Units", "Unit Price", "Gross Profit", "Cost",
            "Margin %"]
    if not findings:
        return pd.DataFrame(columns=cols + ["Anomaly Type", "Reason"])
    f = pd.DataFrame(findings)
    out = d.loc[f["index"], cols].reset_index(drop=True)
    out["Anomaly Type"], out["Reason"] = f["Anomaly Type"].to_numpy(), f["Reason"].to_numpy()
    return out


def constant_price_products(df):
    """Observation (not an anomaly): products whose every line has the same unit price and margin."""
    d = df.assign(**{"Unit Price": (df["Sales"] / df["Units"]).round(4),
                     "Margin %": (100 * df["Gross Profit"] / df["Sales"]).round(2)})
    g = d.groupby("Product Name").agg(Lines=("Row ID", "count"), Prices=("Unit Price", "nunique"),
                                      Margins=("Margin %", "nunique"), Unit_Price=("Unit Price", "first"),
                                      Margin_pct=("Margin %", "first")).reset_index()
    g = g[(g["Prices"] == 1) & (g["Margins"] == 1) & (g["Lines"] >= MIN_GROUP_SIZE_FOR_IQR)]
    g = g.rename(columns={"Unit_Price": "Unit Price", "Margin_pct": "Margin %"})
    g["Observation"] = ("All " + g["Lines"].astype(str) + " lines have the same unit price and margin, so "
                        "price/margin outliers cannot occur; real price variation is absent from the data.")
    return g[["Product Name", "Lines", "Unit Price", "Margin %", "Observation"]].reset_index(drop=True)


# ---------------------------------------------------------------------------
# 5. Factory-product distribution
# ---------------------------------------------------------------------------
def factory_product_distribution(df):
    """Unusual patterns between factories, products and divisions. Returns (line_level, summary_level)."""
    prefix_div = df["Product ID"].astype(str).str[:3].map(_PRODUCT_ID_PREFIX)
    mismatch = df[prefix_div.notna() & (prefix_div != df["Division"])].copy()
    mismatch["Anomaly Type"] = "Product ID prefix disagrees with Division"
    mismatch["Reason"] = ("Product ID " + mismatch["Product ID"].astype(str) + " has prefix "
                          + mismatch["Product ID"].astype(str).str[:3] + " (= "
                          + mismatch["Product ID"].astype(str).str[:3].map(_PRODUCT_ID_PREFIX)
                          + ") but Division is " + mismatch["Division"].astype(str) + ".")
    line_level = mismatch[["Row ID", "Order ID", "Product ID", "Product Name", "Division", "Factory",
                           "Anomaly Type", "Reason"]].reset_index(drop=True)

    total = len(df)
    rows = []
    fac = df.groupby("Factory").agg(Lines=("Row ID", "count"), Units=("Units", "sum"), Sales=("Sales", "sum"),
                                    Products=("Product Name", "nunique")).reset_index()
    for r in fac.itertuples():
        share = r.Lines / total
        if share < LOW_VOLUME_FACTORY_SHARE:
            rows.append({"Subject": r.Factory, "Kind": "Factory", "Anomaly Type": "Factory with very low volume",
                         "Order Lines": r.Lines, "Share of lines %": 100 * share, "Units": r.Units, "Sales": r.Sales,
                         "Reason": (f"{r.Factory} has {r.Lines:,} order lines ({100 * share:.2f}% of all lines), below "
                                    f"the {100 * LOW_VOLUME_FACTORY_SHARE:g}% threshold, across {r.Products} products.")})
    prod = df.groupby(["Product Name", "Factory"]).agg(Lines=("Row ID", "count"), Units=("Units", "sum"),
                                                       Sales=("Sales", "sum")).reset_index()
    for r in prod.itertuples():
        share = r.Lines / total
        if share < LOW_VOLUME_PRODUCT_SHARE:
            rows.append({"Subject": f"{r._1} ({r.Factory})", "Kind": "Product", "Anomaly Type": "Product with very low volume",
                         "Order Lines": r.Lines, "Share of lines %": 100 * share, "Units": r.Units, "Sales": r.Sales,
                         "Reason": (f"{r._1} has {r.Lines:,} order lines ({100 * share:.2f}% of all lines), below the "
                                    f"{100 * LOW_VOLUME_PRODUCT_SHARE:g}% threshold.")})
    summary = pd.DataFrame(rows, columns=["Subject", "Kind", "Anomaly Type", "Order Lines", "Share of lines %",
                                          "Units", "Sales", "Reason"])
    return line_level, summary


# ---------------------------------------------------------------------------
# Everything at once
# ---------------------------------------------------------------------------
def detect_all(df):
    """Run every detector on a (filtered) DataFrame. Returns a dict of results plus a count summary."""
    routes, bounds = route_distance_outliers(df, "State/Province")
    dup = duplicate_order_lines(df)
    geo = missing_geography(df)
    sales = sales_profit_anomalies(df)
    fp_lines, fp_summary = factory_product_distribution(df)
    summary = pd.DataFrame([
        {"Check": "Route distance outliers (IQR)", "Flagged": len(routes), "Unit": "routes",
         "Note": f"{bounds['routes_assessed']} routes assessed"},
        {"Check": "Duplicate / repeated order lines", "Flagged": len(dup), "Unit": "order lines",
         "Note": f"{int(dup['Identical Values'].sum()) if len(dup) else 0} with identical values"},
        {"Check": "Missing geographical information", "Flagged": len(geo), "Unit": "order lines", "Note": ""},
        {"Check": "Unusual sales / gross-profit patterns", "Flagged": len(sales), "Unit": "order lines",
         "Note": f"{len(constant_price_products(df))} products have one constant price and margin"},
        {"Check": "Product ID vs Division mismatch", "Flagged": len(fp_lines), "Unit": "order lines", "Note": ""},
        {"Check": "Very-low-volume factories / products", "Flagged": len(fp_summary), "Unit": "factories/products",
         "Note": ""}])
    return {"route_outliers": routes, "route_bounds": bounds, "duplicates": dup, "missing_geography": geo,
            "sales_profit": sales, "constant_prices": constant_price_products(df), "factory_product_lines": fp_lines, "factory_product_summary": fp_summary,
            "summary": summary}
