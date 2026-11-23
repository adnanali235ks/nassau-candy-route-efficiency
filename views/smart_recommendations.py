"""Smart Recommendations: explainable, rule-based prompts to investigate. No AI."""

import streamlit as st

from modules import scenarios as sc
from modules.anomaly_detection import detect_all
from modules.optimization import HYPOTHETICAL_NOTICE, capacity_from_current
from modules.recommendations import generate_recommendations
from ui import common
from ui.scenario_controls import scenario_form

ctx = common.load_page_data()
fdf = ctx["fdf"]

st.title("Smart Recommendations")
st.caption("Each recommendation comes from a documented rule: **IF** a measured value crosses a threshold **THEN** a prompt to "
           "investigate appears, with **Why**, the **Rule** and the **Supporting Values**. They are not operational instructions. "
           "Basis: **Dataset** and **Calculated** are real data; **Hypothetical** depends on simulation assumptions.")

with st.expander("Reference scenario for the hypothetical recommendations", expanded=False):
    st.warning(HYPOTHETICAL_NOTICE)
    scenario = scenario_form("rec", "Reference scenario", {"limit": True, "headroom": 20})
    check_headroom = st.slider("Capacity assumption for the overload check: current volume + (%)", 0, 200, 20, step=5,
                               key="rec_check_headroom")
    st.caption("The overload check compares the *unconstrained* nearest-factory plan with this hypothetical capacity.")

context = sc.prepare_context(fdf)
result = sc.run_scenario(context, scenario) if not context["cells"].empty else None
free = sc.run_scenario(context, sc.Scenario("Unconstrained")) if not context["cells"].empty else None
unconstrained = (free["allocation"].groupby("Factory")["Units"].sum() if free and free["status"] == "OPTIMAL" else None)
caps = capacity_from_current(context["current_volume"], check_headroom) if not context["cells"].empty else None
table = generate_recommendations(fdf, detect_all(fdf), result, unconstrained, caps)

c1, c2, c3 = st.columns(3)
priorities = c1.multiselect("Priority", ["High", "Medium", "Low"], default=["High", "Medium", "Low"], key="rec_prio")
categories = c2.multiselect("Category", sorted(table["Category"].unique()), default=sorted(table["Category"].unique()), key="rec_cat")
bases = c3.multiselect("Basis", ["Dataset", "Calculated", "Hypothetical"], default=["Dataset", "Calculated", "Hypothetical"], key="rec_basis")
view = table[table["Priority"].isin(priorities) & table["Category"].isin(categories) & table["Basis"].isin(bases)]

st.markdown(f"**{len(view)} of {len(table)} recommendations**")
icons = {"High": "🔴", "Medium": "🟠", "Low": "🟢"}
for _, rec in view.iterrows():
    with st.expander(f"{rec['ID']} · {icons[rec['Priority']]} {rec['Priority']} · {rec['Basis']} · {rec['Title']}"):
        st.markdown(f"**Recommendation.** {rec['Recommendation']}")
        st.markdown(f"**Why.** {rec['Why']}")
        st.markdown(f"**Rule.** {rec['Rule']}")
        st.markdown(f"**Supporting values.** {rec['Supporting Values']}")
        if rec["Basis"] == "Hypothetical":
            st.caption("🧪 Hypothetical: depends on simulation assumptions, not on actual factory capabilities.")

st.download_button("⬇️ Download recommendations (CSV)", view.to_csv(index=False).encode("utf-8"),
                   file_name="recommendations.csv", mime="text/csv", key="dl_recs")
