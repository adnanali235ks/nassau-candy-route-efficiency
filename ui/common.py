"""
Shared dashboard pieces: styling, cached data, sidebar filters, scoring settings.

Every page calls `load_page_data()` first. Widgets use fixed `key`s, so a filter
chosen on one page is still selected when the user opens another page.
"""

import pandas as pd
import streamlit as st

from config import DEFAULT_SCORE_WEIGHTS, DEFAULT_SHIP_MODE_SUITABILITY
from route_core import DataFileError, load_and_clean, route_summary, CANADA_CENTROIDS_STATUS

PRIMARY, ACCENT, GOOD, RISK, NEUTRAL = "#5B2C6F", "#E67E22", "#2E8B57", "#C0392B", "#7f8c8d"

# Labels used on every page so viewers can tell where a number comes from.
DATASET, CALCULATED, ASSUMPTION = "Dataset observation", "Calculated metric", "Assumption"

_CSS = f"""
<style>
.metric-card {{ background:#faf7fc; border:1px solid #e8dff0; border-radius:10px; padding:14px 18px; text-align:center; height:150px; box-sizing:border-box; display:flex; flex-direction:column; justify-content:center; overflow:hidden;}}
.metric-card h3 {{ margin:0; font-size:13px; color:{NEUTRAL}; font-weight:600; text-transform:uppercase; letter-spacing:.03em;}}
.metric-card p {{ margin:4px 0 0 0; font-size:26px; font-weight:700; color:{PRIMARY};}}
.metric-card small {{ color:{NEUTRAL}; font-size:11px; }}
.block-title {{ font-size:22px; font-weight:700; color:{PRIMARY}; margin-bottom:0px;}}
@media (prefers-color-scheme: dark) {{ .metric-card {{ background:#2a2233; border-color:#4a3b57; }} .metric-card p {{ color:#d9b8ee; }} .block-title {{ color:#d9b8ee; }} }}
</style>
"""


def apply_style():
    st.markdown(_CSS, unsafe_allow_html=True)


@st.cache_data
def _load_cached():
    return load_and_clean()


def get_data():
    """Cached cleaned data. A missing or malformed CSV shows a friendly explanation instead of a traceback."""
    try:
        return _load_cached()
    except DataFileError as exc:
        st.error("### Data file problem")
        st.markdown(f"```\n{exc}\n```")
        st.stop()


@st.cache_data
def get_reference_distances():
    """Longest average route distance in the WHOLE dataset, per route level.

    Used as the "distance that scores 0", so filters never change a route's score.
    """
    df, _ = get_data()
    return {level: float(route_summary(df, level, include_unscored=True)["Avg Distance (mi)"].max())
            for level in ("Region", "State/Province")}


_NO_THOUSANDS = {"Row ID", "Customer ID", "Postal Code"}      # identifiers: never show 1,234


def show_table(df, max_height=640, **kwargs):
    """Show a DataFrame with a height that fits its rows (up to max_height) and thousands separators.

    st.dataframe's default frame shows only about 10 rows and scrolls inside, which made "full" tables look cut off.
    Whole-number columns are displayed as 21,412; decimals are left as they are; identifier columns are untouched.
    """
    df = df.reset_index(drop=True)
    config = {}
    for col in df.columns:
        values = df[col]
        if col in _NO_THOUSANDS or not pd.api.types.is_numeric_dtype(values) or pd.api.types.is_bool_dtype(values):
            continue
        present = values.dropna()
        if len(present) and (present == present.round()).all():
            config[col] = st.column_config.NumberColumn(format="localized")
    height = int(min(40 + 35 * max(len(df), 1), max_height))
    st.dataframe(df, column_config=config or None, height=height, width="stretch", hide_index=True, **kwargs)


def metric_card(column, label, value, note=""):
    note_html = f"<small>{note}</small>" if note else ""
    column.markdown(f'<div class="metric-card"><h3>{label}</h3><p>{value}</p>{note_html}</div>',
                    unsafe_allow_html=True)


def data_quality_banner():
    st.warning(
        "⚠️ **Data quality finding:** `Ship Date` does not track `Order Date` like a real shipment record "
        "(lead time averages ~1,300 days for every ship mode, including Same Day), so **no delivery-time or "
        "delay metric is reported**. Routes are scored from distance and ship-mode mix only. "
        "Distances are straight-line miles to the state/province **centroid**, not road distance."
    )


def provisional_note():
    if CANADA_CENTROIDS_STATUS == "PROVISIONAL":
        st.caption("Canadian province centroids are **provisional** (unverified); see docs/DATA_SOURCES.md.")


def score_settings():
    """Sidebar controls for the score weights and ship-mode suitability (all assumptions)."""
    with st.sidebar.expander("Scoring settings (assumptions)"):
        st.caption("Score = distance weight × Distance Score + ship-mode weight × Ship-Mode Score. "
                   "Defaults are proposed values, not validated business facts.")
        w_dist = st.slider("Distance weight %", 0, 100, int(DEFAULT_SCORE_WEIGHTS["distance"] * 100),
                           step=5, key="w_distance")
        st.caption(f"Ship-mode weight: {100 - w_dist}%")
        suitability = {}
        for mode, default in DEFAULT_SHIP_MODE_SUITABILITY.items():
            suitability[mode] = st.slider(f"{mode} suitability", 0.0, 1.0, float(default), step=0.05,
                                          key=f"suit_{mode}")
    weights = {"distance": w_dist / 100, "ship_mode": (100 - w_dist) / 100}
    return weights, suitability


def load_page_data():
    """Render the sidebar, apply filters, and return everything a page needs.

    Returns a dict: df (all rows), fdf (filtered rows), meta, weights, suitability.
    Stops the page with a message if the filters match nothing.
    """
    apply_style()
    df, meta = get_data()

    st.sidebar.caption("Filters apply to every page")
    min_date, max_date = df["Order Date"].min(), df["Order Date"].max()
    date_range = st.sidebar.date_input("Order date range", value=(min_date, max_date),
                                       min_value=min_date, max_value=max_date, key="f_dates")
    countries = st.sidebar.multiselect("Country", sorted(df["Country/Region"].unique()),
                                       default=sorted(df["Country/Region"].unique()), key="f_country")
    regions = st.sidebar.multiselect("Region", sorted(df["Region"].unique()),
                                     default=sorted(df["Region"].unique()), key="f_region")
    states = st.sidebar.multiselect("State/Province (optional)", sorted(df["State/Province"].unique()),
                                    key="f_states")
    ship_modes = st.sidebar.multiselect("Ship Mode", sorted(df["Ship Mode"].unique()),
                                        default=sorted(df["Ship Mode"].unique()), key="f_modes")
    dist_threshold = st.sidebar.slider("Minimum route distance (mi)", 0, 3000, 0, step=50, key="f_dist")
    weights, suitability = score_settings()

    # A NaN distance compares False against any number, so rows with unknown
    # distance are kept only while the minimum-distance slider is at 0.
    dist_ok = df["Route Distance (mi)"] >= dist_threshold
    if dist_threshold == 0:
        dist_ok |= df["Route Distance (mi)"].isna()
    mask = (df["Country/Region"].isin(countries) & df["Region"].isin(regions)
            & df["Ship Mode"].isin(ship_modes) & dist_ok)
    if states:
        mask &= df["State/Province"].isin(states)
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        mask &= (df["Order Date"] >= start) & (df["Order Date"] <= end)
    fdf = df[mask]

    st.sidebar.markdown("---")
    st.sidebar.caption(f"Rows loaded: **{meta['rows_after']:,}** · matching filters: **{len(fdf):,}**")
    if meta["rows_missing_geo"]:
        st.sidebar.warning(f"{meta['rows_missing_geo']:,} rows have unknown location: "
                           f"{', '.join(meta['unmapped_locations'])}")
    if fdf.empty:
        st.warning("No shipments match the current filters.")
        st.stop()
    return {"df": df, "fdf": fdf, "meta": meta, "weights": weights, "suitability": suitability}


def scored_routes(fdf, level, weights, suitability, include_unscored=False):
    """Route table for the filtered rows, scored against the fixed full-dataset reference."""
    return route_summary(fdf, level, include_unscored=include_unscored, weights=weights,
                         suitability=suitability,
                         reference_max_distance=get_reference_distances()[level])
