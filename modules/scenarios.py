"""
Scenario Simulator engine: run several HYPOTHETICAL factory-allocation scenarios and compare them.

A scenario is a named set of assumptions:
  * eligibility  - which factories may make which products
                   "all"     every factory can make every product (assumption)
                   "current" only the dataset's product->factory mapping (reproduces the existing plan)
                   "custom"  start from "all", then lock chosen products to their current factory and/or
                             forbid chosen factories from making anything
  * headroom_pct - hypothetical capacity = current volume x (1 + headroom %); None = no capacity limits
  * cost_rate    - optional illustrative $ per unit-mile; None = no cost is calculated

Every scenario is solved with the same optimiser as the Optimization Center (modules/optimization.py).
All results here are hypothetical; "Existing" is the dataset's own allocation (calculated, not simulated).
No Streamlit code; the original data is never modified.
"""

from dataclasses import dataclass

import pandas as pd

import route_core as rc
from modules.optimization import (
    build_demand_cells, distance_matrix, all_factories_eligible, current_mapping_eligibility,
    capacity_from_current, solve_allocation, baseline_allocation, compare_allocations, estimated_cost)


@dataclass
class Scenario:
    name: str
    eligibility_mode: str = "all"            # "all" | "current" | "custom"
    locked_products: tuple = ()              # custom: products fixed to their current factory
    excluded_factories: tuple = ()           # custom: factories that may not make any product
    headroom_pct: float = None               # None = no capacity limits
    cost_rate: float = None                  # None = no cost estimate


def prepare_context(df):
    """Everything scenarios share: demand cells, distances and the EXISTING allocation (computed once)."""
    cells, valid, excluded = build_demand_cells(df)
    if cells.empty:
        return {"cells": cells, "valid": valid, "excluded": excluded, "distance": None,
                "existing": None, "current_volume": pd.Series(dtype=float)}
    distance = distance_matrix(cells)
    existing = baseline_allocation(valid, cells, distance)
    volume = existing.groupby("Factory")["Units"].sum().reindex(list(rc.FACTORIES)).fillna(0.0)
    return {"cells": cells, "valid": valid, "excluded": excluded, "distance": distance,
            "existing": existing, "current_volume": volume}


def build_eligibility(products, scenario, factories=None):
    """Product x factory eligibility matrix for a scenario (see module docstring)."""
    factories = list(rc.FACTORIES if factories is None else factories)
    if scenario.eligibility_mode == "current":
        return current_mapping_eligibility(products, rc.PRODUCT_FACTORY_MAP, factories)
    elig = all_factories_eligible(products, factories)
    if scenario.eligibility_mode == "custom":
        for product in scenario.locked_products:           # 1) lock products to their current factory
            if product in elig.index:
                elig.loc[product, :] = False
                current = rc.PRODUCT_FACTORY_MAP.get(product)
                if current in elig.columns:
                    elig.loc[product, current] = True
        for factory in scenario.excluded_factories:        # 2) forbid factories (may leave a locked product with none)
            if factory in elig.columns:
                elig[factory] = False
    elif scenario.eligibility_mode != "all":
        raise ValueError(f"unknown eligibility mode: {scenario.eligibility_mode}")
    return elig


def describe_scenario(s):
    """One-line plain-language statement of a scenario's assumptions (used in the UI and reports)."""
    if s.eligibility_mode == "all":
        elig = "every factory can make every product (assumption)"
    elif s.eligibility_mode == "current":
        elig = "products stay at their current factory"
    else:
        parts = ["every factory can make every product"]
        if s.locked_products:
            parts.append("locked at current factory: " + ", ".join(s.locked_products))
        if s.excluded_factories:
            parts.append("factories not allowed to make products: " + ", ".join(s.excluded_factories))
        elig = "; ".join(parts) + " (assumptions)"
    cap = ("no capacity limits" if s.headroom_pct is None
           else f"hypothetical capacity = current volume + {s.headroom_pct:g}%")
    cost = ("no cost estimate" if s.cost_rate is None
            else f"illustrative cost ${s.cost_rate:g} per unit-mile (estimate, not an actual cost)")
    return f"Eligibility: {elig}. Capacity: {cap}. Cost: {cost}."


def run_scenario(context, scenario):
    """Solve one scenario. Returns a dict (status, message, comparison, allocation, costs...)."""
    out = {"name": scenario.name, "scenario": scenario, "assumptions": describe_scenario(scenario),
           "status": "NO DATA", "message": "No demand with known locations.", "allocation": pd.DataFrame(),
           "comparison": None, "capacities": None}
    cells = context["cells"]
    if cells.empty:
        return out
    products = sorted(cells["Product Name"].unique())
    eligibility = build_eligibility(products, scenario)
    capacities = (None if scenario.headroom_pct is None
                  else capacity_from_current(context["current_volume"], scenario.headroom_pct))
    result = solve_allocation(cells, context["distance"], eligibility, capacities)
    out.update(status=result.status, message=result.message, capacities=capacities, eligibility=eligibility,
               integral=result.integral)
    if result.status != "OPTIMAL":
        return out
    cmp = compare_allocations(context["existing"], result.allocation)
    out.update(allocation=result.allocation, comparison=cmp)
    base_cost = estimated_cost(cmp["baseline_unit_miles"], scenario.cost_rate)
    if base_cost is not None:
        new_cost = estimated_cost(cmp["proposed_unit_miles"], scenario.cost_rate)
        out.update(cost_existing=base_cost, cost_proposed=new_cost, cost_difference=base_cost - new_cost)
    return out


def run_scenarios(context, scenarios):
    return [run_scenario(context, s) for s in scenarios]


def compare_scenarios(context, results):
    """Summary table: the existing allocation first, then each scenario. Cost columns only if a rate was given."""
    existing_um = float(context["existing"]["Unit-Miles"].sum()) if context["existing"] is not None else float("nan")
    units = float(context["existing"]["Units"].sum()) if context["existing"] is not None else float("nan")
    rows = [{"Scenario": "Existing (dataset)", "Type": "Actual allocation (calculated)", "Status": "-",
             "Unit-miles": existing_um, "Reduction (unit-miles)": 0.0, "Reduction %": 0.0,
             "Avg miles per unit": existing_um / units if units else float("nan"), "Demand cells changed": 0}]
    for r in results:
        c = r["comparison"]
        row = {"Scenario": r["name"], "Type": "Hypothetical", "Status": r["status"],
               "Unit-miles": c["proposed_unit_miles"] if c else float("nan"),
               "Reduction (unit-miles)": c["reduction_unit_miles"] if c else float("nan"),
               "Reduction %": c["reduction_pct"] if c else float("nan"),
               "Avg miles per unit": c["avg_miles_per_unit_after"] if c else float("nan"),
               "Demand cells changed": c["cells_changed"] if c else float("nan")}
        rows.append(row)
    table = pd.DataFrame(rows)
    if any(r["scenario"].cost_rate is not None for r in results):
        table["Rate ($/unit-mile)"] = [float("nan")] + [r["scenario"].cost_rate if r["scenario"].cost_rate is not None
                                                         else float("nan") for r in results]
        table["Est. cost, existing ($)"] = [float("nan")] + [r.get("cost_existing", float("nan")) for r in results]
        table["Est. cost, scenario ($)"] = [float("nan")] + [r.get("cost_proposed", float("nan")) for r in results]
        table["Est. cost difference ($)"] = [float("nan")] + [r.get("cost_difference", float("nan")) for r in results]
    return table


def factory_volume_table(context, results):
    """Units per factory: existing and each solved scenario (side by side)."""
    table = pd.DataFrame({"Factory": list(rc.FACTORIES),
                          "Existing (dataset)": context["current_volume"].reindex(list(rc.FACTORIES)).fillna(0.0).to_numpy()})
    for r in results:
        if r["comparison"] is None:
            table[r["name"]] = float("nan")
            continue
        units = r["allocation"].groupby("Factory")["Units"].sum()
        table[r["name"]] = units.reindex(table["Factory"]).fillna(0.0).to_numpy()
    return table
