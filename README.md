# Olist Forecast-Driven Inventory and Fulfillment Optimization

[中文说明](README_CN.md)

This project implements a reproducible **describe → forecast → plan → fulfill → update** experiment using the Brazilian E-Commerce Public Dataset by Olist. It responds to the central research question: can forecast-driven replenishment and fulfillment decisions reduce simulated cost while maintaining regional service?

## Interactive results MVP

Live site: [Olist OR Lab](https://olist-forecast-or-lab.peishanli1013.chatgpt.site)

[`site/`](site/) contains the complete source for the English interactive website. It has Overview, Demand, Forecast, Optimization, and Sensitivity sections. Its controls expose eleven scenarios already solved by the MILP across safety buffer, lead time, service target, capacity, risk weights, and shortage value. The interface does not interpolate unsolved parameter combinations.

```bash
cd site
npm install
npm run dev
```

Open `http://localhost:3000`. Run `npm test` to verify the production build, rendered content, and social metadata.

## Research questions

1. How do weekly demand patterns and historical fulfillment risks differ across product categories, customer regions, and seller-origin routes?
2. Do pooled Ridge forecasts outperform transparent time-series benchmarks, and for which category-region segments?
3. Do forecast-driven replenishment and fulfillment decisions reduce simulated cost while maintaining regional service levels?

## What the project does

1. Joins Olist orders, order items, products, category translation, customers, and sellers.
2. Builds 50 zero-inclusive weekly demand series: 10 product categories × 5 Brazilian regions.
3. Quantifies demand concentration, sparsity, volatility, trend, and route-level historical fulfillment risk.
4. Compares last-week, four-week moving-average, and pooled Ridge forecasts using chronological validation.
5. Selects Ridge regularization strength using a past-only holdout and estimates uncertainty consistently for all methods.
6. Uses forecasts and historical forecast errors to solve a four-week multi-period inventory-replenishment MILP.
7. Reveals actual weekly demand and solves a capacitated transportation/fulfillment MILP using inventory available.
8. Repeats the loop for 13 historical weeks and exports detailed replenishment, flow, shortage, inventory, regional-service, capacity, and cost decisions.
9. Stress-tests safety stock, replenishment lead time, shortage cost, service target, capacity, and risk weights.

The modeling window contains 86 complete Monday-starting weeks from 2017-01-02 through 2018-08-20. The incomplete week beginning 2018-08-27 is excluded.

## Main findings

- Ridge produces the lowest one-week WAPE: **30.94%**, compared with 34.12% for moving average and 34.74% for last week.
- Across 50 category-region segments, Ridge has the best one-week WAPE in 26, moving average in 23, and last week in 1.
- The Ridge-driven policy has the lowest base simulated cost: **996,695.41**, with a **94.01%** fill rate.
- Moving average reaches a slightly higher 94.26% fill rate but uses more replenishment and ends with more inventory.
- Zero safety buffer lowers fill rate to 86.03%; one full error-scale buffer raises it to 98.82% under the current cost assumptions.
- A two-week replenishment lead time raises shortage to 1,187 units and cost to 1,091,625.68.
- Capacity at 80% or 120% of the base multiplier does not change the solution, showing that tested weight throughput is not the binding constraint.
- The North and Northeast have the weakest Ridge regional fill rates, showing that the soft service constraint must be interpreted together with its penalized slack.

## Important interpretation boundary

Olist does not provide actual warehouse locations, historical inventory, procurement contracts, or replenishment decisions. Demand, seller and customer geography, price, freight, timing, and smoothed historical service risk are observed or estimated from Olist. The six proxy hubs, opening inventory, capacities, procurement costs, replenishment lead time, and cost penalties are documented scenario assumptions.

The approval-to-carrier measure is a historical fulfillment proxy, not Olist's procurement lead time. Total costs are simulated BRL-equivalent planning outcomes, not actual Olist financial results.

## Repository structure

```text
.
├── docs/                 # Final proposal
├── outputs/
│   ├── data/             # Balanced panel and auditable network parameters
│   ├── figures/          # Demand, forecast, risk, policy, and sensitivity figures
│   ├── tables/           # Aggregate and detailed model outputs
│   └── RESULTS_SUMMARY.md
├── src/                  # Analysis, forecasting, optimization, validation, and reporting code
├── site/                 # Interactive results and sensitivity MVP
├── DATA_DICTIONARY.md
├── MODEL.md
├── PROJECT_STATUS.md
├── requirements.txt
├── setup_project.command
└── run_project.command
```

## Data setup

Download the Brazilian E-Commerce Public Dataset by Olist separately. Raw CSV files are intentionally not stored in this repository.

Required files:

- `olist_orders_dataset.csv`
- `olist_order_items_dataset.csv`
- `olist_products_dataset.csv`
- `product_category_name_translation.csv`
- `olist_customers_dataset.csv`
- `olist_sellers_dataset.csv`

The code can locate data by:

1. passing `--data-dir /path/to/olist/csvs`;
2. setting `OLIST_DATA_DIR`;
3. placing files in a sibling `archive` directory or `data/raw` inside the project.

Payments, reviews, and geolocation are not used in the core model.

## Run

On macOS, run `setup_project.command` once and then `run_project.command`.

From a terminal:

```bash
python -m src.run_all --data-dir /path/to/olist/csvs
```

For a quick validation without sensitivity experiments:

```bash
python -m src.run_all --data-dir /path/to/olist/csvs --quick
```

Dependencies are listed in `requirements.txt`. Optimization uses PuLP with the bundled CBC solver.

## Main auditable outputs

### Data insights

- `outputs/tables/demand_segment_summary.csv`
- `outputs/tables/fulfillment_risk_ranking.csv`
- `outputs/tables/forecast_segment_metrics.csv`
- `outputs/tables/regional_service_summary.csv`

### Forecast and policy results

- `outputs/tables/forecast_predictions.csv`
- `outputs/tables/forecast_metrics.csv`
- `outputs/tables/weekly_policy_results.csv`
- `outputs/tables/policy_summary.csv`

### Detailed OR decisions

- `outputs/tables/replenishment_decisions.csv`
- `outputs/tables/planned_fulfillment_flows.csv`
- `outputs/tables/planned_inventory.csv`
- `outputs/tables/planned_shortages.csv`
- `outputs/tables/actual_shortages.csv`
- `outputs/tables/inventory_positions.csv`
- `outputs/tables/capacity_utilization.csv`
- `outputs/tables/regional_service_results.csv`

Parameter sources and rationales are recorded in `outputs/data/network/metadata.csv`. The current run passes all automated validation checks, including forecast chronology, decision reconciliation, capacity feasibility, inventory balance, cost accounting, solver status, regional-service reconciliation, and sensitivity completeness.
