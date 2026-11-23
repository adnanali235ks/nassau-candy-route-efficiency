"""Integration tests: the real CSV through load_and_clean()."""
import pathlib
import pytest
from route_core import load_and_clean

CSV = pathlib.Path(__file__).resolve().parents[1] / "Nassau_Candy_Distributor.csv"


@pytest.fixture(scope="module")
def loaded():
    return load_and_clean(str(CSV))


def test_no_rows_lost(loaded):
    df, meta = loaded
    assert meta["rows_before"] == 10194 and meta["rows_after"] == 10194 and meta["rows_removed"] == 0


def test_canadian_rows_have_distance(loaded):
    df, meta = loaded
    canada = df[df["Country/Region"] == "Canada"]
    assert len(canada) == 200
    assert canada["Route Distance (mi)"].notna().all()
    assert meta["rows_missing_geo"] == 0 and meta["unmapped_locations"] == []


def test_distances_are_plausible(loaded):
    df, _ = loaded
    d = df["Route Distance (mi)"]
    assert d.min() >= 0 and d.max() < 4000    # continental North America scale


def test_repeated_order_product_rows_are_flagged_not_removed(loaded):
    df, meta = loaded
    assert meta["rows_repeated_order_product"] > 0
    assert df["Repeated Order-Product Line"].sum() == meta["rows_repeated_order_product"]
    assert len(df) == 10194


def test_each_order_has_one_ship_mode_factory_state_and_customer(loaded):
    # Assumption behind "shipments = distinct Order IDs" and the ship-mode pie chart.
    # If this fails, per-mode order counts would double count and need rethinking.
    df, _ = loaded
    for col in ["Ship Mode", "Factory", "State/Province", "Customer ID"]:
        assert df.groupby("Order ID")[col].nunique().max() == 1, col
    assert df.groupby("Ship Mode")["Order ID"].nunique().sum() == df["Order ID"].nunique()


def test_loading_does_not_modify_source_csv():
    before = CSV.stat().st_mtime_ns
    load_and_clean(str(CSV))
    assert CSV.stat().st_mtime_ns == before


def test_unknown_location_is_flagged_not_dropped_or_zeroed(tmp_path):
    # Copy two rows, rename one state to something unknown, and check explicit handling.
    import pandas as pd
    raw = pd.read_csv(CSV).head(2).copy()
    raw.loc[0, "State/Province"] = "Atlantis"
    p = tmp_path / "mini.csv"
    raw.to_csv(p, index=False)
    df, meta = load_and_clean(str(p))
    assert len(df) == 2
    assert meta["rows_missing_geo"] == 1 and meta["unmapped_locations"] == ["Atlantis"]
    assert pd.isna(df.loc[df["State/Province"] == "Atlantis", "Route Distance (mi)"]).all()
