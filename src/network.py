from __future__ import annotations

import math
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

from .config import Settings


def _smoothed_rate(frame: pd.DataFrame, group_cols: list[str], outcome: str, prior_strength: float) -> pd.DataFrame:
    observed = frame.dropna(subset=[outcome]).copy()
    global_rate = float(observed[outcome].mean()) if len(observed) else 0.0
    grouped = observed.groupby(group_cols, observed=True)[outcome].agg(["sum", "count"]).reset_index()
    grouped[f"{outcome}_rate"] = (
        grouped["sum"] + prior_strength * global_rate
    ) / (grouped["count"] + prior_strength)
    return grouped[group_cols + [f"{outcome}_rate", "count"]]


def build_network(enriched: pd.DataFrame, panel: pd.DataFrame, settings: Settings) -> dict[str, pd.DataFrame]:
    categories = sorted(panel["category"].unique())
    regions = sorted(panel["region"].unique())
    stable = enriched.loc[
        enriched["purchase_week"].between(settings.stable_start, settings.stable_end)
        & enriched["category"].isin(categories)
        & enriched["customer_region"].isin(regions)
        & enriched["seller_state"].notna()
    ].copy()
    hubs = stable.groupby("seller_state").size().nlargest(settings.candidate_hubs).index.tolist()
    stable = stable[stable["seller_state"].isin(hubs)]

    dispatch = _smoothed_rate(stable, ["seller_state", "category"], "late_dispatch", 25.0)
    dispatch = dispatch.rename(columns={"late_dispatch_rate": "supplier_risk", "count": "supplier_risk_n"})
    delivery = _smoothed_rate(stable, ["seller_state", "category", "customer_region"], "late_delivery", 35.0)
    delivery = delivery.rename(columns={"late_delivery_rate": "late_probability", "count": "late_probability_n"})

    global_dispatch = float(stable["late_dispatch"].dropna().mean())
    global_delivery = float(stable["late_delivery"].dropna().mean())
    global_freight = float(stable["freight_value"].median())
    global_lead = float(stable["approval_to_carrier_days"].dropna().clip(lower=0).median())

    lead = (
        stable.dropna(subset=["approval_to_carrier_days"])
        .assign(approval_to_carrier_days=lambda x: x["approval_to_carrier_days"].clip(lower=0, upper=30))
        .groupby(["seller_state", "category"], observed=True)["approval_to_carrier_days"]
        .agg(lead_time_days="median", lead_time_n="count")
        .reset_index()
    )
    freight = (
        stable.groupby(["seller_state", "category", "customer_region"], observed=True)["freight_value"]
        .agg(shipping_cost="median", freight_n="count")
        .reset_index()
    )
    category_info = (
        stable.groupby("category", observed=True)
        .agg(median_price=("price", "median"), median_weight_kg=("weight_kg", "median"))
        .reset_index()
    )
    category_info["median_price"] = category_info["median_price"].fillna(stable["price"].median()).clip(lower=5.0)
    category_info["median_weight_kg"] = category_info["median_weight_kg"].fillna(1.0).clip(lower=0.10, upper=10.0)

    hub_category_volume = stable.groupby(["seller_state", "category"], observed=True).size().rename("units").reset_index()
    hub_category_volume["share"] = hub_category_volume["units"] / hub_category_volume.groupby("category")["units"].transform("sum")
    weekly_hub_category = (
        stable.groupby(["purchase_week", "seller_state", "category"], observed=True).size().rename("units").reset_index()
    )
    replenishment_p90 = (
        weekly_hub_category.groupby(["seller_state", "category"], observed=True)["units"]
        .quantile(0.90)
        .rename("weekly_units_p90")
        .reset_index()
    )

    weekly_weight = (
        stable.assign(shipped_weight=lambda x: x["weight_kg"].fillna(1.0))
        .groupby(["purchase_week", "seller_state"], observed=True)["shipped_weight"]
        .sum()
        .reset_index()
    )
    capacity = (
        weekly_weight.groupby("seller_state", observed=True)["shipped_weight"]
        .quantile(0.90)
        .mul(settings.capacity_multiplier)
        .clip(lower=50.0)
        .rename("weekly_capacity_kg")
        .reset_index()
        .rename(columns={"seller_state": "hub"})
    )

    demand_by_category = panel.groupby("category", observed=True)["demand"].mean().to_dict()
    category_lookup = category_info.set_index("category").to_dict("index")
    share_lookup = hub_category_volume.set_index(["seller_state", "category"])["share"].to_dict()
    replenishment_lookup = replenishment_p90.set_index(["seller_state", "category"])["weekly_units_p90"].to_dict()
    dispatch_lookup = dispatch.set_index(["seller_state", "category"])["supplier_risk"].to_dict()
    lead_lookup = lead.set_index(["seller_state", "category"])["lead_time_days"].to_dict()

    hub_category_rows = []
    for hub, category in product(hubs, categories):
        info = category_lookup[category]
        share = float(share_lookup.get((hub, category), 0.0))
        category_total_opening = max(1, math.ceil(demand_by_category[category] * len(regions) * settings.opening_weeks_cover))
        opening = int(round(category_total_opening * share))
        replenishment_cap = max(1, math.ceil(float(replenishment_lookup.get((hub, category), 1.0)) * settings.replenishment_multiplier))
        supplier_risk = float(dispatch_lookup.get((hub, category), global_dispatch))
        median_price = float(info["median_price"])
        hub_category_rows.append(
            {
                "hub": hub,
                "category": category,
                "opening_inventory": opening,
                "replenishment_capacity": replenishment_cap,
                "procurement_cost": median_price * settings.procurement_share_of_price,
                "holding_cost": median_price * settings.holding_rate_per_week,
                "shortage_cost": median_price * settings.shortage_value_multiplier + global_freight,
                "weight_kg": float(info["median_weight_kg"]),
                "supplier_risk": supplier_risk,
                "lead_time_days_proxy": float(lead_lookup.get((hub, category), global_lead)),
                "lead_time_weeks_scenario": settings.lead_time_weeks,
                "historical_supply_share": share,
            }
        )
    hub_category = pd.DataFrame(hub_category_rows)

    freight_lookup = freight.set_index(["seller_state", "category", "customer_region"])["shipping_cost"].to_dict()
    delivery_lookup = delivery.set_index(["seller_state", "category", "customer_region"])["late_probability"].to_dict()
    arc_rows = []
    for hub, category, region in product(hubs, categories, regions):
        arc_rows.append(
            {
                "hub": hub,
                "category": category,
                "region": region,
                "shipping_cost": float(freight_lookup.get((hub, category, region), global_freight)),
                "late_probability": float(delivery_lookup.get((hub, category, region), global_delivery)),
            }
        )
    arcs = pd.DataFrame(arc_rows)
    metadata = pd.DataFrame(
        [
            {"parameter": "candidate_hubs", "value": ", ".join(hubs), "source": "top seller states by selected-category volume"},
            {"parameter": "global_late_dispatch_rate", "value": global_dispatch, "source": "Olist observed"},
            {"parameter": "global_late_delivery_rate", "value": global_delivery, "source": "Olist observed"},
            {"parameter": "global_median_freight", "value": global_freight, "source": "Olist observed"},
            {"parameter": "lead_time_weeks", "value": settings.lead_time_weeks, "source": "planning scenario"},
            {"parameter": "opening_weeks_cover", "value": settings.opening_weeks_cover, "source": "planning scenario"},
        ]
    )
    return {"hub_category": hub_category, "arcs": arcs, "capacity": capacity, "metadata": metadata}


def save_network(network: dict[str, pd.DataFrame], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in network.items():
        frame.to_csv(output_dir / f"{name}.csv", index=False)

