"""Tests for modules/anomaly_detection.py (flags only; nothing is modified)."""
import numpy as np
import pandas as pd
import pytest

import route_core as rc
from modules import anomaly_detection as ad


def line(row_id, order="o1", product_id="CHO-AAA-1", product="Prod", sales=10.0, units=2, gp=6.0, cost=4.0,
         state="Texas", factory="F1", division="Chocolate", mode="Standard Class", dist=500.0, lat=31.0, lon=-97.0,
         city="Austin", postal="73301", customer=1, region="Gulf", country="United States", odate="2024-01-01"):
    return {"Row ID": row_id, "Order ID": order, "Product ID": product_id, "Product Name": product, "Sales": sales,
            "Units": units, "Gross Profit": gp, "Cost": cost, "State/Province": state, "Factory": factory,
            "Division": division, "Ship Mode": mode, "Route Distance (mi)": dist, "Customer Lat": lat,
            "Customer Lon": lon, "City": city, "Postal Code": postal, "Customer ID": customer, "Region": region,
            "Country/Region": country, "Order Date": pd.Timestamp(odate), "Ship Date": pd.Timestamp("2026-01-01"),
            "Units ": units}


def frame(rows):
    df = pd.DataFrame(rows).drop(columns=["Units "])
    df["Raw Lead Time (days)"] = np.nan
    df["Route (Factory-Region)"] = df["Factory"] + " -> " + df["Region"]
    df["Route (Factory-State)"] = df["Factory"] + " -> " + df["State/Province"]
    return df


# ---- IQR --------------------------------------------------------------------------------------------------------------
def test_iqr_bounds_worked_example():
    q1, q3, iqr, lower, upper = ad.iqr_bounds([300, 800, 1500, 2200, 5000])
    assert (q1, q3, iqr, upper) == (800, 2200, 1400, 4300) and lower == 800 - 2100


def test_iqr_bounds_too_few_values_are_nan():
    assert all(np.isnan(v) for v in ad.iqr_bounds([1, 2, 3]))


def test_route_outlier_flagged_with_reason_and_values():
    rows = [line(i, order=f"o{i}", state=f"S{i}", dist=d) for i, d in
            enumerate([300, 350, 400, 450, 500, 550, 600, 650, 5000], start=1)]
    flagged, bounds = ad.route_distance_outliers(frame(rows), "State/Province")
    assert list(flagged["Route"]) == ["F1 -> S9"] and flagged.iloc[0]["Direction"] == "unusually long"
    assert flagged.iloc[0]["Avg Distance (mi)"] == 5000 and bounds["upper_fence"] < 5000
    assert "outside the IQR fence" in flagged.iloc[0]["Reason"] and "Q3" in flagged.iloc[0]["Reason"]


def test_route_outliers_ignore_unknown_distance():
    rows = [line(i, order=f"o{i}", state=f"S{i}", dist=d) for i, d in
            enumerate([300, 350, 400, 450, 500, 550, 600, 650, np.nan], start=1)]
    flagged, bounds = ad.route_distance_outliers(frame(rows), "State/Province")
    assert flagged.empty and bounds["routes_assessed"] == 8


def test_records_for_route_returns_underlying_lines_without_changing_input():
    df = frame([line(1, state="A"), line(2, order="o2", state="A"), line(3, order="o3", state="B")])
    snap = df.copy(deep=True)
    out = ad.records_for_route(df, "F1 -> A")
    assert list(out["Row ID"]) == [1, 2]
    pd.testing.assert_frame_equal(df, snap)


# ---- duplicates ---------------------------------------------------------------------------------------------------------
def test_duplicates_identical_vs_different_values():
    df = frame([line(1, order="oA"), line(2, order="oA"),                          # exact duplicate pair
                line(3, order="oB", sales=10.0), line(4, order="oB", sales=20.0, units=4),   # same keys, different values
                line(5, order="oC")])                                              # unique
    d = ad.duplicate_order_lines(df).set_index("Row ID")
    assert set(d.index) == {1, 2, 3, 4}
    assert d.loc[1, "Anomaly Type"].startswith("Duplicate order line") and d.loc[1, "Identical Values"]
    assert d.loc[3, "Anomaly Type"].startswith("Repeated Order ID") and not d.loc[3, "Identical Values"]
    assert "not removed" in d.loc[1, "Reason"] and (d["Group Size"] == 2).all()


def test_no_duplicates_gives_empty_result():
    assert ad.duplicate_order_lines(frame([line(1, order="a"), line(2, order="b")])).empty


# ---- missing geography ---------------------------------------------------------------------------------------------------
def test_missing_geography_reasons():
    df = frame([line(1), line(2, order="o2", lat=np.nan, lon=np.nan, state="Atlantis"),
                line(3, order="o3", city=None), line(4, order="o4", factory=np.nan)])
    out = ad.missing_geography(df).set_index("Row ID")
    assert set(out.index) == {2, 3, 4}
    assert "Unknown state/province centroid" in out.loc[2, "Reason"] and "never treated as 0" in out.loc[2, "Reason"]
    assert "Blank City" in out.loc[3, "Reason"] and "no mapped factory" in out.loc[4, "Reason"]


# ---- sales / profit ---------------------------------------------------------------------------------------------------------
def test_unit_price_outlier_flagged_within_product():
    rows = [line(i, order=f"o{i}", sales=10.0 + (i % 3) * 0.2, units=2, gp=6.0, cost=4.0 + (i % 3) * 0.2) for i in range(1, 11)]
    rows.append(line(11, order="o11", sales=90.0, units=2, gp=86.0, cost=4.0))          # unit price 45 vs ~5
    out = ad.sales_profit_anomalies(frame(rows))
    assert 11 in set(out["Row ID"]) and "unit price" in " ".join(out["Anomaly Type"]).lower()
    assert "IQR range" in out.loc[out["Row ID"] == 11, "Reason"].iloc[0]


def test_constant_price_group_flags_any_deviation():
    rows = [line(i, order=f"o{i}") for i in range(1, 11)] + [line(11, order="o11", sales=12.0, units=2, gp=8.0, cost=4.0)]
    out = ad.sales_profit_anomalies(frame(rows))
    assert set(out["Row ID"]) == {11}                                       # only the deviating line


def test_arithmetic_and_negative_profit_checks():
    rows = [line(i, order=f"o{i}") for i in range(1, 10)]
    rows.append(line(10, order="o10", sales=10.0, gp=7.0, cost=4.0))                  # 7 + 4 != 10
    rows.append(line(11, order="o11", sales=10.0, gp=-2.0, cost=12.0))                # a loss
    types = ad.sales_profit_anomalies(frame(rows)).groupby("Row ID")["Anomaly Type"].apply(list)
    assert "Gross Profit + Cost does not equal Sales" in types[10]
    assert "Negative gross profit" in types[11]


def test_constant_price_observation_listed_not_flagged():
    df = frame([line(i, order=f"o{i}") for i in range(1, 11)])
    obs = ad.constant_price_products(df)
    assert list(obs["Product Name"]) == ["Prod"] and ad.sales_profit_anomalies(df).empty


# ---- factory/product distribution ---------------------------------------------------------------------------------------------
def test_product_id_prefix_vs_division_mismatch():
    df = frame([line(1, product_id="OTH-FIZ-1", division="Sugar", product="Fizzy"), line(2, order="o2")])
    lines_, _ = ad.factory_product_distribution(df)
    assert list(lines_["Row ID"]) == [1] and "prefix OTH" in lines_.iloc[0]["Reason"]


def test_low_volume_factory_and_product_flagged_with_share():
    rows = [line(i, order=f"o{i}") for i in range(1, 300)] + [line(1000, order="rare", factory="F2", product="Rare")]
    _, summary = ad.factory_product_distribution(frame(rows))
    kinds = set(summary["Anomaly Type"])
    assert {"Factory with very low volume", "Product with very low volume"} <= kinds
    assert (summary["Share of lines %"] < 1).all() and summary["Reason"].str.contains("threshold").all()


# ---- real data -----------------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def real():
    df, _ = rc.load_and_clean()
    return df, df.copy(deep=True), ad.detect_all(df)


def test_real_data_known_findings(real):
    _, _, r = real
    s = r["summary"].set_index("Check")["Flagged"]
    assert s["Missing geographical information"] == 0
    assert s["Duplicate / repeated order lines"] == 3018
    assert s["Product ID vs Division mismatch"] == 6
    assert list(r["route_outliers"]["Route"]) == ["Lot's O' Nuts -> Newfoundland and Labrador"]
    assert int(r["duplicates"]["Identical Values"].sum()) == 396
    assert len(r["constant_prices"]) == 10 and len(r["sales_profit"]) == 0   # 5 products have < 8 lines (too few to assess)


def test_every_flagged_record_has_a_reason(real):
    _, _, r = real
    for key in ["route_outliers", "duplicates", "missing_geography", "sales_profit", "factory_product_lines",
                "factory_product_summary"]:
        t = r[key]
        assert t["Reason"].astype(str).str.len().gt(10).all(), key
        assert "Anomaly Type" in t.columns


def test_detection_never_modifies_the_input(real):
    df, snapshot, _ = real
    ad.detect_all(df)
    pd.testing.assert_frame_equal(df, snapshot)
