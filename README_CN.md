# 基于 Olist 数据的需求预测、库存与履约优化

[English README](README.md)

本项目基于巴西 Olist 电商公开数据，构建了可复现的 **描述分析 → 需求预测 → 库存计划 → 实际履约 → 滚动更新** 实验。研究重点不是单纯求解一个数学模型，而是先从历史订单中发现需求和履约风险规律，再检验这些信息能否改善后续库存与履约决策。

## 交互式结果网站（MVP）

在线访问：[Olist OR Lab](https://olist-forecast-or-lab.peishanli1013.chatgpt.site)

[`site/`](site/) 提供完整源码。网站包含 Overview、Demand、Forecast、Optimization 和 Sensitivity 五个模块。敏感性页面现在提供两种模式：**Verified Runs** 精确展示已经求解的单因素 MILP 情景；**Live What-if** 允许同时调整安全缓冲、提前期、服务目标、容量、风险权重和缺货价值，并即时更新结果。组合情景采用由已求解锚点校准的分段线性加总估算，页面会明确标注为 estimate；只有参数与已求解情景完全一致时才显示 solver-verified。

本地启动网站：

```bash
cd site
npm install
npm run dev
```

然后在浏览器打开 `http://localhost:3000`。使用 `npm test` 可重新检查正式构建、首页内容和分享元数据。

## 核心研究问题

1. 不同商品品类、客户地区和卖家路线的需求规律与历史履约风险有何差异？
2. Pooled Ridge 是否优于简单预测基准，并且在哪些品类—地区组合中更有效？
3. 预测驱动的补货和履约决策能否在维持地区服务水平的同时降低模拟成本？

## 项目流程

1. 合并订单、订单商品、商品、品类翻译、客户和卖家数据。
2. 构建 10 个主要品类 × 5 个巴西地区的 50 条零需求周完整序列。
3. 分析需求集中度、波动、稀疏程度、趋势和路线履约风险。
4. 使用时间顺序验证比较上一周、四周移动平均和 pooled Ridge。
5. 使用过去八周留出误差统一估计三种方法的不确定性，并在每个预测起点从 `{1, 5, 25, 100}` 中选择 Ridge 正则化强度。
6. 将预测和历史误差输入四周多期库存补货 MILP。
7. 实际需求出现后，求解带库存和仓库容量约束的运输／履约 MILP。
8. 进行 13 周滚动历史回测，导出补货、计划流量、实际履约、缺货、库存、地区服务和容量利用率。
9. 对安全库存、补货提前期、缺货成本、服务目标、仓库容量和风险权重进行敏感性分析。

研究窗口为 2017-01-02 至 2018-08-20，共 86 个完整周；不完整的 2018-08-27 周被排除。

## 主要结果

- Ridge 的一步 WAPE 为 **30.94%**，优于移动平均的 34.12% 和上一周方法的 34.74%。
- 在 50 个品类—地区序列中，Ridge 在 26 个序列中取得最佳一步 WAPE，移动平均为 23 个，上一周方法为 1 个。
- Ridge 策略的基准模拟成本最低，为 **996,695.41**，履约率为 **94.01%**。
- 移动平均履约率略高，为 94.26%，但补货更多、期末库存更高。
- 不使用安全缓冲时履约率下降至 86.03%；使用一个完整误差尺度时履约率提高至 98.82%。
- 补货提前期从一周增加到两周后，缺货上升至 1,187 件，总成本上升至 1,091,625.68。
- 仓库重量容量上下调整 20% 没有改变解，说明该容量在当前情景中不是主要瓶颈。
- North 和 Northeast 的地区履约率最低，说明最低服务约束中的惩罚松弛变量需要与地区结果共同解释。

## 数据来源与边界

实际使用六个 Olist 文件：

- `olist_orders_dataset.csv`
- `olist_order_items_dataset.csv`
- `olist_products_dataset.csv`
- `product_category_name_translation.csv`
- `olist_customers_dataset.csv`
- `olist_sellers_dataset.csv`

Payments、reviews 和 geolocation 未用于核心模型。

Olist 没有提供真实仓库、历史库存、采购合同和实际补货决策。需求、卖家和客户地理位置、价格、运费、交付时间以及平滑历史履约风险来自 Olist；六个代理履约中心、初始库存、仓库容量、采购成本、补货提前期和成本惩罚是透明的研究情景。

订单批准到卖家交给承运商的时间只被解释为历史履约时间代理变量，不被表述为 Olist 的采购提前期。模型总成本是基于 Olist 价格与运费尺度构造的模拟成本，不是 Olist 的真实财务支出。

## 运行方法

原始 CSV 不上传 GitHub。可以通过以下任一方式指定数据：

1. 运行时传入 `--data-dir /path/to/olist/csvs`；
2. 设置 `OLIST_DATA_DIR`；
3. 将数据放在项目同级 `archive` 或项目内 `data/raw`。

运行完整项目：

```bash
python -m src.run_all --data-dir /path/to/olist/csvs
```

跳过敏感性分析的快速验证：

```bash
python -m src.run_all --data-dir /path/to/olist/csvs --quick
```

macOS 也可以先运行一次 `setup_project.command`，之后运行 `run_project.command`。

## 关键结果文件

### 数据挖掘

- `outputs/tables/demand_segment_summary.csv`：需求规模、波动、零需求率和趋势。
- `outputs/tables/fulfillment_risk_ranking.csv`：路线样本量、运费、延迟率和风险成本。
- `outputs/tables/forecast_segment_metrics.csv`：50 个细分序列的预测表现。
- `outputs/tables/regional_service_summary.csv`：地区需求、缺货、履约率和延迟风险。

### 预测与策略结果

- `outputs/tables/forecast_predictions.csv`
- `outputs/tables/forecast_metrics.csv`
- `outputs/tables/weekly_policy_results.csv`
- `outputs/tables/policy_summary.csv`

### OR 详细决策

- `outputs/tables/replenishment_decisions.csv`
- `outputs/tables/planned_fulfillment_flows.csv`
- `outputs/tables/planned_inventory.csv`
- `outputs/tables/planned_shortages.csv`
- `outputs/tables/actual_shortages.csv`
- `outputs/tables/inventory_positions.csv`
- `outputs/tables/capacity_utilization.csv`
- `outputs/tables/regional_service_results.csv`

所有参数的来源和选择理由记录在 `outputs/data/network/metadata.csv`。当前完整运行已经通过预测时间顺序、需求与成本核算、库存平衡、容量可行性、地区服务汇总、详细决策对账、求解状态和敏感性情景完整性检查。

最终 proposal 位于 [`docs/Olist_Forecast_OR_Project_Proposal.docx`](docs/Olist_Forecast_OR_Project_Proposal.docx)。
