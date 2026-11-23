"""Headless smoke tests of the Streamlit dashboard (no browser needed)."""
import pathlib
import pytest
from streamlit.testing.v1 import AppTest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGES = ["views/executive_overview.py", "views/geographic_analysis.py", "views/route_performance.py"]


def run(path):
    return AppTest.from_file(str(ROOT / path), default_timeout=180).run()


def test_entry_point_navigation_runs():
    at = run("app.py")                      # the default page (Executive Overview) renders
    assert not at.exception, [e.value for e in at.exception]
    assert any("Executive Overview" in t.value for t in at.title)


@pytest.mark.parametrize("page", PAGES)
def test_every_page_runs_without_exceptions(page):
    at = run(page)
    assert not at.exception, [e.value for e in at.exception]


@pytest.mark.parametrize("page", PAGES)
def test_default_filters_keep_every_row_including_canada(page):
    at = run(page)
    assert any("matching filters: **10,194**" in c.value for c in at.sidebar.caption)
    country = [m for m in at.sidebar.multiselect if m.key == "f_country"][0]
    assert "Canada" in country.value


def test_country_filter_removes_canadian_rows():
    at = run("views/executive_overview.py")
    [m for m in at.sidebar.multiselect if m.key == "f_country"][0].set_value(["United States"]).run()
    assert not at.exception
    assert any("matching filters: **9,994**" in c.value for c in at.sidebar.caption)


def test_distance_filter_above_zero_excludes_nothing_unexpected():
    at = run("views/route_performance.py")
    [s for s in at.sidebar.slider if s.key == "f_dist"][0].set_value(500).run()
    assert not at.exception


def test_drilldown_renders_for_us_and_canada():
    at = run("views/route_performance.py")
    drill = [s for s in at.selectbox if "Ontario" in s.options][0]
    for state in ("Ontario", "Texas", "Alabama"):
        drill.select(state).run()
        assert not at.exception, (state, [e.value for e in at.exception])


def test_state_level_route_table_renders():
    at = run("views/route_performance.py")
    at.radio[0].set_value("State/Province").run()
    assert not at.exception


def test_score_settings_change_is_accepted():
    at = run("views/executive_overview.py")
    [s for s in at.sidebar.slider if s.key == "w_distance"][0].set_value(50).run()
    assert not at.exception
    assert any("50% distance" in c.value for c in at.caption)


def test_geographic_filters_work():
    at = run("views/geographic_analysis.py")
    [s for s in at.slider if s.key == "geo_pct"][0].set_value(10).run()
    assert not at.exception
    at.checkbox[0].set_value(True).run()
    assert not at.exception
    f = [m for m in at.multiselect if m.key == "geo_factories"][0]
    f.set_value(["Sugar Shack"]).run()
    assert not at.exception


# ---------------------------------------------------------------------------
# Optimization Center
# ---------------------------------------------------------------------------
OPT = "views/optimization_center.py"


def card_values(at):
    return [m.value.split("<p>")[1].split("</p>")[0] for m in at.markdown if "metric-card" in m.value and "<p>" in m.value]


def test_optimization_page_runs_and_is_labelled_hypothetical():
    at = run(OPT)
    assert not at.exception, [e.value for e in at.exception]
    assert any("HYPOTHETICAL SIMULATION" in e.value for e in at.error)
    assert card_values(at)[0] == "48,099,961"                       # existing unit-miles, calculated from the dataset


def test_optimization_cost_hidden_until_rate_entered():
    at = run(OPT)
    assert not any("Estimated transport cost (illustrative" in m.value for m in at.markdown)
    assert any("Estimated transport cost is not shown" in c.value for c in at.caption)
    [n for n in at.number_input if n.key == "opt_rate"][0].set_value(0.01).run()
    assert not at.exception
    assert any("Estimated transport cost (illustrative" in m.value for m in at.markdown)


def test_optimization_current_mapping_gives_zero_reduction():
    at = run(OPT)
    [r for r in at.radio if r.key == "opt_elig"][0].set_value("Current mapping only (reproduces the existing plan)").run()
    assert not at.exception
    vals = card_values(at)
    assert vals[0] == vals[1] and vals[2] == "0"


def test_optimization_automatic_capacity_runs_and_changes_result():
    at = run(OPT)
    free = card_values(at)[1]
    [r for r in at.radio if r.key == "opt_cap"][0].set_value("Automatic: current volume + headroom").run()
    assert not at.exception
    capped = card_values(at)[1]
    assert capped != free and float(capped.replace(",", "")) > float(free.replace(",", ""))   # limits can only cost more


def test_optimization_infeasible_manual_capacities_are_explained():
    at = run(OPT)
    [r for r in at.radio if r.key == "opt_cap"][0].set_value("Manual per factory").run()
    for n in at.number_input:
        if n.key and n.key.startswith("opt_cap_"):
            n.set_value(1000)
    at.run()
    assert not at.exception
    assert any("No valid plan" in e.value and "short by" in e.value for e in at.error)


# ---------------------------------------------------------------------------
# Phase 4 pages
# ---------------------------------------------------------------------------
def text_of(at):
    return " ".join([m.value for m in at.markdown] + [c.value for c in at.caption] + [e.value for e in at.error]
                    + [w.value for w in at.warning] + [i.value for i in at.info] + [s.value for s in at.success])


def test_scenario_simulator_compares_scenarios_and_hides_cost_until_rate():
    at = run("views/scenario_simulator.py")
    assert not at.exception, [e.value for e in at.exception]
    assert any("HYPOTHETICAL SIMULATION" in e.value for e in at.error)
    assert "No cost is shown" in text_of(at)
    [n for n in at.number_input if n.key == "sim0_rate"][0].set_value(0.01).run()
    assert not at.exception and "Cost columns are ESTIMATES" in text_of(at)
    table = [d for d in at.dataframe if "Scenario" in d.value.columns][0].value
    assert list(table["Scenario"])[:2] == ["Existing (dataset)", "Scenario 1"]
    assert "Est. cost difference ($)" in table.columns and table["Type"].iloc[0].startswith("Actual")


def test_scenario_simulator_four_scenarios_and_infeasible_one():
    at = run("views/scenario_simulator.py")
    [r for r in at.radio if r.key == "sim_n"][0].set_value(4).run()
    assert not at.exception
    elig = [r for r in at.radio if r.key == "sim1_elig"][0]
    elig.set_value("Custom: lock products / exclude factories").run()
    [m for m in at.multiselect if m.key == "sim1_locked"][0].set_value(["Nerds"]).run()
    [m for m in at.multiselect if m.key == "sim1_excl"][0].set_value(["Sugar Shack"]).run()
    assert not at.exception
    assert any("no valid plan" in e.value and "Scenario 2" in e.value for e in at.error)      # reason shown
    table = [d for d in at.dataframe if "Scenario" in d.value.columns][0].value
    assert len(table) == 5 and table.loc[table["Scenario"] == "Scenario 2", "Status"].iloc[0] == "INFEASIBLE"


def test_smart_recommendations_page_explains_every_recommendation():
    at = run("views/smart_recommendations.py")
    assert not at.exception, [e.value for e in at.exception]
    labels = [e.label for e in at.expander]
    assert any(l.startswith("R01") for l in labels)
    t = text_of(at)
    assert "Why." in t and "Rule." in t and "Supporting values." in t
    [m for m in at.multiselect if m.key == "rec_basis"][0].set_value(["Dataset"]).run()
    assert not at.exception
    assert not any("Hypothetical ·" in e.label or "· Hypothetical ·" in e.label for e in at.expander)


def test_anomaly_page_shows_summary_reasons_and_route_records():
    at = run("views/anomaly_detection.py")
    assert not at.exception, [e.value for e in at.exception]
    summary = [d for d in at.dataframe if "Check" in d.value.columns][0].value
    assert summary.set_index("Check").loc["Duplicate / repeated order lines", "Flagged"] == 3018
    assert "No record is ever deleted or modified" in text_of(at)
    sel = [s for s in at.selectbox if s.key == "an_route"][0]
    assert sel.value == "Lot's O' Nuts -> Newfoundland and Labrador"
    reasons = [d.value for d in at.dataframe if "Reason" in d.value.columns]
    assert reasons and all(r["Reason"].astype(str).str.len().gt(10).all() for r in reasons)


def test_reports_page_generates_pdf_excel_csv_with_scenario_and_timestamp():
    at = run("views/reports.py")
    assert not at.exception, [e.value for e in at.exception]
    assert "press **Generate reports**" in text_of(at)
    [n for n in at.number_input if n.key == "rep_rate"][0].set_value(0.02)
    [b for b in at.button if b.key == "rep_generate"][0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    bundle = at.session_state["report_bundle"]
    assert bundle["pdf"].startswith(b"%PDF-") and bundle["xlsx"][:2] == b"PK" and bundle["zip"][:2] == b"PK"
    assert "illustrative cost $0.02 per unit-mile" in bundle["assumptions"] and len(bundle["stamp"]) == 19
    assert "order_allocations.csv" in bundle["csv"]
    assert len(at.get("download_button")) >= 3
    assert "Reports generated" in text_of(at)


def test_reports_page_infeasible_scenario_is_explained_not_hidden():
    at = run("views/reports.py")
    [r for r in at.radio if r.key == "rep_elig"][0].set_value("Custom: lock products / exclude factories").run()
    [m for m in at.multiselect if m.key == "rep_locked"][0].set_value(["Nerds"]).run()
    [m for m in at.multiselect if m.key == "rep_excl"][0].set_value(["Sugar Shack"]).run()
    [b for b in at.button if b.key == "rep_generate"][0].click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state["report_bundle"]["status"] == "INFEASIBLE"
    assert "no valid plan" in text_of(at).lower()


def test_entry_point_lists_all_eight_pages():
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    for title in ["Executive Overview", "Geographic Analysis", "Route Performance", "Optimization Center",
                  "Scenario Simulator", "Smart Recommendations", "Anomaly Detection", "Reports"]:
        assert f'title="{title}"' in src
