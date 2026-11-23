"""Phase 5 robustness and regression tests: data loading, edge cases, all pages under awkward filters,
and guards that the original CSV and the product-to-factory mapping are unchanged."""
import ast
import hashlib
import pathlib
import shutil
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import route_core as rc
from modules import anomaly_detection as ad
from modules import recommendations as rec
from modules import scenarios as sc
from modules.reporting import build_report_data
from modules.scenarios import Scenario
from utils.report_generator import make_csv_exports, make_excel, make_pdf

ROOT = pathlib.Path(__file__).resolve().parents[1]
CSV = ROOT / "Nassau_Candy_Distributor.csv"
PAGES = ["executive_overview", "geographic_analysis", "route_performance", "optimization_center",
         "scenario_simulator", "smart_recommendations", "anomaly_detection", "reports"]


# ---------------------------------------------------------------------------------------------------
# Guards: original data and mapping must never change
# ---------------------------------------------------------------------------------------------------
ORIGINAL_CSV_SHA256 = "6ae9208e77ce410e90073b19813d29f89853ce9f3cce43d41f9643781696e94f"

ORIGINAL_PRODUCT_FACTORY_MAP = {
    "Wonka Bar - Nutty Crunch Surprise": "Lot's O' Nuts", "Wonka Bar - Fudge Mallows": "Lot's O' Nuts",
    "Wonka Bar -Scrumdiddlyumptious": "Lot's O' Nuts", "Wonka Bar - Milk Chocolate": "Wicked Choccy's",
    "Wonka Bar - Triple Dazzle Caramel": "Wicked Choccy's", "Laffy Taffy": "Sugar Shack", "SweeTARTS": "Sugar Shack",
    "Nerds": "Sugar Shack", "Fun Dip": "Sugar Shack", "Fizzy Lifting Drinks": "Sugar Shack",
    "Everlasting Gobstopper": "Secret Factory", "Hair Toffee": "The Other Factory", "Lickable Wallpaper": "Secret Factory",
    "Wonka Gum": "Secret Factory", "Kazookles": "The Other Factory"}


def test_original_csv_is_byte_for_byte_unchanged():
    digest = hashlib.sha256(CSV.read_bytes()).hexdigest()
    assert digest == ORIGINAL_CSV_SHA256, "Nassau_Candy_Distributor.csv has changed; the original data must be preserved."


def test_product_to_factory_mapping_is_unchanged():
    assert rc.PRODUCT_FACTORY_MAP == ORIGINAL_PRODUCT_FACTORY_MAP


# ---------------------------------------------------------------------------------------------------
# CSV path and friendly errors
# ---------------------------------------------------------------------------------------------------
def test_default_csv_path_is_absolute_and_inside_the_project():
    assert rc.DEFAULT_CSV_PATH.is_absolute() and rc.DEFAULT_CSV_PATH == CSV and rc.DEFAULT_CSV_PATH.exists()


def test_loading_works_from_any_working_directory(tmp_path):
    code = (f"import sys; sys.path.insert(0, r'{ROOT}'); import route_core as rc; "
            "df, meta = rc.load_and_clean(); print(len(df))")
    out = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-500:]
    assert out.stdout.strip().splitlines()[-1] == "10194"


def test_bare_file_name_is_looked_up_in_the_project_folder(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    df, _ = rc.load_and_clean("Nassau_Candy_Distributor.csv")
    assert len(df) == 10194


def test_missing_file_gives_friendly_error_with_expected_path_and_fix(tmp_path):
    with pytest.raises(rc.DataFileError) as err:
        rc.load_and_clean(tmp_path / "nope.csv")
    text = str(err.value)
    assert "Data file not found" in text and "nope.csv" in text
    assert "Nassau_Candy_Distributor.csv" in text and "Fix:" in text and str(rc.PROJECT_DIR) in text


def test_directory_instead_of_file_is_reported(tmp_path):
    with pytest.raises(rc.DataFileError, match="not a file"):
        rc.load_and_clean(tmp_path)


def test_empty_file_is_reported(tmp_path):
    p = tmp_path / "empty.csv"
    p.write_text("", encoding="utf-8")
    with pytest.raises(rc.DataFileError, match="empty"):
        rc.load_and_clean(p)


def test_wrong_columns_list_what_is_missing_and_what_is_required(tmp_path):
    p = tmp_path / "wrong.csv"
    pd.read_csv(CSV).drop(columns=["Sales", "Units"]).head(20).to_csv(p, index=False)
    with pytest.raises(rc.DataFileError) as err:
        rc.load_and_clean(p)
    text = str(err.value)
    assert "missing required column(s): Sales, Units" in text and "Required columns:" in text and "Found columns:" in text


def test_every_required_column_exists_in_the_real_csv():
    assert set(rc.REQUIRED_COLUMNS) <= set(pd.read_csv(CSV, nrows=1).columns)


def test_file_without_usable_rows_is_reported(tmp_path):
    p = tmp_path / "bad_rows.csv"
    raw = pd.read_csv(CSV).head(5)
    raw["Sales"] = "n/a"                                           # no numeric sales at all
    raw.to_csv(p, index=False)
    with pytest.raises(rc.DataFileError, match="No usable rows"):
        rc.load_and_clean(p)


def test_non_numeric_values_drop_only_their_own_rows(tmp_path):
    p = tmp_path / "some_bad.csv"
    raw = pd.read_csv(CSV).head(10).astype({"Sales": object})
    raw.loc[0, "Sales"] = "oops"
    raw.to_csv(p, index=False)
    df, meta = rc.load_and_clean(p)
    assert len(df) == 9 and meta["rows_removed"] == 1


def test_cli_entry_point_prints_a_clean_message_when_data_missing(tmp_path):
    # Copy the code (but NOT the CSV) into an empty folder and run `python route_core.py` there.
    shutil.copy(ROOT / "route_core.py", tmp_path / "route_core.py")
    shutil.copy(ROOT / "config.py", tmp_path / "config.py")
    shutil.copytree(ROOT / "modules", tmp_path / "modules", ignore=shutil.ignore_patterns("__pycache__"))
    out = subprocess.run([sys.executable, str(tmp_path / "route_core.py")], cwd=tmp_path, capture_output=True,
                         text=True, timeout=120)
    assert out.returncode != 0
    assert "Data problem: Data file not found" in out.stderr and "Traceback" not in out.stderr
    assert not list(tmp_path.glob("*.csv"))                          # and nothing was written


def test_dashboard_shows_friendly_error_instead_of_a_traceback(monkeypatch, tmp_path):
    monkeypatch.setattr(rc, "DEFAULT_CSV_PATH", tmp_path / "missing.csv")
    st.cache_data.clear()
    try:
        at = AppTest.from_file(str(ROOT / "views" / "executive_overview.py"), default_timeout=120).run()
        assert not at.exception                                     # no crash
        assert any("Data file problem" in e.value for e in at.error)
        assert any("Data file not found" in m.value and "Fix:" in m.value for m in at.markdown)
    finally:
        st.cache_data.clear()                                       # do not leak the failure into other tests


# ---------------------------------------------------------------------------------------------------
# Edge cases: tiny and unusual subsets through every module and writer
# ---------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def full():
    return rc.load_and_clean()


def subset(df, name):
    unknown = {"Customer Lat": np.nan, "Customer Lon": np.nan, "Route Distance (mi)": np.nan, "Missing Geo": True}
    return {
        "canada": lambda: df[df["Country/Region"] == "Canada"],
        "sugar_shack": lambda: df[df["Factory"] == "Sugar Shack"],
        "one_state": lambda: df[df["State/Province"] == "Wyoming"],
        "one_line": lambda: df.head(1),
        "two_lines": lambda: df[df["State/Province"] == "Wyoming"].head(2),
        "same_day": lambda: df[df["Ship Mode"] == "Same Day"],
        "far_routes": lambda: df[df["Route Distance (mi)"] >= 2500],
        "some_unknown_location": lambda: df.head(3).assign(**unknown),
        "all_unknown_location": lambda: df.head(50).assign(**unknown),
    }[name]()


EDGE = ["canada", "sugar_shack", "one_state", "one_line", "two_lines", "same_day", "far_routes",
        "some_unknown_location", "all_unknown_location"]
SCENARIOS = [Scenario("free"), Scenario("limited", headroom_pct=0, cost_rate=0.01),
             Scenario("custom", "custom", locked_products=("Nerds",), excluded_factories=("Sugar Shack",))]


@pytest.mark.parametrize("name", EDGE)
def test_analysis_modules_survive_edge_subsets(full, name):
    df, _ = full
    sub = subset(df, name)
    snapshot = sub.copy(deep=True)
    ad.detect_all(sub)
    rec.generate_recommendations(sub)
    rc.route_summary(sub, "State/Province")
    rc.route_summary(sub, "Region", include_unscored=True)
    results = sc.run_scenarios(sc.prepare_context(sub), SCENARIOS)
    assert all(r["status"] in ("OPTIMAL", "INFEASIBLE", "NO DATA") for r in results)
    pd.testing.assert_frame_equal(sub, snapshot)                    # nothing was modified


@pytest.mark.parametrize("name", EDGE)
def test_report_writers_survive_edge_subsets(full, name):
    df, meta = full
    sub = subset(df, name)
    for scenario in (SCENARIOS[0], SCENARIOS[2]):
        data = build_report_data(sub, scenario, meta=meta, total_rows=len(df))
        assert make_excel(data)[:2] == b"PK" and make_pdf(data).startswith(b"%PDF-")
        assert "report_info.csv" in make_csv_exports(data)


def test_unknown_location_rows_are_excluded_from_optimisation_and_reported(full):
    df, _ = full
    sub = subset(df, "some_unknown_location")
    ctx = sc.prepare_context(sub)
    assert ctx["cells"].empty and len(ctx["excluded"]) == 3
    assert sc.run_scenario(ctx, SCENARIOS[0])["status"] == "NO DATA"


def test_empty_dataframe_does_not_crash_the_pure_functions(full):
    df, _ = full
    empty = df.iloc[0:0]
    assert len(ad.detect_all(empty)["summary"]) == 6
    assert sc.run_scenario(sc.prepare_context(empty), SCENARIOS[0])["status"] == "NO DATA"


# ---------------------------------------------------------------------------------------------------
# Every page under awkward filter settings
# ---------------------------------------------------------------------------------------------------
def widget(at, key):
    return [w for w in list(at.sidebar.multiselect) + list(at.sidebar.slider) if w.key == key][0]


@pytest.mark.parametrize("page", PAGES)
def test_page_with_filter_that_matches_nothing_shows_a_warning(page):
    at = AppTest.from_file(str(ROOT / "views" / f"{page}.py"), default_timeout=240).run()
    widget(at, "f_dist").set_value(3000)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("No shipments match" in w.value for w in at.warning)


@pytest.mark.parametrize("page", PAGES)
def test_page_with_canada_only_filter_renders(page):
    at = AppTest.from_file(str(ROOT / "views" / f"{page}.py"), default_timeout=240).run()
    widget(at, "f_country").set_value(["Canada"])
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("matching filters: **200**" in c.value for c in at.sidebar.caption)


def test_filters_are_shared_between_pages_by_widget_key():
    keys = {}
    for page in ("executive_overview", "route_performance"):
        at = AppTest.from_file(str(ROOT / "views" / f"{page}.py"), default_timeout=240).run()
        keys[page] = {w.key for w in list(at.sidebar.multiselect) + list(at.sidebar.slider) + list(at.sidebar.date_input)}
    assert keys["executive_overview"] == keys["route_performance"] >= {"f_country", "f_region", "f_states", "f_modes", "f_dist", "f_dates"}


# ---------------------------------------------------------------------------------------------------
# Project configuration
# ---------------------------------------------------------------------------------------------------
def test_streamlit_config_hides_the_deploy_button():
    text = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert 'toolbarMode = "minimal"' in text


def test_requirements_cover_every_third_party_import():
    third_party = {"streamlit", "pandas", "numpy", "plotly", "ortools", "openpyxl", "reportlab", "pytest"}
    imported = set()
    for path in ROOT.rglob("*.py"):
        if ".venv" in path.parts or "tools" in path.parts:      # tools/ is an optional developer script (see its docstring)
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                imported |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                imported.add(node.module.split(".")[0])
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    for package in sorted(imported & third_party):
        assert package in requirements, f"{package} is imported but missing from requirements.txt"
    local = {"route_core", "config", "modules", "ui", "utils"}
    stdlib_or_local_or_known = third_party | local | set(sys.stdlib_module_names) | {"views", "tests"}
    unknown = imported - stdlib_or_local_or_known
    assert not unknown, f"unexpected third-party imports not listed in requirements.txt: {sorted(unknown)}"
