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

