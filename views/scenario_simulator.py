"""Scenario Simulator: compare several HYPOTHETICAL factory-allocation scenarios side by side."""

import plotly.express as px
import streamlit as st

from modules import scenarios as sc
from modules.optimization import HYPOTHETICAL_NOTICE
from ui import common
from ui.common import ACCENT, PRIMARY
from ui.scenario_controls import scenario_form

ctx_page = common.load_page_data()
fdf = ctx_page["fdf"]

st.title("Scenario Simulator")
st.error("🧪 " + HYPOTHETICAL_NOTICE)
st.caption("Build up to four scenarios (what-if assumption sets) and compare them with the **existing allocation**. "
           "**Existing** is calculated from the dataset; every scenario row is a **hypothetical simulation**. "
           "Uses the rows matching the sidebar filters.")

with st.expander("How scenarios work"):
    st.markdown("""
A **scenario** is a named set of assumptions: *which factories may make which products*, an optional *capacity headroom*
(hypothetical capacity = current volume + X%), and an optional *illustrative cost per unit-mile*.
Each scenario is solved with the same optimizer as the Optimization Center (OR-Tools GLOP): it assigns every state/province × product
demand cell to factories to minimise **unit-miles** (units × straight-line miles). Locking is per **product**: a locked product
stays at its current factory; excluded factories may not make anything. Costs appear only for scenarios where you enter a rate.
""")

n = st.radio("Number of scenarios", [2, 3, 4], horizontal=True, key="sim_n")
DEFAULTS = [{"limit": False}, {"limit": True, "headroom": 20}, {"limit": True, "headroom": 0},
            {"elig_index": 1}]
cols = st.columns(n)
scenarios = []
for i in range(n):
    with cols[i]:
        st.markdown(f"**Scenario {i + 1}**")
        scenarios.append(scenario_form(f"sim{i}", f"Scenario {i + 1}", DEFAULTS[i], container=st))

context = sc.prepare_context(fdf)
if context["cells"].empty:
    st.warning("No demand with known locations matches the current filters.")
    st.stop()
results = sc.run_scenarios(context, scenarios)
table = sc.compare_scenarios(context, results)
volumes = sc.factory_volume_table(context, results)

st.markdown('<p class="block-title">Comparison</p>', unsafe_allow_html=True)
for r in results:
    if r["status"] != "OPTIMAL":
        st.error(f"**{r['name']}: no valid plan ({r['status'].lower()}).** {r['message']}")
common.show_table(table.round({"Unit-miles": 0, "Reduction (unit-miles)": 0, "Reduction %": 1, "Avg miles per unit": 0}))
st.caption("Unit-miles = units × straight-line miles to the state/province centroid (Canadian centroids provisional). "
           "Reduction = existing minus scenario.")
if any(s.cost_rate is not None for s in scenarios):
    st.caption("💲 **Cost columns are ESTIMATES** = the illustrative rate you entered × unit-miles; they are not actual costs. "
               "Scenarios without a rate show no cost.")
else:
    st.caption("💲 No cost is shown: enter an illustrative cost per unit-mile in a scenario to see an estimate for it.")

solved = table[table["Status"].isin(["-", "OPTIMAL"])]
fig = px.bar(solved, x="Scenario", y="Unit-miles", color="Type",
             color_discrete_map={"Actual allocation (calculated)": PRIMARY, "Hypothetical": ACCENT})
fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig, width="stretch")

st.markdown('<p class="block-title">Volume by factory</p>', unsafe_allow_html=True)
long = volumes.melt(id_vars="Factory", var_name="Plan", value_name="Units").dropna()
fig2 = px.bar(long, x="Factory", y="Units", color="Plan", barmode="group")
fig2.update_layout(margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig2, width="stretch")
common.show_table(volumes.round(0))
st.caption("Existing = actual units by supplying factory (dataset). Scenario columns are hypothetical.")

st.markdown('<p class="block-title">Scenario assumptions</p>', unsafe_allow_html=True)
for r in results:
    with st.expander(f"{r['name']} — {r['status']}"):
        st.write(r["assumptions"])
        if r["comparison"] is not None:
            st.markdown(f"**{r['comparison']['cells_changed']:,} demand cells change factory** (hypothetical). Largest changes:")
            common.show_table(r["comparison"]["changed_cells"].head(10).round(0))
