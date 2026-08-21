from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


COLORS = {"last_week": "#9CA3AF", "moving_average": "#3B82F6", "ridge": "#F59E0B"}


def create_figures(
    panel: pd.DataFrame,
    forecast_metrics: pd.DataFrame,
    weekly: pd.DataFrame,
    summary: pd.DataFrame,
    sensitivity: pd.DataFrame,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    demand = panel.groupby("week", as_index=False)["demand"].sum()
    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(pd.to_datetime(demand["week"]), demand["demand"], color="#1F4E78", linewidth=2)
    ax.set(title="Observed Weekly Demand in the Selected Olist Panel", xlabel="Week", ylabel="Item units")
    fig.tight_layout()
    fig.savefig(output_dir / "01_weekly_demand.png", dpi=180)
    plt.close(fig)

    one_step = forecast_metrics[forecast_metrics["horizon"] == 1].copy()
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    ax.bar(one_step["method"], one_step["WAPE"], color=[COLORS.get(x, "#4B5563") for x in one_step["method"]])
    ax.set(title="One-Week-Ahead Forecast Error", xlabel="Forecast method", ylabel="WAPE")
    ax.yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    fig.tight_layout()
    fig.savefig(output_dir / "02_forecast_wape.png", dpi=180)
    plt.close(fig)

    base = summary[summary["scenario"] == "base"].set_index("policy")
    components = ["procurement_cost", "shipping_cost", "risk_cost", "holding_cost", "shortage_cost", "service_gap_cost"]
    component_labels = ["Procurement", "Shipping", "Risk", "Holding", "Shortage", "Service gap"]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    bottom = pd.Series(0.0, index=base.index)
    palette = sns.color_palette("deep", len(components))
    for column, label, color in zip(components, component_labels, palette):
        ax.bar(base.index, base[column], bottom=bottom, label=label, color=color)
        bottom = bottom + base[column]
    ax.set(title="Realized Cost by Forecast-Driven Policy", xlabel="Policy", ylabel="Simulated cost (BRL-equivalent)")
    ax.legend(ncol=3, fontsize=8)
    fig.tight_layout()
    fig.savefig(output_dir / "03_policy_cost_components.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    ax.bar(base.index, base["fill_rate"], color=[COLORS.get(x, "#4B5563") for x in base.index])
    ax.axhline(0.90, color="#B91C1C", linestyle="--", linewidth=1.5, label="90% target")
    ax.set_ylim(max(0.0, base["fill_rate"].min() - 0.05), 1.0)
    ax.set(title="Realized Fill Rate", xlabel="Policy", ylabel="Fill rate")
    ax.yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "04_policy_fill_rate.png", dpi=180)
    plt.close(fig)

    base_weekly = weekly[weekly["scenario"] == "base"].copy()
    base_weekly["cumulative_cost"] = base_weekly.groupby("policy")["total_cost"].cumsum()
    fig, ax = plt.subplots(figsize=(9, 5.0))
    for policy, group in base_weekly.groupby("policy"):
        ax.plot(pd.to_datetime(group["week"]), group["cumulative_cost"], label=policy, color=COLORS.get(policy), linewidth=2)
    ax.set(title="Cumulative Realized Cost During the 13-Week Backtest", xlabel="Week", ylabel="Cumulative cost")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "05_cumulative_cost.png", dpi=180)
    plt.close(fig)

    if not sensitivity.empty:
        fig, ax = plt.subplots(figsize=(8.5, 5.0))
        ax.scatter(sensitivity["fill_rate"], sensitivity["total_cost"], s=70, color="#7C3AED")
        for row in sensitivity.itertuples(index=False):
            ax.annotate(row.scenario, (row.fill_rate, row.total_cost), xytext=(5, 4), textcoords="offset points", fontsize=8)
        ax.set(title="Ridge Policy Sensitivity: Cost-Service Trade-off", xlabel="Fill rate", ylabel="Total cost")
        ax.xaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
        fig.tight_layout()
        fig.savefig(output_dir / "06_sensitivity.png", dpi=180)
        plt.close(fig)
