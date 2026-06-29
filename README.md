# Nassau Candy Distributor — Factory-to-Customer Shipping Route Efficiency Analysis

## ⚠️ Read this first: a critical data-quality finding

Before trusting any "lead time" or "delay" number from this dataset: the `Ship Date` field
does **not** track `Order Date` realistically. Computed lead times average ~1,300 days with
**no meaningful difference between Same Day and Standard Class shipping** — which is not
possible for real shipment data. This points to an upstream ETL/data-generation issue.

Because of this, **no lead-time, delay-frequency, or time-based efficiency claim appears
anywhere in this project.** Instead, a **Route Efficiency Proxy Score** is used, built only from
validated fields: shipping distance (factory → customer) and ship-mode mix. This is documented
in full in Section 3 of the research paper, with a dedicated chart (`05_data_quality_exhibit.png`)
showing the issue visually.

## What's in this package

| File | Purpose |
|---|---|
| `Nassau_Candy_Route_Efficiency_Research_Paper.docx` | Full research paper — methodology, data validation finding, route benchmarking, geographic bottlenecks, recommendations |
| `Nassau_Candy_Route_Efficiency_Executive_Summary.docx` | 2-page stakeholder briefing |
| `app.py` | Streamlit dashboard (live, filterable analytics) |
| `route_core.py` | Core analysis engine — cleaning, route definition, efficiency proxy, ship-mode/geo analysis. Imported by `app.py` |
| `Nassau_Candy_Distributor.csv` | Source dataset |
| `requirements.txt` | Python dependencies |
| `charts/` | Static chart images embedded in the report |

## Running the dashboard

1. Keep all files in the same folder (the dashboard expects the CSV next to it).
2. ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```
3. Four tabs:
   - **Route Efficiency Overview** — top/bottom 10 routes by efficiency proxy, full route table
   - **Geographic Shipping Map** — US choropleth of shipment volume, factory locations, bottleneck flags
   - **Ship Mode Comparison** — volume and distance by ship mode, plus the data-quality exhibit
   - **Route Drill-Down** — pick a state, see factory mix, ship-mode mix, and order-level records

Sidebar filters: date range, region, state, ship mode, minimum route distance.

## Headline findings

- **Ship Date field is broken** — flagged prominently rather than used.
- **Short-haul regional routes are most efficient** (Wicked Choccy's → Gulf, Secret Factory → Interior); **long-haul national routes are least efficient** (Lot's O' Nuts → Atlantic, Wicked Choccy's → Pacific).
- The company's two highest-revenue factories are also running its two least-efficient high-volume routes.
- **18 of 59 states** are flagged as bottleneck candidates (high volume + long distance) — led by California, New York, Pennsylvania.

## Notes for your portfolio / internship application

This is a strong project to discuss in interviews specifically *because* it required pushing back
on the brief: the assignment asked for lead-time/delay KPIs, but the data couldn't support them
honestly. Building a defensible substitute metric and documenting the limitation — rather than
reporting numbers you know are wrong — is exactly the kind of judgment call that distinguishes a
strong analyst from someone who just runs the requested calculation blindly.

This project pairs naturally with the companion **Product Line Profitability & Margin Performance
Analysis** (same dataset, same Ship Date issue, different business question) — together they make
a two-project portfolio piece showing range across profitability and logistics analytics.
