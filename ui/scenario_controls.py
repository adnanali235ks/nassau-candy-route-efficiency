"""Reusable Streamlit form that builds a hypothetical Scenario (used by Simulator, Recommendations, Reports)."""

import streamlit as st

import route_core as rc
from modules.scenarios import Scenario

ELIG_ALL = "Hypothetical: every factory can make every product"
ELIG_CURRENT = "Current mapping only (reproduces the existing plan)"
ELIG_CUSTOM = "Custom: lock products / exclude factories"


def scenario_form(prefix, default_name, defaults=None, container=None):
    """Draw the scenario inputs inside `container` and return the Scenario they describe.

    Every widget key starts with `prefix`, so several forms can live on one page.
    Cost rate is left empty by default; with no rate, no cost is calculated.
    """
    defaults = defaults or {}
    box = container if container is not None else st
    name = box.text_input("Scenario name", default_name, key=f"{prefix}_name").strip() or default_name
    elig = box.radio("Which factories may make each product?", [ELIG_ALL, ELIG_CURRENT, ELIG_CUSTOM],
                     key=f"{prefix}_elig", index=defaults.get("elig_index", 0))
    locked, excluded, mode = (), (), "all"
    if elig == ELIG_CURRENT:
        mode = "current"
    elif elig == ELIG_CUSTOM:
        mode = "custom"
        products = sorted(rc.PRODUCT_FACTORY_MAP)
        locked = tuple(box.multiselect("Lock these products at their current factory", products,
                                       key=f"{prefix}_locked"))
        excluded = tuple(box.multiselect("Factories that may not make any product", list(rc.FACTORIES),
                                         key=f"{prefix}_excl"))
        box.caption("A locked product whose current factory is excluded has no eligible factory (infeasible).")
    limit = box.checkbox("Apply hypothetical capacity limits (current volume + headroom)",
                         value=defaults.get("limit", False), key=f"{prefix}_limit")
    headroom = None
    if limit:
        headroom = float(box.slider("Headroom above current volume (%)", 0, 200, int(defaults.get("headroom", 20)),
                                    step=5, key=f"{prefix}_headroom"))
    rate = box.number_input("Illustrative cost per unit-mile ($), optional", min_value=0.0, value=None, step=0.001,
                            format="%.4f", key=f"{prefix}_rate",
                            help="Empty by default. A cost estimate appears only when you enter a rate; it is your "
                                 "assumption, not a dataset value.")
    return Scenario(name, mode, locked, excluded, headroom, rate)
