from __future__ import annotations

import json
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

from .config import REGION_BY_STATE, REGION_ORDER, Settings


DATE_COLUMNS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
    "shipping_limit_date",
]


def _read(data_dir: Path, name: str, **kwargs) -> pd.DataFrame:
    return pd.read_csv(data_dir / name, low_memory=False, **kwargs)


def load_and_join_olist(data_dir: Path) -> pd.DataFrame:
    orders = _read(data_dir, "olist_orders_dataset.csv")
    items = _read(data_dir, "olist_order_items_dataset.csv")
    products = _read(data_dir, "olist_products_dataset.csv")
    customers = _read(data_dir, "olist_customers_dataset.csv")
    sellers = _read(data_dir, "olist_sellers_dataset.csv")
    translation = _read(data_dir, "product_category_name_translation.csv", encoding="utf-8-sig")

    for column in DATE_COLUMNS[:-1]:
        if column in orders.columns:
            orders[column] = pd.to_datetime(orders[column], errors="coerce")
    items["shipping_limit_date"] = pd.to_datetime(items["shipping_limit_date"], errors="coerce")

    products = products.merge(translation, on="product_category_name", how="left")
    products["category"] = products["product_category_name_english"].fillna(
        products["product_category_name"].fillna("unknown")
    )

    enriched = (
        items.merge(orders, on="order_id", how="left", validate="many_to_one")
        .merge(customers, on="customer_id", how="left", validate="many_to_one")
        .merge(products, on="product_id", how="left", validate="many_to_one")
        .merge(sellers, on="seller_id", how="left", validate="many_to_one")
    )
    enriched["customer_region"] = enriched["customer_state"].map(REGION_BY_STATE).fillna("Unknown")
    enriched["purchase_week"] = (
        enriched["order_purchase_timestamp"].dt.to_period("W-SUN").dt.start_time
    )
    enriched["late_dispatch"] = np.where(
        enriched["order_delivered_carrier_date"].notna() & enriched["shipping_limit_date"].notna(),
        (enriched["order_delivered_carrier_date"] > enriched["shipping_limit_date"]).astype(float),
        np.nan,
    )
    enriched["late_delivery"] = np.where(
        enriched["order_delivered_customer_date"].notna()
        & enriched["order_estimated_delivery_date"].notna(),
        (enriched["order_delivered_customer_date"] > enriched["order_estimated_delivery_date"]).astype(float),
        np.nan,
    )
    enriched["approval_to_carrier_days"] = (
        enriched["order_delivered_carrier_date"] - enriched["order_approved_at"]
    ).dt.total_seconds() / 86400.0
    enriched["weight_kg"] = pd.to_numeric(enriched["product_weight_g"], errors="coerce") / 1000.0
    enriched["weight_kg"] = enriched["weight_kg"].clip(lower=0.05, upper=50.0)
    return enriched


def build_weekly_panel(enriched: pd.DataFrame, settings: Settings) -> tuple[pd.DataFrame, list[str]]:
    stable = enriched.loc[
        enriched["order_status"].notna()
        & ~enriched["order_status"].isin(["created", "unavailable"])
        & enriched["purchase_week"].between(settings.stable_start, settings.stable_end)
        & enriched["customer_region"].isin(REGION_ORDER)
    ].copy()
    top_categories = (
        stable.groupby("category").size().sort_values(ascending=False).head(settings.top_categories).index.tolist()
    )
    stable = stable[stable["category"].isin(top_categories)]
    weeks = pd.date_range(settings.stable_start, settings.stable_end, freq="W-MON")
    skeleton = pd.DataFrame(
        product(weeks, top_categories, REGION_ORDER),
        columns=["week", "category", "region"],
    )
    observed = (
        stable.groupby(["purchase_week", "category", "customer_region"], observed=True)
        .size()
        .rename("demand")
        .reset_index()
        .rename(columns={"purchase_week": "week", "customer_region": "region"})
    )
    panel = skeleton.merge(observed, on=["week", "category", "region"], how="left")
    panel["demand"] = panel["demand"].fillna(0).astype(int)
    panel = panel.sort_values(["week", "category", "region"]).reset_index(drop=True)
    return panel, top_categories


def data_audit(enriched: pd.DataFrame, panel: pd.DataFrame, categories: list[str], settings: Settings) -> dict:
    stable_mask = (
        enriched["order_status"].notna()
        & ~enriched["order_status"].isin(["created", "unavailable"])
        & enriched["purchase_week"].between(settings.stable_start, settings.stable_end)
    )
    product_counts = enriched.loc[stable_mask].groupby("product_id").size()
    selected_units = int(panel["demand"].sum())
    stable_units = int(stable_mask.sum())
    return {
        "item_lines_total": int(len(enriched)),
        "item_lines_primary_status": int((enriched["order_status"].notna() & ~enriched["order_status"].isin(["created", "unavailable"])).sum()),
        "stable_window_start": settings.stable_start,
        "stable_window_end": settings.stable_end,
        "stable_weeks": int(panel["week"].nunique()),
        "categories": categories,
        "regions": REGION_ORDER,
        "series": int(panel.groupby(["category", "region"]).ngroups),
        "panel_rows": int(len(panel)),
        "stable_units_all_categories": stable_units,
        "selected_units": selected_units,
        "selected_unit_share": selected_units / stable_units if stable_units else None,
        "products_fewer_than_five_units_share": float((product_counts < 5).mean()),
        "products_single_unit_share": float((product_counts == 1).mean()),
        "missing_category_share": float(enriched["category"].isna().mean()),
        "missing_customer_region_share": float((enriched["customer_region"] == "Unknown").mean()),
    }


def run_data_pipeline(data_dir: Path, output_dir: Path, settings: Settings) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    enriched = load_and_join_olist(data_dir)
    panel, categories = build_weekly_panel(enriched, settings)
    audit = data_audit(enriched, panel, categories, settings)

    panel.to_csv(output_dir / "weekly_demand_panel.csv", index=False)
    enriched.to_csv(output_dir / "enriched_order_items.csv.gz", index=False, compression="gzip")
    with (output_dir / "data_audit.json").open("w", encoding="utf-8") as handle:
        json.dump(audit, handle, indent=2, ensure_ascii=False)
    return enriched, panel, audit

