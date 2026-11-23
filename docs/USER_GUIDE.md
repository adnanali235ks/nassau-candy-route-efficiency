# User guide

How to run the dashboard and what each page does. For how the numbers are calculated see [METHODOLOGY.md](METHODOLOGY.md); for data limitations see [DATA_SOURCES.md](DATA_SOURCES.md).

## 1. Start the dashboard
**Windows:** run `setup_env.bat` once, then `run_app.bat`.

**Any platform, manually:**
```
python -m venv .venv
.venv\Scriptsctivate            (macOS/Linux: source .venv/bin/activate)
python -m pip install -r requirements.txt
python -m streamlit run app.py
```
Always use the project's `.venv` (`.venv\Scripts\python.exe`), never a global or temporary Python, and run from the project folder: the CSV is read from there. Run the tests with `.venv\Scripts\python.exe -m pytest`.

## 2. Reading the labels
Everything on screen is one of three kinds. Look for these words:

| Label | Meaning |
|---|---|
| **Dataset** | Read straight from the CSV (orders, sales, customers). |
| **Calculated** | Derived by the code from the dataset (distances, scores, unit-miles of the *existing* plan). |
| **Hypothetical** / **Assumption** | Depends on what you assume (which factories could make which products, capacities, cost rate). Not a fact about the business. |

**Estimated costs** are your illustrative rate × unit-miles. They are shown only when you type a rate, and they are never actual costs.

## 3. Sidebar filters (all pages)
Order date range, country, region, state/province, ship mode, minimum route distance. The row count at the bottom shows how many rows match. A **Scoring settings** panel changes the distance / ship-mode weights and the ship-mode suitability numbers (both are assumptions).

## 4. Pages
| Page | Use it to |
|---|---|
| **Executive Overview** | See KPIs, ship-mode and factory charts, best and worst routes and short rule-based insights, each with a "Why" line. |
| **Geographic Analysis** | See factory-to-state/province lines on a map (endpoints are *centroids*, distances are straight-line), compare distances, find high-volume long-distance locations. |
| **Route Performance** | Rank routes by the Route Efficiency Score, see how each score is made up, compare ship modes, drill into one state/province. |
| **Optimization Center** | Run the hypothetical allocation simulation once: choose eligibility and capacity assumptions, read the comparison, download the changed allocations. |
| **Scenario Simulator** | Compare 2 to 4 hypothetical scenarios side by side against the existing allocation. |
| **Smart Recommendations** | Read rule-based prompts to investigate; each shows its reason, rule and values. |
| **Anomaly Detection** | See flagged records (unusual routes, duplicates, missing geography, price/profit patterns, factory-product patterns) and open the records behind each flag. |
| **Reports** | Generate the PDF report, the 9-sheet Excel workbook and CSV exports. |

## 5. Scenario Simulator, step by step
1. Pick how many scenarios (2 to 4).
2. For each: name it; choose **eligibility**: *every factory can make every product* (hypothetical), *current mapping only* (a check that must equal the existing plan), or *custom* (lock chosen products at their current factory and/or forbid chosen factories from making anything).
3. Optionally tick **capacity limits**: each factory's capacity = its current volume + the headroom % you choose.
4. Optionally enter an **illustrative cost per unit-mile**. Leave empty for no cost figures.
5. Read the comparison table: the first row is the existing allocation (actual, calculated); the others are hypothetical. Unit-miles = units × straight-line miles; the reduction is existing minus scenario.
6. A scenario that cannot be solved (for example, a locked product whose only factory is excluded) shows its reason instead of numbers.

Locking works per **product**, not per state.

## 6. Smart Recommendations
Priorities: **High / Medium / Low** follow documented thresholds (shown in each recommendation's *Rule*). **Basis** tells you whether it rests on the data or on simulation assumptions. Use the filters to hide hypothetical rows. Recommendations are prompts to investigate, never instructions.

## 7. Anomaly Detection
* **Flags are not errors.** Nothing is ever deleted or changed.
* *Route distance (IQR)*: routes unusually long or short compared with all routes; pick a flagged route to see its order lines.
* *Duplicate lines*: lines sharing an Order ID + Product ID. "Identical values" are likely exact duplicates; the others may be legitimate extra lines.
* *Missing geography*: blank location fields, unknown centroid or unmapped factory.
* *Sales & profit*: unusual unit price or margin within a product, and Gross Profit + Cost ≠ Sales. (This dataset has one constant price and margin per product, so nothing is flagged and the page says so.)
* *Factory / product pattern*: Product ID prefix versus Division, and very-low-volume factories and products.
Each tab has a CSV download of the flagged records.

## 8. Reports
1. Choose the scenario for the optimization sections (same inputs as above).
2. Press **Generate reports**.
3. Download the **PDF** (executive summary, KPIs, factory performance, route analysis, optimization comparison, recommendations, anomalies, limitations), the **Excel workbook** (sheets: Executive Summary, Route Analysis, Factory Performance, Shipping Modes, Optimization, Order Allocations, Anomalies, Recommendations, Data Quality) or the **CSV ZIP** (individual files are also listed).

Every output shows the generation time and the scenario assumptions. In *Order Allocations* (Excel and CSV), a line whose units are shared between factories appears on **several rows**, each with its own *Allocated Units* and *Line Split = True*. Which orders inside a state/product group take which factory is a bookkeeping rule, not an optimizer decision.
If a scenario is infeasible, the reports say so and give the reason instead of an allocation.

## 9. Tables and downloads
* Tables are sized to show their rows (up to a maximum height, then they scroll inside the frame). Whole-number columns show thousands separators (21,412); identifiers such as Row ID do not.
* Every download button produces a real file: CSV for tables, PDF, Excel (9 sheets) and a CSV ZIP on the Reports page. Their contents were verified by clicking each button in a real browser (see the capture tool in the next section).
* The Optimization Center's on-screen tables hide the internal "Cell" label (it repeats State and Product); the CSV downloads keep it.

## 10. Troubleshooting
| Symptom | Cause and fix |
|---|---|
| **"Data file problem"** page | The CSV is missing, empty, unreadable or lacks required columns. The message states the expected path (the project folder) and the required column names. Put the original `Nassau_Candy_Distributor.csv` there and refresh. |
| The Deploy button shows | Start `streamlit run app.py` from the project folder so `.streamlit/config.toml` is read. Nothing is deployed either way. |
| A page shows "No shipments match the current filters" | Widen the sidebar filters (for example set Minimum route distance back to 0). |
| **"Missing Python packages"** page, or `ModuleNotFoundError: No module named 'ortools'` (or openpyxl, reportlab) | The app is running under a Python that does not have the project's packages, for example a global Python or an old virtual environment. The page names the Python in use. Fix: `.venv\Scripts\python.exe -m pip install -r requirements.txt`, then start with `.venv\Scripts\python.exe -m streamlit run app.py`, and stop the old server. |
| `ImportError: cannot import name 'X' from 'route_core'` (or another project module), although the code contains X | A server that has been running since before the code was updated holds an old copy of the module. Stop it and start a new one. |
| An error mentions `pyarrow requires NumPy 2.0 or newer` | You pinned numpy 1.x with the newest pyarrow. Install `pyarrow==17.0.0`, or upgrade numpy. |
| Changes to code do not appear while the app runs | Stop and restart `python -m streamlit run app.py` (Streamlit keeps old copies of already-loaded helper modules). |

## 11. Re-creating the screenshots (optional)
`tools/capture_screenshots.py` takes full-page screenshots of all pages with Microsoft Edge (installed with Windows) and clicks every download button to check the files. Start the app (`streamlit run app.py --server.port 8503`), then run `python tools/capture_screenshots.py --url http://localhost:8503 --out docs/screenshots`. It needs the `websockets` package (installed with recent Streamlit; otherwise `pip install websockets`).

## 12. Common questions
* **Why is "Factories" an assumption?** The CSV has no factory column; factories come from a product-to-factory map in the code.
* **Why no delivery times?** Ship Date does not track Order Date (about 1,300 days for every ship mode).
* **Why are Canadian numbers marked provisional?** No authoritative province centroid table was found.
* **Is the optimizer result what we should do?** No. It is a what-if simulation; with no capacity limits it is an upper bound.
* **Does anything change the CSV?** No. Every calculation works on copies.
