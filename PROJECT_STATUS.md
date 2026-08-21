# Project status

## Implemented scope

The project now runs as a two-stage weekly decision cycle:

1. Use only historical weeks to predict four weeks of category-region demand.
2. Convert the point forecast into planning demand with a past-error safety buffer.
3. Solve a four-week inventory planning MILP and implement only the first replenishment decision.
4. Reveal actual demand and solve a reactive fulfillment MILP with the inventory available.
5. Update inventory and repeat for 13 historical weeks.

This design is deliberately smaller than SKU-level stochastic optimization, but it still answers the main research question with a reproducible predict-then-optimize experiment.

## Verified data scope

- 112,643 valid primary-status order-item lines.
- 86 complete Monday-starting weeks from 2017-01-02 to 2018-08-20.
- 50 series: 10 largest translated categories x 5 destination regions.
- 4,300 balanced category-region-week rows, including zero-demand weeks.
- 63.6% of valid units covered by the selected categories.

The incomplete week beginning 2018-08-27 is excluded because it contains only two observed purchase days.

## Current pilot results

- One-week Ridge WAPE: 31.3%.
- One-week four-week-mean WAPE: 34.1%.
- One-week last-week WAPE: 34.7%.
- Under the common base assumptions, the Ridge-driven policy has the lowest simulated total cost and a 92.9% fill rate.
- A safety multiplier of 1.0 raises the simulated fill rate to 97.4% and lowers cost under the current shortage penalties, so this parameter should be selected by backtest rather than fixed in advance.

These cost results are scenario results. Olist contains no warehouse, opening-inventory, procurement-contract, or historical replenishment records.

## Verification

The full run completed in under one minute on the available machine. All 14 automated checks passed, including balanced-panel construction, nonnegative and integer demand, forecast completeness, demand and cost accounting, nonnegative inventory, fill-rate bounds, optimal CBC solver status, and summary reconciliation.

