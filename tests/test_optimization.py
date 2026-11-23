"""Tests for modules/optimization.py (hypothetical factory allocation, OR-Tools GLOP)."""
import numpy as np
import pandas as pd
import pytest

import route_core as rc
from modules.optimization import (
    build_demand_cells, distance_matrix, all_factories_eligible, current_mapping_eligibility,
    capacity_from_current, solve_allocation, baseline_allocation, compare_allocations,
    estimated_cost, split_order_lines)


# ---------------------------------------------------------------------------
# The worked example from the design: factories A, B; cells X=10, Y=20, Z=30 units
# ---------------------------------------------------------------------------
def toy():
    cells = pd.DataFrame({"Cell": ["X", "Y", "Z"], "State/Province": ["X", "Y", "Z"],
                          "Product Name": ["P", "P", "P"], "Units": [10, 20, 30]})
    distance = pd.DataFrame({"A": [100.0, 400.0, 250.0], "B": [300.0, 200.0, 150.0]}, index=["X", "Y", "Z"])
    elig = pd.DataFrame(True, index=["P"], columns=["A", "B"])
    lines = pd.DataFrame({"Cell": ["X", "Y", "Z"], "Factory": ["A", "A", "A"], "Units": [10, 20, 30]})
    return cells, distance, elig, lines


def test_toy_baseline_is_16500():
    cells, distance, _, lines = toy()
    assert baseline_allocation(lines, cells, distance)["Unit-Miles"].sum() == pytest.approx(16500)


def test_toy_uncapacitated_optimum_is_9500_and_42_4_percent():
    cells, distance, elig, lines = toy()
    res = solve_allocation(cells, distance, elig)
    assert res.status == "OPTIMAL" and res.total_unit_miles == pytest.approx(9500)
    cmp = compare_allocations(baseline_allocation(lines, cells, distance), res.allocation)
    assert cmp["reduction_unit_miles"] == pytest.approx(7000)
    assert cmp["reduction_pct"] == pytest.approx(42.42, abs=0.01)
    plan = res.allocation.set_index(["Cell", "Factory"])["Units"]
    assert plan[("X", "A")] == 10 and plan[("Y", "B")] == 20 and plan[("Z", "B")] == 30


def test_toy_capacity_b40_gives_10500_with_z_split_20_10():
    cells, distance, elig, lines = toy()
    res = solve_allocation(cells, distance, elig, {"B": 40})
    assert res.status == "OPTIMAL" and res.total_unit_miles == pytest.approx(10500)
    plan = res.allocation.set_index(["Cell", "Factory"])["Units"]
    assert plan[("Z", "B")] == 20 and plan[("Z", "A")] == 10          # Z is split between factories
    cmp = compare_allocations(baseline_allocation(lines, cells, distance), res.allocation)
    assert cmp["reduction_pct"] == pytest.approx(36.36, abs=0.01)


def test_toy_capacity_is_respected():
    cells, distance, elig, _ = toy()
    res = solve_allocation(cells, distance, elig, {"B": 25})
    assert res.allocation.groupby("Factory")["Units"].sum()["B"] <= 25 + 1e-9


def test_toy_infeasible_capacities_report_shortfall_of_10():
    cells, distance, elig, _ = toy()
    res = solve_allocation(cells, distance, elig, {"A": 20, "B": 30})
    assert res.status == "INFEASIBLE" and res.allocation.empty and np.isnan(res.total_unit_miles)
    assert "60" in res.message and "50" in res.message and "10" in res.message


def test_toy_eligibility_restriction_is_respected():
    cells, distance, _, _ = toy()
    elig = pd.DataFrame(True, index=["P"], columns=["A", "B"])
    elig.loc["P", "B"] = False                                         # only A may make P
    res = solve_allocation(cells, distance, elig)
    assert set(res.allocation["Factory"]) == {"A"} and res.total_unit_miles == pytest.approx(16500)


def test_product_with_no_eligible_factory_is_infeasible_with_reason():
    cells, distance, _, _ = toy()
    elig = pd.DataFrame(False, index=["P"], columns=["A", "B"])
    res = solve_allocation(cells, distance, elig)
    assert res.status == "INFEASIBLE" and "P" in res.message


def test_capacity_shortfall_for_one_product_is_named():
    cells, distance, _, _ = toy()
    cells["Product Name"] = ["P", "P", "Q"]                            # Z (30 units) is product Q
    elig = pd.DataFrame(True, index=["P", "Q"], columns=["A", "B"])
    elig.loc["Q", "B"] = False                                         # Q only at A
    res = solve_allocation(cells, distance, elig, {"A": 20})           # A can supply 20 < 30
    assert res.status == "INFEASIBLE" and "Q" in res.message and "short by 10" in res.message


def test_shared_capacity_infeasibility_is_caught_by_the_solver():
    # P and Q both need factory A (only eligible one); A's capacity 35 < 10+20+30 even though
    # no single product check fails (P: 30 <= 35, Q: 30 <= 35).
    cells = pd.DataFrame({"Cell": ["X", "Y", "Z"], "State/Province": list("XYZ"),
                          "Product Name": ["P", "P", "Q"], "Units": [10, 20, 30]})
    distance = pd.DataFrame({"A": [1.0, 1.0, 1.0], "B": [2.0, 2.0, 2.0]}, index=list("XYZ"))
    elig = pd.DataFrame([[True, False], [True, False]], index=["P", "Q"], columns=["A", "B"])
    res = solve_allocation(cells, distance, elig, {"A": 35})
    assert res.status == "INFEASIBLE"


def test_missing_distance_is_refused_not_zeroed():
    cells, distance, elig, _ = toy()
    distance.loc["X", "A"] = np.nan
    assert solve_allocation(cells, distance, elig).status == "ERROR"


@pytest.mark.parametrize("bad", [{"B": -1}, {"B": 2.5}, {"Nowhere": 5}])
def test_invalid_capacities_rejected(bad):
    cells, distance, elig, _ = toy()
    with pytest.raises(ValueError):
        solve_allocation(cells, distance, elig, bad)


def test_unlimited_factory_when_capacity_missing_or_none():
    cells, distance, elig, _ = toy()
    assert solve_allocation(cells, distance, elig, {"B": None}).total_unit_miles == pytest.approx(9500)


# ---------------------------------------------------------------------------
# Property tests: solver vs nearest-factory, integrality
# ---------------------------------------------------------------------------
def random_instance(seed, n_cells=25, n_factories=4):
    rng = np.random.default_rng(seed)
    labels = [f"c{i}" for i in range(n_cells)]
    factories = [f"F{j}" for j in range(n_factories)]
    cells = pd.DataFrame({"Cell": labels, "State/Province": labels,
                          "Product Name": [f"P{i % 3}" for i in range(n_cells)],
                          "Units": rng.integers(1, 40, n_cells)})
    distance = pd.DataFrame(rng.uniform(50, 3000, (n_cells, n_factories)), index=labels, columns=factories)
    elig = pd.DataFrame(True, index=["P0", "P1", "P2"], columns=factories)
    return cells, distance, elig


@pytest.mark.parametrize("seed", range(5))
def test_uncapacitated_optimum_equals_nearest_factory(seed):
    cells, distance, elig = random_instance(seed)
    nearest = float((cells.set_index("Cell")["Units"] * distance.min(axis=1)).sum())
    res = solve_allocation(cells, distance, elig)
    assert res.total_unit_miles == pytest.approx(nearest, rel=1e-9)


@pytest.mark.parametrize("seed", range(5))
def test_capacitated_solutions_are_whole_numbers_and_feasible(seed):
    cells, distance, elig = random_instance(seed)
    total = int(cells["Units"].sum())
    caps = {f: total // 4 + 20 for f in distance.columns}            # tight but feasible
    res = solve_allocation(cells, distance, elig, caps)
    assert res.status == "OPTIMAL" and res.integral
    assert (res.allocation["Units"] == res.allocation["Units"].round()).all()
    assert (res.allocation.groupby("Factory")["Units"].sum() <= pd.Series(caps) + 1e-9).all()
    supplied = res.allocation.groupby("Cell")["Units"].sum()
    assert (supplied.reindex(cells["Cell"]).to_numpy() == cells["Units"].to_numpy()).all()


@pytest.mark.parametrize("seed", range(3))
def test_adding_capacity_never_improves_the_optimum(seed):
    cells, distance, elig = random_instance(seed)
    free = solve_allocation(cells, distance, elig).total_unit_miles
    limited = solve_allocation(cells, distance, elig, {"F0": 20, "F1": 20, "F2": 400, "F3": 400}).total_unit_miles
    assert limited >= free - 1e-6


# ---------------------------------------------------------------------------
# Cost, capacity helper
# ---------------------------------------------------------------------------
def test_cost_is_none_without_rate_and_rate_times_unit_miles_with_one():
    assert estimated_cost(9500, None) is None and estimated_cost(9500, float("nan")) is None
    assert estimated_cost(9500, 0.01) == pytest.approx(95.0)
    assert estimated_cost(16500, 0.01) == pytest.approx(165.0)
    with pytest.raises(ValueError):
        estimated_cost(100, -1)


def test_cost_does_not_change_the_optimiser_result():
    cells, distance, elig, _ = toy()
    before = solve_allocation(cells, distance, elig).total_unit_miles
    estimated_cost(before, 5.0)
    assert solve_allocation(cells, distance, elig).total_unit_miles == before


def test_capacity_from_current_volume_plus_headroom_rounds_down():
    assert capacity_from_current({"A": 100, "B": 33}, 0) == {"A": 100, "B": 33}
    assert capacity_from_current({"A": 100, "B": 33}, 10) == {"A": 110, "B": 36}   # 36.3 -> 36
    assert capacity_from_current({"A": 0}, 50) == {"A": 0}
    with pytest.raises(ValueError):
        capacity_from_current({"A": 1}, -5)


# ---------------------------------------------------------------------------
# Order-line export with explicit splits
# ---------------------------------------------------------------------------
def test_order_line_split_is_explicit_and_conserves_units():
    cells, distance, elig, _ = toy()
    lines = pd.DataFrame({
        "Row ID": [1, 2, 3, 4], "Order ID": ["o1", "o2", "o3", "o4"], "Customer ID": [1, 2, 3, 4],
        "Order Date": pd.to_datetime(["2024-01-01"] * 4), "Country/Region": ["US"] * 4,
        "State/Province": ["Z"] * 4, "Product Name": ["P"] * 4, "Units": [8, 8, 8, 6],
        "Factory": ["A"] * 4, "Cell": ["Z"] * 4})                     # cell Z has 30 units over 4 lines
    z_cells = cells[cells["Cell"] == "Z"].copy()
    res = solve_allocation(z_cells, distance.loc[["Z"]], elig, {"B": 20})   # 20 from B, 10 from A
    out = split_order_lines(lines, res.allocation, distance)
    assert out["Allocated Units"].sum() == 30
    assert out.groupby("Row ID")["Allocated Units"].sum().to_dict() == {1: 8, 2: 8, 3: 8, 4: 6}
    assert out.groupby("Proposed Factory")["Allocated Units"].sum().to_dict() == {"A": 10, "B": 20}
    # Factories are filled alphabetically: A's 10 units cover line 1 (8) and 2 units of line 2,
    # so line 2 straddles the A/B boundary and becomes two explicit rows (A: 2, B: 6).
    split = out[out["Row ID"] == 2].set_index("Proposed Factory")["Allocated Units"]
    assert split.to_dict() == {"A": 2, "B": 6}
    assert out[out["Row ID"] == 2]["Line Split"].all()
    assert out[out["Line Split"]]["Row ID"].unique().tolist() == [2]            # no other line is split
    assert not out[out["Row ID"] == 1]["Line Split"].any()


def test_order_line_split_rejects_fractional_allocations():
    alloc = pd.DataFrame({"Cell": ["Z"], "Factory": ["A"], "Units": [2.5]})
    with pytest.raises(ValueError):
        split_order_lines(pd.DataFrame(), alloc, pd.DataFrame())


# ---------------------------------------------------------------------------
# Real data: aggregation, exclusions, baseline, immutability
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def real():
    df, _ = rc.load_and_clean()
    cells, valid, excluded = build_demand_cells(df)
    distance = distance_matrix(cells)
    return df, cells, valid, excluded, distance


def test_real_cells_conserve_units_and_preserve_customers(real):
    df, cells, valid, excluded, _ = real
    assert len(excluded) == 0 and len(valid) == len(df)
    assert cells["Units"].sum() == df["Units"].sum()
    assert cells["Order_Lines"].sum() == len(df)
    assert {"Customers", "Orders", "Product Name", "State/Province"} <= set(cells.columns)
    assert (cells["Customers"] >= 1).all()


def test_real_baseline_matches_line_level_unit_miles(real):
    df, cells, valid, _, distance = real
    base = baseline_allocation(valid, cells, distance)
    expected = float((df["Units"] * df["Route Distance (mi)"]).sum())
    assert base["Unit-Miles"].sum() == pytest.approx(expected, rel=1e-9)
    assert base["Units"].sum() == df["Units"].sum()


def test_real_current_mapping_eligibility_reproduces_baseline(real):
    _, cells, valid, _, distance = real
    elig = current_mapping_eligibility(cells["Product Name"], rc.PRODUCT_FACTORY_MAP)
    res = solve_allocation(cells, distance, elig)
    base = baseline_allocation(valid, cells, distance)["Unit-Miles"].sum()
    assert res.status == "OPTIMAL" and res.total_unit_miles == pytest.approx(base, rel=1e-9)


def test_real_uncapacitated_equals_nearest_factory_and_improves(real):
    _, cells, valid, _, distance = real
    elig = all_factories_eligible(cells["Product Name"])
    res = solve_allocation(cells, distance, elig)
    nearest = float((cells.set_index("Cell")["Units"] * distance.min(axis=1)).sum())
    base = baseline_allocation(valid, cells, distance)["Unit-Miles"].sum()
    assert res.total_unit_miles == pytest.approx(nearest, rel=1e-9) and res.integral
    assert res.total_unit_miles < base
    cmp = compare_allocations(baseline_allocation(valid, cells, distance), res.allocation)
    assert 50 < cmp["reduction_pct"] < 70                              # about 58.8% on this dataset [preview]


def test_real_capacity_at_current_volume_is_feasible_and_never_worse_than_existing(real):
    _, cells, valid, _, distance = real
    elig = all_factories_eligible(cells["Product Name"])
    base = baseline_allocation(valid, cells, distance)
    caps = capacity_from_current(base.groupby("Factory")["Units"].sum(), 0)   # 0% headroom
    res = solve_allocation(cells, distance, elig, caps)
    assert res.status == "OPTIMAL" and res.total_unit_miles <= base["Unit-Miles"].sum() + 1e-6
    assert (res.allocation.groupby("Factory")["Units"].sum() <= pd.Series(caps) + 1e-9).all()


def test_real_capacity_below_demand_is_infeasible(real):
    _, cells, valid, _, distance = real
    elig = all_factories_eligible(cells["Product Name"])
    res = solve_allocation(cells, distance, elig, {f: 1000 for f in distance.columns})
    assert res.status == "INFEASIBLE" and "short by" in res.message


def test_missing_coordinates_are_excluded_and_reported_not_zeroed(real):
    df = real[0].copy()
    df.loc[df.index[:5], ["Customer Lat", "Customer Lon"]] = np.nan
    cells, valid, excluded = build_demand_cells(df)
    assert len(excluded) == 5 and (excluded["Exclusion Reason"] == "Unknown destination coordinates").all()
    assert len(valid) == len(df) - 5
    assert cells["Units"].sum() == df["Units"].sum() - excluded["Units"].sum()
    assert not distance_matrix(cells).isna().to_numpy().any()


def test_unmapped_product_is_excluded_with_reason(real):
    df = real[0].copy()
    df.loc[df.index[:3], "Factory"] = np.nan
    _, valid, excluded = build_demand_cells(df)
    assert len(excluded) == 3 and (excluded["Exclusion Reason"] == "Product has no mapped factory").all()


def test_optimiser_does_not_modify_the_original_dataframe(real):
    df = real[0]
    snapshot = df.copy(deep=True)
    cells, valid, excluded = build_demand_cells(df)
    distance = distance_matrix(cells)
    res = solve_allocation(cells, distance, all_factories_eligible(cells["Product Name"]))
    split_order_lines(valid, res.allocation, distance)
    pd.testing.assert_frame_equal(df, snapshot)


def test_real_line_level_export_conserves_units_and_flags_splits(real):
    _, cells, valid, _, distance = real
    elig = all_factories_eligible(cells["Product Name"])
    base = baseline_allocation(valid, cells, distance)
    caps = capacity_from_current(base.groupby("Factory")["Units"].sum(), 10)
    res = solve_allocation(cells, distance, elig, caps)
    out = split_order_lines(valid, res.allocation, distance)
    assert out["Allocated Units"].sum() == valid["Units"].sum()
    per_line = out.groupby("Row ID")["Allocated Units"].sum()
    assert (per_line.reindex(valid["Row ID"]).to_numpy() == valid["Units"].to_numpy()).all()
    assert out["Unit-Miles"].sum() == pytest.approx(res.total_unit_miles, rel=1e-9)
    # a line marked as split must really appear on more than one row
    assert (out[out["Line Split"]].groupby("Row ID").size() > 1).all()


def test_original_csv_untouched_by_optimiser_tests():
    import pathlib
    csv = pathlib.Path(__file__).resolve().parents[1] / "Nassau_Candy_Distributor.csv"
    before = csv.stat().st_mtime_ns
    df, _ = rc.load_and_clean()
    build_demand_cells(df)
    assert csv.stat().st_mtime_ns == before


def test_comparing_identical_plans_gives_zero_change_and_empty_table():
    # Regression: this used to crash the page ("Current mapping only" mode).
    cells, distance, _, lines = toy()
    base = baseline_allocation(lines, cells, distance)
    cmp = compare_allocations(base, base)
    assert cmp["reduction_unit_miles"] == 0 and cmp["reduction_pct"] == 0 and cmp["cells_changed"] == 0
    assert cmp["changed_cells"].empty
    assert (cmp["units_by_factory"]["Change (units)"] == 0).all()
