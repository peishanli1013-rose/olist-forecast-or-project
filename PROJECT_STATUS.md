# Project status

## Implemented scope

The project now runs as a two-stage weekly decision cycle:

1. Use only historical weeks to predict four weeks of category-region demand.
2. Use a common eight-week chronological holdout to estimate uncertainty for all methods, and select Ridge alpha from a past-only grid.
3. Convert the point forecast into planning demand with a past-error safety buffer.
4. Solve a four-week inventory planning MILP and implement only the first replenishment decision.
5. Reveal actual demand and solve a reactive fulfillment MILP with the inventory available.
6. Update inventory and repeat for 13 historical weeks.

This design is deliberately smaller than SKU-level stochastic optimization, but it still answers the main research question with a reproducible predict-then-optimize experiment.

## Verified data scope

- 112,643 valid primary-status order-item lines.
- 86 complete Monday-starting weeks from 2017-01-02 to 2018-08-20.
- 50 series: 10 largest translated categories x 5 destination regions.
- 4,300 balanced category-region-week rows, including zero-demand weeks.
- 63.6% of valid units covered by the selected categories.

The incomplete week beginning 2018-08-27 is excluded because it contains only two observed purchase days.

## Current full-run results

- One-week Ridge WAPE: 30.9%.
- One-week four-week-mean WAPE: 34.1%.
- One-week last-week WAPE: 34.7%.
- Ridge is best in 26 of the 50 category-region segments by one-week WAPE; moving average is best in 23 and last week in 1.
- Under common base assumptions, Ridge has the lowest simulated total cost (996,695.41) and a 94.0% fill rate.
- A safety multiplier of 1.0 raises the simulated fill rate to 98.8% and lowers cost under current shortage and service penalties.
- A two-week replenishment lead time raises shortage to 1,187 units and cost to 1,091,625.68.
- Capacity at 80% and 120% of the base multiplier does not change the solution, so tested weight throughput is not binding.
- North and Northeast have the lowest regional fill rates under Ridge, which makes the soft service-gap interpretation operationally important.

These cost results are scenario results. Olist contains no warehouse, opening-inventory, procurement-contract, or historical replenishment records.

## Verification

The upgraded full run completed in about 105 seconds on the available machine. All automated checks passed, including balanced-panel construction, chronological uncertainty, nonnegative and integer planning demand, forecast and risk-table completeness, regional reconciliation, detailed replenishment/shortage/inventory reconciliation, capacity feasibility, nonnegative solver time, sensitivity completeness, optimal CBC status, and cost reconciliation.
