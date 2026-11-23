"""Tests for report building (modules/reporting.py) and the CSV / Excel / PDF writers (utils/report_generator.py)."""
import io
import re
import zipfile
from datetime import datetime

import numpy as np
import pandas as pd
import pytest
from openpyxl import load_workbook

import route_core as rc
from modules.reporting import build_report_data, factory_performance_table, shipping_mode_table
from modules.scenarios import Scenario
from utils.report_generator import (SHEETS, make_csv_exports, make_excel, make_pdf, number_format, format_value,
                                    _safe)

STAMP = datetime(2026, 11, 9, 14, 30, 5)


@pytest.fixture(scope="module")
def base():
    df, meta = rc.load_and_clean()
    return df, meta


@pytest.fixture(scope="module")
def data_no_cost(base):
    df, meta = base
    return build_report_data(df, Scenario("Plain scenario", headroom_pct=20), meta=meta, total_rows=len(df), generated_at=STAMP)


@pytest.fixture(scope="module")
def data_cost(base):
    df, meta = base
    return build_report_data(df, Scenario("Costed scenario", headroom_pct=20, cost_rate=0.01), meta=meta,
                             total_rows=len(df), generated_at=STAMP)


@pytest.fixture(scope="module")
def data_infeasible(base):
    df, meta = base
    s = Scenario("Impossible", "custom", locked_products=("Nerds",), excluded_factories=("Sugar Shack",))
    return build_report_data(df, s, meta=meta, total_rows=len(df), generated_at=STAMP)


def pdf_text(pdf_bytes):
    """Visible text of an UNCOMPRESSED ReportLab PDF (text shows as (..) Tj operators)."""
    raw = pdf_bytes.decode("latin-1")
    return " ".join(re.findall(r"\(((?:[^()\\]|\\.)*)\)\s*Tj", raw))


# ---- report content ------------------------------------------------------------------------------------------------
def test_report_data_contains_every_section_and_timestamp(data_no_cost):
    d = data_no_cost
    assert d["generated_at"] == "2026-11-09 14:30:05"
    for key in ["kpis", "insights", "region_routes", "state_routes", "factory_performance", "shipping_modes",
                "scenario_comparison", "factory_volumes", "changed_cells", "order_allocations", "anomaly_overview",
                "recommendations", "data_quality", "limitations"]:
        assert key in d and len(d[key]) > 0, key
    assert "hypothetical capacity = current volume + 20%" in d["scenario_text"]
    assert "70% distance + 30% ship-mode" in d["score_text"]


def test_report_does_not_modify_the_original_data(base):
    df, meta = base
    snapshot = df.copy(deep=True)
    build_report_data(df, Scenario("x", cost_rate=0.5), meta=meta)
    pd.testing.assert_frame_equal(df, snapshot)


def test_cost_only_present_when_rate_entered(data_no_cost, data_cost):
    assert not data_no_cost["has_cost"] and data_cost["has_cost"]
    assert not any("cost" in c.lower() for c in data_no_cost["scenario_comparison"].columns)
    assert "Est. cost difference ($)" in data_cost["scenario_comparison"].columns
    assert (data_cost["scenario_comparison"]["Est. cost, scenario ($)"].dropna() > 0).all()


def test_factory_performance_matches_known_totals(base):
    df, _ = base
    t = factory_performance_table(df).set_index("Factory")
    assert t["Sales"].sum() == pytest.approx(df["Sales"].sum()) and t["Units"].sum() == df["Units"].sum()
    assert t.loc["Sugar Shack", "Orders"] == 33 and t["Sales Share %"].sum() == pytest.approx(100)


def test_shipping_modes_table_excludes_unreliable_lead_time(base):
    df, _ = base
    t = shipping_mode_table(df)
    assert not any("UNRELIABLE" in c or "Lead" in c for c in t.columns) and t["Orders"].sum() == df["Order ID"].nunique()


def test_anomaly_overview_has_reason_for_every_row(data_no_cost):
    ov = data_no_cost["anomaly_overview"]
    assert len(ov) > 3000 and ov["Reason"].astype(str).str.len().gt(10).all()
    assert {"Duplicate order line (identical values)", "Route distance outlier (IQR)"} <= set(ov["Anomaly Type"])


def test_infeasible_scenario_report_has_no_allocation_and_says_why(data_infeasible):
    d = data_infeasible
    assert d["scenario_result"]["status"] == "INFEASIBLE" and d["order_allocations"].empty
    assert "INFEASIBLE" in d["order_allocation_note"]
    assert d["scenario_comparison"].loc[1, "Status"] == "INFEASIBLE"


# ---- Excel ----------------------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def workbook(data_cost):
    return load_workbook(io.BytesIO(make_excel(data_cost)))


def test_excel_has_the_nine_required_sheets_in_order(workbook):
    assert workbook.sheetnames == ["Executive Summary", "Route Analysis", "Factory Performance", "Shipping Modes",
                                   "Optimization", "Order Allocations", "Anomalies", "Recommendations", "Data Quality"]
    assert workbook.sheetnames == SHEETS


def test_excel_executive_summary_has_timestamp_assumptions_and_labels(workbook):
    ws = workbook["Executive Summary"]
    text = " ".join(str(c.value) for row in ws.iter_rows() for c in row if c.value is not None)
    assert "Generated: 2026-11-09 14:30:05" in text
    assert "illustrative cost $0.01 per unit-mile (estimate, not an actual cost)" in text
    assert "HYPOTHETICAL SIMULATION" in text and "Dataset (distinct Order IDs)" in text


def test_excel_numbers_are_numeric_with_formats(workbook):
    ws = workbook["Factory Performance"]
    header = [c.value for c in ws[3]]
    first = {h: ws.cell(row=4, column=i + 1) for i, h in enumerate(header)}
    assert isinstance(first["Sales"].value, float) and first["Sales"].number_format == "#,##0.00"
    assert first["Gross Profit %"].number_format == "0.0" and first["Units"].number_format == "#,##0"
    assert ws.cell(row=3, column=1).font.bold and ws.cell(row=3, column=1).fill.fgColor.rgb.endswith("5B2C6F")


def test_excel_route_sheet_has_scores_and_clear_names(workbook):
    ws = workbook["Route Analysis"]
    headers = [c.value for row in ws.iter_rows(min_row=1, max_row=8) for c in row if c.value in
               ("Route Efficiency Score", "Distance Points", "Ship-Mode Points", "Avg Distance (mi)")]
    assert {"Route Efficiency Score", "Distance Points", "Ship-Mode Points", "Avg Distance (mi)"} <= set(headers)


def test_excel_optimization_sheet_is_labelled_hypothetical_and_costs_are_estimates(workbook):
    text = " ".join(str(c.value) for row in workbook["Optimization"].iter_rows() for c in row if c.value is not None)
    assert "HYPOTHETICAL SIMULATION" in text and "Cost columns are ESTIMATES" in text and "not actual costs" in text
    assert "Est. cost difference ($)" in text and "Existing (dataset)" in text


def test_excel_without_rate_has_no_cost_text(data_no_cost):
    wb = load_workbook(io.BytesIO(make_excel(data_no_cost)))
    text = " ".join(str(c.value) for row in wb["Optimization"].iter_rows() for c in row if c.value is not None)
    assert "Est. cost" not in text and "ESTIMATES" not in text


def test_excel_order_allocations_show_splits_explicitly(workbook, data_cost):
    ws = workbook["Order Allocations"]
    rows = list(ws.iter_rows(values_only=True))
    header_idx = next(i for i, r in enumerate(rows) if r and r[0] == "Row ID")
    header = rows[header_idx]
    body = pd.DataFrame(rows[header_idx + 1:], columns=header)
    assert len(body) == len(data_cost["order_allocations"])
    assert body["Allocated Units"].sum() == data_cost["order_allocations"]["Allocated Units"].sum()
    split = body[body["Line Split"] == True]                                         # noqa: E712
    assert len(split) > 0 and (split.groupby("Row ID").size() > 1).all()             # a split line spans several rows
    assert body["Original Line Units"].notna().all() and body["Proposed Factory"].notna().all()


def test_excel_anomalies_and_recommendations_sheets_have_reasons(workbook):
    anom = list(workbook["Anomalies"].iter_rows(values_only=True))
    assert any(r[0] == "Anomaly Type" and "Reason" in r for r in anom)
    rec_rows = list(workbook["Recommendations"].iter_rows(values_only=True))
    header = next(r for r in rec_rows if r and r[0] == "ID")
    assert {"Why", "Rule", "Supporting Values", "Basis", "Priority"} <= set(header)


def test_excel_data_quality_lists_limitations(workbook):
    text = " ".join(str(c.value) for row in workbook["Data Quality"].iter_rows() for c in row if c.value is not None)
    assert "Ship Date does not track Order Date" in text and "not actual costs" in text


def test_excel_infeasible_scenario_explains_and_omits_allocation(data_infeasible):
    wb = load_workbook(io.BytesIO(make_excel(data_infeasible)))
    opt = " ".join(str(c.value) for row in wb["Optimization"].iter_rows() for c in row if c.value is not None)
    assert "No valid plan (INFEASIBLE)" in opt
    alloc = [r for r in wb["Order Allocations"].iter_rows(values_only=True) if r[0] == "Row ID"]
    assert alloc == []


def test_excel_is_a_valid_zip_container(data_no_cost):
    assert zipfile.is_zipfile(io.BytesIO(make_excel(data_no_cost)))


# ---- CSV -------------------------------------------------------------------------------------------------------------------------------
def test_csv_exports_are_parseable_and_consistent(data_cost):
    files = make_csv_exports(data_cost)
    assert "report_info.csv" in files and "order_allocations.csv" in files and "recommendations.csv" in files
    info = pd.read_csv(io.BytesIO(files["report_info.csv"])).set_index("Item")["Value"]
    assert info["Generated"] == "2026-11-09 14:30:05" and "illustrative cost" in info["Scenario assumptions"]
    alloc = pd.read_csv(io.BytesIO(files["order_allocations.csv"]))
    assert len(alloc) == len(data_cost["order_allocations"]) and "Line Split" in alloc.columns
    for name, blob in files.items():
        assert len(pd.read_csv(io.BytesIO(blob)).columns) >= 2, name


# ---- PDF -------------------------------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def pdf_cost(data_cost):
    return make_pdf(data_cost, compress=False)


def test_pdf_is_valid_and_has_all_sections(pdf_cost):
    assert pdf_cost.startswith(b"%PDF-") and pdf_cost.rstrip().endswith(b"%%EOF")
    text = pdf_text(pdf_cost)
    for heading in ["1. Executive summary", "2. Factory performance", "3. Route analysis", "4. Optimization comparison",
                    "5. Recommendations", "6. Anomalies", "7. Data quality and methodology limitations"]:
        assert heading in text, heading


def test_pdf_has_timestamp_assumptions_and_hypothetical_labelling(pdf_cost):
    text = pdf_text(pdf_cost)
    assert "2026-11-09 14:30:05" in text and "HYPOTHETICAL SIMULATION" in text
    assert "illustrative cost $0.01 per unit-mile" in text and "They are not actual costs" in text
    assert "Ship Date does not track Order Date" in text


def test_pdf_without_rate_has_no_cost_estimates(data_no_cost):
    text = pdf_text(make_pdf(data_no_cost, compress=False))
    assert "Est. cost" not in text and "ESTIMATES" not in text


def test_pdf_infeasible_scenario_states_no_valid_plan(data_infeasible):
    text = pdf_text(make_pdf(data_infeasible, compress=False))
    assert "No valid plan" in text and "INFEASIBLE" in text


def test_pdf_compressed_and_uncompressed_both_build(data_no_cost):
    a, b = make_pdf(data_no_cost), make_pdf(data_no_cost, compress=False)
    assert a.startswith(b"%PDF-") and b.startswith(b"%PDF-") and len(a) < len(b)


# ---- formatting helpers ----------------------------------------------------------------------------------------------------------------
def test_number_formats_and_value_formatting():
    assert number_format("Sales") == "#,##0.00" and number_format("Gross Profit %") == "0.0"
    assert number_format("Row ID") == "0" and number_format("Avg Distance (mi)") == "#,##0"
    assert format_value("Sales", 1234.5) == "1,234.50" and format_value("Units", 21412) == "21,412"
    assert format_value("Reduction %", 48.949) == "48.9" and format_value("Row ID", 4237) == "4237"
    assert format_value("Sales", np.nan) == "-" and format_value("Line Split", True) == "Yes"


def test_pdf_text_sanitizer_handles_unsupported_characters():
    assert _safe("a → b ≥ c") == "a -&gt; b &gt;= c"
    assert _safe("R&D <x>") == "R&amp;D &lt;x&gt;"
