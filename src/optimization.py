from __future__ import annotations

from dataclasses import dataclass
import time

import pandas as pd
import pulp

from .config import Settings


@dataclass
class SolveResult:
    status: str
    objective: float
    values: dict


def _solver(settings: Settings):
    return pulp.PULP_CBC_CMD(
        msg=False,
        timeLimit=settings.solver_time_limit_seconds,
        gapRel=settings.solver_relative_gap,
    )


def _network_dicts(network: dict[str, pd.DataFrame], settings: Settings):
    hc = network["hub_category"]
    arcs = network["arcs"]
    capacity = network["capacity"]
    hubs = sorted(hc["hub"].unique())
    categories = sorted(hc["category"].unique())
    regions = sorted(arcs["region"].unique())
    hc_idx = hc.set_index(["hub", "category"])
    arc_idx = arcs.set_index(["hub", "category", "region"])
    capacity_dict = capacity.set_index("hub")["weekly_capacity_kg"].to_dict()
    shortage_cost = hc.groupby("category")["shortage_cost"].mean().to_dict()
    return hubs, categories, regions, hc_idx, arc_idx, capacity_dict, shortage_cost


def solve_inventory_plan(
    forecast: pd.DataFrame,
    network: dict[str, pd.DataFrame],
    current_inventory: dict[tuple[str, str], float],
    known_pipeline: dict[tuple[pd.Timestamp, str, str], float],
    settings: Settings,
) -> SolveResult:
    hubs, categories, regions, hc, arcs, capacity, shortage_cost = _network_dicts(network, settings)
    weeks = sorted(pd.to_datetime(forecast["target_week"].unique()))
    time_ids = list(range(len(weeks)))
    demand = forecast.set_index(["target_week", "category", "region"])["planning_demand"].to_dict()
    quantity_type = pulp.LpInteger if settings.integer_quantities else pulp.LpContinuous

    model = pulp.LpProblem("rolling_inventory_plan", pulp.LpMinimize)
    q = pulp.LpVariable.dicts("replenish", (hubs, categories, time_ids), lowBound=0, cat=quantity_type)
    x = pulp.LpVariable.dicts("plan_flow", (hubs, categories, regions, time_ids), lowBound=0, cat=quantity_type)
    inventory = pulp.LpVariable.dicts("inventory", (hubs, categories, time_ids), lowBound=0, cat=quantity_type)
    shortage = pulp.LpVariable.dicts("shortage", (categories, regions, time_ids), lowBound=0, cat=quantity_type)
    service_gap = pulp.LpVariable.dicts("service_gap", (regions, time_ids), lowBound=0, cat=pulp.LpContinuous)

    procurement_terms = []
    fulfillment_terms = []
    holding_terms = []
    shortage_terms = []
    service_terms = []
    for hub in hubs:
        for category in categories:
            for t in time_ids:
                procurement_terms.append(float(hc.loc[(hub, category), "procurement_cost"]) * q[hub][category][t])
                holding_terms.append(float(hc.loc[(hub, category), "holding_cost"]) * inventory[hub][category][t])
                model += q[hub][category][t] <= float(hc.loc[(hub, category), "replenishment_capacity"])
                previous = current_inventory.get((hub, category), 0.0) if t == 0 else inventory[hub][category][t - 1]
                pipeline_arrival = float(known_pipeline.get((pd.Timestamp(weeks[t]), hub, category), 0.0))
                decision_arrival = q[hub][category][t - settings.lead_time_weeks] if t >= settings.lead_time_weeks else 0.0
                model += inventory[hub][category][t] == (
                    previous + pipeline_arrival + decision_arrival - pulp.lpSum(x[hub][category][region][t] for region in regions)
                )
                for region in regions:
                    shipping = float(arcs.loc[(hub, category, region), "shipping_cost"])
                    late = float(arcs.loc[(hub, category, region), "late_probability"])
                    supplier_risk = float(hc.loc[(hub, category), "supplier_risk"])
                    unit_cost = (
                        shipping
                        + settings.late_penalty_per_expected_unit * late
                        + settings.supplier_risk_penalty_per_expected_unit * supplier_risk
                    )
                    fulfillment_terms.append(unit_cost * x[hub][category][region][t])

    for category in categories:
        for region in regions:
            for t, week in enumerate(weeks):
                value = float(demand.get((pd.Timestamp(week), category, region), 0.0))
                model += pulp.lpSum(x[hub][category][region][t] for hub in hubs) + shortage[category][region][t] == value
                shortage_terms.append(float(shortage_cost[category]) * shortage[category][region][t])

    for hub in hubs:
        for t in time_ids:
            model += (
                pulp.lpSum(
                    float(hc.loc[(hub, category), "weight_kg"]) * x[hub][category][region][t]
                    for category in categories
                    for region in regions
                )
                <= float(capacity[hub])
            )

    average_shortage_cost = float(pd.Series(shortage_cost).mean())
    for region in regions:
        for t, week in enumerate(weeks):
            region_demand = sum(float(demand.get((pd.Timestamp(week), category, region), 0.0)) for category in categories)
            model += (
                pulp.lpSum(x[hub][category][region][t] for hub in hubs for category in categories)
                + service_gap[region][t]
                >= settings.service_target * region_demand
            )
            service_terms.append(
                average_shortage_cost * settings.service_gap_penalty_multiplier * service_gap[region][t]
            )

    model += pulp.lpSum(procurement_terms + fulfillment_terms + holding_terms + shortage_terms + service_terms)
    solve_start = time.perf_counter()
    model.solve(_solver(settings))
    solve_seconds = time.perf_counter() - solve_start
    status = pulp.LpStatus[model.status]
    if status not in {"Optimal", "Feasible"}:
        raise RuntimeError(f"Inventory planning model failed with status {status}")
    q0 = {(hub, category): float(q[hub][category][0].value() or 0.0) for hub in hubs for category in categories}
    replenishment_rows = []
    flow_rows = []
    inventory_rows = []
    shortage_rows = []
    service_rows = []
    for hub in hubs:
        for category in categories:
            for t, week in enumerate(weeks):
                replenishment_rows.append(
                    {
                        "target_week": week,
                        "horizon": t + 1,
                        "hub": hub,
                        "category": category,
                        "quantity": float(q[hub][category][t].value() or 0.0),
                    }
                )
                inventory_rows.append(
                    {
                        "target_week": week,
                        "horizon": t + 1,
                        "hub": hub,
                        "category": category,
                        "ending_inventory": float(inventory[hub][category][t].value() or 0.0),
                    }
                )
                for region in regions:
                    quantity = float(x[hub][category][region][t].value() or 0.0)
                    if quantity > 0:
                        flow_rows.append(
                            {
                                "target_week": week,
                                "horizon": t + 1,
                                "hub": hub,
                                "category": category,
                                "region": region,
                                "quantity": quantity,
                            }
                        )
    for category in categories:
        for region in regions:
            for t, week in enumerate(weeks):
                shortage_rows.append(
                    {
                        "target_week": week,
                        "horizon": t + 1,
                        "category": category,
                        "region": region,
                        "planned_shortage": float(shortage[category][region][t].value() or 0.0),
                    }
                )
    for region in regions:
        for t, week in enumerate(weeks):
            service_rows.append(
                {
                    "target_week": week,
                    "horizon": t + 1,
                    "region": region,
                    "service_gap": float(service_gap[region][t].value() or 0.0),
                }
            )
    return SolveResult(
        status=status,
        objective=float(pulp.value(model.objective)),
        values={
            "first_week_replenishment": q0,
            "replenishment_plan": pd.DataFrame(replenishment_rows),
            "planned_flows": pd.DataFrame(flow_rows),
            "planned_inventory": pd.DataFrame(inventory_rows),
            "planned_shortages": pd.DataFrame(shortage_rows),
            "planned_service_gaps": pd.DataFrame(service_rows),
            "solve_seconds": solve_seconds,
        },
    )


def solve_actual_fulfillment(
    actual_demand: pd.DataFrame,
    network: dict[str, pd.DataFrame],
    available_inventory: dict[tuple[str, str], float],
    settings: Settings,
) -> SolveResult:
    hubs, categories, regions, hc, arcs, capacity, shortage_cost = _network_dicts(network, settings)
    demand = actual_demand.set_index(["category", "region"])["demand"].to_dict()
    quantity_type = pulp.LpInteger if settings.integer_quantities else pulp.LpContinuous
    model = pulp.LpProblem("actual_fulfillment", pulp.LpMinimize)
    x = pulp.LpVariable.dicts("actual_flow", (hubs, categories, regions), lowBound=0, cat=quantity_type)
    shortage = pulp.LpVariable.dicts("actual_shortage", (categories, regions), lowBound=0, cat=quantity_type)
    service_gap = pulp.LpVariable.dicts("actual_service_gap", regions, lowBound=0, cat=pulp.LpContinuous)

    shipping_terms = []
    risk_terms = []
    shortage_terms = []
    service_terms = []
    for hub in hubs:
        for category in categories:
            model += pulp.lpSum(x[hub][category][region] for region in regions) <= float(available_inventory.get((hub, category), 0.0))
            for region in regions:
                shipping = float(arcs.loc[(hub, category, region), "shipping_cost"])
                late = float(arcs.loc[(hub, category, region), "late_probability"])
                supplier_risk = float(hc.loc[(hub, category), "supplier_risk"])
                shipping_terms.append(shipping * x[hub][category][region])
                risk_terms.append(
                    (
                        settings.late_penalty_per_expected_unit * late
                        + settings.supplier_risk_penalty_per_expected_unit * supplier_risk
                    )
                    * x[hub][category][region]
                )

    for category in categories:
        for region in regions:
            value = float(demand.get((category, region), 0.0))
            model += pulp.lpSum(x[hub][category][region] for hub in hubs) + shortage[category][region] == value
            shortage_terms.append(float(shortage_cost[category]) * shortage[category][region])

    for hub in hubs:
        model += (
            pulp.lpSum(
                float(hc.loc[(hub, category), "weight_kg"]) * x[hub][category][region]
                for category in categories
                for region in regions
            )
            <= float(capacity[hub])
        )

    average_shortage_cost = float(pd.Series(shortage_cost).mean())
    for region in regions:
        region_demand = sum(float(demand.get((category, region), 0.0)) for category in categories)
        model += (
            pulp.lpSum(x[hub][category][region] for hub in hubs for category in categories)
            + service_gap[region]
            >= settings.service_target * region_demand
        )
        service_terms.append(average_shortage_cost * settings.service_gap_penalty_multiplier * service_gap[region])

    model += pulp.lpSum(shipping_terms + risk_terms + shortage_terms + service_terms)
    solve_start = time.perf_counter()
    model.solve(_solver(settings))
    solve_seconds = time.perf_counter() - solve_start
    status = pulp.LpStatus[model.status]
    if status not in {"Optimal", "Feasible"}:
        raise RuntimeError(f"Fulfillment model failed with status {status}")

    flow_rows = []
    remaining = dict(available_inventory)
    for hub in hubs:
        for category in categories:
            shipped_from_stock = 0.0
            for region in regions:
                quantity = float(x[hub][category][region].value() or 0.0)
                shipped_from_stock += quantity
                if quantity > 0:
                    flow_rows.append({"hub": hub, "category": category, "region": region, "quantity": quantity})
            remaining[(hub, category)] = max(0.0, remaining.get((hub, category), 0.0) - shipped_from_stock)

    total_demand = float(sum(demand.values()))
    total_shortage = float(sum(shortage[category][region].value() or 0.0 for category in categories for region in regions))
    shortage_rows = [
        {
            "category": category,
            "region": region,
            "shortage_units": float(shortage[category][region].value() or 0.0),
        }
        for category in categories
        for region in regions
    ]
    service_rows = [
        {"region": region, "service_gap": float(service_gap[region].value() or 0.0)}
        for region in regions
    ]
    capacity_rows = []
    for hub in hubs:
        used_kg = sum(
            float(hc.loc[(hub, category), "weight_kg"])
            * float(x[hub][category][region].value() or 0.0)
            for category in categories
            for region in regions
        )
        capacity_rows.append(
            {
                "hub": hub,
                "used_capacity_kg": used_kg,
                "available_capacity_kg": float(capacity[hub]),
                "capacity_utilization": used_kg / float(capacity[hub]) if float(capacity[hub]) else 0.0,
            }
        )
    values = {
        "flows": pd.DataFrame(flow_rows),
        "remaining_inventory": remaining,
        "total_demand": total_demand,
        "fulfilled_units": total_demand - total_shortage,
        "shortage_units": total_shortage,
        "fill_rate": (total_demand - total_shortage) / total_demand if total_demand else 1.0,
        "shipping_cost": float(sum(pulp.value(term) or 0.0 for term in shipping_terms)),
        "risk_cost": float(sum(pulp.value(term) or 0.0 for term in risk_terms)),
        "shortage_cost": float(sum(pulp.value(term) or 0.0 for term in shortage_terms)),
        "service_gap_cost": float(sum(pulp.value(term) or 0.0 for term in service_terms)),
        "shortages": pd.DataFrame(shortage_rows),
        "service_gaps": pd.DataFrame(service_rows),
        "capacity_utilization": pd.DataFrame(capacity_rows),
        "solve_seconds": solve_seconds,
    }
    return SolveResult(status=status, objective=float(pulp.value(model.objective)), values=values)
