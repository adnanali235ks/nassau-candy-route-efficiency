"""Tests for modules/scenarios.py (scenario engine). Toy data uses the A/B/X/Y/Z example."""
import numpy as np
import pandas as pd
import pytest

import route_core as rc
from modules import scenarios as sc
from modules.scenarios import Scenario, build_eligibility, describe_scenario


# ---- toy context (A/B/X/Y/Z) built by hand so the maths can be checked ----------------------------
def toy_context():
    cells = pd.DataFrame({"Cell": ["X", "Y", "Z"], "State/Province": ["X", "Y", "Z"],
                          "Product Name": ["P", "P", "P"], "Units": [10, 20, 30]})
    distance = pd.DataFrame({"A": [100.0, 400.0, 250.0], "B": [300.0, 200.0, 150.0]}, index=["X", "Y", "Z"])
    lines = pd.DataFrame({"Cell": ["X", "Y", "Z"], "Factory": ["A", "A", "A"], "Units": [10, 20, 30]})
    from modules.optimization import baseline_allocation
    existing = baseline_allocation(lines, cells, distance)
    volume = existing.groupby("Factory")["Units"].sum().reindex(["A", "B"]).fillna(0.0)
    return {"cells": cells, "valid": lines, "excluded": pd.DataFrame(), "distance": distance,
            "existing": existing, "current_volume": volume}


@pytest.fixture
def toy_patch(monkeypatch):
    """Make the engine's factory list and product map match the toy example (A, B; product P at A)."""
    monkeypatch.setattr(sc.rc, "FACTORIES", {"A": (0, 0), "B": (0, 1)})
    monkeypatch.setattr(sc.rc, "PRODUCT_FACTORY_MAP", {"P": "A"})


def test_scenario_no_limits_matches_worked_example(toy_patch):
    ctx = toy_context()
    r = sc.run_scenario(ctx, Scenario("S1"))
    assert r["status"] == "OPTIMAL" and r["comparison"]["proposed_unit_miles"] == pytest.approx(9500)
    assert r["comparison"]["reduction_pct"] == pytest.approx(42.42, abs=0.01)


def test_scenario_locking_product_at_current_factory_gives_baseline(toy_patch):
    # Lock the only product at A: nothing can move, so result equals the existing 16,500.
    r = sc.run_scenario(toy_context(), Scenario("S3", "custom", locked_products=("P",)))
    assert r["comparison"]["proposed_unit_miles"] == pytest.approx(16500) and r["comparison"]["reduction_pct"] == 0


def test_scenario_headroom_limits_move_less_volume(toy_patch):
    ctx = toy_context()           # existing: A=60, B=0 -> capacity B=0 at any headroom (no current volume)
    r = sc.run_scenario(ctx, Scenario("S2", headroom_pct=0))
    assert r["status"] == "OPTIMAL" and r["comparison"]["proposed_unit_miles"] == pytest.approx(16500)
    assert r["capacities"] == {"A": 60, "B": 0}


def test_excluding_the_locked_factory_is_infeasible_with_reason(toy_patch):
    r = sc.run_scenario(toy_context(), Scenario("bad", "custom", locked_products=("P",), excluded_factories=("A",)))
    assert r["status"] == "INFEASIBLE" and "No factory is eligible" in r["message"]
    assert r["comparison"] is None


def test_excluding_a_factory_forbids_it(toy_patch):
    r = sc.run_scenario(toy_context(), Scenario("noB", "custom", excluded_factories=("B",)))
    assert set(r["allocation"]["Factory"]) == {"A"}


def test_eligibility_builder_modes(toy_patch):
    e_all = build_eligibility(["P"], Scenario("a"))
    e_cur = build_eligibility(["P"], Scenario("c", "current"))
    assert e_all.to_numpy().all() and e_cur.loc["P"].to_dict() == {"A": True, "B": False}
    with pytest.raises(ValueError):
        build_eligibility(["P"], Scenario("x", "nonsense"))


def test_cost_only_when_rate_given_and_stays_separate(toy_patch):
    ctx = toy_context()
    none = sc.run_scenario(ctx, Scenario("S1"))
    rated = sc.run_scenario(ctx, Scenario("S1", cost_rate=0.01))
    assert "cost_existing" not in none and "cost_proposed" not in none
    assert rated["cost_existing"] == pytest.approx(165) and rated["cost_proposed"] == pytest.approx(95)
    assert rated["cost_difference"] == pytest.approx(70)
    assert rated["comparison"]["proposed_unit_miles"] == none["comparison"]["proposed_unit_miles"]   # distance unchanged


def test_comparison_table_labels_and_cost_columns(toy_patch):
    ctx = toy_context()
    res = sc.run_scenarios(ctx, [Scenario("S1"), Scenario("S2", headroom_pct=0)])
    table = sc.compare_scenarios(ctx, res)
    assert list(table["Scenario"]) == ["Existing (dataset)", "S1", "S2"]
    assert table.loc[0, "Type"].startswith("Actual") and (table.loc[1:, "Type"] == "Hypothetical").all()
    assert table.loc[0, "Unit-miles"] == pytest.approx(16500)
    assert not any("cost" in c.lower() for c in table.columns)           # no rate anywhere -> no cost columns
    res2 = sc.run_scenarios(ctx, [Scenario("S1", cost_rate=0.01), Scenario("S2")])
    t2 = sc.compare_scenarios(ctx, res2)
    assert "Est. cost difference ($)" in t2.columns
    assert t2.loc[1, "Est. cost difference ($)"] == pytest.approx(70) and np.isnan(t2.loc[2, "Est. cost difference ($)"])


def test_factory_volume_table_side_by_side(toy_patch):
    ctx = toy_context()
    res = sc.run_scenarios(ctx, [Scenario("S1")])
    vol = sc.factory_volume_table(ctx, res).set_index("Factory")
    assert vol.loc["A", "Existing (dataset)"] == 60 and vol.loc["B", "Existing (dataset)"] == 0
    assert vol.loc["A", "S1"] == 10 and vol.loc["B", "S1"] == 50


def test_unsolved_scenario_appears_as_nan_not_zero(toy_patch):
    ctx = toy_context()
    res = sc.run_scenarios(ctx, [Scenario("bad", "custom", locked_products=("P",), excluded_factories=("A",))])
    table = sc.compare_scenarios(ctx, res)
    assert table.loc[1, "Status"] == "INFEASIBLE" and np.isnan(table.loc[1, "Unit-miles"])
    assert sc.factory_volume_table(ctx, res)["bad"].isna().all()


def test_describe_scenario_mentions_assumptions_and_estimate_wording():
    text = describe_scenario(Scenario("s", "custom", ("Nerds",), ("Sugar Shack",), 20, 0.01))
    assert "locked at current factory: Nerds" in text and "Sugar Shack" in text
    assert "+ 20%" in text and "not an actual cost" in text
    assert "no cost estimate" in describe_scenario(Scenario("s"))


# ---- real data -------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def real():
    df, _ = rc.load_and_clean()
    snapshot = df.copy(deep=True)
    return df, snapshot, sc.prepare_context(df)


def test_real_scenarios_ordering_and_baseline(real):
    df, _, ctx = real
    res = sc.run_scenarios(ctx, [Scenario("free"), Scenario("+0%", headroom_pct=0), Scenario("+20%", headroom_pct=20),
                                 Scenario("current", "current")])
    um = {r["name"]: r["comparison"]["proposed_unit_miles"] for r in res}
    base = float(ctx["existing"]["Unit-Miles"].sum())
    assert um["free"] < um["+20%"] < um["+0%"] <= base + 1e-6          # more freedom -> less distance
    assert um["current"] == pytest.approx(base, rel=1e-9)               # sanity check: no change allowed -> baseline


def test_real_lock_and_exclusion_scenario_runs(real):
    _, _, ctx = real
    r = sc.run_scenario(ctx, Scenario("custom", "custom", locked_products=("Nerds",), excluded_factories=("Sugar Shack",)))
    assert r["status"] == "INFEASIBLE"                                   # Nerds is mapped to Sugar Shack, which is excluded
    r2 = sc.run_scenario(ctx, Scenario("custom2", "custom", excluded_factories=("Sugar Shack",)))
    assert r2["status"] == "OPTIMAL" and "Sugar Shack" not in set(r2["allocation"]["Factory"])


def test_scenarios_do_not_modify_the_original_data(real):
    df, snapshot, ctx = real
    sc.run_scenarios(ctx, [Scenario("free", cost_rate=0.02), Scenario("+10%", headroom_pct=10)])
    pd.testing.assert_frame_equal(df, snapshot)
