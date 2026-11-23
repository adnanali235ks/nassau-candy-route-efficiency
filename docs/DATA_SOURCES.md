# Data sources and provenance

Labels used throughout this project: **Dataset observation** (read straight from the CSV), **Calculated metric** (derived by our code from observations), **Assumption / hypothetical** (not supported by the dataset).

## Original dataset
`Nassau_Candy_Distributor.csv`: 10,194 rows, 18 columns, no null values. It is never modified by any code in this repo (a test checks the file's modification time).
Dataset observations: 9,994 US rows and **200 Canadian rows** (`Country/Region = Canada`). 5,044 customers, 8,549 orders, 15 products.

## Reference data hard-coded in `route_core.py` (not in the CSV)
| Item | Origin | Status |
|---|---|---|
| `FACTORIES` coordinates | "project brief" (per the original code comment) | Assumption: unverified here |
| `PRODUCT_FACTORY_MAP` (each product has exactly one factory) | "project brief" | Assumption: the CSV has **no factory column** |
| `STATE_CENTROIDS` (US states + DC) | Inherited from the original code; values look like standard state centroids | Not independently verified in Phase 1 |
| `CANADA_PROVINCE_CENTROIDS` (10 provinces) | Added in Phase 1, see below | **Approximate** |

## Canadian province centroids: source record
- **What was done:** a web search for an authoritative per-province centroid table (Natural Resources Canada / Statistics Canada) found only information about the national "Centre of Canada" and an NRCan outline map, **not** a provincial coordinate table.
- **What was used instead:** approximate geographic-centre coordinates, rounded to 1 decimal degree (about 7 miles), entered by the developer from general knowledge. They are *not* copied from a cited dataset.
- **Consistency:** like the US values, these are area-centre points, not population-weighted. For provinces such as Ontario, Quebec and British Columbia, most customers live far from the area centre, so distances to those provinces are **rough**.
- **Todo before any operational use:** verify against NRCan or Statistics Canada boundary files.
- **Effect:** the 200 Canadian rows (about 2% of rows) now have a distance. The largest is Newfoundland and Labrador at about 2,979 miles.

### Verification attempt (Phase 2 review): result = PROVISIONAL
| Check | Outcome |
|---|---|
| NRCan / Statistics Canada per-province centroid table | **Not found.** StatCan's Geographic Attribute File publishes population-weighted "representative points", a different definition from an area centre. NRCan material found covers only the national centre. |
| Ontario | Matches the midpoint of Ontario's bounding box (about 50.0, -86.0, per a map-aggregator listing). A 2019 CBC story reports a calculated geographic centre north-north-west of Hornepayne, so the true centre differs from the value used. Not an official source. |
| Other nine provinces | **Unverified.** |
| Sensitivity | Moving Newfoundland and Labrador (the farthest province, which sets the score scale) by about 100 miles changes any route's score by at most 1.4 points (median 0.5) [ran]. Moving a province changes only routes that serve it. |

**Conclusion:** the coordinates are fit for a relative route comparison with a stated caveat. They are **not** fit for operational use. The dashboard labels them provisional (`CANADA_CENTROIDS_STATUS` in `route_core.py`).

## Orders, ship modes and shipments (Phase 2 review) [ran]
Every one of the 8,549 Order IDs has exactly one ship mode, one factory, one state/province and one customer. So counting distinct Order IDs per ship mode is unambiguous: the mode counts sum to 8,549. In this project, **"shipment" means a distinct Order ID**, an approximation: if the data ever contained one order split across factories, it would be several physical shipments. `tests/test_pipeline.py` fails if that assumption stops holding.

## Known limitations of the location data
- Distances are **straight-line (great-circle) miles** from the factory to the *state or province centroid*. They are not road distances, and not distances to the actual customer address.
- `Ship Date` is unreliable (lead times of about 1,300 days for every ship mode) and is not used for scoring.
- `Cost` and `Gross Profit` are product economics (Gross Profit + Cost = Sales on every row). They are **not** shipping costs.
