# Mathematical Model and Implementation Logic

## 1. Demand forecast

Let `D[k,r,t]` be observed units for category `k`, customer region `r`, and week `t`. The pooled Ridge model uses lags 1, 2, 4, and 8; rolling means 4 and 8; trend and calendar terms; and category/region indicators.

The estimated coefficients minimize squared error plus an L2 penalty:

`beta* = argmin sum(D - beta0 - z'beta)^2 + lambda ||beta||^2`.

The nonnegative four-week forecast is:

`D_hat[k,r,t+h] = max(0, beta0* + z[k,r,t,h]' beta*)`, for `h = 1,...,4`.

Planning demand includes an empirical safety buffer based only on past forecast errors:

`D_tilde[k,r,t] = ceil(max(0, D_hat[k,r,t] + safety_z * error_scale[k,r,t]))`.

## 2. Stage A: inventory and replenishment planning

Indices:

- `i`: six scenario hubs, represented by the largest seller states.
- `k`: ten product categories.
- `r`: five Brazilian regions.
- `t`: four planning weeks.

Decision variables:

- `q[i,k,t]`: replenishment ordered.
- `x_plan[i,k,r,t]`: planned fulfillment flow.
- `I[i,k,t]`: ending inventory.
- `u[k,r,t]`: planned shortage.
- `g[r,t]`: soft service-target gap.

The planning model minimizes procurement, risk-adjusted shipping, inventory holding, shortage, and service-gap penalties.

Core constraints are:

1. Inventory balance, including known pipeline arrivals and scenario lead time.
2. Planned demand balance: every unit is fulfilled or counted as shortage.
3. Hub throughput capacity using product weight.
4. Replenishment capacity by hub and category.
5. Minimum regional service level with a penalized slack variable.
6. Nonnegative integer quantities.

Only the first week's replenishment orders are implemented. Planned fulfillment is not treated as a shipment before an order exists.

## 3. Stage B: reactive fulfillment after demand is observed

When the week's actual Olist demand is revealed, a second transportation model assigns the inventory actually available to customer regions. It minimizes shipping cost, expected lateness/supplier-risk cost, shortage cost, and service-gap cost subject to inventory and hub-capacity limits.

This stage produces realized shipments, shortages, fill rate, ending inventory, and cost. Inventory then becomes the opening state for the next week.

## 4. Why two stages are used

Forecasts should influence what must be decided before demand is known: replenishment and inventory positioning. Actual fulfillment should react to orders after they appear. The two-stage weekly loop is more defensible than shipping the forecast quantity in advance and is still straightforward traditional OR.

## 5. Scope decisions made for feasibility

- Category-region forecasting replaces full-SKU forecasting because the Olist product tail is sparse.
- A deterministic rolling model plus empirical safety buffer replaces stochastic programming.
- Smoothed historical risk rates replace a separate machine-learning lateness model.
- CBC replaces HiGHS because CBC is already available and sufficient for this model size.
- Oracle policy is omitted from the core comparison because later four-week actual demand is unavailable for the final origins and the three operational policies answer the main question.

