from __future__ import annotations

import math

import pandas as pd

from .config import Settings
from .optimization import solve_actual_fulfillment, solve_inventory_plan


def _opening_inventory(network: dict[str, pd.DataFrame]) -> dict[tuple[str, str], float]:
    frame = network["hub_category"]
    return {
        (row.hub, row.category): float(row.opening_inventory)
        for row in frame.itertuples(index=False)
    }


def _procurement_cost(order_quantities: dict[tuple[str, str], float], network: dict[str, pd.DataFrame]) -> float:
    costs = network["hub_category"].set_index(["hub", "category"])["procurement_cost"].to_dict()
    return float(sum(quantity * float(costs[key]) for key, quantity in order_quantities.items()))


def _holding_cost(inventory: dict[tuple[str, str], float], network: dict[str, pd.DataFrame]) -> float:
    costs = network["hub_category"].set_index(["hub", "category"])["holding_cost"].to_dict()
    return float(sum(quantity * float(costs[key]) for key, quantity in inventory.items()))


def _risk_exposure(flows: pd.DataFrame, network: dict[str, pd.DataFrame]) -> tuple[float, float]:
    if flows.empty:
        return 0.0, 0.0
    arcs = network["arcs"][["hub", "category", "region", "late_probability"]]
    supplier = network["hub_category"][["hub", "category", "supplier_risk"]]
    merged = flows.merge(arcs, on=["hub", "category", "region"], how="left").merge(
        supplier, on=["hub", "category"], how="left"
    )
    late_units = float((merged["quantity"] * merged["late_probability"]).sum())
    supplier_risk_units = float((merged["quantity"] * merged["supplier_risk"]).sum())
    return late_units, supplier_risk_units


def run_policy_backtest(
    policy: str,
    panel: pd.DataFrame,
    forecasts: pd.DataFrame,
    network: dict[str, pd.DataFrame],
    settings: Settings,
    scenario: str = "base",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    evaluation_weeks = sorted(pd.to_datetime(panel["week"].unique()))[-settings.backtest_weeks :]
    inventory = _opening_inventory(network)
    pipeline: dict[tuple[pd.Timestamp, str, str], float] = {}
    weekly_rows = []
    flow_frames = []

    for week in evaluation_weeks:
        week = pd.Timestamp(week)
        arrivals = [key for key in pipeline if key[0] == week]
        for key in arrivals:
            _, hub, category = key
            inventory[(hub, category)] = inventory.get((hub, category), 0.0) + pipeline.pop(key)

        forecast = forecasts[(forecasts["origin"] == week) & (forecasts["method"] == policy)].copy()
        if forecast.empty:
            raise RuntimeError(f"No {policy} forecast found for {week.date()}")
        forecast["planning_demand"] = (
            forecast["forecast"] + settings.safety_z * forecast["error_scale"]
        ).clip(lower=0).map(math.ceil)

        plan = solve_inventory_plan(forecast, network, inventory, pipeline, settings)
        orders = plan.values["first_week_replenishment"]
        arrival_week = week + pd.Timedelta(weeks=settings.lead_time_weeks)
        for (hub, category), quantity in orders.items():
            if quantity > 0:
                pipeline[(arrival_week, hub, category)] = pipeline.get((arrival_week, hub, category), 0.0) + quantity

        actual = panel[pd.to_datetime(panel["week"]) == week][["category", "region", "demand"]].copy()
        fulfillment = solve_actual_fulfillment(actual, network, inventory, settings)
        inventory = fulfillment.values["remaining_inventory"]
        procurement_cost = _procurement_cost(orders, network)
        holding_cost = _holding_cost(inventory, network)
        late_exposure, supplier_exposure = _risk_exposure(fulfillment.values["flows"], network)
        realized_total_cost = (
            procurement_cost
            + holding_cost
            + fulfillment.values["shipping_cost"]
            + fulfillment.values["risk_cost"]
            + fulfillment.values["shortage_cost"]
            + fulfillment.values["service_gap_cost"]
        )
        weekly_rows.append(
            {
                "scenario": scenario,
                "policy": policy,
                "week": week,
                "planning_status": plan.status,
                "fulfillment_status": fulfillment.status,
                "planned_objective": plan.objective,
                "demand_units": fulfillment.values["total_demand"],
                "fulfilled_units": fulfillment.values["fulfilled_units"],
                "shortage_units": fulfillment.values["shortage_units"],
                "fill_rate": fulfillment.values["fill_rate"],
                "ordered_units": float(sum(orders.values())),
                "ending_inventory": float(sum(inventory.values())),
                "procurement_cost": procurement_cost,
                "shipping_cost": fulfillment.values["shipping_cost"],
                "risk_cost": fulfillment.values["risk_cost"],
                "holding_cost": holding_cost,
                "shortage_cost": fulfillment.values["shortage_cost"],
                "service_gap_cost": fulfillment.values["service_gap_cost"],
                "total_cost": realized_total_cost,
                "expected_late_units": late_exposure,
                "supplier_risk_units": supplier_exposure,
            }
        )
        if not fulfillment.values["flows"].empty:
            flow = fulfillment.values["flows"].copy()
            flow.insert(0, "week", week)
            flow.insert(0, "policy", policy)
            flow.insert(0, "scenario", scenario)
            flow_frames.append(flow)

    weekly = pd.DataFrame(weekly_rows)
    flows = pd.concat(flow_frames, ignore_index=True) if flow_frames else pd.DataFrame()
    return weekly, flows


def summarize_policies(weekly: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (scenario, policy), group in weekly.groupby(["scenario", "policy"], observed=True):
        demand = group["demand_units"].sum()
        fulfilled = group["fulfilled_units"].sum()
        rows.append(
            {
                "scenario": scenario,
                "policy": policy,
                "weeks": int(len(group)),
                "demand_units": float(demand),
                "fulfilled_units": float(fulfilled),
                "fill_rate": float(fulfilled / demand) if demand else 1.0,
                "shortage_units": float(group["shortage_units"].sum()),
                "ordered_units": float(group["ordered_units"].sum()),
                "ending_inventory": float(group.iloc[-1]["ending_inventory"]),
                "procurement_cost": float(group["procurement_cost"].sum()),
                "shipping_cost": float(group["shipping_cost"].sum()),
                "risk_cost": float(group["risk_cost"].sum()),
                "holding_cost": float(group["holding_cost"].sum()),
                "shortage_cost": float(group["shortage_cost"].sum()),
                "service_gap_cost": float(group["service_gap_cost"].sum()),
                "total_cost": float(group["total_cost"].sum()),
                "expected_late_units": float(group["expected_late_units"].sum()),
                "supplier_risk_units": float(group["supplier_risk_units"].sum()),
            }
        )
    return pd.DataFrame(rows).sort_values(["scenario", "total_cost"])

