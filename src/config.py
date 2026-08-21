from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def resolve_data_dir(explicit: str | Path | None = None) -> Path:
    """Resolve the nine Olist CSV files without hard-coding one machine path."""
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    if os.environ.get("OLIST_DATA_DIR"):
        candidates.append(Path(os.environ["OLIST_DATA_DIR"]).expanduser())
    candidates.extend(
        [
            PROJECT_ROOT.parent / "archive",
            PROJECT_ROOT / "data" / "raw",
        ]
    )
    required = {
        "olist_orders_dataset.csv",
        "olist_order_items_dataset.csv",
        "olist_products_dataset.csv",
        "olist_customers_dataset.csv",
        "olist_sellers_dataset.csv",
        "product_category_name_translation.csv",
    }
    for candidate in candidates:
        if candidate.exists() and required.issubset({p.name for p in candidate.glob("*.csv")}):
            return candidate.resolve()
    searched = "\n".join(f"- {p}" for p in candidates)
    raise FileNotFoundError(f"Could not find the Olist CSV directory. Searched:\n{searched}")


@dataclass(frozen=True)
class Settings:
    stable_start: str = "2017-01-02"
    # The week beginning 2018-08-27 contains only two observed days.
    # Use the final complete Monday-starting week instead.
    stable_end: str = "2018-08-20"
    top_categories: int = 10
    candidate_hubs: int = 6
    planning_horizon: int = 4
    backtest_weeks: int = 13
    ridge_alpha: float = 25.0
    safety_z: float = 0.50
    service_target: float = 0.90
    lead_time_weeks: int = 1
    opening_weeks_cover: float = 2.0
    capacity_multiplier: float = 1.35
    replenishment_multiplier: float = 1.50
    procurement_share_of_price: float = 0.60
    holding_rate_per_week: float = 0.01
    shortage_value_multiplier: float = 1.25
    late_penalty_per_expected_unit: float = 8.0
    supplier_risk_penalty_per_expected_unit: float = 5.0
    service_gap_penalty_multiplier: float = 1.50
    integer_quantities: bool = True
    solver_time_limit_seconds: int = 60
    solver_relative_gap: float = 0.001

    def with_changes(self, **kwargs) -> "Settings":
        return replace(self, **kwargs)


REGION_BY_STATE = {
    "AC": "North", "AP": "North", "AM": "North", "PA": "North",
    "RO": "North", "RR": "North", "TO": "North",
    "AL": "Northeast", "BA": "Northeast", "CE": "Northeast", "MA": "Northeast",
    "PB": "Northeast", "PE": "Northeast", "PI": "Northeast", "RN": "Northeast", "SE": "Northeast",
    "DF": "Central-West", "GO": "Central-West", "MT": "Central-West", "MS": "Central-West",
    "ES": "Southeast", "MG": "Southeast", "RJ": "Southeast", "SP": "Southeast",
    "PR": "South", "RS": "South", "SC": "South",
}

REGION_ORDER = ["North", "Northeast", "Central-West", "Southeast", "South"]
