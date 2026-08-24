# Mathematical Model and Implementation Logic

## 1. Research design

The project is a reproducible **describe → forecast → plan → fulfill → update** experiment. It first identifies demand concentration, volatility, and historical fulfillment risk; then compares forecasting policies; finally it evaluates the downstream inventory and service consequences under the same Operations Research environment.

The operational loop has two deterministic decision stages each week. It is not claimed to be a formal two-stage stochastic program.

## 2. Demand forecast and chronological uncertainty

Let `D[k,r,t]` be observed item-line demand for category `k`, customer region `r`, and week `t`. The project compares:

1. last-week demand;
2. a recursive four-week moving average;
3. a pooled Ridge regression across all 50 category-region series.

Ridge features are lags 1, 2, 4, and 8; rolling means 4 and 8; trend and annual sine/cosine terms; and category and region indicators. Coefficients minimize:

`sum(D - beta0 - z'beta)^2 + alpha ||beta||^2`.

At every forecast origin, `alpha` is selected from `{1, 5, 25, 100}` using an eight-week chronological holdout containing only earlier observations. All three methods use that same recent holdout logic to estimate category-region forecast-error scale. This replaces the earlier inconsistent comparison between Ridge in-sample residuals and baseline rolling errors.

The nonnegative recursive forecast is:

`D_hat[k,r,t+h] = max(0, beta0* + z[k,r,t,h]' beta*)`, for `h = 1,...,4`.

Planning demand includes a policy safety buffer:

`D_tilde[k,r,t] = ceil(max(0, D_hat[k,r,t] + safety_z * error_scale[k,r,t]))`.

The base policy uses `safety_z = 0.50`; zero and one-full-error-scale alternatives are tested.

## 3. Data-derived risk and planning parameters

The six scenario hubs are the largest retained seller states by selected-category volume: SP, PR, MG, RJ, SC, and RS. Historical median freight and smoothed late-delivery rates are estimated for each hub-category-region route. Seller late-dispatch risk is estimated for each hub-category pair.

For a group `g`, the smoothed rate is:

`p_hat[g] = (late_count[g] + prior_strength * global_rate) / (sample_count[g] + prior_strength)`.

This is described as a smoothed historical risk estimate, not as an individual-order machine-learning prediction. Approval-to-carrier time is a fulfillment proxy; Olist does not reveal procurement lead time.

Scenario parameters and their rationales are recorded in `outputs/data/network/metadata.csv`. Capacity, service target, lead time, shortage penalty, safety multiplier, and risk weights are stress-tested.

## 4. Stage A: multi-period inventory and replenishment MILP

Indices:

- `i`: six scenario hubs;
- `k`: ten product categories;
- `r`: five customer regions;
- `t`: four planning weeks.

Decision variables:

- `q[i,k,t]`: replenishment ordered;
- `x_plan[i,k,r,t]`: planned fulfillment flow;
- `I[i,k,t]`: ending inventory;
- `u[k,r,t]`: planned shortage;
- `g[r,t]`: soft regional service-target gap.

The objective minimizes procurement, risk-adjusted route cost, holding cost, shortage cost, and service-gap penalties:

`min sum(p[i,k] q[i,k,t])`

`  + sum((ship[i,k,r] + late_penalty * late_prob[i,k,r] + supplier_penalty * supplier_risk[i,k]) x_plan[i,k,r,t])`

`  + sum(h[i,k] I[i,k,t]) + sum(shortage_cost[k] u[k,r,t]) + sum(service_penalty g[r,t])`.

Core constraints are:

1. Inventory balance with current stock, known pipeline, and decision arrivals after scenario lead time:

   `I[i,k,t] = prior_inventory + known_arrival + q[i,k,t-L] - sum_r x_plan[i,k,r,t]`.

2. Planning-demand accounting:

   `sum_i x_plan[i,k,r,t] + u[k,r,t] = D_tilde[k,r,t]`.

3. Hub throughput capacity:

   `sum_k sum_r weight[k] x_plan[i,k,r,t] <= capacity[i]`.

4. Replenishment capacity:

   `q[i,k,t] <= replenishment_capacity[i,k]`.

5. Regional service target with penalized slack:

   `sum_i sum_k x_plan[i,k,r,t] + g[r,t] >= service_target * sum_k D_tilde[k,r,t]`.

6. Nonnegative integer quantities, with continuous service-gap slack.

Only the first week's replenishment orders are implemented. Planned flows are not treated as shipments before real orders exist.

## 5. Stage B: capacitated transportation and fulfillment MILP

After the week's actual Olist demand is revealed, a second model allocates inventory actually available. Decision variables are actual hub-category-region flows, category-region shortages, and regional service gaps.

Constraints are:

1. actual demand balance;
2. inventory availability by hub and category;
3. hub weight-throughput capacity;
4. regional service target with penalized slack;
5. nonnegative integer unit flows.

The model minimizes median freight, expected late-delivery and seller-risk penalties, shortage cost, and service-gap cost. Procurement and holding costs are added to the realized weekly accounting after the solve.

This stage produces auditable flow, shortage, regional service, capacity-utilization, and ending-inventory tables.

## 6. Rolling historical evaluation

The final 13 complete weeks are evaluated as sequential forecast origins. For each week and each policy:

1. receive pipeline inventory due that week;
2. estimate the forecast using only previous weeks;
3. convert forecast and historical holdout error into planning demand;
4. solve the four-week inventory MILP;
5. implement only first-week replenishment;
6. reveal actual demand;
7. solve the realized fulfillment MILP;
8. update inventory and carry state into the next week.

The Last Week + OR, Moving Average + OR, and Ridge + OR policies use identical actual demand, network, cost, capacity, and service assumptions.

## 7. Sensitivity design

The Ridge policy is rerun under:

- safety multipliers 0 and 1;
- two-week replenishment lead time;
- low and high shortage penalties;
- regional service targets of 85% and 95%;
- capacity at 80% and 120% of the base multiplier;
- zero and doubled fulfillment-risk weights.

These scenarios show whether conclusions are driven by one arbitrary parameter choice. The current results indicate that capacity is not binding in the tested range, while safety stock and replenishment lead time materially change service and cost.

## 8. Scope boundaries

- Category-region forecasting replaces SKU forecasting because 85.3% of products have fewer than five retained observations.
- Deterministic rolling planning plus a chronological error buffer replaces stochastic programming.
- Smoothed historical risk rates replace a separate late-delivery classifier for transparency and feasibility.
- CBC is sufficient for the implemented model sizes.
- Total costs are simulated BRL-equivalent planning outcomes, not Olist financial accounts.
- The project does not reconstruct Olist's real warehouse network and does not use vehicle routing.
