"""
Route Efficiency Score: transparent, configurable, no hidden steps.

    Final score (0-100) = w_distance  * Distance Score
                        + w_ship_mode * Ship-Mode Score

Both components are on a 0-100 scale, so the weights directly say how many of the
100 points each one can contribute. The score contains NO cost term: any cost
estimate lives elsewhere (later phases) and never feeds into this score.

Missing data rules (explicit, never silently zero):
  * Unknown distance          -> Distance Score = NaN -> final score = NaN (route is "unscored").
  * Unknown ship mode in mix   -> that mode is ignored and the other shares are re-scaled to 100%.
  * No known ship mode at all  -> Ship-Mode Score = NaN -> final score = NaN.
"""

import numpy as np
import pandas as pd

from config import DEFAULT_SCORE_WEIGHTS, DEFAULT_SHIP_MODE_SUITABILITY


def normalize_weights(weights=None):
    """Return {'distance': w1, 'ship_mode': w2} re-scaled so they add up to 1.

    Example: {"distance": 7, "ship_mode": 3} -> {"distance": 0.7, "ship_mode": 0.3}.
    """
    weights = dict(DEFAULT_SCORE_WEIGHTS if weights is None else weights)
    missing = {"distance", "ship_mode"} - set(weights)
    if missing:
        raise ValueError(f"weights must contain 'distance' and 'ship_mode' (missing: {sorted(missing)})")
    w_dist, w_mode = float(weights["distance"]), float(weights["ship_mode"])
    if w_dist < 0 or w_mode < 0:
        raise ValueError("weights must not be negative")
    total = w_dist + w_mode
    if total == 0:
        raise ValueError("at least one weight must be greater than zero")
    return {"distance": w_dist / total, "ship_mode": w_mode / total}


def distance_score(avg_distance, reference_max_distance=None):
    """Normalise distance to 0-100, where shorter = better.

        score = 100 * (1 - distance / reference_max_distance)

    The longest route (the reference) scores 0; a zero-mile route scores 100.
    `reference_max_distance` defaults to the largest distance in `avg_distance`.
    Pass a fixed value to keep scores stable when filters change the visible routes.
    NaN distances stay NaN (unscored). Distances above the reference are clipped to 0.
    """
    distances = pd.Series(avg_distance, dtype="float64")
    if reference_max_distance is None:
        reference_max_distance = distances.max()          # NaN-aware: skips missing values
    if pd.isna(reference_max_distance) or reference_max_distance <= 0:
        return pd.Series(np.nan, index=distances.index)   # nothing to compare against
    return (100 * (1 - distances / reference_max_distance)).clip(lower=0, upper=100)


def ship_mode_score(mode_mix, suitability=None):
    """Score one route's ship-mode mix, 0-100 (higher = faster service tiers dominate).

    `mode_mix` is {mode: share of the route's orders}, e.g. {"Standard Class": .5, "First Class": .5}.
    Modes missing from the suitability table are ignored and the rest re-scaled.
    Returns (score, share_of_mix_that_was_recognised). Score is NaN when nothing is recognised.
    """
    suitability = DEFAULT_SHIP_MODE_SUITABILITY if suitability is None else suitability
    known = {mode: share for mode, share in mode_mix.items() if mode in suitability}
    known_share = sum(known.values())
    if known_share <= 0:
        return np.nan, 0.0
    weighted = sum(suitability[mode] * share for mode, share in known.items()) / known_share
    return 100 * weighted, known_share


def combine_scores(distance_scores, ship_mode_scores, weights=None):
    """Weighted sum of the two components. Returns (final, distance_points, ship_mode_points).

    A route missing EITHER component gets NaN: we do not fill the gap with 0 or
    re-weight the other component, because that would make scored and unscored
    routes incomparable.
    """
    w = normalize_weights(weights)
    distance_points = w["distance"] * pd.Series(distance_scores, dtype="float64")
    ship_mode_points = w["ship_mode"] * pd.Series(ship_mode_scores, dtype="float64")
    final = distance_points + ship_mode_points            # NaN + anything = NaN
    return final, distance_points, ship_mode_points


def score_routes(routes, weights=None, suitability=None, reference_max_distance=None):
    """Add score columns to a route table.

    Required columns of `routes`: "Avg Distance (mi)" and "Ship Mode Mix" (dict per row).
    Adds: Distance Score, Speed Weight (0-1), Ship-Mode Score, Distance Points,
          Ship-Mode Points and "Route Efficiency Proxy Score" (the final 0-100 score).
    The final column keeps its historical name so existing code and exports still work.
    """
    out = routes.copy()
    out["Distance Score"] = distance_score(out["Avg Distance (mi)"], reference_max_distance)
    mode_results = out["Ship Mode Mix"].apply(lambda mix: ship_mode_score(mix, suitability))
    # astype(float): on an EMPTY table apply() returns a text-typed column that cannot be divided or added.
    out["Ship-Mode Score"] = mode_results.apply(lambda result: result[0]).astype("float64")
    out["Speed Weight"] = out["Ship-Mode Score"] / 100          # legacy 0-1 column
    final, dist_pts, mode_pts = combine_scores(out["Distance Score"], out["Ship-Mode Score"], weights)
    out["Distance Points"] = dist_pts
    out["Ship-Mode Points"] = mode_pts
    out["Route Efficiency Proxy Score"] = final.round(1)
    return out
