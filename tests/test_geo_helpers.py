"""Tests for the geographic helpers in modules/route_analysis.py and the map figure."""
import numpy as np
import pandas as pd
import pytest

from modules.route_analysis import (route_map_table, long_distance_threshold, flag_long_routes,
                                    destination_summary)
from ui.charts import build_route_map


def make_routes():
    return pd.DataFrame({
        "Route": ["Wicked Choccy's -> California", "Wicked Choccy's -> Georgia",
                  "Lot's O' Nuts -> Ontario", "Lot's O' Nuts -> Atlantis"],
        "Factory": ["Wicked Choccy's", "Wicked Choccy's", "Lot's O' Nuts", "Lot's O' Nuts"],
        "State/Province": ["California", "Georgia", "Ontario", "Atlantis"],
        "Shipments": [100, 50, 10, 5], "Sales": [1.0, 1.0, 1.0, 1.0],
        "Avg Distance (mi)": [2200.0, 200.0, 1800.0, np.nan],
    })


def test_map_table_adds_us_and_canadian_coordinates():
    t = route_map_table(make_routes()).set_index("State/Province")
    assert t.loc["California", "Dest Lat"] == pytest.approx(36.1, abs=0.1)
    assert t.loc["Ontario", "Dest Lat"] == pytest.approx(50.0, abs=1.0)     # Canadian province is supported
    assert t.loc["California", "Factory Lat"] == pytest.approx(32.08, abs=0.01)


def test_unknown_location_keeps_nan_coordinates():
    t = route_map_table(make_routes()).set_index("State/Province")
    assert np.isnan(t.loc["Atlantis", "Dest Lat"]) and np.isnan(t.loc["Atlantis", "Dest Lon"])


def test_long_distance_threshold_worked_example():
    # distances 300, 800, 1500, 2200 -> 75th percentile = 1675
    assert long_distance_threshold([300, 800, 1500, 2200], 75) == pytest.approx(1675)


def test_threshold_ignores_missing_and_handles_empty():
    assert long_distance_threshold([np.nan, 100, 200], 50) == pytest.approx(150)
    assert np.isnan(long_distance_threshold([np.nan, np.nan]))


def test_flag_long_routes_never_flags_unknown_distance():
    flagged = flag_long_routes(route_map_table(make_routes()), 1675).set_index("State/Province")
    assert flagged.loc["California", "Long Distance"] and flagged.loc["Ontario", "Long Distance"]   # 2200 and 1800 > 1675
    assert not flagged.loc["Georgia", "Long Distance"]
    assert not flagged.loc["Atlantis", "Long Distance"]


def test_destination_summary_weights_distance_by_orders():
    t = route_map_table(pd.DataFrame({
        "Route": ["a", "b"], "Factory": ["Sugar Shack", "Secret Factory"],
        "State/Province": ["Texas", "Texas"], "Shipments": [30, 10], "Sales": [1.0, 1.0],
        "Avg Distance (mi)": [1000.0, 2000.0]}))
    d = destination_summary(t)
    assert len(d) == 1 and d.iloc[0]["Orders"] == 40
    assert d.iloc[0]["Avg Distance (mi)"] == pytest.approx((30 * 1000 + 10 * 2000) / 40)


def test_map_figure_draws_lines_markers_and_skips_missing_coordinates():
    t = flag_long_routes(route_map_table(make_routes()), 1675)
    fig = build_route_map(t)
    names = [tr.name for tr in fig.data]
    assert any(n.startswith("Long-distance routes (2)") for n in names)          # California + Ontario
    assert any(n.startswith("Shorter routes (1)") for n in names)                # Georgia; Atlantis (no coordinates) skipped
    dest = [tr for tr in fig.data if tr.name == "Destination centroid"][0]
    assert "Atlantis" not in list(np.array(dest.customdata)[:, 0])
    assert "centroid" in dest.hovertemplate                                       # endpoints labelled as centroids
    assert [tr.name for tr in fig.data if tr.name == "Factory"] == ["Factory"]
