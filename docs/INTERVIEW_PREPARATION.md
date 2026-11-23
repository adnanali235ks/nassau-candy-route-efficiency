# Interview and presentation preparation

Everything here is checked against the project's code, tests and measured results. Numbers marked [ran] were produced by running the code. The three diagrams (architecture, data flow, optimization workflow) are in [PROJECT.md](PROJECT.md); the formulas and worked examples are in [METHODOLOGY.md](METHODOLOGY.md).

## 0. The project in one minute
> "Nassau Candy ships from five factories to customers across the US and Canada. I built a dashboard that measures how efficient each shipping route is, finds unusual data, and tests a what-if question: *if other factories could make a product, how much shorter would the shipping distances be?* The dataset's delivery dates turned out to be unusable, so instead of reporting fake lead times I scored routes from distance and ship-mode mix, and I labelled everything as *dataset*, *calculated* or *hypothetical*. The optimizer uses Google OR-Tools. It shows a distance reduction of up to 59%, but I present that as an upper bound from a simulation, not a recommendation."

**Five facts to know cold [ran]:** 10,194 order lines · 8,549 orders · 5,044 customers · 5 factories (via a product map) · 59 US states and Canadian provinces.

## 1. Presentation outline (13 topics)
Suggested length: 12 to 15 minutes plus questions. One short paragraph per topic is enough.

### 1. Problem statement
A distributor needs to know which shipping routes are efficient, where distance hurts, and whether a different factory assignment could shorten shipping, using only the data it has. The brief asked for lead-time and delay KPIs.

### 2. Project objectives
1. Understand and validate the data. 2. Score route efficiency honestly. 3. Show geography and bottlenecks. 4. Simulate alternative factory allocation. 5. Flag data problems and explain every flag. 6. Give explainable recommendations. 7. Export professional reports. 8. Keep it testable, local and easy to explain.

### 3. Dataset and limitations
18 columns, no nulls. **Ship Date does not track Order Date** (about 1,300 days for every mode, including Same Day), so no time metric is valid: I flagged this instead of using it. There is **no factory column, shipping cost, capacity or customer coordinate**. The product-to-factory map comes from the project brief. 96.6% of lines are chocolate, so two factories dominate. Every product has one constant price and margin.

### 4. System architecture
Three layers: **logic** (`route_core.py`, `modules/`: no Streamlit, fully testable), **UI helpers** (`ui/`) and **pages** (`views/`), with `app.py` as the navigation shell. Reports are built from one data dictionary so PDF, Excel and CSV agree. Diagram: [PROJECT.md](PROJECT.md) section 1.

### 5. Technology stack
| Technology | Used for | Why this and not something else |
|---|---|---|
| Python | everything | readable, strong data libraries |
| pandas / NumPy | cleaning, grouping, calculations | the standard tools for tabular data |
| Streamlit | the dashboard | pure-Python UI, no web-development stack; right size for an analytics tool |
| Plotly | charts and maps | interactive (hover, zoom), geographic maps built in |
| Google OR-Tools (GLOP) | the allocation optimizer | free, fast, well-documented linear-programming solver |
| OpenPyXL | Excel export | writes real numeric cells, formats and multiple sheets |
| ReportLab | PDF export | full control over layout; no browser needed |
| pytest (+ Streamlit AppTest) | 268 automated tests | AppTest runs the pages without a browser |
Deliberately **not** used: machine learning (nothing here needs it; rules are easier to explain), a database (no shared state needed), web frameworks, Docker, cloud services.

### 6. Data cleaning
Validate the file and columns (friendly error if wrong); coerce `Sales`/`Units` to numbers; drop invalid rows (duplicate Row ID, missing key fields, non-positive sales/units); trim text; parse day-month-year dates; map product to factory and state/province to a centroid; compute distance; **flag rather than delete** unknown locations and repeated lines. On this CSV nothing was removed [ran]. Full list: METHODOLOGY section 0.

### 7. Haversine distance
Distance along the Earth's surface between two latitude/longitude points: `a = sin²(Δφ/2) + cos φ₁ cos φ₂ sin²(Δλ/2)`, `d = 2R·atan2(√a, √(1−a))`, R = 3,958.8 miles. Factory coordinates to the **centroid** of the destination state/province. New York to Los Angeles is about 2,445 miles (a unit test). It is straight-line, not road distance, and centroid-to-factory, not the real address.

### 8. Route efficiency scoring
`Score = 70% × Distance Score + 30% × Ship-Mode Score`, each 0 to 100.
*Distance Score* = 100 × (1 − route distance ÷ longest route). *Ship-Mode Score* = order-share-weighted average of suitability (Same Day 1.0, First 0.85, Second 0.6, Standard 0.4) × 100. Example: 500 miles of a 2,000-mile maximum gives 75; a 50/50 Standard/First mix gives 62.5; the score is 0.7×75 + 0.3×62.5 = **71.25**. Weights and suitability are **assumptions** (editable); unknown distance gives an *unscored* route, never a zero.

### 9. GLOP optimization
Group demand into cells (state/province × product, weighted by Units). Variables: units each factory ships to each cell. Objective: minimise Σ distance × units ("unit-miles"). Constraints: every cell's demand is supplied; optional capacity per factory; a factory ships only products it is eligible to make. GLOP (simplex) moves between corner points of the feasible region, always improving, until none is better. With whole-number demands and capacities the optimum is whole-number (a *transportation problem*), so no rounding is needed. **Result [ran]:** existing 48,099,961 unit-miles; no limits 19,836,723 (−58.8%, an upper bound); capacity = current volume + 20%: 24,602,248 (−48.9%); +0%: 27,394,134 (−43.0%).

### 10. Scenario simulation
A scenario is a named set of assumptions (eligibility, capacity headroom, optional cost rate). The simulator runs the optimizer once per scenario and compares them with the **existing** allocation, which is calculated from the data, not simulated. Infeasible scenarios show their reason. Costs appear only if a rate is entered and are always labelled estimates.

### 11. Anomaly detection
Simple statistics, not ML. **IQR rule:** Q1 and Q3 are the 25th and 75th percentiles, IQR = Q3 − Q1; values outside Q1 − 1.5·IQR or Q3 + 1.5·IQR are unusual. Example: 300, 800, 1,500, 2,200, 5,000 → fence 4,300 → 5,000 is flagged. Also: duplicate lines, missing geography, price/profit checks, factory/product patterns. Findings [ran]: one outlier route (Lot's O' Nuts → Newfoundland and Labrador, 2,979 mi vs fence 2,720), 396 likely exact duplicates among 3,018 repeated lines. **Nothing is deleted.**

### 12. Recommendation generation
Rules of the form *IF a measured value crosses a documented threshold THEN show a prompt to investigate*, always with **Why**, **Rule** and **Supporting values**, and a Basis label (Dataset, Calculated, Hypothetical). 17 recommendations on the full data; hypothetical ones are marked and can be filtered out. No AI.

### 13. Results and limitations
Biggest lever: *which factory serves which region*. Without capacity limits the simulation would overload the small factories (Secret Factory 7×, Sugar Shack 10× their current volume), so the saving is an upper bound. Limitations: straight-line centroid distances, provisional Canadian centroids, assumed weights, hypothetical eligibility and capacity, heuristic thresholds. Future work is in PROJECT.md section 11.

## 2. Five-minute demo script
1. **Executive Overview**: read the KPI labels aloud (dataset / calculated / assumption); point at the data-quality banner.
2. **Geographic Analysis**: show the map and the "centroids, not customers" note.
3. **Route Performance**: open the score breakdown (distance points + ship-mode points).
4. **Optimization Center**: show the red *hypothetical* banner, the 58.8% number and immediately the volume chart (small factories overloaded). Switch capacity to *current volume + 20%*.
5. **Scenario Simulator**: compare no limits vs +20% vs +0%. Create an infeasible scenario (lock Nerds, exclude Sugar Shack) to show the explanation.
6. **Anomaly Detection** and **Smart Recommendations**: open one recommendation, read Why / Rule / Values.
7. **Reports**: press *Generate reports*, open the PDF and the Excel *Order Allocations* sheet, show a split line on several rows.

## 3. Viva questions and answers
### Project and design
**Why did you not report delivery times?**
Because the dates are not credible: lead time averages about 1,300 days for every ship mode, including Same Day. Reporting them would be reporting numbers I know are wrong. I documented the problem and built a proxy from fields that validate.

**What is a "proxy score" and is it reliable?**
It is a stand-in built from other measurable things (distance and ship-mode mix). It ranks routes by those factors only. It is reliable as a *relative comparison of distance and service tier*, not as a measure of delivery speed or cost.

**Why 70/30?**
It was a proposed split agreed for the project, not a validated fact. Distance is measured; the ship-mode part rests on assumed suitability values. That is why the weights are editable and labelled as assumptions.

**Why straight-line distance?**
Road distance needs a routing service and real addresses, which the data does not have. Straight-line is consistent and reproducible, and it is clearly labelled.

**Why centroids?**
The dataset has no customer coordinates, only state or province. The centroid is the best location-free choice. It hides differences inside a state.

**Why no machine learning?**
Nothing in the brief needs prediction. Rules and simple statistics are transparent, testable and easy to defend; ML would add complexity without a clear benefit.

**Why separate `modules/` from `views/`?**
So the calculations can be tested without a browser and reused by the PDF/Excel code. Streamlit code only draws.

**Is there a circular import?**
No, not today. `route_core.py` imports `modules/scoring.py`, which imports only `config.py`. A cycle would appear if `scoring.py` imported `route_core.py`; I documented this rather than restructuring.

### Data
**Why did you not delete duplicate lines?**
Repeated Order ID + Product ID may be legitimate extra lines. 396 of the 3,018 repeated lines are identical in every compared value (likely true duplicates), but only the data owner can say. I flagged them and report totals both ways.

**Why is "Factories = 5" labelled an assumption?**
There is no factory column; factories come from a product-to-factory map in the code, taken from the project brief.

**Why are Sugar Shack's sales so small?**
Demand, not an error: 96.6% of all lines are chocolate, and Sugar Shack's five products have only 33 lines in total. Per-line values (units, price) look normal. I investigated and documented it without changing the mapping.

**How do you treat missing locations?**
They get a missing distance, are flagged `Missing Geo`, are listed separately, are excluded from the optimizer, and are never treated as 0 miles.

**How did you handle Canada?**
The original code had no Canadian centroids, so 200 rows lost their distance and vanished under the default filter. I added the ten provinces. The values are **provisional** (no authoritative source was found), and a 100-mile error changes a score by at most 1.4 points.

### Haversine and scoring
**Why haversine and not Euclidean distance?**
Latitude/longitude are angles on a sphere. Euclidean distance on raw degrees is wrong (a degree of longitude shrinks toward the poles). Haversine gives the great-circle distance.

**How accurate is it?**
It treats the Earth as a sphere, typically within about 0.5% of true distance. Far smaller than the centroid approximation.

**Why do scores change when I add data?**
The Distance Score is relative to the longest route. When Newfoundland (2,979 miles) joined the data, the reference grew from 2,393 to 2,979 miles at state level, so other routes' scores rose. Like grading on a curve.

**What happens to a route with no distance?**
It is *unscored*: excluded from rankings and listed separately. Never zero, because zero would make it look like the worst or best route by accident.

### Optimization
**What is linear programming?**
Choosing numbers to minimise (or maximise) a straight-line formula subject to straight-line limits. Here: minimise total distance × units, subject to supplying all demand and respecting capacities.

**What are the decision variables, objective and constraints?**
Variables: units each factory ships to each state/product cell. Objective: minimise the sum of distance × units. Constraints: each cell's demand is met; factory shipments ≤ capacity (if set); only eligible factories ship a product; no negative shipments.

**How does GLOP find the answer?**
It uses the simplex method: it starts at one corner of the feasible region and keeps moving to a neighbouring corner with lower cost, stopping when none is lower. That corner is optimal.

**Why are the answers whole numbers?**
This is a transportation problem: each shipment variable appears in one supply constraint and at most one capacity constraint. Such problems have whole-number optimal corners when demands and capacities are whole numbers. The code also verifies it.

**Why a linear solver and not an integer one?**
Because the integer solution comes for free here, so the simpler, faster and easier-to-explain LP is enough.

**What happens without capacity limits?**
Every cell simply goes to its nearest eligible factory. That is an upper bound. It would send 7× more volume to Secret Factory and 10× more to Sugar Shack, which is unrealistic, so I always show it with that warning.

**How do you know the optimizer is correct?**
Tests: the hand-checked A/B/X/Y/Z example (16,500 → 9,500 → 10,500); on random problems the uncapacitated optimum equals "nearest factory"; capacity and eligibility are respected; "current mapping only" reproduces the existing 48,099,961 unit-miles exactly; demand is conserved.

**What does infeasible mean and how is it handled?**
No plan can meet all constraints, for example total capacity below total demand. The code checks first and states the reason ("short by 10 units"), then also handles the solver's own infeasible status. No partial plan is shown.

**Are the optimizer's results a recommendation?**
No. They assume any factory can make any product, which the data contradicts, and they ignore production cost and capacity unless entered. They show the size of an opportunity and what data would be needed to confirm it.

**How is a split order line represented?**
The optimizer decides per state/product cell. The export fills each factory's quota over the cell's order lines in Row ID order; a line that straddles two factories appears on two rows, each with its own units and *Line Split = True*. Which orders go where inside a cell is a bookkeeping rule, not an optimizer decision.

**Why are costs separate from the score and the distances?**
There is no real shipping cost in the data. An estimate (rate × unit-miles) is a scaled copy of distance, so putting it in the score would count distance twice. It appears only if the user types a rate and is always labelled an estimate.

### Anomalies and recommendations
**What is the IQR rule?**
Sort the values, take the 25th and 75th percentiles (Q1, Q3), IQR = Q3 − Q1. Values beyond Q1 − 1.5×IQR or Q3 + 1.5×IQR are unusual. It does not assume a bell-shaped distribution.

**Does a flag mean the data is wrong?**
No, only unusual. Each flag shows its reason and the underlying records, and nothing is changed.

**How do you generate recommendations without AI?**
Fixed rules with documented thresholds: IF a value crosses it THEN show a prompt with the reason, the rule and the numbers. This is why every recommendation can be explained.

### Engineering
**How did you test the project?**
268 automated tests: unit tests for the maths, property-style tests for the optimizer, integration tests on the real CSV, UI tests that run every page with Streamlit's AppTest (including empty and Canada-only filters), checks on the Excel/PDF/CSV contents, guards that the CSV hash and the product-to-factory map never change, and fresh-environment runs on Python 3.12 and 3.14.

**Did the tests find real bugs?**
Yes: a crash on empty input in the scoring step, a crash when comparing two identical plans, text-typed columns breaking arithmetic, and PDF markup printing as literal tags.

**Has the CI pipeline passed?**
It has **not** been run: the project has not been pushed to GitHub. The workflow file's syntax was checked, and the same suite passes locally in fresh environments.

**How did you make the app robust to a bad data file?**
The CSV path is resolved from the project folder; a missing, empty, unreadable or wrong-column file raises a `DataFileError` that the page turns into a plain explanation of the problem and the fix; tests cover each case.

**What would you do with more time or real data?**
Get a real factory × product eligibility table and capacities; add shipping cost data and road distances; verify the Canadian centroids; run the CI; investigate the duplicate lines with the data owner.

## 4. Statements to avoid
- "The optimizer shows we can cut distance by 59%." (It is a hypothetical upper bound.)
- "The route score measures delivery speed." (It measures distance and service-tier mix.)
- "Costs saved are $X." (Costs are illustrative estimates from a user-entered rate.)
- "The CI passes." (It has not been run.)
- "It works with older package versions." (Only the versions listed in the README were tested.)
- "The Canadian distances are exact." (Provisional centroids.)

## 5. Quick self-check before presenting
Can you, without notes: (1) state the data problem and what you did about it; (2) work the 71.25 score example; (3) work the A/B/X/Y/Z optimizer example (16,500 existing → 9,500 with no limits → 10,500 with B capped at 40; and the infeasible case where capacities 20 + 30 = 50 cannot meet 60 units of demand); (4) explain the IQR fence with 300, 800, 1,500, 2,200, 5,000; (5) name three limitations; (6) explain why 58.8% is an upper bound?
