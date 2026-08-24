# Data Dictionary

## Raw Olist files used directly

- `olist_orders_dataset.csv`: order status and purchase/approval/carrier/customer/promise timestamps.
- `olist_order_items_dataset.csv`: product, seller, price, freight, shipping limit.
- `olist_products_dataset.csv`: product category, weight, and dimensions.
- `product_category_name_translation.csv`: Portuguese-to-English category names.
- `olist_customers_dataset.csv`: destination state used to construct five macro-regions.
- `olist_sellers_dataset.csv`: seller state used as a supply-location and scenario-hub proxy.

Payments, reviews, and geolocation are not needed for the core forecast-inventory question. They remain available for extensions.

## Main derived fields

- `purchase_week`: Monday of the order-purchase week.
- `customer_region`: North, Northeast, Central-West, Southeast, or South.
- `category`: translated English product category.
- `demand`: count of item lines in a category-region-week.
- `late_dispatch`: carrier handoff after the item shipping-limit timestamp.
- `late_delivery`: customer delivery after the promised date.
- `approval_to_carrier_days`: historical operational lead-time proxy.

## Analysis and forecast outputs

- `demand_segment_summary.csv`: 50 category-region segments with total demand, demand share, weekly mean, standard deviation, coefficient of variation, zero-week share, peak, and trend slope.
- `forecast_segment_metrics.csv`: one-week MAE, WAPE, bias, rank, and best-method flag for every category-region-method combination.
- `fulfillment_risk_ranking.csv`: route sample size, raw delay rates, smoothed delivery and supplier risk, median freight, evidence level, and expected risk cost per unit.
- `forecast_predictions.csv`: forecast, actual demand when available, eight-week chronological error scale, selected Ridge alpha, and base safety-adjusted planning demand.

## Detailed OR decision outputs

- `replenishment_decisions.csv`: planned replenishment by origin, target week, horizon, hub, and category.
- `planned_fulfillment_flows.csv`: nonzero planned hub-category-region flows.
- `planned_inventory.csv`: projected ending inventory by hub, category, and horizon.
- `planned_shortages.csv`: planned shortage by category, region, and horizon.
- `actual_shortages.csv`: realized category-region shortages.
- `inventory_positions.csv`: realized ending inventory by hub and category.
- `capacity_utilization.csv`: used and available hub weight capacity.
- `regional_service_results.csv`: weekly regional demand, fulfillment, shortage, fill rate, and risk exposure.
- `regional_service_summary.csv`: 13-week regional results by forecast policy.

## Observed versus assumed

Observed or estimated from Olist:

- weekly demand;
- seller and customer geography;
- freight values;
- price and product weight;
- late-dispatch and late-delivery rates;
- approval-to-carrier time.

Scenario assumptions:

- seller-state proxy hubs;
- opening inventory and replenishment capacity;
- procurement and holding-cost relationships;
- one-week base replenishment lead time;
- 90% service target;
- shortage and risk penalty values.

Every network and scenario parameter is recorded with its source and rationale in `outputs/data/network/metadata.csv`.
