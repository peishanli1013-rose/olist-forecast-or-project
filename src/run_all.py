from __future__ import annotations

import argparse
import math
import time
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from .backtest import run_policy_backtest, summarize_policies
from .analysis import demand_segment_summary, forecast_segment_metrics, fulfillment_risk_ranking
from .config import PROJECT_ROOT, Settings, resolve_data_dir
from .data_pipeline import run_data_pipeline
from .forecasting import forecast_metrics, generate_backtest_forecasts
from .network import build_network, save_network
from .report import write_results_report, write_run_manifest
from .visualize import create_figures
from .validation import validate_outputs


def parse_args():
    parser = argparse.ArgumentParser(description="Run the Olist forecast-to-OR project")
    parser.add_argument("--data-dir", type=Path, default=None, help="Directory containing the Olist CSV files")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "outputs")
    parser.add_argument("--quick", action="store_true", help="Skip sensitivity tests")
    return parser.parse_args()


def main():
    args = parse_args()
    settings = Settings()
    data_dir = resolve_data_dir(args.data_dir)
    output_dir = args.output_dir.resolve()
    processed_dir = output_dir / "data"
    tables_dir = output_dir / "tables"
    figures_dir = output_dir / "figures"
    for directory in (processed_dir, tables_dir, figures_dir):
        directory.mkdir(parents=True, exist_ok=True)

    start = time.perf_counter()
    print(f"[1/6] Loading and auditing Olist data from {data_dir}")
    enriched, panel, audit = run_data_pipeline(data_dir, processed_dir, settings)

    print("[2/6] Calibrating the six-hub planning scenario and historical risk parameters")
    network = build_network(enriched, panel, settings)
    save_network(network, processed_dir / "network")
    demand_summary = demand_segment_summary(panel)
    risk_ranking = fulfillment_risk_ranking(enriched, panel, network, settings)
    demand_summary.to_csv(tables_dir / "demand_segment_summary.csv", index=False)
    risk_ranking.to_csv(tables_dir / "fulfillment_risk_ranking.csv", index=False)

    print("[3/6] Generating chronological forecasts for 13 rolling origins")
    forecasts = generate_backtest_forecasts(
        panel,
        backtest_weeks=settings.backtest_weeks,
        horizon=settings.planning_horizon,
        alpha=settings.ridge_alpha,
        alpha_grid=settings.ridge_alpha_grid,
        calibration_weeks=settings.uncertainty_calibration_weeks,
    )
    forecasts["planning_demand"] = (
        forecasts["forecast"] + settings.safety_z * forecasts["error_scale"]
    ).clip(lower=0).map(math.ceil)
    metrics = forecast_metrics(forecasts)
    segment_metrics = forecast_segment_metrics(forecasts)
    forecasts.to_csv(tables_dir / "forecast_predictions.csv", index=False)
    metrics.to_csv(tables_dir / "forecast_metrics.csv", index=False)
    segment_metrics.to_csv(tables_dir / "forecast_segment_metrics.csv", index=False)

    print("[4/6] Running forecast-driven inventory and reactive fulfillment policies")
    weekly_frames = []
    flow_frames = []
    detail_frames: dict[str, list[pd.DataFrame]] = {}
    for policy in ("last_week", "moving_average", "ridge"):
        print(f"      policy={policy}")
        weekly, flows, details = run_policy_backtest(policy, panel, forecasts, network, settings, scenario="base")
        weekly_frames.append(weekly)
        if not flows.empty:
            flow_frames.append(flows)
        for name, frame in details.items():
            if not frame.empty:
                detail_frames.setdefault(name, []).append(frame)
    base_weekly = pd.concat(weekly_frames, ignore_index=True)
    base_flows = pd.concat(flow_frames, ignore_index=True) if flow_frames else pd.DataFrame()
    base_summary = summarize_policies(base_weekly)

    sensitivity_weekly_frames = []
    sensitivity_summary = pd.DataFrame()
    if not args.quick:
        print("[5/6] Running one-factor-at-a-time Ridge sensitivity tests")
        scenarios = {
            "safety_0": settings.with_changes(safety_z=0.0),
            "safety_1": settings.with_changes(safety_z=1.0),
            "lead_time_2": settings.with_changes(lead_time_weeks=2, opening_weeks_cover=3.0),
            "shortage_low": settings.with_changes(shortage_value_multiplier=0.80),
            "shortage_high": settings.with_changes(shortage_value_multiplier=2.00),
            "service_85": settings.with_changes(service_target=0.85),
            "service_95": settings.with_changes(service_target=0.95),
            "capacity_80": settings.with_changes(capacity_multiplier=settings.capacity_multiplier * 0.80),
            "capacity_120": settings.with_changes(capacity_multiplier=settings.capacity_multiplier * 1.20),
            "risk_0": settings.with_changes(
                late_penalty_per_expected_unit=0.0,
                supplier_risk_penalty_per_expected_unit=0.0,
            ),
            "risk_2x": settings.with_changes(
                late_penalty_per_expected_unit=settings.late_penalty_per_expected_unit * 2.0,
                supplier_risk_penalty_per_expected_unit=settings.supplier_risk_penalty_per_expected_unit * 2.0,
            ),
        }
        for scenario_name, scenario_settings in scenarios.items():
            print(f"      scenario={scenario_name}")
            scenario_network = build_network(enriched, panel, scenario_settings)
            weekly, _, _ = run_policy_backtest(
                "ridge", panel, forecasts, scenario_network, scenario_settings, scenario=scenario_name
            )
            sensitivity_weekly_frames.append(weekly)
        sensitivity_weekly = pd.concat(sensitivity_weekly_frames, ignore_index=True)
        sensitivity_summary = summarize_policies(sensitivity_weekly)
    else:
        print("[5/6] Sensitivity tests skipped (--quick)")

    all_weekly = pd.concat([base_weekly] + sensitivity_weekly_frames, ignore_index=True)
    all_summary = pd.concat([base_summary, sensitivity_summary], ignore_index=True)
    all_weekly.to_csv(tables_dir / "weekly_policy_results.csv", index=False)
    all_summary.to_csv(tables_dir / "policy_summary.csv", index=False)
    if not base_flows.empty:
        base_flows.to_csv(tables_dir / "base_fulfillment_flows.csv", index=False)
    combined_details = {
        name: pd.concat(frames, ignore_index=True)
        for name, frames in detail_frames.items()
    }
    for name, frame in combined_details.items():
        frame.to_csv(tables_dir / f"{name}.csv", index=False)

    regional_service = combined_details["regional_service_results"]
    regional_summary = (
        regional_service.groupby(["policy", "region"], observed=True)
        .agg(
            demand_units=("demand_units", "sum"),
            fulfilled_units=("fulfilled_units", "sum"),
            shortage_units=("shortage_units", "sum"),
            expected_late_units=("expected_late_units", "sum"),
            supplier_risk_units=("supplier_risk_units", "sum"),
        )
        .reset_index()
    )
    regional_summary["fill_rate"] = regional_summary["fulfilled_units"] / regional_summary["demand_units"]
    regional_summary.to_csv(tables_dir / "regional_service_summary.csv", index=False)

    print("[6/6] Creating figures and the results summary")
    create_figures(
        panel,
        metrics,
        all_weekly,
        all_summary,
        sensitivity_summary,
        demand_summary,
        segment_metrics,
        risk_ranking,
        regional_summary,
        figures_dir,
    )
    write_results_report(
        audit,
        metrics,
        all_summary,
        sensitivity_summary,
        demand_summary,
        segment_metrics,
        risk_ranking,
        regional_summary,
        output_dir / "RESULTS_SUMMARY.md",
    )
    write_run_manifest(data_dir, asdict(settings), output_dir / "run_manifest.json")
    validate_outputs(output_dir)
    elapsed = time.perf_counter() - start
    print(f"Completed in {elapsed:.1f} seconds. Results: {output_dir}")


if __name__ == "__main__":
    main()
