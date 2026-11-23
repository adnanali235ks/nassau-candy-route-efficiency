"""Tests for modules/recommendations.py: every recommendation must explain itself with real values."""
import pandas as pd
import pytest

import route_core as rc
from modules import recommendations as rec
from modules import scenarios as sc
from modules.anomaly_detection import detect_all
from modules.scenarios import Scenario


def make_df(rows):
    """rows: (row, order, factory, state, units, distance, country)"""
    df = pd.DataFrame(rows, columns=["Row ID", "Order ID", "Factory", "State/Province", "Units",
                                     "Route Distance (mi)", "Country/Region"])
    df["Product ID"] = "CHO-X-1"
    df["Route (Factory-State)"] = df["Factory"] + " -> " + df["State/Province"]
    return df


def empty_anoms():
    return {"route_outliers": pd.DataFrame(), "route_bounds": {"multiplier": 1.5, "upper_fence": 0, "q1": 0, "q3": 0},
            "duplicates": pd.DataFrame(), "missing_geography": pd.DataFrame(), "factory_product_lines": pd.DataFrame(),
            "factory_product_summary": pd.DataFrame(), "constant_prices": pd.DataFrame()}


def assert_explained(table):
    """Every recommendation carries a reason, a rule and supporting values."""
    assert len(table) > 0
    for col in ["Why", "Rule", "Supporting Values", "Recommendation", "Title"]:
        assert table[col].astype(str).str.len().gt(3).all(), col
    assert set(table["Priority"]) <= {"High", "Medium", "Low"}
    assert set(table["Basis"]) <= {"Dataset", "Calculated", "Hypothetical"}


# ---- long distance --------------------------------------------------------------------------------
def test_outlier_route_recommended_with_fence_values_and_priority_by_volume():
    anoms = empty_anoms()
    anoms["route_bounds"] = {"multiplier": 1.5, "upper_fence": 2720.0, "q1": 679.0, "q3": 1495.0}
    anoms["route_outliers"] = pd.DataFrame({"Route": ["F1 -> Far", "F1 -> Tiny"], "Shipments": [500, 5],
                                            "Avg Distance (mi)": [2979.0, 3100.0], "Direction": ["unusually long"] * 2})
    out = pd.DataFrame(rec.long_distance_recommendations(make_df([(1, "o", "F1", "S", 1, 100.0, "United States")]), anoms))
    prio = dict(zip(out["Title"], out["Priority"]))
    assert prio["Unusually long route: F1 -> Far"] == "High" and prio["Unusually long route: F1 -> Tiny"] == "Low"
    far = out[out["Title"].str.contains("Far")].iloc[0]
    assert "2,979 mi" in far["Supporting Values"] and "2,720 mi" in far["Rule"]


def test_large_distance_contributor_rule_uses_share_of_unit_miles():
    df = make_df([(1, "a", "F1", "Far", 100, 2000.0, "United States"), (2, "b", "F1", "Near", 100, 10.0, "United States")])
    out = pd.DataFrame(rec.long_distance_recommendations(df, empty_anoms()))
    assert list(out["Title"]) == ["Large distance contributor: F1 -> Far"]
    assert "99.5%" in out.iloc[0]["Supporting Values"] and ">= 5%" in out.iloc[0]["Rule"]


# ---- hypothetical reassignment ------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def real():
    df, _ = rc.load_and_clean()
    ctx = sc.prepare_context(df)
    free = sc.run_scenario(ctx, Scenario("No limits"))
    return df, ctx, free


def test_reassignment_recommendations_are_hypothetical_and_ranked(real):
    _, _, free = real
    out = pd.DataFrame(rec.reassignment_recommendations(free))
    assert 1 <= len(out) <= rec.TOP_N_REASSIGNMENTS and (out["Basis"] == "Hypothetical").all()
    saved = out["Supporting Values"].str.extract(r"Unit-miles saved: ([\d,]+)")[0].str.replace(",", "").astype(float)
    assert saved.is_monotonic_decreasing and (saved > 0).all()
    assert out["Title"].str.startswith("Hypothetical").all() and out["Recommendation"].str.contains("operationally possible").all()
    assert out["Why"].str.contains("optimizer").all()


def test_infeasible_scenario_gives_explanatory_recommendation_not_a_plan(real):
    _, ctx, _ = real
    bad = sc.run_scenario(ctx, Scenario("bad", "custom", locked_products=("Nerds",), excluded_factories=("Sugar Shack",)))
    out = pd.DataFrame(rec.reassignment_recommendations(bad))
    assert len(out) == 1 and "no valid plan" in out.iloc[0]["Title"] and "INFEASIBLE" in out.iloc[0]["Supporting Values"]
    assert rec.reassignment_recommendations(None) == []


# ---- capacity -----------------------------------------------------------------------------------------------------------
def test_capacity_exceedance_flags_only_overloaded_factories():
    plan = pd.Series({"A": 500.0, "B": 90.0, "C": 10.0})
    out = pd.DataFrame(rec.capacity_recommendations(plan, {"A": 200, "B": 100, "C": 0}))
    assert set(out["Title"]) == {"Hypothetical overload: A", "Hypothetical overload: C"}     # B is within capacity
    a = out[out["Title"].str.endswith("A")].iloc[0]
    assert "Excess units: 300" in a["Supporting Values"] and "150%" in a["Supporting Values"] and a["Priority"] == "High"
    assert out[out["Title"].str.endswith("C")].iloc[0]["Priority"] == "High"                 # capacity 0
    assert rec.capacity_recommendations(plan, None) == []


def test_real_unconstrained_plan_overloads_small_factories_under_current_plus_20(real):
    _, ctx, free = real
    from modules.optimization import capacity_from_current
    caps = capacity_from_current(ctx["current_volume"], 20)
    units = free["allocation"].groupby("Factory")["Units"].sum()
    out = pd.DataFrame(rec.capacity_recommendations(units, caps))
    assert {"Hypothetical overload: Sugar Shack", "Hypothetical overload: Secret Factory"} <= set(out["Title"])
    assert (out["Basis"] == "Hypothetical").all()


# ---- geography ----------------------------------------------------------------------------------------------------------------
def test_wide_reach_factory_rule():
    far = [(i, f"o{i}", "Wide", f"S{i % 5}", 10, 2000.0, "United States") for i in range(1, 9)]
    near = [(100 + i, f"n{i}", "Local", f"S{i % 5}", 10, 100.0, "United States") for i in range(1, 9)]
    df = make_df(far + near)
    out = pd.DataFrame(rec.geography_recommendations(df))
    assert list(out["Title"]) == ["Wide-reach factory: Wide"] and out.iloc[0]["Priority"] == "High"
    assert "100%" in out.iloc[0]["Supporting Values"] and "1,500" in out.iloc[0]["Rule"]


# ---- data quality ------------------------------------------------------------------------------------------------------------------
def test_data_quality_recommendations_from_anomalies_with_counts():
    anoms = empty_anoms()
    anoms["duplicates"] = pd.DataFrame({"Identical Values": [True, True, False], "Sales": [10.0, 10.0, 5.0]})
    anoms["missing_geography"] = pd.DataFrame({"Units": [3, 4]})
    anoms["factory_product_lines"] = pd.DataFrame({"Product Name": ["Fizzy"]})
    anoms["factory_product_summary"] = pd.DataFrame({"Kind": ["Factory"], "Subject": ["Sugar Shack"], "Share of lines %": [0.32]})
    df = make_df([(1, "o", "F1", "S", 1, 1.0, "United States")])
    out = pd.DataFrame(rec.data_quality_recommendations(df, anoms)).set_index("Title")
    assert out.loc["Possible exact duplicate order lines", "Priority"] == "High"
    assert "Lines involved: 2" in out.loc["Possible exact duplicate order lines", "Supporting Values"]
    assert "No record has been removed" in out.loc["Possible exact duplicate order lines", "Recommendation"]
    assert out.loc["Records with missing geographical information", "Priority"] == "High"
    assert "Units excluded: 7" in out.loc["Records with missing geographical information", "Supporting Values"]
    assert "Very-low-volume factories" in out.index and "Product ID prefix disagrees with Division" in out.index


# ---- everything ----------------------------------------------------------------------------------------------------------------------
def test_generate_recommendations_real_data_is_sorted_explained_and_non_destructive(real):
    df, ctx, free = real
    snapshot = df.copy(deep=True)
    from modules.optimization import capacity_from_current
    caps = capacity_from_current(ctx["current_volume"], 20)
    table = rec.generate_recommendations(df, detect_all(df), free, free["allocation"].groupby("Factory")["Units"].sum(), caps)
    assert_explained(table)
    assert list(table["ID"]) == [f"R{i:02d}" for i in range(1, len(table) + 1)]
    order = table["Priority"].map({"High": 0, "Medium": 1, "Low": 2})
    assert order.is_monotonic_increasing
    cats = set(table["Category"])
    assert {"Long-distance route", "Alternative factory allocation", "Factory capacity", "Data quality"} <= cats
    assert "Possible exact duplicate order lines" in set(table["Title"])
    pd.testing.assert_frame_equal(df, snapshot)


def test_generate_recommendations_without_optimizer_has_no_hypothetical_rows(real):
    df, _, _ = real
    table = rec.generate_recommendations(df)
    assert "Hypothetical" not in set(table["Basis"])
