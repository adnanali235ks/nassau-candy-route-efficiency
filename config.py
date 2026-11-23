"""
Central, editable settings for the route-efficiency score.

Everything here is an ASSUMPTION chosen by the project owner, not something
measured from the dataset. Change a number here and the whole app (and the
tests that read these defaults) follows.
"""

# How much each component contributes to the final 0-100 Route Efficiency Score.
# Approved split: 70% distance, 30% ship-mode suitability. Weights are re-scaled to
# sum to 1 when used, so (7, 3) and (0.7, 0.3) mean the same thing.
DEFAULT_SCORE_WEIGHTS = {"distance": 0.70, "ship_mode": 0.30}

# Ship-mode "suitability": 1.0 = fastest service tier, lower = slower tier.
# ASSUMPTION: based on what each service level is *meant* to be. The dataset cannot
# confirm it, because Ship Date is unreliable (every mode shows ~1,300 days).
# The same values were used by the original 60/40 formula.
DEFAULT_SHIP_MODE_SUITABILITY = {
    "Same Day": 1.00,
    "First Class": 0.85,
    "Second Class": 0.60,
    "Standard Class": 0.40,
}

# Legacy weights, kept only so the old 60/40 result can be reproduced and compared.
LEGACY_SCORE_WEIGHTS = {"distance": 0.60, "ship_mode": 0.40}
