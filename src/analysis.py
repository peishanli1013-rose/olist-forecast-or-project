from __future__ import annotations

import numpy as np
import pandas as pd

from .config import Settings


def demand_segment_summary(panel: pd.DataFrame) -> pd.DataFrame:
    """Describe demand concentration, sparsity, volatility, and trend for each series."""
    rows = []
    for (category, region), group in panel.groupby(["category", "region"], observed=True):
        group = group.sort_values("week")
        demand = group["demand"].astype(float).to_numpy()
        mean = float(demand.mean())
        slope = float(np.polyfit(np.arange(len(demand)), demand, 1)[0]) if len(demand) > 1 else 0.0
        rows.append(
            {
                "category": category,
                "region": region,
                "weeks": int(len(demand)),
                "total_demand": float(demand.sum()),
                "mean_weekly_demand": mean,
                "std_weekly_demand": float(demand.std(ddof=1)),
                "coefficient_of_variation": float(demand.std(ddof=1) / mean) if mean else np.nan,
                "zero_week_share": float((demand == 0).mean()),
                "maximum_weekly_demand": float(demand.max()),
                "weekly_trend_slope": slope,
            }
        )
    result = pd.DataFrame(rows)
    result["demand_share"] = result["total_demand"] / result["total_demand"].sum()
    return result.sort_values(["total_demand", "category", "region"], ascending=[False, True, True])


def forecast_segment_metrics(forecasts: pd.DataFrame) -> pd.DataFrame:
    """Report one-step performance for every category-region segment and method."""
    valid = forecasts[(forecasts["horizon"] == 1) & forecasts["actual"].notna()].copy()
    valid["absolute_error"] = (valid["actual"] - valid["forecast"]).abs()
    valid["signed_error"] = valid["forecast"] - valid["actual"]
    rows = []
    for (category, region, method), group in valid.groupby(
        ["category", "region", "method"], observed=True
    ):
        denominator = float(group["actual"].abs().sum())
        rows.append(
            {
                "category": category,
                "region": region,
                "method": method,
                "observations": int(len(group)),
                "actual_units": float(group["actual"].sum()),
                "MAE": float(group["absolute_error"].mean()),
                "WAPE": float(group["absolute_error"].sum() / denominator) if denominator else np.nan,
                "bias": float(group["signed_error"].mean()),
            }
        )
    result = pd.DataFrame(rows)
    result["wape_rank"] = result.groupby(["category", "region"])["WAPE"].rank(method="min")
    result["is_best_wape"] = result["wape_rank"].eq(1.0)
    return result.sort_values(["category", "region", "wape_rank", "method"])


def fulfillment_risk_ranking(
    enriched: pd.DataFrame,
    panel: pd.DataFrame,
    network: dict[str, pd.DataFrame],
    settings: Settings,
) -> pd.DataFrame:
    """Create an auditable route-risk table with raw and smoothed historical evidence."""
    categories = set(panel["category"].unique())
    regions = set(panel["region"].unique())
    hubs = set(network["hub_category"]["hub"].unique())
    stable = enriched.loc[
        enriched["purchase_week"].between(settings.stable_start, settings.stable_end)
        & enriched["category"].isin(categories)
        & enriched["customer_region"].isin(regions)
        & enriched["seller_state"].isin(hubs)
    ].copy()
    observed = (
        stable.groupby(["seller_state", "category", "customer_region"], observed=True)
        .agg(
            sample_size=("order_id", "size"),
            raw_late_dispatch_rate=("late_dispatch", "mean"),
            raw_late_delivery_rate=("late_delivery", "mean"),
            median_freight=("freight_value", "median"),
            median_approval_to_carrier_days=("approval_to_carrier_days", "median"),
        )
        .reset_index()
        .rename(
            columns={
                "seller_state": "hub",
                "customer_region": "region",
            }
        )
    )
    arcs = network["arcs"][["hub", "category", "region", "shipping_cost", "late_probability"]]
    supplier = network["hub_category"][["hub", "category", "supplier_risk"]]
    result = observed.merge(arcs, on=["hub", "category", "region"], how="left").merge(
        supplier, on=["hub", "category"], how="left"
    )
    result["expected_risk_cost_per_unit"] = (
        settings.late_penalty_per_expected_unit * result["late_probability"]
        + settings.supplier_risk_penalty_per_expected_unit * result["supplier_risk"]
    )
    result["risk_adjusted_route_cost"] = result["shipping_cost"] + result["expected_risk_cost_per_unit"]
    result["evidence_level"] = pd.cut(
        result["sample_size"],
        bins=[-np.inf, 9, 29, np.inf],
        labels=["low", "medium", "high"],
    ).astype(str)
    return result.sort_values(
        ["expected_risk_cost_per_unit", "sample_size"], ascending=[False, False]
    ).reset_index(drop=True)

