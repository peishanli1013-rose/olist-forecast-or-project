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

    checks = {}
    n_weeks = panel["week"].nunique()
    n_series = panel.groupby(["category", "region"]).ngroups
    checks["panel_has_expected_86_complete_weeks"] = n_weeks == 86
    checks["panel_has_50_series"] = n_series == 50
    checks["panel_is_balanced"] = len(panel) == n_weeks * n_series
    checks["panel_demand_nonnegative_integer"] = bool((panel["demand"] >= 0).all() and np.allclose(panel["demand"], np.round(panel["demand"])))
    checks["forecast_methods_complete"] = set(forecasts["method"]) == {"last_week", "moving_average", "ridge"}
    checks["forecasts_nonnegative"] = bool((forecasts["forecast"] >= -1e-9).all())
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
