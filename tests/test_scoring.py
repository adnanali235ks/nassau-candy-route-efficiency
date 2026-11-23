"""Unit tests for modules/scoring.py (pure functions, no CSV needed)."""
import inspect
import numpy as np
import pandas as pd
import pytest

from config import DEFAULT_SCORE_WEIGHTS, DEFAULT_SHIP_MODE_SUITABILITY
from modules import scoring
from modules.scoring import (normalize_weights, distance_score, ship_mode_score,
                             combine_scores, score_routes)


# ---- weights ---------------------------------------------------------------
def test_default_weights_are_70_30():
    assert DEFAULT_SCORE_WEIGHTS == {"distance": 0.70, "ship_mode": 0.30}
    assert normalize_weights() == pytest.approx({"distance": 0.7, "ship_mode": 0.3})


def test_weights_are_rescaled_to_sum_to_one():
    w = normalize_weights({"distance": 7, "ship_mode": 3})
    assert w["distance"] == pytest.approx(0.7) and w["ship_mode"] == pytest.approx(0.3)
    assert sum(w.values()) == pytest.approx(1.0)


@pytest.mark.parametrize("bad", [
    {"distance": -1, "ship_mode": 1},
    {"distance": 0, "ship_mode": 0},
    {"distance": 1},
])
def test_invalid_weights_rejected(bad):
    with pytest.raises(ValueError):
        normalize_weights(bad)


# ---- distance normalisation ------------------------------------------------
def test_distance_score_endpoints_and_midpoint():
    s = distance_score([0, 1000, 2000])
    assert list(s) == pytest.approx([100, 50, 0])


def test_distance_score_with_fixed_reference():
    # 500 of 2000 -> 75 (the worked example in docs/METHODOLOGY.md)
    assert distance_score([500], reference_max_distance=2000).iloc[0] == pytest.approx(75)


def test_distance_beyond_reference_is_clipped_to_zero():
    assert distance_score([3000], reference_max_distance=2000).iloc[0] == 0


def test_missing_distance_stays_nan_not_zero():
    s = distance_score([np.nan, 1000, 2000])
    assert np.isnan(s.iloc[0]) and s.iloc[1] == pytest.approx(50)


def test_reference_ignores_missing_values():
    s = distance_score([np.nan, 500, 1000])
    assert s.iloc[2] == 0      # 1000 is the longest *known* distance


def test_all_missing_distances_give_all_nan():
    assert distance_score([np.nan, np.nan]).isna().all()


# ---- ship-mode suitability -------------------------------------------------
def test_ship_mode_score_worked_example():
    score, known = ship_mode_score({"Standard Class": 0.5, "First Class": 0.5})
    assert score == pytest.approx(62.5) and known == pytest.approx(1.0)


def test_pure_modes_hit_table_values():
    for mode, value in DEFAULT_SHIP_MODE_SUITABILITY.items():
        assert ship_mode_score({mode: 1.0})[0] == pytest.approx(100 * value)


def test_unknown_mode_is_ignored_and_rest_rescaled():
    score, known = ship_mode_score({"Same Day": 0.5, "Pigeon Post": 0.5})
    assert score == pytest.approx(100.0)          # only Same Day counted
    assert known == pytest.approx(0.5)            # half the mix was recognised


def test_no_recognised_mode_gives_nan():
    score, known = ship_mode_score({"Pigeon Post": 1.0})
    assert np.isnan(score) and known == 0


def test_custom_suitability_table_is_used():
    assert ship_mode_score({"Standard Class": 1.0}, {"Standard Class": 0.9})[0] == pytest.approx(90)


# ---- combining ---------------------------------------------------------------
def test_combine_worked_example_and_components_add_up():
    final, dist_pts, mode_pts = combine_scores([75], [62.5])
    assert dist_pts.iloc[0] == pytest.approx(52.5)
    assert mode_pts.iloc[0] == pytest.approx(18.75)
    assert final.iloc[0] == pytest.approx(71.25)
    assert final.iloc[0] == pytest.approx(dist_pts.iloc[0] + mode_pts.iloc[0])


def test_changing_weights_changes_result():
    default = combine_scores([100], [0])[0].iloc[0]                                  # 70
    mode_heavy = combine_scores([100], [0], {"distance": 0.2, "ship_mode": 0.8})[0].iloc[0]  # 20
    assert default == pytest.approx(70) and mode_heavy == pytest.approx(20)


def test_missing_component_gives_nan_never_zero():
    final, _, _ = combine_scores([np.nan, 80], [50, np.nan])
    assert final.isna().all()


# ---- full table ------------------------------------------------------------------
def make_routes():
    return pd.DataFrame({
        "Route": ["near", "far", "unknown"],
        "Avg Distance (mi)": [500.0, 2000.0, np.nan],
        "Ship Mode Mix": [{"Standard Class": .5, "First Class": .5}, {"Same Day": 1.0}, {"Same Day": 1.0}],
    })


def test_score_routes_columns_and_values():
    out = score_routes(make_routes()).set_index("Route")
    assert out.loc["near", "Distance Score"] == pytest.approx(75)
    assert out.loc["near", "Route Efficiency Proxy Score"] == pytest.approx(71.2, abs=0.05)   # 71.25 rounded
    assert out.loc["far", "Route Efficiency Proxy Score"] == pytest.approx(30.0)              # 0.7*0 + 0.3*100
    assert out.loc["near", "Distance Points"] + out.loc["near", "Ship-Mode Points"] == pytest.approx(71.25)


def test_score_routes_unscored_route_is_nan():
    out = score_routes(make_routes()).set_index("Route")
    assert np.isnan(out.loc["unknown", "Route Efficiency Proxy Score"])


def test_score_routes_does_not_mutate_input():
    routes = make_routes()
    before = routes.copy(deep=True)
    score_routes(routes)
    assert list(routes.columns) == list(before.columns)


def test_scores_stay_within_0_100():
    out = score_routes(make_routes(), reference_max_distance=500)
    scored = out["Route Efficiency Proxy Score"].dropna()
    assert ((scored >= 0) & (scored <= 100)).all()


def test_score_has_no_cost_input():
    # Estimated costs must stay out of the efficiency score: no cost-like parameter exists.
    for fn in (distance_score, ship_mode_score, combine_scores, score_routes):
        assert not any("cost" in p.lower() for p in inspect.signature(fn).parameters)
    assert "cost" not in inspect.getsource(scoring).lower().replace("no cost", "").replace("any cost", "")
