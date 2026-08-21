# Olist Forecast-Driven Inventory and Fulfillment Optimization

This project implements a reproducible **forecast → plan → fulfill → update** experiment using the Brazilian E-Commerce Public Dataset by Olist.

## Research objective

The project investigates whether demand forecasts and forecast uncertainty can improve simulated inventory replenishment and fulfillment decisions. It compares forecasting policies under the same Operations Research model and evaluates both statistical accuracy and downstream cost and service performance.

## What the project does

1. Joins Olist orders, order items, products, category translation, customers, and sellers.
2. Builds 50 zero-inclusive weekly demand series: 10 product categories × 5 Brazilian regions.
3. Compares last-week, four-week moving-average, and pooled Ridge forecasts using chronological validation.
4. Estimates seller late-dispatch risk, delivery-lateness risk, and approval-to-carrier lead-time proxies.
5. Uses forecasts and past forecast errors to plan replenishment and inventory positioning in a transparent six-hub scenario.
6. Reveals actual weekly demand and solves a capacitated fulfillment-allocation model using the inventory available.
7. Repeats the process for 13 historical weeks and compares realized cost, fill rate, shortages, inventory, and risk.

The modeling window contains 86 complete Monday-starting weeks from 2017-01-02 through 2018-08-20. The incomplete week beginning 2018-08-27 is excluded.

## Important interpretation

Olist does not provide actual warehouse locations, historical inventory, procurement contracts, or replenishment decisions. Demand, seller and customer geography, freight, and service timing are observed. The six proxy hubs, opening inventory, capacities, procurement costs, and replenishment rules are documented scenario assumptions and are evaluated through sensitivity analysis.

## Repository structure

```text
.
├── docs/                 # Proposal documents
├── outputs/
│   ├── data/             # Small reproducible derived datasets and network parameters
│   ├── figures/          # Presentation-ready figures
│   ├── tables/           # Forecast and policy results
│   └── RESULTS_SUMMARY.md
├── src/                  # Data, forecasting, optimization, validation, and reporting code
├── DATA_DICTIONARY.md
├── MODEL.md
├── PROJECT_STATUS.md
├── requirements.txt
├── setup_project.command
└── run_project.command
```

## Data setup

Download the Brazilian E-Commerce Public Dataset by Olist separately. The raw CSV files are intentionally not stored in this repository.

Place the following files in a local data directory:

- `olist_orders_dataset.csv`
- `olist_order_items_dataset.csv`
- `olist_products_dataset.csv`
- `product_category_name_translation.csv`
- `olist_customers_dataset.csv`
- `olist_sellers_dataset.csv`

The code can locate the data through any of the following methods:

1. Pass `--data-dir /path/to/olist/csvs` on the command line.
2. Set the `OLIST_DATA_DIR` environment variable.
3. Place the files in a sibling directory named `archive` or `data`.

## Run

On macOS, run `setup_project.command` once to create the local Python environment, then run `run_project.command` to rebuild the outputs.

From a terminal in the repository root:

```bash
python -m src.run_all --data-dir /path/to/olist/csvs
```

For a faster validation run without sensitivity tests:

```bash
python -m src.run_all --data-dir /path/to/olist/csvs --quick
```

Dependencies are listed in `requirements.txt`. The verified optimization solver is PuLP's bundled CBC solver.

## Main outputs

- `outputs/data/weekly_demand_panel.csv`: balanced 50-series demand panel.
- `outputs/data/network/`: data-derived risk, freight, and scenario parameter tables.
- `outputs/tables/forecast_predictions.csv`: forecasts by origin and horizon.
- `outputs/tables/forecast_metrics.csv`: WAPE, MAE, and bias.
- `outputs/tables/weekly_policy_results.csv`: weekly realized operations and cost.
- `outputs/tables/policy_summary.csv`: policy and sensitivity comparison.
- `outputs/figures/`: demand, forecast, cost, fill-rate, and sensitivity figures.
- `outputs/RESULTS_SUMMARY.md`: concise findings and limitations.

## Verified project scope

- 112,643 valid primary-status order-item lines.
- 86 complete weekly periods.
- 50 category-region demand series and 4,300 balanced panel rows.
- A four-week inventory-planning model followed by realized fulfillment allocation.
- A 13-week rolling historical backtest.
- Automated validation of demand accounting, cost accounting, inventory balance, solver status, and output reconciliation.

The core project intentionally does not claim to reconstruct Olist's real warehouse network and does not use SKU-level deep learning, stochastic programming, or vehicle routing.

