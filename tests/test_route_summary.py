"""Tests for ranking behaviour with scored vs unscored routes (synthetic data)."""
import numpy as np
import pandas as pd
import pytest
from route_core import route_summary, unscored_routes, geo_bottleneck_summary


def make_df():
    """Three routes: two with known distance, one (Nowhere/Atlantis) with unknown distance."""
    rows = [
        # Order ID, Factory, Region, State, Ship Mode, Units, Sales, Distance
        ("o1", "F1", "East", "Near", "Standard Class", 1, 10.0, 100.0),
        ("o2", "F1", "East", "Near", "Standard Class", 1, 10.0, 100.0),
        ("o3", "F1", "West", "Far", "Standard Class", 1, 10.0, 2000.0),
        ("o4", "F1", "Nowhere", "Atlantis", "Standard Class", 1, 10.0, np.nan),
    ]
    df = pd.DataFrame(rows, columns=["Order ID", "Factory", "Region", "State/Province",
                                     "Ship Mode", "Units", "Sales", "Route Distance (mi)"])
    df["Raw Lead Time (days)"] = np.nan
    df["Route (Factory-Region)"] = df["Factory"] + " -> " + df["Region"]
    df["Route (Factory-State)"] = df["Factory"] + " -> " + df["State/Province"]
    return df


def test_unscored_route_excluded_from_ranking():
    rs = route_summary(make_df(), "Region")
    assert set(rs["Route"]) == {"F1 -> East", "F1 -> West"}
    assert rs["Route Efficiency Proxy Score"].notna().all()


def test_unscored_route_is_never_least_efficient():
    rs = route_summary(make_df(), "Region")
    assert rs.tail(1)["Route"].iloc[0] == "F1 -> West"      # the genuinely far route


def test_shorter_route_scores_higher():
    rs = route_summary(make_df(), "Region").set_index("Route")
    assert rs.loc["F1 -> East", "Route Efficiency Proxy Score"] > rs.loc["F1 -> West", "Route Efficiency Proxy Score"]


def test_include_unscored_keeps_nan_not_zero_and_last():
    rs = route_summary(make_df(), "Region", include_unscored=True)
    last = rs.iloc[-1]
    assert last["Route"] == "F1 -> Nowhere" and np.isnan(last["Route Efficiency Proxy Score"])


def test_default_output_is_include_unscored_minus_unscored_rows():
    # Compatibility: same columns as before; only the NaN-score rows are removed.
    full = route_summary(make_df(), "Region", include_unscored=True)
    default = route_summary(make_df(), "Region")
    assert list(default.columns) == list(full.columns)
    pd.testing.assert_frame_equal(default, full[full["Route Efficiency Proxy Score"].notna()])


def test_complete_data_gives_identical_output_either_way():
    df = make_df().dropna(subset=["Route Distance (mi)"])
    pd.testing.assert_frame_equal(route_summary(df, "Region"),
                                  route_summary(df, "Region", include_unscored=True))


def test_unscored_routes_listing():
    u = unscored_routes(make_df(), "Region")
    assert list(u["Route"]) == ["F1 -> Nowhere"]


def test_default_score_is_70_30():
    # Standard Class suitability = 0.4 -> ship-mode score 40.
    # West is the max-distance route -> distance score 0 -> total 0.3*40 = 12.
    rs = route_summary(make_df(), "Region").set_index("Route")
    assert rs.loc["F1 -> West", "Route Efficiency Proxy Score"] == pytest.approx(12.0)
    # East: distance 100 of max 2000 -> 95 ; 0.7*95 + 0.3*40 = 78.5
    assert rs.loc["F1 -> East", "Route Efficiency Proxy Score"] == pytest.approx(78.5)


def test_legacy_60_40_can_still_be_reproduced():
    rs = route_summary(make_df(), "Region", weights={"distance": 0.6, "ship_mode": 0.4}).set_index("Route")
    assert rs.loc["F1 -> West", "Route Efficiency Proxy Score"] == pytest.approx(16.0)
    assert rs.loc["F1 -> East", "Route Efficiency Proxy Score"] == pytest.approx(73.0)


def test_geo_summary_marks_missing_distance_not_assessed():
    g = geo_bottleneck_summary(make_df()).set_index("State/Province")
    assert g.loc["Atlantis", "Bottleneck Risk"] == "Not assessed (no distance)"
