# Methodology

Status: covers everything built so far: scoring (sections 1 to 4), the factory allocation simulation (5), scenarios (6), anomaly detection (7), recommendations (8) and reports (9). Nothing here describes unbuilt features.

Terminology used everywhere in the project: **Dataset observation** (read from the CSV), **Calculated metric** (derived by our code), **Assumption / hypothetical** (chosen by us, not in the data).

## 0. Data cleaning
Code: `load_and_clean` in [route_core.py](../route_core.py). Steps, in order:
1. **Find and validate the file.** The CSV path is resolved from the project folder (not the terminal's folder). A missing, empty, unreadable or wrong-column file raises `DataFileError`, and the dashboard shows what is wrong and how to fix it. Required columns are listed in `REQUIRED_COLUMNS`.
2. **Coerce `Sales` and `Units` to numbers.** Non-numeric text becomes missing and that row is dropped in step 3 (it never crashes the load).
3. **Drop invalid rows:** duplicate `Row ID`; missing `Order Date`, `Ship Date`, `Ship Mode`, `State/Province`, `Region`, `Product Name`, `Sales` or `Units`; non-positive `Sales` or `Units`.
4. **Trim text** in the division, region, state/province, city, ship-mode and product columns.
5. **Parse dates** in day-month-year format; rows with unparseable dates are dropped. If nothing is left, `DataFileError` explains it.
6. **Raw lead time** (`Ship Date − Order Date`) is computed only for transparency and flagged unreliable; it is never used for scoring.
7. **Map each product to its factory** with `PRODUCT_FACTORY_MAP` (an assumption from the project brief) and each state/province to its centroid (`STATE_CENTROIDS`).
8. **Compute the haversine distance** (section 1). A row whose factory or centroid is unknown gets a missing distance and is flagged `Missing Geo`; it is never given 0 miles.
9. **Flag, don't delete:** `Repeated Order-Product Line` marks lines that share an Order ID + Product ID.

Result on the supplied CSV [ran]: 10,194 rows in, 10,194 rows out (none removed), 0 unknown locations, 3,018 repeated lines flagged. Nothing here modifies the CSV file.

## 1. Distance (calculated metric)
Great-circle ("as the crow flies") distance in miles, computed with the **haversine formula** between a factory's coordinates and the **centroid of the customer's state or province**. It is not road distance and not the distance to the customer's address. Canadian province centroids are provisional (see [DATA_SOURCES.md](DATA_SOURCES.md)).

For two points with latitudes φ₁, φ₂ and longitudes λ₁, λ₂ (in radians):
```
a = sin²((φ₂ − φ₁) / 2) + cos φ₁ · cos φ₂ · sin²((λ₂ − λ₁) / 2)
distance = 2 · R · atan2(√a, √(1 − a))          with R = 3,958.8 miles (Earth's radius)
```
*Why haversine:* the Earth is round, so straight lines on a flat map mislead; haversine is a short, exact-enough formula for the great-circle distance on a sphere (it treats the Earth as a perfect sphere, which is typically within about 0.5% of the true distance). *Example:* New York to Los Angeles is about 2,445 miles (a test checks this); one degree of latitude is about 69.1 miles; the distance is symmetric (A→B equals B→A).

## 2. Route Efficiency Score
A *route* is a factory paired with a destination (a region, or a state/province). Each route gets a score from 0 to 100, where higher means more efficient.

```
Score = 70% × Distance Score  +  30% × Ship-Mode Score        (weights configurable)
```

The score has **no cost component**. Estimated shipping costs, when they appear in later phases, are shown separately and never feed into this number.

### 2.1 Distance Score (calculated, from the dataset)
```
Distance Score = 100 × (1 − route's average distance ÷ reference distance)
```
The reference distance is the longest route in the comparison. It scores 0, a zero-mile route would score 100, and everything else falls proportionally in between.

*Worked example.* A route averaging 500 miles, with a 2,000-mile reference: 100 × (1 − 500/2000) = **75**.

### 2.2 Ship-Mode Score (calculated, from an **assumption**)
Each ship mode has a *suitability* between 0 and 1 (Same Day 1.0, First Class 0.85, Second Class 0.6, Standard Class 0.4; set in [config.py](../config.py)). A route's score is the order-share-weighted average of these, times 100.

*Worked example.* 50% Standard Class and 50% First Class: (0.5 × 0.4 + 0.5 × 0.85) × 100 = **62.5**.

**Why this is an assumption.** The numbers describe what each service level is *meant* to deliver. The dataset cannot confirm it, because `Ship Date` is unreliable (every mode averages about 1,300 days between order and "ship"). Changing these values changes the rankings, so they are editable, and the dashboard says they are assumptions.

### 2.3 Combining (the worked example continued)
0.7 × 75 + 0.3 × 62.5 = 52.5 + 18.75 = **71.25**. The table keeps both pieces (`Distance Points`, `Ship-Mode Points`), so every score can be broken down.

### 2.4 Weights
Defaults 70 / 30 (the approved split; they are proposed weights, not validated business facts). They are re-scaled to sum to 1, so 7 / 3 means the same as 0.7 / 0.3. Negative or all-zero weights raise an error. The legacy 60 / 40 is kept in `config.py` only to reproduce old results.

### 2.5 Missing values
| Situation | Behaviour |
|---|---|
| Route's distance unknown | Distance Score = NaN, so the final score = NaN. The route is "unscored", **excluded from rankings** and listed separately. Never 0. |
| A ship mode not in the suitability table | Ignored; remaining shares re-scaled to 100%. (The original code treated unknown modes as 0.5; no such modes exist in this dataset.) |
| No recognised ship mode at all | Ship-Mode Score = NaN, so the final score = NaN |
| One component missing | The other is **not** re-weighted to fill the gap, so scored routes stay comparable |

### 2.6 Limitations
- **Scores are relative.** The longest route sets the zero point, so a route's score depends on what it is compared with. The dashboard fixes the reference to the longest route in the *whole dataset*, so filters don't change scores; the code default (`reference_max_distance=None`) uses the longest route in whatever table it is given.
- The Ship-Mode part rewards *service tier mix*, not measured speed or cost-effectiveness. A route that buys more premium shipping scores higher even if that is wasteful.
- Distance is to a state centroid, so within-state differences are invisible.
- A short route with few orders scores the same as a short route with many; volume is shown beside the score, not inside it.

## 3. Why the scores changed between versions
Two independent things moved the numbers; the formula change in Phase 2 was the second.

| Step | What changed | Effect (measured [ran]) |
|---|---|---|
| Original → Phase 1 | The 200 Canadian rows got distances. Newfoundland and Labrador (about 2,979 miles) is now the farthest State-level route, so the **reference** distance rose from 2,393 to 2,979 miles. Since every Distance Score is `100 × (1 − d ÷ reference)`, a larger reference makes **every** State-level distance look relatively shorter, and scores rise. | State-level routes: up to **11.8** points. Region-level: up to **1.0** (the Region reference barely moved, 2,143 → 2,145 miles, because averages absorb the Canadian rows). |
| Phase 1 → Phase 2 | Weights 60/40 → 70/30. Distance matters more, ship mix less, so long-distance routes fell and short routes rose. | Region-level: up to **5.4** points. State-level: up to **5.2** points. The bottom Region route stays Wicked Choccy's → Pacific. The top changes from The Other Factory → Gulf (72.0, only 19 orders) to Wicked Choccy's → Gulf (74.6, 547 orders). |

Simple intuition: normalising by the maximum is like grading on a curve. Adding one far-away student to the class changes everyone's grade, even though nobody else did anything differently.

## 4. Sensitivity of the provisional Canadian coordinates
Shifting Newfoundland and Labrador's centroid by about 100 miles changed any route's State-level score by at most 1.4 points (median 0.5) [ran].

## 5. Factory allocation simulation (HYPOTHETICAL)
Code: [modules/optimization.py](../modules/optimization.py); page: Optimization Center. **Everything in this section is a what-if simulation, not an operational recommendation.**

### 5.1 The question
The dataset says each product is made at exactly one factory (via the product→factory map). The simulation asks: *if other factories could make the product, how much shorter would the total straight-line shipping distance be?* "Any factory can make any product" is an **assumption** (editable per product); capacities are **hypothetical**; production cost, quality, inventory, lead time and real road routes are ignored.

### 5.2 Data preparation
Order lines are grouped into **demand cells** = (state/province, product). A cell's **Units** (the demand weight) is the sum of its lines' Units; the cell also keeps its order, customer and order-line counts. Customers in one state share the same destination centroid, so grouping loses no distance information. Cells whose destination coordinates or current factory are unknown are **excluded and reported separately**, never given a distance of 0. The original DataFrame is never modified (a test compares it before and after).

### 5.3 The model
| Part | Meaning |
|---|---|
| Decision variables | `x[cell, factory]` = units of the cell shipped by that factory (≥ 0) |
| Objective | minimise Σ `distance(cell, factory) × x[cell, factory]` ("**unit-miles**") |
| Constraint 1 | each cell's units are fully supplied: Σ over factories of `x` = cell units |
| Constraint 2 (optional) | factory capacity: Σ over cells of `x` ≤ capacity |
| Constraint 3 | a factory may only ship products it is eligible to make (no variable exists otherwise) |

A cell may be supplied by **more than one** factory (a split).

### 5.4 Worked example
Factories A, B; cells X (10 units), Y (20), Z (30); miles from A: 100, 400, 250; from B: 300, 200, 150.
* Existing (everything from A): 10×100 + 20×400 + 30×250 = **16,500** unit-miles.
* No capacity: X→A, Y→B, Z→B = 1,000 + 4,000 + 4,500 = **9,500** (−7,000, **−42.4%**).
* B capped at 40 units: B takes Y (20) and 20 of Z; 10 of Z stay at A: 1,000 + 4,000 + 3,000 + 2,500 = **10,500** (−36.4%). Z is split because moving Z's units costs only 100 miles per unit, whereas Y's would cost 200.
* Capacities A ≤ 20 and B ≤ 30 supply 50 of 60 demanded units: **infeasible**, short by 10.

These cases are automated tests (`tests/test_optimization.py`).

### 5.5 How GLOP finds the answer
OR-Tools' **GLOP** solver uses the *simplex method*. Every valid plan is a point in a many-sided shape; the best plan always sits at a corner. GLOP starts at one corner and hops to a neighbouring corner that lowers total unit-miles, repeating until no neighbour is cheaper; that corner is optimal.

### 5.6 Why whole-number demands give whole-number plans
This is a *transportation problem*: each shipment variable appears in exactly one "supply this cell" constraint and at most one "factory capacity" constraint. Such constraint matrices are *totally unimodular*, so when demands and capacities are whole numbers every corner of the shape is a whole-number plan, and the simplex method stops at a corner. Therefore no rounding is needed. The code requires whole-number capacities, rounds the automatic capacity **down**, and verifies the result (`AllocationResult.integral`; random-instance tests).

### 5.7 Capacity options (both hypothetical)
* **Automatic:** capacity = current units of the factory under the existing allocation × (1 + headroom %), rounded down. A factory with no current volume gets 0.
* **Manual:** a whole number per factory; empty = unlimited.

Without any limit, every cell simply goes to its nearest eligible factory: an **upper bound** on savings, not a plan.

### 5.8 Infeasible and invalid inputs
Before solving, the code checks and explains: a product with no eligible factory; a product whose capacity-limited eligible factories cannot cover its demand ("short by N units"); total capacity below total demand. If the solver itself reports infeasible (for example shared capacity across products), that is reported too. A distance matrix with missing values is refused, never treated as 0. Negative, fractional or unknown-factory capacities raise an error.

### 5.9 Existing vs proposed and the exports
The existing allocation is expressed in the same shape. The comparison reports unit-miles, reduction (absolute and %), average miles per unit, units per factory before and after, and the demand cells whose factory changes. **Estimated cost = the user's illustrative rate × unit-miles, calculated only when a rate is entered (empty by default), and shown separately from unit-miles and from the efficiency score.**

The **order-line export** keeps every original line. Each cell's factory quotas are filled over its order lines in Row ID order (factories alphabetical); a line that straddles two quotas appears on **two rows** with its own *Allocated Units* and *Line Split = True*, so a split line is never falsely given to a single factory. Which orders inside a cell take which factory is this bookkeeping rule, **not** an optimizer decision.

### 5.10 Results on this dataset [ran]
| Scenario | Unit-miles | vs existing 48,099,961 | Avg miles per unit |
|---|---|---|---|
| No capacity limits (upper bound) | 19,836,723 | −58.8% | 1,244 → 513 |
| Capacity = current volume + 0% | 27,394,134 | −43.0% | 1,244 → 709 |
| Capacity = current volume + 20% | 24,602,248 | −48.9% | 1,244 → 636 |

Without limits, Secret Factory's volume rises 7× and Sugar Shack's 10× (see [SUGAR_SHACK_INVESTIGATION.md](SUGAR_SHACK_INVESTIGATION.md)); that is why the unlimited figure is not a plan. Even with each factory's volume held at its current level the simulated distance falls 43%, because the existing mapping sends many products far from their customers.

### 5.11 Limitations
Straight-line distance to a state centroid (Canadian centroids are provisional); units as the only demand weight (no revenue weighting); no production cost, setup, minimum batch, product compatibility or service-level data; hypothetical capacities; the line-level assignment is arbitrary bookkeeping; results change if the product→factory map or the eligibility assumption changes.

## 6. Scenario simulation (HYPOTHETICAL)
Code: [modules/scenarios.py](../modules/scenarios.py). A **scenario** = a name + assumptions: *eligibility* (`all`: every factory can make every product; `current`: the dataset's mapping; `custom`: start from `all`, lock chosen products at their current factory, forbid chosen factories), *headroom %* (hypothetical capacity = current volume × (1 + headroom), rounded down; none = no limits), and an optional *cost rate*. Each scenario is solved with the section 5 model; the Existing row is the dataset's own allocation (calculated, not simulated).

*Example* (A/B/X/Y/Z of section 5.4): Existing 16,500; S1 no limits 9,500 (−42.4%); S2 B capped at 40: 10,500 (−36.4%). With an illustrative $0.01 per unit-mile the estimates are $165, $95 and $105. A scenario without a rate shows no cost.

Rules: locks are per **product**; a locked product whose factory is excluded has no eligible factory, so the scenario is reported **infeasible** with that reason; unsolved scenarios appear as blanks (never 0); cost columns exist only if at least one scenario has a rate and are blank for scenarios without one; solving never modifies the data.

## 7. Anomaly detection
Code: [modules/anomaly_detection.py](../modules/anomaly_detection.py). Simple statistics only; **flags never delete or change records**, and every flag carries a plain-language reason and supporting values.

**IQR rule (Tukey fences).** Sort the values; Q1 is 25% of the way up, Q3 is 75%; IQR = Q3 − Q1; fences are Q1 − 1.5·IQR and Q3 + 1.5·IQR. Example: 300, 800, 1,500, 2,200, 5,000 → Q1 800, Q3 2,200, IQR 1,400, upper fence 4,300 → 5,000 is flagged. "Unusual" does not mean "wrong".

| Detector | Rule | Result on this dataset [ran] |
|---|---|---|
| Route distance outliers | IQR on the average distance of the 196 factory→state/province routes; unknown distances are not assessed | 1 route: Lot's O' Nuts → Newfoundland and Labrador (2,979 mi; upper fence 2,720 mi) |
| Duplicate order lines | Same Order ID + Product ID. *Identical values* (sales, units, profit, cost, ship mode, dates) = likely exact duplicate; otherwise possibly a legitimate extra line | 3,018 lines: 396 identical, 2,622 different |
| Missing geography | Blank location field, unknown centroid, unmapped factory | 0 |
| Sales / profit | Per product (≥ 8 lines): IQR on unit price and on margin %; if most lines share one value, any different value is flagged; plus Gross Profit + Cost = Sales and negative profit checks | 0 flagged: every product has one constant price and margin (reported as an observation) |
| Factory-product distribution | Product ID prefix (CHO/SUG/OTH) vs Division; factories under 1% and products under 0.5% of order lines | 6 lines (Fizzy Lifting Drinks); 2 factories and 7 products flagged as very low volume |

Thresholds are constants at the top of the module.

## 8. Recommendations
Code: [modules/recommendations.py](../modules/recommendations.py). Each rule is **IF a measured value crosses a documented threshold THEN a prompt to investigate**, with *Why*, *Rule* (the exact threshold) and *Supporting Values*. No AI, no external service. *Basis*: Dataset (counted), Calculated (derived), Hypothetical (depends on simulation assumptions).

| Family | Rule (thresholds in the module) | Priority |
|---|---|---|
| Long-distance route | IQR outlier route (section 7); or a route contributing ≥ 5% of all unit-miles | Outlier: High if ≥ 100 orders, else Low; contributor: Medium |
| Alternative factory allocation (hypothetical) | Per product, ranked by unit-miles the scenario saves | High ≥ 2% of total unit-miles, Medium ≥ 0.5%, else Low |
| Factory capacity (hypothetical) | Unconstrained nearest-factory volume > hypothetical capacity | High if over by ≥ 100% (or capacity 0), else Medium |
| Geographic pattern | Factory ships ≥ 50% of its units farther than 1,500 mi | High ≥ 75%, else Medium |
| Data quality | Exact duplicates (High), repeated lines with different values (Medium), missing geography (High), provisional Canadian centroids (Medium), ID/division mismatch, low-volume factories, constant prices (Low) | as listed |

If the scenario is infeasible, a single explanatory recommendation replaces the reassignment suggestions.

## 9. Reports
Code: [modules/reporting.py](../modules/reporting.py) (content) and [utils/report_generator.py](../utils/report_generator.py) (files). One function computes everything, so PDF, Excel and CSV agree. Every output carries the generation time, the scenario assumptions and the scoring method.

* **PDF (ReportLab):** executive summary and KPIs, factory performance (with charts), route analysis, optimization comparison (hypothetical banner, factory volumes chart, top changed cells), recommendations, anomalies, data quality and limitations.
* **Excel (OpenPyXL):** sheets *Executive Summary, Route Analysis, Factory Performance, Shipping Modes, Optimization, Order Allocations, Anomalies, Recommendations, Data Quality*, with styled headers, numeric cells with number formats, frozen headers and wrapped reason columns.
* **CSV:** one file per table plus `report_info.csv` (timestamp, assumptions, label).
* **Costs:** cost columns and the "ESTIMATES, not actual costs" note appear only if a rate was entered.
* **Split allocations:** the order-line allocation lists a split line on several rows (section 5.9); an infeasible scenario produces an explanation, not an allocation.
* The lead-time column is excluded from the shipping-mode table (unreliable).

## Presenting this to a mentor
Lead with the data-quality finding: the date fields can't measure speed, so a proxy score was built from the two fields that *do* validate (distance, and the ship-mode mix). Then show the worked example, then the "what is an assumption?" table: weights and suitability are editable, and documented as assumptions.
