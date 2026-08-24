from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _pct(value: float) -> str:
    return f"{value:.1%}"


def _markdown_table(frame: pd.DataFrame) -> str:
    rendered = frame.copy()
    for column in rendered.select_dtypes(include="number").columns:
        rendered[column] = rendered[column].map(lambda value: f"{value:.4f}" if pd.notna(value) else "")
    headers = [str(column) for column in rendered.columns]
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rendered.astype(str).itertuples(index=False, name=None):
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def write_results_report(
    audit: dict,
    forecast_metrics: pd.DataFrame,
    policy_summary: pd.DataFrame,
    sensitivity: pd.DataFrame,
    demand_summary: pd.DataFrame,
    segment_metrics: pd.DataFrame,
    risk_ranking: pd.DataFrame,
    regional_summary: pd.DataFrame,
    output_path: Path,
) -> None:
    base = policy_summary[policy_summary["scenario"] == "base"].sort_values("total_cost")
    best = base.iloc[0]
    one_step = forecast_metrics[forecast_metrics["horizon"] == 1].sort_values("WAPE")
    top_demand = demand_summary.head(8)[
        ["category", "region", "total_demand", "demand_share", "coefficient_of_variation", "zero_week_share"]
    ]
    winner_counts = (
        segment_metrics[segment_metrics["is_best_wape"]]
        .groupby("method")
        .size()
        .rename("best_segment_count")
        .reset_index()
        .sort_values("best_segment_count", ascending=False)
    )
    high_evidence_risk = risk_ranking[risk_ranking["sample_size"] >= 30].head(8)[
        [
            "hub", "category", "region", "sample_size", "late_probability",
            "supplier_risk", "shipping_cost", "expected_risk_cost_per_unit",
        ]
    ]
    ridge_region = regional_summary[regional_summary["policy"] == "ridge"][
        ["region", "demand_units", "fulfilled_units", "shortage_units", "fill_rate", "expected_late_units"]
    ].sort_values("fill_rate")
    lines = [
        "# Olist Forecast-Driven OR Project: Results Summary",
        "",
        "## Data foundation",
        "",
        f"- Valid primary-status item lines: {audit['item_lines_primary_status']:,}",
        f"- Stable window: {audit['stable_window_start']} to {audit['stable_window_end']} ({audit['stable_weeks']} weeks)",
        f"- Balanced panel: {audit['series']} category-region series and {audit['panel_rows']:,} rows",
        f"- Selected-category coverage: {_pct(audit['selected_unit_share'])}",
        f"- Products appearing once: {_pct(audit['products_single_unit_share'])}",
        "",
        "## Data-derived demand insights",
        "",
        "The following category-region segments account for the largest observed demand in the retained panel:",
        "",
        _markdown_table(top_demand),
        "",
        "## Forecast comparison",
        "",
        _markdown_table(one_step),
        "",
        "The count below shows how often each method attains the lowest one-week WAPE across the 50 category-region segments (ties are retained):",
        "",
        _markdown_table(winner_counts),
        "",
        "All three methods use an eight-week chronological holdout to estimate forecast-error scale. Ridge alpha is selected from {1, 5, 25, 100} at each forecast origin using only prior observations.",
        "",
        "## Historical fulfillment-risk insights",
        "",
        "Routes below have at least 30 observations and the highest smoothed expected risk penalty per fulfilled unit:",
        "",
        _markdown_table(high_evidence_risk),
        "",
        "## Base rolling-backtest comparison",
        "",
        _markdown_table(base[["policy", "total_cost", "fill_rate", "shortage_units", "ending_inventory", "expected_late_units"]]),
        "",
        f"The lowest simulated total cost in the base assumptions is produced by **{best['policy']}**, with a fill rate of {_pct(best['fill_rate'])}.",
        "",
        "## Regional service under the Ridge policy",
        "",
        _markdown_table(ridge_region),
        "",
        "## Sensitivity tests for the Ridge policy",
        "",
        _markdown_table(sensitivity[["scenario", "total_cost", "fill_rate", "shortage_units", "ending_inventory"]]) if not sensitivity.empty else "Sensitivity analysis was not run.",
        "",
        "## Interpretation boundary",
        "",
        "Demand, timing, geography, freight, and smoothed historical service risk are estimated from Olist. Warehouses, opening inventory, capacities, procurement costs, replenishment lead time, and replenishment rules are transparent planning scenarios, not Olist's actual network. The approval-to-carrier measure is a historical fulfillment proxy and is not presented as Olist's procurement lead time.",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_run_manifest(data_dir: Path, settings: dict, output_path: Path) -> None:
    output_path.write_text(
        json.dumps({"data_dir": str(data_dir), "settings": settings}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
