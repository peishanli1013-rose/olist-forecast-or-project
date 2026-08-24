from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


def validate_outputs(output_dir: Path) -> dict:
    panel = pd.read_csv(output_dir / "data" / "weekly_demand_panel.csv")
    forecasts = pd.read_csv(output_dir / "tables" / "forecast_predictions.csv")
    weekly = pd.read_csv(output_dir / "tables" / "weekly_policy_results.csv")
    summary = pd.read_csv(output_dir / "tables" / "policy_summary.csv")
    demand_segments = pd.read_csv(output_dir / "tables" / "demand_segment_summary.csv")
    forecast_segments = pd.read_csv(output_dir / "tables" / "forecast_segment_metrics.csv")
    risk_ranking = pd.read_csv(output_dir / "tables" / "fulfillment_risk_ranking.csv")
    regional = pd.read_csv(output_dir / "tables" / "regional_service_summary.csv")
    replenishment = pd.read_csv(output_dir / "tables" / "replenishment_decisions.csv")
    actual_shortages = pd.read_csv(output_dir / "tables" / "actual_shortages.csv")
    inventory_positions = pd.read_csv(output_dir / "tables" / "inventory_positions.csv")
    capacity_utilization = pd.read_csv(output_dir / "tables" / "capacity_utilization.csv")
    parameter_metadata = pd.read_csv(output_dir / "data" / "network" / "metadata.csv")

    checks = {}
    n_weeks = panel["week"].nunique()
    n_series = panel.groupby(["category", "region"]).ngroups
    checks["panel_has_expected_86_complete_weeks"] = n_weeks == 86
    checks["panel_has_50_series"] = n_series == 50
    checks["panel_is_balanced"] = len(panel) == n_weeks * n_series
    checks["panel_demand_nonnegative_integer"] = bool((panel["demand"] >= 0).all() and np.allclose(panel["demand"], np.round(panel["demand"])))
    checks["forecast_methods_complete"] = set(forecasts["method"]) == {"last_week", "moving_average", "ridge"}
    checks["forecasts_nonnegative"] = bool((forecasts["forecast"] >= -1e-9).all())
    checks["forecast_uncertainty_is_positive_and_chronological"] = bool(
        (forecasts["error_scale"] > 0).all()
        and forecasts["uncertainty_source"].eq("chronological_holdout").all()
    )
    checks["planning_demand_nonnegative_integer"] = bool(
        (forecasts["planning_demand"] >= 0).all()
        and np.allclose(forecasts["planning_demand"], np.round(forecasts["planning_demand"]))
    )
    checks["forecast_origins_13"] = forecasts["origin"].nunique() == 13
    checks["demand_accounting"] = bool(
        np.allclose(weekly["demand_units"], weekly["fulfilled_units"] + weekly["shortage_units"], atol=1e-6)
    )
    cost_columns = [
        "procurement_cost", "shipping_cost", "risk_cost", "holding_cost",
        "shortage_cost", "service_gap_cost",
    ]
    checks["cost_accounting"] = bool(np.allclose(weekly["total_cost"], weekly[cost_columns].sum(axis=1), atol=1e-5))
    checks["inventory_nonnegative"] = bool((weekly["ending_inventory"] >= -1e-9).all())
    checks["fill_rate_in_unit_interval"] = bool(weekly["fill_rate"].between(0, 1).all())
    checks["all_solver_statuses_optimal"] = bool(
        weekly["planning_status"].eq("Optimal").all() and weekly["fulfillment_status"].eq("Optimal").all()
    )
    checks["base_policies_13_weeks_each"] = bool(
        (weekly[weekly["scenario"] == "base"].groupby("policy").size() == 13).all()
    )
    checks["demand_insight_table_has_50_segments"] = len(demand_segments) == 50
    checks["forecast_segment_table_is_complete"] = bool(
        len(forecast_segments) == 50 * 3
        and set(forecast_segments["method"]) == {"last_week", "moving_average", "ridge"}
    )
    checks["risk_ranking_has_evidence_and_smoothed_rates"] = bool(
        len(risk_ranking) > 0
        and (risk_ranking["sample_size"] > 0).all()
        and risk_ranking["late_probability"].between(0, 1).all()
        and risk_ranking["supplier_risk"].between(0, 1).all()
    )
    checks["parameter_sources_and_rationales_are_documented"] = bool(
        len(parameter_metadata) >= 15
        and parameter_metadata["source"].notna().all()
        and parameter_metadata["rationale"].str.len().ge(20).all()
    )
    base_weekly = weekly[weekly["scenario"] == "base"].copy()
    base_weekly["week"] = pd.to_datetime(base_weekly["week"])
    regional_totals = regional.groupby("policy")[["demand_units", "fulfilled_units", "shortage_units"]].sum()
    policy_totals = base_weekly.groupby("policy")[["demand_units", "fulfilled_units", "shortage_units"]].sum()
    checks["regional_service_reconciles_to_policy_totals"] = bool(
        np.allclose(regional_totals.sort_index(), policy_totals.sort_index(), atol=1e-6)
    )
    first_orders = replenishment[replenishment["horizon"] == 1].copy()
    first_orders["origin_week"] = pd.to_datetime(first_orders["origin_week"])
    ordered_by_week = first_orders.groupby(["policy", "origin_week"])["quantity"].sum().sort_index()
    weekly_ordered = base_weekly.set_index(["policy", "week"])["ordered_units"].sort_index()
    checks["replenishment_details_reconcile"] = bool(np.allclose(ordered_by_week, weekly_ordered, atol=1e-6))
    actual_shortages["origin_week"] = pd.to_datetime(actual_shortages["origin_week"])
    shortage_by_week = actual_shortages.groupby(["policy", "origin_week"])["shortage_units"].sum().sort_index()
    weekly_shortage = base_weekly.set_index(["policy", "week"])["shortage_units"].sort_index()
    checks["shortage_details_reconcile"] = bool(np.allclose(shortage_by_week, weekly_shortage, atol=1e-6))
    inventory_positions["origin_week"] = pd.to_datetime(inventory_positions["origin_week"])
    inventory_by_week = inventory_positions.groupby(["policy", "origin_week"])["ending_inventory"].sum().sort_index()
    weekly_inventory = base_weekly.set_index(["policy", "week"])["ending_inventory"].sort_index()
    checks["inventory_details_reconcile"] = bool(np.allclose(inventory_by_week, weekly_inventory, atol=1e-6))
    checks["capacity_utilization_within_limits"] = bool(
        capacity_utilization["capacity_utilization"].between(0, 1 + 1e-8).all()
    )
    checks["solver_times_nonnegative"] = bool(
        (weekly[["planning_solve_seconds", "fulfillment_solve_seconds"]] >= 0).all().all()
    )
    nonbase_scenarios = set(summary.loc[summary["scenario"] != "base", "scenario"])
    expected_scenarios = {
        "safety_0", "safety_1", "lead_time_2", "shortage_low", "shortage_high",
        "service_85", "service_95", "capacity_80", "capacity_120", "risk_0", "risk_2x",
    }
    checks["promised_sensitivity_scenarios_complete_or_skipped"] = bool(
        not nonbase_scenarios or expected_scenarios.issubset(nonbase_scenarios)
    )
    checks["summary_matches_weekly_cost"] = bool(
        np.allclose(
            summary.set_index(["scenario", "policy"])["total_cost"].sort_index(),
            weekly.groupby(["scenario", "policy"])["total_cost"].sum().sort_index(),
            atol=1e-5,
        )
    )
    passed = all(checks.values())
    report = {"passed": passed, "checks": checks}
    (output_dir / "validation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not passed:
        failed = [name for name, result in checks.items() if not result]
        raise AssertionError(f"Validation failed: {failed}")
    return report
