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
    output_path: Path,
) -> None:
    base = policy_summary[policy_summary["scenario"] == "base"].sort_values("total_cost")
    best = base.iloc[0]
    one_step = forecast_metrics[forecast_metrics["horizon"] == 1].sort_values("WAPE")
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
        "## Forecast comparison",
        "",
        _markdown_table(one_step),
        "",
        "## Base rolling-backtest comparison",
        "",
        _markdown_table(base[["policy", "total_cost", "fill_rate", "shortage_units", "ending_inventory", "expected_late_units"]]),
        "",
        f"The lowest simulated total cost in the base assumptions is produced by **{best['policy']}**, with a fill rate of {_pct(best['fill_rate'])}.",
        "",
        "## Sensitivity tests for the Ridge policy",
        "",
        _markdown_table(sensitivity[["scenario", "total_cost", "fill_rate", "shortage_units", "ending_inventory"]]) if not sensitivity.empty else "Sensitivity analysis was not run.",
        "",
        "## Interpretation boundary",
        "",
        "Demand, timing, geography, freight, and historical service risk are estimated from Olist. Warehouses, opening inventory, capacities, procurement costs, and replenishment rules are transparent planning scenarios, not Olist's actual network.",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_run_manifest(data_dir: Path, settings: dict, output_path: Path) -> None:
    output_path.write_text(
        json.dumps({"data_dir": str(data_dir), "settings": settings}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
