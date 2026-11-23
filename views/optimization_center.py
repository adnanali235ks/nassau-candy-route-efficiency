"""Optimization Center: HYPOTHETICAL factory allocation simulation (OR-Tools GLOP)."""

import plotly.express as px
import streamlit as st

import route_core as rc
from modules.optimization import (
    HYPOTHETICAL_NOTICE, build_demand_cells, distance_matrix, all_factories_eligible,
    current_mapping_eligibility, capacity_from_current, solve_allocation, baseline_allocation,
    compare_allocations, estimated_cost, split_order_lines)
from ui import common
from ui.common import ACCENT, PRIMARY

ctx = common.load_page_data()
fdf = ctx["fdf"]

st.title("Optimization Center")
st.error("🧪 " + HYPOTHETICAL_NOTICE)
st.caption("Labels: **Dataset** = read from the CSV · **Calculated** = derived from the data · "
           "**Hypothetical** = depends on assumptions you set below. Uses the rows matching the sidebar filters.")

with st.expander("How the optimizer works (plain language)"):
    st.markdown("""
**Question.** *If other factories could make a product, how much shorter would the straight-line shipping distance be?*

**Demand cells.** Orders are grouped into *cells* = one state/province × one product. A cell's **units** are its demand.
Customers in the same state share a destination centroid, so grouping loses no distance information; each cell keeps its
order, customer and order-line counts, and the export traces every original order line.

**Decision variables.** `x[cell, factory]` = how many units of the cell that factory ships.

**Objective.** Minimise the total of `distance × units` over all cells ("**unit-miles**"), using straight-line miles from the
factory to the state/province centroid.

**Constraints.** (1) every cell's units are fully supplied; (2) *optional*: a factory ships no more than its **hypothetical**
capacity; (3) a factory may only ship products it is **eligible** to make (all-factory eligibility is an *assumption*);
(4) no negative shipments. A cell may be supplied by more than one factory.

**How OR-Tools finds the answer.** It uses the **GLOP** linear solver (the simplex method). Picture every valid plan as a corner
of a many-sided shape. GLOP hops from corner to corner, each hop lowering total unit-miles, and stops when no neighbouring
corner is cheaper, which is then the best plan.

**Why the answer comes out in whole units.** This is a *transportation problem*: each shipment variable appears in exactly one
"supply this cell" constraint and at most one "factory capacity" constraint. For such problems, when demands and capacities are
whole numbers, every corner of the shape is a whole-number plan. So no rounding is needed (the code checks this too).

**Without capacity limits** every cell simply goes to its nearest eligible factory, which is an *upper bound* on distance savings,
not a plan. Capacity inputs here are **hypothetical assumptions, not real factory capacities.**
""")

# ---------------------------------------------------------------------------
# Demand cells, distances, existing allocation
# ---------------------------------------------------------------------------
cells, valid, excluded = build_demand_cells(fdf)
if cells.empty:
    st.warning("No demand with known locations matches the current filters.")
    st.stop()
distance = distance_matrix(cells)
existing = baseline_allocation(valid, cells, distance)
current_volume = existing.groupby("Factory")["Units"].sum()
factories = list(rc.FACTORIES)

if len(excluded):
    reasons = excluded.groupby("Exclusion Reason")["Units"].agg(["count", "sum"])
    st.warning(f"**{len(excluded):,} order lines ({int(excluded['Units'].sum()):,} units) are excluded** from the "
               "optimization because their location or factory is unknown; they are never treated as 0 miles. "
               + "; ".join(f"{k}: {int(v['count'])} lines" for k, v in reasons.iterrows()))

# ---------------------------------------------------------------------------
# Assumptions
# ---------------------------------------------------------------------------
st.markdown('<p class="block-title">1 · Hypothetical assumptions</p>', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    elig_mode = st.radio("Which factories may make each product?", [
        "Hypothetical: every factory can make every product",
        "Current mapping only (reproduces the existing plan)",
        "Custom per product"], key="opt_elig")
    products = sorted(cells["Product Name"].unique())
    if elig_mode.startswith("Hypothetical"):
        eligibility = all_factories_eligible(products, factories)
        st.caption("⚠️ **Assumption:** the dataset says each product is made at exactly one factory. "
                   "Letting other factories make it is hypothetical.")
    elif elig_mode.startswith("Current"):
        eligibility = current_mapping_eligibility(products, rc.PRODUCT_FACTORY_MAP, factories)
        st.caption("Each product stays at its mapped factory, so the result must equal the existing plan (a sanity check).")
    else:
        edited = st.data_editor(all_factories_eligible(products, factories), key="opt_elig_editor", width="stretch")
        eligibility = edited.astype(bool)
        st.caption("Untick a box to forbid a factory from making a product. ⚠️ Hypothetical eligibility.")
with c2:
    cap_mode = st.radio("Factory capacity (hypothetical)", [
        "No capacity limits", "Automatic: current volume + headroom", "Manual per factory"], key="opt_cap")
    capacities = None
    if cap_mode.startswith("Automatic"):
        headroom = st.slider("Headroom above each factory's current volume (%)", 0, 200, 20, step=5, key="opt_headroom")
        capacities = capacity_from_current(current_volume.reindex(factories).fillna(0), headroom)
        st.caption("⚠️ **Hypothetical capacity assumption**, calculated from the current allocation "
                   f"(current units + {headroom}%, rounded down); not an actual factory capacity. "
                   "A factory with no current volume gets 0.")
    elif cap_mode.startswith("Manual"):
        st.caption("⚠️ Hypothetical capacities in units over the whole period. Leave a field empty for unlimited.")
        capacities = {}
        for f in factories:
            capacities[f] = st.number_input(f"{f} — max units (current: {int(current_volume.get(f, 0)):,})",
                                            min_value=0, value=None, step=1, key=f"opt_cap_{f}")
    rate = st.number_input("Illustrative transport cost per unit-mile ($) — optional", min_value=0.0, value=None,
                           step=0.001, format="%.4f", key="opt_rate",
                           help="Left empty by default. No cost is calculated unless you enter a rate. "
                                "The rate is your assumption, not a dataset value.")

# ---------------------------------------------------------------------------
# Solve
# ---------------------------------------------------------------------------
result = solve_allocation(cells, distance, eligibility, capacities)
st.markdown('<p class="block-title">2 · Result</p>', unsafe_allow_html=True)

if result.status != "OPTIMAL":
    st.error(f"**No valid plan: {result.status.lower()}.** {result.message}")
    st.caption("Raise capacities, add eligible factories for the product, or remove the capacity limits.")
    st.stop()

cmp = compare_allocations(existing, result.allocation)
if not result.integral:
    st.warning("The solver returned fractional unit counts; the line-level export is disabled.")

cols = st.columns(5)
common.metric_card(cols[0], "Existing unit-miles", f"{cmp['baseline_unit_miles']:,.0f}", "calculated · dataset allocation")
common.metric_card(cols[1], "Hypothetical unit-miles", f"{cmp['proposed_unit_miles']:,.0f}", "hypothetical simulation")
common.metric_card(cols[2], "Reduction", f"{cmp['reduction_unit_miles']:,.0f}",
                   f"hypothetical · {cmp['reduction_pct']:.1f}% lower")
common.metric_card(cols[3], "Avg miles per unit",
                   f"{cmp['avg_miles_per_unit_before']:,.0f} → {cmp['avg_miles_per_unit_after']:,.0f}", "calculated / hypothetical")
common.metric_card(cols[4], "Demand cells changed", f"{cmp['cells_changed']:,} / {len(cells):,}", "hypothetical")
st.caption("Unit-miles = units × straight-line miles to the state/province centroid. Canadian centroids are provisional. "
           + ("" if capacities else "With no capacity limits this is an **upper bound** on savings, not a plan."))

st.markdown("")
base_cost = estimated_cost(cmp["baseline_unit_miles"], rate)
if base_cost is None:
    st.caption("💲 Estimated transport cost is not shown: enter an illustrative cost per unit-mile above to see it. "
               "Cost is always kept separate from unit-miles and from the route efficiency score.")
else:
    new_cost = estimated_cost(cmp["proposed_unit_miles"], rate)
    st.markdown("**Estimated transport cost (illustrative: your rate × unit-miles; not an actual financial metric)**")
    k = st.columns(3)
    common.metric_card(k[0], "Existing (estimate)", f"${base_cost:,.0f}", f"at ${rate:g} per unit-mile")
    common.metric_card(k[1], "Hypothetical (estimate)", f"${new_cost:,.0f}", "hypothetical")
    common.metric_card(k[2], "Difference (estimate)", f"${base_cost - new_cost:,.0f}", "hypothetical")

# ---------------------------------------------------------------------------
# Factory volumes
# ---------------------------------------------------------------------------
st.markdown('<p class="block-title">3 · Volume by factory, before and after</p>', unsafe_allow_html=True)
vol = cmp["units_by_factory"]
long = vol.melt(id_vars="Factory", value_vars=["Before (units)", "After (units)"], var_name="Plan", value_name="Units")
fig = px.bar(long, x="Factory", y="Units", color="Plan", barmode="group",
             color_discrete_map={"Before (units)": PRIMARY, "After (units)": ACCENT})
fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig, width="stretch")
if capacities:
    st.caption("Capacity limits used (hypothetical): " + ", ".join(
        f"{f}: {c:,}" for f, c in capacities.items() if c is not None))
common.show_table(vol.round(0))

# ---------------------------------------------------------------------------
# Changed allocations
# ---------------------------------------------------------------------------
st.markdown('<p class="block-title">4 · Changed demand allocations</p>', unsafe_allow_html=True)
st.caption("Each row is a state/province × product cell whose supplying factory changes. A cell can be split across "
           "factories; units moved are shown with the existing and proposed allocation.")
info = cells.set_index("Cell")[["Orders", "Customers", "Order_Lines"]].rename(columns={"Order_Lines": "Order Lines"})
changed = cmp["changed_cells"].join(info, on="Cell")
common.show_table(changed.drop(columns="Cell").round(0))

st.markdown("**Units allocated from each factory to each demand cell (hypothetical plan)**")
plan = result.allocation.join(info, on="Cell").round(1)
common.show_table(plan.drop(columns="Cell"))

# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------
st.markdown('<p class="block-title">5 · Export</p>', unsafe_allow_html=True)
d1, d2 = st.columns(2)
d1.download_button("⬇️ Cell-level allocation (CSV)", plan.to_csv(index=False).encode("utf-8"),
                   file_name="hypothetical_allocation_by_cell.csv", mime="text/csv")
if result.integral:
    line_level = split_order_lines(valid, result.allocation, distance)
    d2.download_button("⬇️ Order-line allocation with explicit splits (CSV)",
                       line_level.to_csv(index=False).encode("utf-8"),
                       file_name="hypothetical_allocation_by_order_line.csv", mime="text/csv")
    n_split = int(line_level.loc[line_level["Line Split"], "Row ID"].nunique())
    st.caption(f"Order-line file: {len(line_level):,} rows for {len(valid):,} original lines. {n_split:,} line(s) are "
               "split across factories and appear on several rows (see *Line Split*). Which orders inside a cell take "
               "which factory is a bookkeeping rule (Row ID order), **not** an optimizer decision.")
st.caption("The original dataset is never modified; this page works on copies.")
