"""
HYPOTHETICAL factory allocation simulation (Google OR-Tools, GLOP linear solver).

*** This is a what-if simulation, NOT an operational recommendation. ***
The dataset says each product is made at exactly one factory. The simulation asks:
"IF other factories could make the product (eligibility is an editable ASSUMPTION),
how much shorter would the straight-line shipping distance be?" It ignores production
cost, quality, inventory, lead time, real road routes and real factory capacity.

The model (plain language)
--------------------------
Demand cell      = one (state/province, product) pair, weighted by its total Units.
Decision         = x[cell, factory]: how many units of the cell each factory ships.
Objective        = minimise  sum( distance(cell, factory) * x[cell, factory] )   "unit-miles".
Constraints      = (1) every cell's units are fully supplied;
                   (2) optional: a factory ships at most its (hypothetical) capacity;
                   (3) a factory may only ship products it is eligible to make;
                   (4) x >= 0.
Solver           = OR-Tools GLOP (simplex method). Because all demands and capacities are
                   whole numbers, this "transportation problem" has whole-number optimal
                   solutions, so no rounding is needed. The code still verifies that.
Distances        = great-circle miles from the factory to the state/province CENTROID
                   (not road distance, not the customer's address).
Missing data     = demand whose destination coordinates (or current factory) is unknown is
                   EXCLUDED and reported separately; it is never given distance 0.
Original data    = never modified; every function works on copies.
"""

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from ortools.linear_solver import pywraplp

from route_core import FACTORIES, haversine_miles

HYPOTHETICAL_NOTICE = (
    "HYPOTHETICAL SIMULATION: this is not an operational recommendation. It assumes factories can make "
    "products that the dataset says they do not, ignores production cost, capacity limits that are not "
    "entered here, and real road routes. Distances are straight-line miles to state/province centroids."
)

_TOL = 1e-6


# ---------------------------------------------------------------------------
# 1. Aggregate demand into cells (state/province x product)
# ---------------------------------------------------------------------------
def build_demand_cells(df):
    """Group order lines into demand cells. Returns (cells, valid_lines, excluded_lines).

    cells          one row per (State/Province, Product Name): Units, Order_Lines, Orders,
                   Customers, destination coordinates, and a "Cell" label.
    valid_lines    copy of the order lines that take part (with a "Cell" column), so every
                   original line can be traced back to its cell.
    excluded_lines copy of lines left out, with an "Exclusion Reason". Never treated as 0 miles.
    The input DataFrame is not modified.
    """
    lines = df.copy()
    lines["Cell"] = lines["State/Province"].astype(str) + " | " + lines["Product Name"].astype(str)

    no_destination = lines["Customer Lat"].isna() | lines["Customer Lon"].isna()
    no_factory = lines["Factory"].isna()
    excluded_mask = no_destination | no_factory
    lines["Exclusion Reason"] = np.where(no_destination, "Unknown destination coordinates",
                                         np.where(no_factory, "Product has no mapped factory", ""))

    excluded = lines[excluded_mask].copy()
    valid = lines[~excluded_mask].drop(columns="Exclusion Reason").copy()

    cells = valid.groupby(["Cell", "State/Province", "Product Name"], sort=True).agg(
        Units=("Units", "sum"),
        Order_Lines=("Row ID", "count"),
        Orders=("Order ID", "nunique"),
        Customers=("Customer ID", "nunique"),
        Country=("Country/Region", "first"),
        Dest_Lat=("Customer Lat", "first"),
        Dest_Lon=("Customer Lon", "first"),
    ).reset_index()
    return cells, valid, excluded


def distance_matrix(cells, factories=None):
    """Straight-line miles: rows = cells, columns = factories (haversine to the destination centroid)."""
    factories = FACTORIES if factories is None else factories
    data = {name: [haversine_miles(lat, lon, d_lat, d_lon)
                   for d_lat, d_lon in zip(cells["Dest_Lat"], cells["Dest_Lon"])]
            for name, (lat, lon) in factories.items()}
    return pd.DataFrame(data, index=cells["Cell"].to_numpy())


# ---------------------------------------------------------------------------
# 2. Eligibility and capacity assumptions
# ---------------------------------------------------------------------------
def all_factories_eligible(products, factories=None):
    """ASSUMPTION: every factory can make every product (product x factory, all True)."""
    factories = list(FACTORIES if factories is None else factories)
    return pd.DataFrame(True, index=sorted(set(products)), columns=factories)


def current_mapping_eligibility(products, product_factory_map, factories=None):
    """Only the factory the dataset's mapping assigns can make each product (reproduces the baseline)."""
    factories = list(FACTORIES if factories is None else factories)
    products = sorted(set(products))
    elig = pd.DataFrame(False, index=products, columns=factories)
    for product in products:
        factory = product_factory_map.get(product)
        if factory in elig.columns:
            elig.loc[product, factory] = True
    return elig


def capacity_from_current(units_by_factory, headroom_pct):
    """HYPOTHETICAL capacity = current volume + headroom %, rounded DOWN to whole units.

    Whole numbers keep the allocation whole-numbered. A factory with no current volume gets 0.
    This is an assumption for exploring the model, not a measured factory capacity.
    """
    if headroom_pct < 0:
        raise ValueError("headroom must not be negative")
    return {f: int(math.floor(float(u) * (1 + headroom_pct / 100.0) + 1e-9))
            for f, u in dict(units_by_factory).items()}


def _clean_capacities(capacities, factories):
    """Validate user capacities. None / missing = unlimited. Must be whole, non-negative numbers."""
    cleaned = {}
    for factory, cap in (capacities or {}).items():
        if factory not in factories:
            raise ValueError(f"capacity given for unknown factory: {factory}")
        if cap is None or (isinstance(cap, float) and math.isnan(cap)):
            continue
        if cap < 0:
            raise ValueError(f"capacity for {factory} must not be negative")
        if abs(cap - round(cap)) > _TOL:
            raise ValueError(f"capacity for {factory} must be a whole number of units")
        cleaned[factory] = int(round(cap))
    return cleaned


# ---------------------------------------------------------------------------
# 3. The optimisation model (GLOP)
# ---------------------------------------------------------------------------
@dataclass
class AllocationResult:
    status: str                      # "OPTIMAL", "INFEASIBLE" or "ERROR"
    message: str                     # plain-language explanation
    allocation: pd.DataFrame = field(default_factory=pd.DataFrame)
    total_unit_miles: float = float("nan")
    integral: bool = True            # were all allocated unit counts whole numbers?


_ALLOCATION_COLUMNS = ["Cell", "State/Province", "Product Name", "Factory", "Units",
                       "Distance (mi)", "Unit-Miles"]


def solve_allocation(cells, distance, eligibility, capacities=None):
    """Find the allocation of units to factories that minimises total unit-miles.

    cells        output of build_demand_cells()[0]
    distance     DataFrame, index = cell labels, columns = factories (miles)
    eligibility  DataFrame, index = product names, columns = factories (bool)
    capacities   {factory: max units} or None; a factory missing from the dict is unlimited
    """
    factories = list(distance.columns)
    caps = _clean_capacities(capacities, factories)
    demand = cells.set_index("Cell")["Units"]
    product_of = cells.set_index("Cell")["Product Name"]
    if distance.isna().to_numpy().any():
        return AllocationResult("ERROR", "Distance matrix contains missing values; refusing to treat them as 0.")

    # --- Pre-checks that give a specific, human-readable reason -------------------------------
    eligible_for = {p: [f for f in factories if bool(eligibility.loc[p, f])]
                    for p in sorted(set(product_of))}
    no_factory = [p for p, fs in eligible_for.items() if not fs]
    if no_factory:
        return AllocationResult("INFEASIBLE", "No factory is eligible to make: " + ", ".join(no_factory) + ".")
    for product, fs in eligible_for.items():
        if all(f in caps for f in fs):                     # every eligible factory is capacity-limited
            need = int(demand[product_of == product].sum())
            have = sum(caps[f] for f in fs)
            if have < need:
                return AllocationResult(
                    "INFEASIBLE",
                    f"Capacity shortfall for {product}: demand is {need:,} units but its eligible factories "
                    f"({', '.join(fs)}) can supply only {have:,} (short by {need - have:,}).")
    if len(caps) == len(factories):                        # all factories limited -> total check
        total_need, total_cap = int(demand.sum()), sum(caps.values())
        if total_cap < total_need:
            return AllocationResult(
                "INFEASIBLE",
                f"Total capacity {total_cap:,} units is below total demand {total_need:,} units "
                f"(short by {total_need - total_cap:,}).")

    # --- Build the linear programme ----------------------------------------------------------
    solver = pywraplp.Solver.CreateSolver("GLOP")
    if solver is None:
        return AllocationResult("ERROR", "OR-Tools GLOP solver is not available.")
    x = {}                                                  # x[(cell, factory)] = units shipped
    for cell in demand.index:
        for factory in eligible_for[product_of[cell]]:
            x[(cell, factory)] = solver.NumVar(0.0, solver.infinity(), f"x|{cell}|{factory}")

    for cell in demand.index:                               # (1) supply every cell's demand
        solver.Add(sum(x[(cell, f)] for f in eligible_for[product_of[cell]]) == float(demand[cell]))
    for factory, cap in caps.items():                       # (2) optional capacity
        terms = [var for (cell, f), var in x.items() if f == factory]
        if terms:
            solver.Add(sum(terms) <= float(cap))

    solver.Minimize(sum(float(distance.loc[cell, f]) * var for (cell, f), var in x.items()))
    status = solver.Solve()

    if status == pywraplp.Solver.INFEASIBLE:
        return AllocationResult("INFEASIBLE", "The capacity and eligibility settings cannot supply all demand "
                                              "together (for example, shared capacity across products is too small).")
    if status != pywraplp.Solver.OPTIMAL:
        return AllocationResult("ERROR", f"Solver did not reach an optimal solution (status code {status}).")

    # --- Read the solution -----------------------------------------------------------------------
    rows, integral = [], True
    meta = cells.set_index("Cell")[["State/Province", "Product Name"]]
    for (cell, factory), var in x.items():
        value = var.solution_value()
        if value <= _TOL:
            continue
        if abs(value - round(value)) <= _TOL:
            value = float(round(value))
        else:
            integral = False
        d = float(distance.loc[cell, factory])
        rows.append((cell, meta.loc[cell, "State/Province"], meta.loc[cell, "Product Name"],
                     factory, value, d, value * d))
    allocation = pd.DataFrame(rows, columns=_ALLOCATION_COLUMNS)
    return AllocationResult("OPTIMAL", "Optimal allocation found.", allocation,
                            float(allocation["Unit-Miles"].sum()), integral)


# ---------------------------------------------------------------------------
# 4. Existing allocation and comparison
# ---------------------------------------------------------------------------
def baseline_allocation(valid_lines, cells, distance):
    """The EXISTING allocation in the same shape: units each cell ships from each current factory."""
    g = valid_lines.groupby(["Cell", "Factory"], as_index=False)["Units"].sum()
    meta = cells.set_index("Cell")[["State/Province", "Product Name"]]
    g["State/Province"] = g["Cell"].map(meta["State/Province"])
    g["Product Name"] = g["Cell"].map(meta["Product Name"])
    g["Distance (mi)"] = [float(distance.loc[c, f]) for c, f in zip(g["Cell"], g["Factory"])]
    g["Unit-Miles"] = g["Units"] * g["Distance (mi)"]
    return g[_ALLOCATION_COLUMNS]


def compare_allocations(baseline, proposed):
    """Existing vs hypothetical: unit-miles, reduction, volume per factory, and changed cells."""
    base_um, new_um = float(baseline["Unit-Miles"].sum()), float(proposed["Unit-Miles"].sum())
    units = float(baseline["Units"].sum())
    reduction = base_um - new_um
    by_factory = pd.DataFrame({
        "Before (units)": baseline.groupby("Factory")["Units"].sum(),
        "After (units)": proposed.groupby("Factory")["Units"].sum(),
    }).fillna(0.0)
    by_factory["Change (units)"] = by_factory["After (units)"] - by_factory["Before (units)"]
    by_factory = by_factory.reset_index().rename(columns={"index": "Factory"})

    # Units whose factory changes = demand minus the overlap between old and new plans.
    before = baseline.pivot_table(index="Cell", columns="Factory", values="Units", aggfunc="sum", fill_value=0.0)
    after = proposed.pivot_table(index="Cell", columns="Factory", values="Units", aggfunc="sum", fill_value=0.0)
    all_cells = before.index.union(after.index)
    all_factories = before.columns.union(after.columns)
    before = before.reindex(index=all_cells, columns=all_factories, fill_value=0.0)
    after = after.reindex(index=all_cells, columns=all_factories, fill_value=0.0)
    moved = before.sum(axis=1) - np.minimum(before, after).sum(axis=1)

    def describe(row):
        return "; ".join(f"{f} ({u:,.0f})" for f, u in row.items() if u > _TOL)

    changed = pd.DataFrame({"Units Moved": moved,
                            "Existing allocation": before.apply(describe, axis=1),
                            "Proposed allocation": after.apply(describe, axis=1)})
    changed = changed[changed["Units Moved"] > _TOL].reset_index()
    um_before = baseline.groupby("Cell")["Unit-Miles"].sum()
    um_after = proposed.groupby("Cell")["Unit-Miles"].sum()
    # astype(float): when nothing changed, `changed` is empty and mapping an empty text column
    # would produce a text column that cannot be subtracted below.
    changed["Unit-Miles Before"] = changed["Cell"].map(um_before).astype(float)
    changed["Unit-Miles After"] = changed["Cell"].map(um_after).astype(float)
    changed["Unit-Miles Saved"] = changed["Unit-Miles Before"] - changed["Unit-Miles After"]
    meta = baseline.drop_duplicates("Cell").set_index("Cell")
    changed.insert(1, "State/Province", changed["Cell"].map(meta["State/Province"]))
    changed.insert(2, "Product Name", changed["Cell"].map(meta["Product Name"]))
    changed = changed.sort_values("Unit-Miles Saved", ascending=False).reset_index(drop=True)

    return {
        "baseline_unit_miles": base_um, "proposed_unit_miles": new_um,
        "reduction_unit_miles": reduction,
        "reduction_pct": 100 * reduction / base_um if base_um > 0 else float("nan"),
        "total_units": units,
        "avg_miles_per_unit_before": base_um / units if units else float("nan"),
        "avg_miles_per_unit_after": new_um / units if units else float("nan"),
        "units_by_factory": by_factory, "changed_cells": changed,
        "cells_changed": int(len(changed)),
    }


def estimated_cost(unit_miles, rate_per_unit_mile):
    """ILLUSTRATIVE cost = rate x unit-miles. Returns None unless the user supplied a rate.

    Kept apart from distance results and from the efficiency score on purpose.
    """
    if rate_per_unit_mile is None or (isinstance(rate_per_unit_mile, float) and math.isnan(rate_per_unit_mile)):
        return None
    if rate_per_unit_mile < 0:
        raise ValueError("cost rate must not be negative")
    return float(rate_per_unit_mile) * float(unit_miles)


# ---------------------------------------------------------------------------
# 5. Order-line level export (explicit splits)
# ---------------------------------------------------------------------------
def split_order_lines(valid_lines, proposed, distance):
    """Spread each cell's proposed factory quotas over its ORIGINAL order lines, with explicit splits.

    The optimiser decides per cell, not per order. To keep line-level detail without falsely
    giving a whole line to one factory, lines are taken in Row ID order and each factory's quota is
    filled in turn (factories alphabetical). A line that straddles two quotas becomes TWO rows,
    each with its own Allocated Units, and "Line Split" = True. This disaggregation rule is
    bookkeeping; WHICH orders go to which factory inside a cell is arbitrary, not an optimiser result.
    """
    if (proposed["Units"] - proposed["Units"].round()).abs().max() > _TOL:
        raise ValueError("Line-level split needs whole-number allocations.")
    quotas = {cell: [[f, int(round(u))] for f, u in sorted(zip(g["Factory"], g["Units"]))]
              for cell, g in proposed.groupby("Cell")}
    keep = ["Row ID", "Order ID", "Customer ID", "Order Date", "Country/Region", "State/Province",
            "Product Name", "Units", "Factory"]
    out = []
    for cell, lines in valid_lines.sort_values("Row ID").groupby("Cell", sort=False):
        queue = quotas.get(cell, [])
        qi = 0
        for rec in lines[keep].itertuples(index=False):
            remaining = int(rec.Units)
            while remaining > 0:
                while qi < len(queue) and queue[qi][1] == 0:
                    qi += 1
                if qi >= len(queue):
                    raise ValueError(f"Allocation for {cell} supplies fewer units than its order lines need.")
                take = min(remaining, queue[qi][1])
                d = float(distance.loc[cell, queue[qi][0]])
                out.append((rec[0], rec[1], rec[2], str(rec[3])[:10], rec[4], rec[5], rec[6], int(rec.Units),
                            rec[8], queue[qi][0], take, d, take * d))
                queue[qi][1] -= take
                remaining -= take
    cols = ["Row ID", "Order ID", "Customer ID", "Order Date", "Country/Region", "State/Province",
            "Product Name", "Original Line Units", "Current Factory", "Proposed Factory",
            "Allocated Units", "Distance (mi)", "Unit-Miles"]
    result = pd.DataFrame(out, columns=cols)
    result["Line Split"] = result.groupby("Row ID")["Row ID"].transform("count") > 1
    result["Factory Changed"] = result["Current Factory"] != result["Proposed Factory"]
    return result
