"""
Write the report content from modules/reporting.build_report_data() as Excel (OpenPyXL), PDF (ReportLab) and CSV.

All three read the SAME data dictionary, so numbers always agree. Every output carries the generation timestamp,
the selected scenario's assumptions, and the hypothetical / estimate labelling.
"""

import io
from xml.sax.saxutils import escape

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

REPORT_TITLE = "Nassau Candy - Supply Chain Route Analytics Report"
SHEETS = ["Executive Summary", "Route Analysis", "Factory Performance", "Shipping Modes", "Optimization",
          "Order Allocations", "Anomalies", "Recommendations", "Data Quality"]

_PURPLE, _AMBER = "5B2C6F", "FDEBD0"


# ---------------------------------------------------------------------------
# Shared formatting
# ---------------------------------------------------------------------------
def number_format(column):
    """Excel number format for a column name (None = leave as is)."""
    c = column.lower()
    if c in ("row id", "customer id", "postal code", "group size"):
        return "0"
    if "%" in c or "score" in c or "points" in c:
        return "0.0"
    if "rate" in c:
        return "0.0000"
    if "($)" in c or c in ("sales", "gross profit", "cost", "est. cost"):
        return "#,##0.00"
    if any(k in c for k in ("mi)", "mi", "unit-miles", "units", "orders", "customers", "shipments", "lines", "served",
                            "saved", "moved", "before", "after", "change")):
        return "#,##0"
    return None


def format_value(column, value):
    """Text for PDF tables (same rules as the Excel formats)."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "-"
    if isinstance(value, (bool, np.bool_)):
        return "Yes" if value else "No"
    if isinstance(value, (int, float, np.integer, np.floating)):
        fmt = number_format(column)
        if fmt == "0":
            return f"{value:.0f}"
        if fmt == "0.0":
            return f"{value:,.1f}"
        if fmt == "0.0000":
            return f"{value:.4f}"
        if fmt == "#,##0.00":
            return f"{value:,.2f}"
        if fmt == "#,##0":
            return f"{value:,.0f}"
        return f"{value:,.2f}" if isinstance(value, (float, np.floating)) and value != int(value) else f"{value:,.0f}"
    return str(value)


def _py(v):
    """Convert numpy/pandas values to plain Python for OpenPyXL (NaN -> None)."""
    if v is None:
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return None if np.isnan(v) else float(v)
    if isinstance(v, float) and np.isnan(v):
        return None
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime().strftime("%Y-%m-%d")
    if v is pd.NaT:
        return None
    return v


_ROUTE_COLUMNS = ["Route", "Factory", "Shipments", "Units", "Sales", "Avg Distance (mi)", "Distance Score",
                  "Ship-Mode Score", "Distance Points", "Ship-Mode Points", "Route Efficiency Proxy Score"]


def route_table(routes):
    """Route table for reports: readable columns, 'Route Efficiency Score' name, unscored kept as blank."""
    t = routes[_ROUTE_COLUMNS].copy()
    t = t.rename(columns={"Shipments": "Orders", "Route Efficiency Proxy Score": "Route Efficiency Score"})
    return t


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------
def _write_title(ws, row, text, size=12, bold=True, fill=None, color=None):
    cell = ws.cell(row=row, column=1, value=text)
    cell.font = Font(bold=bold, size=size, color=color)
    cell.alignment = Alignment(wrap_text=False, vertical="top")
    if fill:
        cell.fill = PatternFill("solid", fgColor=fill)
    return row + 1


def _write_table(ws, df, row, wrap_columns=(), widths=None):
    """Write a DataFrame at `row` with a styled header; return the next free row."""
    if df is None or len(df.columns) == 0:
        return row
    for j, col in enumerate(df.columns, start=1):
        c = ws.cell(row=row, column=j, value=str(col))
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=_PURPLE)
        c.alignment = Alignment(wrap_text=True, vertical="center")
    formats = [number_format(str(col)) for col in df.columns]
    wraps = [str(col) in wrap_columns for col in df.columns]
    for i, rec in enumerate(df.itertuples(index=False), start=row + 1):
        for j, value in enumerate(rec, start=1):
            c = ws.cell(row=i, column=j, value=_py(value))
            if formats[j - 1] and isinstance(c.value, (int, float)) and not isinstance(c.value, bool):
                c.number_format = formats[j - 1]
            if wraps[j - 1]:
                c.alignment = Alignment(wrap_text=True, vertical="top")
    return row + len(df) + 2


def _autosize(ws, max_width=60, min_width=9, fixed=None):
    widths = {}
    for row in ws.iter_rows():
        for c in row:
            if c.value is None:
                continue
            length = min(len(str(c.value)), 200)
            widths[c.column_letter] = max(widths.get(c.column_letter, 0), length)
    for col, w in widths.items():
        ws.column_dimensions[col].width = max(min_width, min(max_width, w + 2))
    for col, w in (fixed or {}).items():
        ws.column_dimensions[col].width = w


def _banner(ws, row, text):
    return _write_title(ws, row, text, size=11, fill=_AMBER, color="8A4B08")


def make_excel(data):
    """Build the Excel workbook (bytes) with the nine required sheets."""
    wb = Workbook()
    wb.remove(wb.active)
    sheets = {name: wb.create_sheet(name) for name in SHEETS}

    # ---- Executive Summary --------------------------------------------------------------------------
    ws = sheets["Executive Summary"]
    r = _write_title(ws, 1, REPORT_TITLE, size=15)
    r = _write_title(ws, r, f"Generated: {data['generated_at']}", bold=False)
    r = _write_title(ws, r, f"Rows in this report: {data['rows_in_report']:,} of {data['total_rows']:,} loaded", bold=False)
    r = _write_title(ws, r + 1, "Selected scenario assumptions (HYPOTHETICAL)")
    r = _write_title(ws, r, data["scenario_text"], bold=False)
    r = _write_title(ws, r, data["score_text"], bold=False)
    r = _banner(ws, r + 1, data["hypothetical_banner"])
    k = data["kpis"]
    kpi_rows = [
        ("Orders", k["total_orders"], "Dataset (distinct Order IDs)"),
        ("Total sales ($)", k["total_sales"], "Dataset"),
        ("Factories", k["factories"], "Assumption (product-to-factory mapping)"),
        ("Customers", k["customers"], "Dataset (distinct Customer IDs)"),
        ("Average shipping distance (mi)", k["avg_distance_mi"], "Calculated (straight-line, per order)"),
        ("Route efficiency (0-100)", k["overall_efficiency"], "Calculated (order-weighted average of Region route scores)"),
        ("Scored routes (Region level)", k["scored_routes"], "Calculated"),
        ("Unscored routes (Region level)", k["unscored_routes"], "Calculated (no known distance)"),
    ]
    r = _write_title(ws, r + 1, "Key performance indicators")
    r = _write_table(ws, pd.DataFrame(kpi_rows, columns=["KPI", "Value", "Basis"]), r)
    for rr in range(r - len(kpi_rows) - 1, r - 1):         # number formats for the Value column
        label = ws.cell(row=rr, column=1).value or ""
        cell = ws.cell(row=rr, column=2)
        if "($)" in label:
            cell.number_format = "#,##0.00"
        elif "(mi)" in label:
            cell.number_format = "#,##0"
        elif "efficiency" in label.lower():
            cell.number_format = "0.0"
        else:
            cell.number_format = "#,##0"
    r = _write_title(ws, r, "Business insights (rule-based, descriptive)")
    ins = pd.DataFrame(data["insights"]).rename(columns={"title": "Insight", "text": "Finding", "why": "Why"})
    r = _write_table(ws, ins, r, wrap_columns=("Finding", "Why"))
    r = _write_title(ws, r, "Best and worst scored routes (Region level)")
    both = pd.concat([data["best_routes"].assign(Rank="Best 5"), data["worst_routes"].assign(Rank="Worst 5")])
    cols = ["Rank", "Route", "Shipments", "Avg Distance (mi)", "Route Efficiency Proxy Score"]
    r = _write_table(ws, both[cols].rename(columns={"Shipments": "Orders", "Route Efficiency Proxy Score": "Route Efficiency Score"}), r)
    _autosize(ws, max_width=70, fixed={"A": 34, "B": 28, "C": 40})

    # ---- Route Analysis -----------------------------------------------------------------------------------
    ws = sheets["Route Analysis"]
    r = _write_title(ws, 1, "Route analysis: Route Efficiency Score = distance + ship-mode points (calculated; weights are assumptions)", size=12)
    r = _write_title(ws, r, data["score_text"], bold=False)
    r = _write_title(ws, r + 1, "Region-level routes (blank score = unscored: distance unknown, never ranked)")
    r = _write_table(ws, route_table(data["region_routes"]), r)
    r = _write_title(ws, r, "State/Province-level routes")
    r = _write_table(ws, route_table(data["state_routes"]), r)
    ws.freeze_panes = "A4"
    _autosize(ws)

    # ---- Factory Performance -------------------------------------------------------------------------------
    ws = sheets["Factory Performance"]
    r = _write_title(ws, 1, "Factory performance (actual sales data; distance is calculated, straight-line to state/province centroids)")
    r = _write_table(ws, data["factory_performance"], r + 1)
    _autosize(ws)

    # ---- Shipping Modes -------------------------------------------------------------------------------------
    ws = sheets["Shipping Modes"]
    r = _write_title(ws, 1, "Shipping modes (Ship Date is unreliable, so no lead-time metric is reported)")
    r = _write_table(ws, data["shipping_modes"], r + 1)
    _autosize(ws)

    # ---- Optimization ---------------------------------------------------------------------------------------------
    ws = sheets["Optimization"]
    res = data["scenario_result"]
    r = _banner(ws, 1, data["hypothetical_banner"])
    r = _write_title(ws, r, f"Scenario: {data['scenario'].name}", bold=True)
    r = _write_title(ws, r, data["scenario_text"], bold=False)
    if res["status"] != "OPTIMAL":
        r = _write_title(ws, r + 1, f"No valid plan ({res['status']}): {res['message']}", bold=True, color="C0392B")
    else:
        r = _write_title(ws, r + 1, "Existing (dataset) versus hypothetical scenario: unit-miles = units x straight-line miles")
        r = _write_table(ws, data["scenario_comparison"], r)
        if data["has_cost"]:
            r = _write_title(ws, r, "Cost columns are ESTIMATES: the illustrative rate you entered x unit-miles. "
                                    "They are not actual costs.", bold=False, color="8A4B08")
        r = _write_title(ws, r, "Units per factory: existing versus hypothetical")
        r = _write_table(ws, data["factory_volumes"], r)
        r = _write_title(ws, r, "Demand cells (state/province x product) whose supplying factory changes (hypothetical)")
        r = _write_table(ws, data["changed_cells"], r)
    _autosize(ws, max_width=55)

    # ---- Order Allocations ----------------------------------------------------------------------------------------
    ws = sheets["Order Allocations"]
    r = _banner(ws, 1, data["hypothetical_banner"])
    r = _write_title(ws, r, data["order_allocation_note"] or "No allocation available.", bold=False)
    r = _write_title(ws, r, "A line split across factories appears on several rows, each with its own Allocated Units. "
                            "Which orders take which factory inside a cell is a bookkeeping rule, not an optimizer decision.",
                     bold=False)
    if len(data["order_allocations"]):
        _write_table(ws, data["order_allocations"], r + 1)
        ws.freeze_panes = ws.cell(row=r + 2, column=1)
    _autosize(ws, max_width=40)

    # ---- Anomalies ---------------------------------------------------------------------------------------------------
    ws = sheets["Anomalies"]
    r = _write_title(ws, 1, "Anomalies: flagged for review only. No record has been deleted or changed.")
    r = _write_table(ws, data["anomalies"]["summary"], r + 1)
    r = _write_title(ws, r, "Flagged records and subjects, with the reason for each flag")
    _write_table(ws, data["anomaly_overview"], r, wrap_columns=("Reason",))
    _autosize(ws, fixed={"E": 90})

    # ---- Recommendations -----------------------------------------------------------------------------------------------
    ws = sheets["Recommendations"]
    r = _write_title(ws, 1, "Smart recommendations: rule-based prompts to investigate, each with its reason, rule and values. "
                            "Rows marked Hypothetical depend on simulation assumptions.")
    _write_table(ws, data["recommendations"], r + 1,
                 wrap_columns=("Title", "Recommendation", "Why", "Rule", "Supporting Values"))
    _autosize(ws, fixed={"E": 38, "F": 60, "G": 50, "H": 45, "I": 55})

    # ---- Data Quality -------------------------------------------------------------------------------------------------------
    ws = sheets["Data Quality"]
    r = _write_title(ws, 1, "Data quality and limitations")
    r = _write_table(ws, data["data_quality"], r + 1)
    r = _write_title(ws, r, "Methodology limitations")
    for text in data["limitations"]:
        c = ws.cell(row=r, column=1, value="- " + text)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
        ws.row_dimensions[r].height = 32
        r += 1
    _autosize(ws, fixed={"A": 58, "B": 60, "C": 24})

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------
def make_csv_exports(data):
    """Dict of file name -> CSV bytes. The first file records the timestamp and assumptions."""
    info = pd.DataFrame({"Item": ["Report", "Generated", "Scenario", "Scenario assumptions", "Score method",
                                  "Rows in report", "Label"],
                         "Value": [REPORT_TITLE, data["generated_at"], data["scenario"].name, data["scenario_text"],
                                   data["score_text"], f"{data['rows_in_report']:,} of {data['total_rows']:,}",
                                   data["hypothetical_banner"]]})
    k = data["kpis"]
    kpis = pd.DataFrame({"KPI": list(k.keys()), "Value": list(k.values())})
    files = {
        "report_info.csv": info, "kpis.csv": kpis,
        "route_analysis_region.csv": route_table(data["region_routes"]),
        "route_analysis_state.csv": route_table(data["state_routes"]),
        "factory_performance.csv": data["factory_performance"], "shipping_modes.csv": data["shipping_modes"],
        "optimization_comparison.csv": data["scenario_comparison"], "factory_volumes.csv": data["factory_volumes"],
        "changed_demand_cells.csv": data["changed_cells"], "order_allocations.csv": data["order_allocations"],
        "anomalies.csv": data["anomaly_overview"], "recommendations.csv": data["recommendations"],
        "data_quality.csv": data["data_quality"],
    }
    return {name: table.to_csv(index=False).encode("utf-8") for name, table in files.items()}


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------
def _safe(text):
    """Make text safe for ReportLab's standard fonts (Latin-1/WinAnsi) and Paragraph markup."""
    text = str(text)
    for a, b in (("→", "->"), ("≥", ">="), ("≤", "<="), ("−", "-"), ("–", "-"), ("—", "-"), ("…", "..."),
                 ("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("•", "-")):
        text = text.replace(a, b)
    text = text.encode("cp1252", "replace").decode("cp1252")
    return escape(text)


def make_pdf(data, compress=True):
    """Build the PDF report (bytes) with ReportLab."""
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

    purple, amber = colors.HexColor("#5B2C6F"), colors.HexColor("#FDEBD0")
    ss = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=ss["BodyText"], fontSize=9, leading=12)
    small = ParagraphStyle("small", parent=body, fontSize=7.5, leading=9.5)
    h1 = ParagraphStyle("h1", parent=ss["Heading1"], textColor=purple, fontSize=17, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=purple, fontSize=13, spaceBefore=10, spaceAfter=4)
    banner_style = ParagraphStyle("banner", parent=body, backColor=amber, borderPadding=5, textColor=colors.HexColor("#8A4B08"))

    page = landscape(A4)
    usable = page[0] - 2 * 1.4 * cm

    def P(text, style=body):
        # Escape everything, then re-enable only our own bold/italic tags (data text never contains them).
        safe = _safe(text)
        for tag in ("b", "i"):
            safe = safe.replace(f"&lt;{tag}&gt;", f"<{tag}>").replace(f"&lt;/{tag}&gt;", f"</{tag}>")
        return Paragraph(safe, style)

    def table(df, widths=None, max_rows=None, columns=None, wrap=()):
        df = df if columns is None else df[columns]
        if max_rows is not None:
            df = df.head(max_rows)
        header = [Paragraph(f"<b>{_safe(c)}</b>", small) for c in df.columns]
        rows = [header]
        for rec in df.itertuples(index=False):
            row = []
            for col, v in zip(df.columns, rec):
                text = format_value(str(col), v)
                row.append(Paragraph(_safe(text), small) if (col in wrap or len(text) > 22) else _safe(text))
            rows.append(row)
        if widths:
            total = sum(widths)
            widths = [w / total * usable for w in widths]
        t = Table(rows, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), purple), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4EEF8")]),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CCCCCC")),
            ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
        # white header text inside Paragraph cells
        for c in header:
            c.style = ParagraphStyle("hdr", parent=small, textColor=colors.white)
        return t

    def bar_chart(categories, series, names, title, width=usable / 2 - 10, height=190):
        d = Drawing(width, height)
        d.add(String(width / 2, height - 10, _safe(title), fontSize=9, textAnchor="middle"))
        chart = VerticalBarChart()
        chart.x, chart.y, chart.width, chart.height = 45, 45, width - 60, height - 75
        chart.data = series
        chart.categoryAxis.categoryNames = [_safe(c) for c in categories]
        chart.categoryAxis.labels.fontSize = 6.5
        chart.categoryAxis.labels.angle = 20
        chart.categoryAxis.labels.boxAnchor = "ne"
        chart.valueAxis.labels.fontSize = 7
        chart.valueAxis.valueMin = 0
        palette = [purple, colors.HexColor("#E67E22"), colors.HexColor("#2E8B57"), colors.HexColor("#8e6bb0")]
        for i in range(len(series)):
            chart.bars[i].fillColor = palette[i % len(palette)]
            chart.bars[i].strokeColor = None
        chart.barSpacing = 1
        d.add(chart)
        for i, n in enumerate(names):                         # simple legend: colour swatch + label
            x0 = 55 + i * 110
            d.add(Rect(x0, 6, 8, 8, fillColor=palette[i % len(palette)], strokeColor=None))
            d.add(String(x0 + 12, 7, _safe(n), fontSize=7))
        return d

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(1.4 * cm, 0.9 * cm, _safe(f"{REPORT_TITLE}  |  Generated {data['generated_at']}"))
        canvas.drawRightString(page[0] - 1.4 * cm, 0.9 * cm, f"Page {doc.page}")
        canvas.restoreState()

    buf = io.BytesIO()
    kwargs = {} if compress else {"pageCompression": 0}
    doc = SimpleDocTemplate(buf, pagesize=page, leftMargin=1.4 * cm, rightMargin=1.4 * cm, topMargin=1.3 * cm,
                            bottomMargin=1.6 * cm, title=REPORT_TITLE, author="Nassau Candy Route Analytics", **kwargs)
    s = []
    k, res = data["kpis"], data["scenario_result"]

    # 1. Title + executive summary
    s += [P(REPORT_TITLE, h1), P(f"Generated: {data['generated_at']}  |  Rows in this report: "
                                 f"{data['rows_in_report']:,} of {data['total_rows']:,} loaded"),
          Spacer(1, 4), P("<b>Selected scenario assumptions (hypothetical):</b> " + data["scenario_text"]),
          P("<b>Scoring method:</b> " + data["score_text"]), Spacer(1, 4),
          P(data["hypothetical_banner"], banner_style), P("1. Executive summary", h2)]
    kpi = [["KPI", "Value", "Basis"],
           ["Orders", f"{k['total_orders']:,}", "Dataset (distinct Order IDs)"],
           ["Total sales", f"${k['total_sales']:,.2f}", "Dataset"],
           ["Factories", f"{k['factories']}", "Assumption (product-to-factory mapping)"],
           ["Customers", f"{k['customers']:,}", "Dataset (distinct Customer IDs)"],
           ["Average shipping distance", f"{k['avg_distance_mi']:,.0f} mi", "Calculated (straight-line, per order)"],
           ["Route efficiency (0-100)", "n/a" if k["overall_efficiency"] != k["overall_efficiency"] else f"{k['overall_efficiency']:.1f}",
            "Calculated (order-weighted average of Region route scores)"]]
    kt = Table([[_safe(c) for c in r] for r in kpi], colWidths=[usable * 0.28, usable * 0.2, usable * 0.5])
    kt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), purple), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("FONTSIZE", (0, 0), (-1, -1), 8.5), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CCCCCC"))]))
    s += [kt, Spacer(1, 6), P("Business insights (rule-based, descriptive)", h2)]
    for item in data["insights"]:
        s.append(P(f"<b>{item['title']}.</b> {item['text']}  <i>Why: {item['why']}</i>", body))
    fs = data["factory_performance"]
    ship = data["ship_mode_distribution"]

    # 2. Factory performance
    s += [PageBreak(), P("2. Factory performance", h2),
          P("Actual sales data by factory (factory assigned through the product-to-factory mapping); distances are "
            "calculated straight-line miles to state/province centroids."),
          table(fs, [1.6, .8, .9, .8, 1, 1, .9, .9, 1, 1.2, 1.2]), Spacer(1, 6),
          Table([[bar_chart(fs["Factory"], [list(fs["Sales"])], ["Sales ($)"], "Sales by factory (dataset)"),
                  bar_chart(ship["Ship Mode"], [list(ship["Orders"])], ["Orders"], "Orders by ship mode (dataset)")]],
                colWidths=[usable / 2, usable / 2])]

    # 3. Route analysis
    s += [PageBreak(), P("3. Route analysis", h2),
          P("Routes are factory-to-region pairs ranked by the Route Efficiency Score (calculated; the weights and ship-mode "
            "suitability are assumptions). Unscored routes (unknown distance) are never ranked."),
          P("Top 5 routes", h2), table(route_table(data["best_routes"]), [3, 1.2, .9, .9, .9, 1.2, 1, 1, 1, 1, 1.1]),
          P("Bottom 5 routes", h2), table(route_table(data["worst_routes"]), [3, 1.2, .9, .9, .9, 1.2, 1, 1, 1, 1, 1.1]),
          P("Shipping modes (Ship Date is unreliable, so no lead time is reported)", h2),
          table(data["shipping_modes"])]

    # 4. Optimization comparison
    s += [PageBreak(), P("4. Optimization comparison (HYPOTHETICAL SIMULATION)", h2), P(data["hypothetical_banner"], banner_style),
          Spacer(1, 4)]
    if res["status"] != "OPTIMAL":
        s.append(P(f"<b>No valid plan ({res['status']}):</b> {res['message']}"))
    else:
        s += [P("Unit-miles = units x straight-line miles. Existing = the dataset's allocation; the scenario row is a "
                "simulation."), table(data["scenario_comparison"], wrap=("Scenario", "Type"))]
        if data["has_cost"]:
            s.append(P("Cost columns are ESTIMATES: the illustrative rate entered x unit-miles. They are not actual costs.",
                       banner_style))
        vol = data["factory_volumes"]
        sc_name = [c for c in vol.columns if c not in ("Factory", "Existing (dataset)")][0]
        s += [Spacer(1, 6), P("Units per factory, existing versus hypothetical", h2),
              Table([[table(vol), bar_chart(vol["Factory"], [list(vol["Existing (dataset)"]), list(vol[sc_name])],
                                            ["Existing", "Hypothetical"], "Units by factory", width=usable * 0.45)]],
                    colWidths=[usable * 0.5, usable * 0.5], style=[("VALIGN", (0, 0), (-1, -1), "TOP")]),
              P("Top demand cells whose factory changes (hypothetical)", h2)]
        if len(data["changed_cells"]):
            s.append(table(data["changed_cells"], [2.6, 1, 1.8, .8, 2.2, 2.2, 1, 1, 1],
                           columns=["Cell", "State/Province", "Product Name", "Units Moved", "Existing allocation",
                                    "Proposed allocation", "Unit-Miles Before", "Unit-Miles After", "Unit-Miles Saved"],
                           max_rows=12, wrap=("Existing allocation", "Proposed allocation", "Cell")))
        s.append(P(data["order_allocation_note"] + " The full order-line allocation, with every split shown explicitly, is "
                   "in the Excel workbook (sheet 'Order Allocations') and the CSV export.", small))

    # 5. Recommendations
    s += [PageBreak(), P("5. Recommendations", h2),
          P("Rule-based prompts to investigate; each shows why it was generated, the rule and the values. Rows marked "
            "Hypothetical depend on simulation assumptions."),
          table(data["recommendations"], [.5, 1.1, .6, .9, 2.2, 2.6, 2.4], max_rows=18,
                columns=["ID", "Category", "Priority", "Basis", "Title", "Why", "Supporting Values"],
                wrap=("Title", "Why", "Supporting Values", "Category"))]
    if len(data["recommendations"]) > 18:
        s.append(P(f"Showing 18 of {len(data['recommendations'])} recommendations; all are in the Excel workbook.", small))

    # 6. Anomalies
    s += [PageBreak(), P("6. Anomalies", h2),
          P("Flagged for review only; no record has been deleted or changed."),
          table(data["anomalies"]["summary"], [3, 1, 1.5, 3]), Spacer(1, 4)]
    ov = data["anomaly_overview"]
    if len(ov):
        sample = ov.groupby("Anomaly Type", sort=False).head(2)
        s += [P("Examples of flagged records (the full list is in the Excel workbook)", h2),
              table(sample, [2.2, 2, .6, 1.6, 5], wrap=("Reason", "Subject", "Anomaly Type"))]

    # 7. Data quality and limitations
    s += [PageBreak(), P("7. Data quality and methodology limitations", h2), table(data["data_quality"], [3, 4, 1.2],
                                                                                   wrap=("Item", "Value"))]
    s.append(P("Limitations", h2))
    for text in data["limitations"]:
        s.append(P("- " + text))

    doc.build(s, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
