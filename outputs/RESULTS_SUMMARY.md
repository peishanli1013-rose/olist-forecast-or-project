# Olist Forecast-Driven OR Project: Results Summary

## Data foundation

- Valid primary-status item lines: 112,643
- Stable window: 2017-01-02 to 2018-08-20 (86 weeks)
- Balanced panel: 50 category-region series and 4,300 rows
- Selected-category coverage: 63.6%
- Products appearing once: 54.9%

## Forecast comparison

| method | horizon | observations | MAE | WAPE | bias |
| --- | --- | --- | --- | --- | --- |
| ridge | 1.0000 | 650.0000 | 6.8657 | 0.3128 | -0.1230 |
| moving_average | 1.0000 | 650.0000 | 7.4885 | 0.3412 | -0.0338 |
| last_week | 1.0000 | 650.0000 | 7.6262 | 0.3474 | -0.0292 |

## Base rolling-backtest comparison

| policy | total_cost | fill_rate | shortage_units | ending_inventory | expected_late_units |
| --- | --- | --- | --- | --- | --- |
| ridge | 1022508.9472 | 0.9291 | 1011.0000 | 878.0000 | 1021.7125 |
| moving_average | 1025257.5471 | 0.9361 | 912.0000 | 1033.0000 | 1033.8214 |
| last_week | 1063669.5418 | 0.9220 | 1113.0000 | 1241.0000 | 1015.8925 |

The lowest simulated total cost in the base assumptions is produced by **ridge**, with a fill rate of 92.9%.

## Sensitivity tests for the Ridge policy

| scenario | total_cost | fill_rate | shortage_units | ending_inventory |
| --- | --- | --- | --- | --- |
| lead_time_2 | 1115426.2162 | 0.9076 | 1318.0000 | 779.0000 |
| safety_0 | 1177948.0495 | 0.8536 | 2088.0000 | 592.0000 |
| safety_1 | 964177.5915 | 0.9737 | 375.0000 | 1230.0000 |
| shortage_high | 1103969.4603 | 0.9291 | 1011.0000 | 878.0000 |
| shortage_low | 973725.1958 | 0.9289 | 1014.0000 | 864.0000 |

## Interpretation boundary

Demand, timing, geography, freight, and historical service risk are estimated from Olist. Warehouses, opening inventory, capacities, procurement costs, and replenishment rules are transparent planning scenarios, not Olist's actual network.