# Olist Forecast-Driven OR Project: Results Summary

## Data foundation

- Valid primary-status item lines: 112,643
- Stable window: 2017-01-02 to 2018-08-20 (86 weeks)
- Balanced panel: 50 category-region series and 4,300 rows
- Selected-category coverage: 63.6%
- Products appearing once: 54.9%

## Data-derived demand insights

The following category-region segments account for the largest observed demand in the retained panel:

| category | region | total_demand | demand_share | coefficient_of_variation | zero_week_share |
| --- | --- | --- | --- | --- | --- |
| bed_bath_table | Southeast | 8420.0000 | 0.1180 | 0.5338 | 0.0000 |
| health_beauty | Southeast | 6468.0000 | 0.0906 | 0.6178 | 0.0000 |
| sports_leisure | Southeast | 5824.0000 | 0.0816 | 0.4900 | 0.0116 |
| furniture_decor | Southeast | 5675.0000 | 0.0795 | 0.5113 | 0.0000 |
| computers_accessories | Southeast | 5305.0000 | 0.0743 | 0.6924 | 0.0116 |
| housewares | Southeast | 5063.0000 | 0.0709 | 0.5742 | 0.0116 |
| watches_gifts | Southeast | 3936.0000 | 0.0552 | 0.7063 | 0.0000 |
| garden_tools | Southeast | 2921.0000 | 0.0409 | 0.6747 | 0.0116 |

## Forecast comparison

| method | horizon | observations | MAE | WAPE | bias |
| --- | --- | --- | --- | --- | --- |
| ridge | 1.0000 | 650.0000 | 6.7901 | 0.3094 | -0.0692 |
| moving_average | 1.0000 | 650.0000 | 7.4885 | 0.3412 | -0.0338 |
| last_week | 1.0000 | 650.0000 | 7.6262 | 0.3474 | -0.0292 |

The count below shows how often each method attains the lowest one-week WAPE across the 50 category-region segments (ties are retained):

| method | best_segment_count |
| --- | --- |
| ridge | 26.0000 |
| moving_average | 23.0000 |
| last_week | 1.0000 |

All three methods use an eight-week chronological holdout to estimate forecast-error scale. Ridge alpha is selected from {1, 5, 25, 100} at each forecast origin using only prior observations.

## Historical fulfillment-risk insights

Routes below have at least 30 observations and the highest smoothed expected risk penalty per fulfilled unit:

| hub | category | region | sample_size | late_probability | supplier_risk | shipping_cost | expected_risk_cost_per_unit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PR | bed_bath_table | Southeast | 73.0000 | 0.2291 | 0.3510 | 23.8500 | 3.5879 |
| PR | bed_bath_table | South | 35.0000 | 0.1004 | 0.3510 | 18.8300 | 2.5582 |
| PR | computers_accessories | Northeast | 44.0000 | 0.1644 | 0.1773 | 42.9200 | 2.2022 |
| MG | telephony | Southeast | 35.0000 | 0.1569 | 0.1718 | 15.1000 | 2.1141 |
| RJ | watches_gifts | Northeast | 89.0000 | 0.1639 | 0.1588 | 23.6300 | 2.1050 |
| PR | furniture_decor | Northeast | 87.0000 | 0.1902 | 0.1018 | 34.1500 | 2.0309 |
| MG | furniture_decor | Northeast | 57.0000 | 0.1612 | 0.1475 | 24.5500 | 2.0269 |
| SP | garden_tools | Northeast | 307.0000 | 0.1775 | 0.0930 | 28.7900 | 1.8851 |

## Base rolling-backtest comparison

| policy | total_cost | fill_rate | shortage_units | ending_inventory | expected_late_units |
| --- | --- | --- | --- | --- | --- |
| ridge | 996695.4079 | 0.9401 | 855.0000 | 824.0000 | 1038.0716 |
| moving_average | 1019523.2481 | 0.9426 | 819.0000 | 1018.0000 | 1042.5029 |
| last_week | 1035993.1714 | 0.9331 | 954.0000 | 1241.0000 | 1032.4587 |

The lowest simulated total cost in the base assumptions is produced by **ridge**, with a fill rate of 94.0%.

## Regional service under the Ridge policy

| region | demand_units | fulfilled_units | shortage_units | fill_rate | expected_late_units |
| --- | --- | --- | --- | --- | --- |
| North | 243.0000 | 165.0000 | 78.0000 | 0.6790 | 17.0674 |
| Northeast | 1248.0000 | 1076.0000 | 172.0000 | 0.8622 | 108.2176 |
| Central-West | 818.0000 | 755.0000 | 63.0000 | 0.9230 | 60.5457 |
| South | 1915.0000 | 1786.0000 | 129.0000 | 0.9326 | 100.7240 |
| Southeast | 10043.0000 | 9630.0000 | 413.0000 | 0.9589 | 751.5167 |

## Sensitivity tests for the Ridge policy

| scenario | total_cost | fill_rate | shortage_units | ending_inventory |
| --- | --- | --- | --- | --- |
| capacity_120 | 996695.4079 | 0.9401 | 855.0000 | 824.0000 |
| capacity_80 | 996695.4079 | 0.9401 | 855.0000 | 824.0000 |
| lead_time_2 | 1091625.6786 | 0.9168 | 1187.0000 | 708.0000 |
| risk_0 | 982120.5240 | 0.9404 | 851.0000 | 824.0000 |
| risk_2x | 1011040.6579 | 0.9399 | 857.0000 | 824.0000 |
| safety_0 | 1164917.2853 | 0.8603 | 1993.0000 | 541.0000 |
| safety_1 | 954750.8189 | 0.9882 | 168.0000 | 1195.0000 |
| service_85 | 974563.9906 | 0.9401 | 855.0000 | 824.0000 |
| service_95 | 1038865.0690 | 0.9401 | 855.0000 | 824.0000 |
| shortage_high | 1060825.5180 | 0.9401 | 855.0000 | 824.0000 |
| shortage_low | 958239.3722 | 0.9400 | 856.0000 | 816.0000 |

## Interpretation boundary

Demand, timing, geography, freight, and smoothed historical service risk are estimated from Olist. Warehouses, opening inventory, capacities, procurement costs, replenishment lead time, and replenishment rules are transparent planning scenarios, not Olist's actual network. The approval-to-carrier measure is a historical fulfillment proxy and is not presented as Olist's procurement lead time.