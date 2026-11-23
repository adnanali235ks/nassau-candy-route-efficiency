"""Tests for modules/route_analysis.py (KPIs, distributions, insights) on synthetic data."""
import numpy as np
import pandas as pd
import pytest

from modules.route_analysis import (executive_kpis, ship_mode_distribution, factory_sales,
                                    best_and_worst_routes, business_insights, SCORE_COL)


def make_fdf():
    rows = [
        # Order ID, Customer, Factory, Mode, Sales, Distance, Country, repeated?
        ("o1", "c1", "F1", "Standard Class", 100.0, 500.0, "United States", False),
        ("o1", "c1", "F1", "Standard Class", 50.0, 500.0, "United States", False),   # 2nd line of o1
        ("o2", "c2", "F1", "First Class", 50.0, 2000.0, "United States", False),
        ("o3", "c3", "F2", "Standard Class", 100.0, np.nan, "Canada", True),
    ]
    return pd.DataFrame(rows, columns=["Order ID", "Customer ID", "Factory", "Ship Mode", "Sales",
                                       "Route Distance (mi)", "Country/Region", "Repeated Order-Product Line"])


def make_routes():
    return pd.DataFrame({
        "Route": ["A", "B", "C", "D"],
        "Shipments": [100, 50, 10, 5],
        SCORE_COL: [80.0, 40.0, 95.0, np.nan],
        "Avg Distance (mi)": [300.0, 1500.0, 100.0, np.nan],
    })


def test_kpis_dataset_values_count_orders_not_lines():
    k = executive_kpis(make_fdf(), make_routes())
    assert k["total_orders"] == 3 and k["customers"] == 3 and k["factories"] == 2
    assert k["total_sales"] == pytest.approx(300.0)


def test_average_distance_is_per_order_and_skips_unknown():
    # o1 (500, counted once, not twice), o2 (2000); o3 unknown is skipped -> 1250
    assert executive_kpis(make_fdf(), make_routes())["avg_distance_mi"] == pytest.approx(1250.0)


def test_overall_efficiency_is_shipment_weighted_and_ignores_unscored():
    # (80*100 + 40*50 + 95*10) / 160 = 10950 / 160 = 68.4375 ; the NaN route D is excluded
    k = executive_kpis(make_fdf(), make_routes())
    assert k["overall_efficiency"] == pytest.approx(68.4375)
    assert k["scored_routes"] == 3 and k["unscored_routes"] == 1


def test_overall_efficiency_nan_when_nothing_scored():
    r = make_routes().assign(**{SCORE_COL: np.nan})
    assert np.isnan(executive_kpis(make_fdf(), r)["overall_efficiency"])


def test_ship_mode_distribution_counts_distinct_orders_and_sums_to_100():
    d = ship_mode_distribution(make_fdf()).set_index("Ship Mode")
    assert d.loc["Standard Class", "Orders"] == 2      # o1 (2 lines) + o3
    assert d.loc["First Class", "Orders"] == 1
    assert d["Share %"].sum() == pytest.approx(100.0)


def test_factory_sales_shares_sum_to_100():
    fs = factory_sales(make_fdf())
    assert fs["Sales Share %"].sum() == pytest.approx(100.0)
    assert fs.iloc[0]["Factory"] == "F1" and fs.iloc[0]["Sales"] == pytest.approx(200.0)


def test_best_and_worst_exclude_unscored_and_are_ordered():
    best, worst = best_and_worst_routes(make_routes(), n=2)
    assert list(best["Route"]) == ["C", "A"]
    assert list(worst["Route"]) == ["B", "A"]           # worst first
    assert "D" not in set(best["Route"]) | set(worst["Route"])


def test_insights_have_text_and_a_reason_each():
    insights = business_insights(make_fdf(), make_routes())
    assert len(insights) >= 4
    for item in insights:
        assert item["title"] and item["text"] and item["why"]


def test_weakest_high_volume_route_ignores_unscored_and_small_routes():
    # median shipments of scored routes (100, 50, 10) = 50 -> candidates A and B ; lowest score = B
    insights = {i["title"]: i for i in business_insights(make_fdf(), make_routes())}
    assert insights["Weakest high-volume route"]["text"].startswith("B ")


def test_data_caveats_insight_counts_unscored_and_repeats():
    text = {i["title"]: i["text"] for i in business_insights(make_fdf(), make_routes())}["Data caveats"]
    assert "1 route(s) are unscored" in text and "1 order lines repeat" in text
