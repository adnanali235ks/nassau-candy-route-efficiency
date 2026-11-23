"""Tests for geographic distance (haversine) and location lookup."""
import pytest
from route_core import haversine_miles, STATE_CENTROIDS, CANADA_PROVINCE_CENTROIDS, FACTORIES


def test_same_point_is_zero():
    assert haversine_miles(40.0, -75.0, 40.0, -75.0) == 0


def test_known_distance_new_york_to_los_angeles():
    # Great-circle NYC -> LA is about 2,445 miles.
    d = haversine_miles(40.7128, -74.0060, 34.0522, -118.2437)
    assert d == pytest.approx(2445, abs=15)


def test_distance_is_symmetric():
    a = haversine_miles(32.0, -81.0, 48.1, -96.2)
    b = haversine_miles(48.1, -96.2, 32.0, -81.0)
    assert a == pytest.approx(b)


def test_one_degree_latitude_is_about_69_miles():
    assert haversine_miles(10.0, 0.0, 11.0, 0.0) == pytest.approx(69.1, abs=0.3)


def test_all_ten_dataset_provinces_have_centroids():
    needed = {"Ontario", "Quebec", "Alberta", "British Columbia", "Manitoba",
              "Prince Edward Island", "New Brunswick", "Nova Scotia",
              "Newfoundland and Labrador", "Saskatchewan"}
    assert needed <= set(STATE_CENTROIDS)
    assert needed == set(CANADA_PROVINCE_CENTROIDS)


def test_centroids_are_valid_coordinates():
    all_points = dict(STATE_CENTROIDS)
    all_points.update(FACTORIES)
    for name, (lat, lon) in all_points.items():
        assert -90 <= lat <= 90 and -180 <= lon <= 180, name
    for name, (lat, lon) in CANADA_PROVINCE_CENTROIDS.items():
        assert 41 <= lat <= 84 and -141 <= lon <= -52, f"{name} is outside Canada's bounds"
