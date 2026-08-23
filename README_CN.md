# 基于 Olist 数据的需求预测、库存与履约优化

[English README](README.md)

本项目使用巴西 Olist 电商公开数据，构建了一个可复现的 **需求预测 → 库存计划 → 履约分配 → 滚动更新** 实验框架。项目不仅比较预测模型的统计精度，还研究不同预测方法如何影响后续的库存成本、缺货、履约率和配送风险。

## 研究目标

本项目希望回答：需求预测及其误差信息能否改善电商企业的库存补货与履约分配决策？为此，我们在相同的运筹优化模型和成本假设下比较多种预测策略，并同时评价预测准确性和实际运营表现。

## 项目主要内容

1. 合并订单、订单明细、商品、品类翻译、客户和卖家数据。
2. 构建包含零需求周的 50 条周度需求序列：10 个商品品类 × 5 个巴西地区。
3. 使用时间顺序验证比较上一周预测、四周移动平均和 pooled Ridge 模型。
4. 根据历史订单估计卖家延迟发货风险、配送延迟风险以及订单批准到承运商接收的提前期代理变量。
5. 将需求预测和历史预测误差输入六个模拟履约中心的库存补货与配置模型。
6. 在实际需求揭示后，使用可用库存求解带容量约束的履约分配模型。
7. 进行 13 周滚动历史回测，比较总成本、履约率、缺货量、期末库存和预期延迟量。

建模窗口包含从 2017-01-02 到 2018-08-20 的 86 个完整周。由于 2018-08-27 开始的一周数据不完整，因此未纳入建模。

## 重要说明

Olist 数据没有提供真实仓库位置、历史库存、采购合同或企业实际补货决策。需求、卖家和客户地理位置、运费及服务时间来自原始数据；六个代理履约中心、初始库存、仓库容量、采购成本和补货规则属于透明记录的情景假设，并通过敏感性分析检验。因此，本项目不声称重建 Olist 的真实仓储网络。

## 仓库结构

```text
.
├── docs/                 # 最终项目 proposal
├── outputs/
│   ├── data/             # 派生数据和履约网络参数
│   ├── figures/          # 可用于展示的结果图
│   ├── tables/           # 预测、回测和优化结果
│   └── RESULTS_SUMMARY.md
├── src/                  # 数据、预测、优化、验证和报告代码
├── DATA_DICTIONARY.md
├── MODEL.md
├── PROJECT_STATUS.md
├── requirements.txt
├── setup_project.command
└── run_project.command
```

## 原始数据准备

请单独下载 Brazilian E-Commerce Public Dataset by Olist。为了控制仓库大小，原始 CSV 文件不上传至本仓库。

需要以下文件：

- `olist_orders_dataset.csv`
- `olist_order_items_dataset.csv`
- `olist_products_dataset.csv`
- `product_category_name_translation.csv`
- `olist_customers_dataset.csv`
- `olist_sellers_dataset.csv`

程序可以通过以下任一方式定位数据：

1. 运行时传入 `--data-dir /path/to/olist/csvs`。
2. 设置环境变量 `OLIST_DATA_DIR`。
3. 将数据放在项目同级的 `archive` 或 `data` 文件夹。

## 运行方法

macOS 用户可以先运行一次 `setup_project.command` 创建 Python 环境，再运行 `run_project.command` 重新生成结果。

也可以在项目根目录运行：

```bash
python -m src.run_all --data-dir /path/to/olist/csvs
```

快速验证模式（跳过敏感性分析）：

```bash
python -m src.run_all --data-dir /path/to/olist/csvs --quick
```

依赖包记录在 `requirements.txt` 中，运筹优化使用 PuLP 自带的 CBC 求解器。

## 主要输出

- `outputs/data/weekly_demand_panel.csv`：50 条平衡周度需求序列。
- `outputs/data/network/`：由历史数据估计的风险、运费代理变量及情景参数。
- `outputs/tables/forecast_predictions.csv`：各预测起点和预测期的预测结果。
- `outputs/tables/forecast_metrics.csv`：WAPE、MAE 和 Bias。
- `outputs/tables/weekly_policy_results.csv`：每周实际运营和成本结果。
- `outputs/tables/policy_summary.csv`：策略对比及敏感性分析结果。
- `outputs/figures/`：需求、预测、成本、履约率和敏感性分析图表。
- `outputs/RESULTS_SUMMARY.md`：主要发现、解释和局限。

## 已验证的项目范围

- 112,643 条有效主状态订单商品记录。
- 86 个完整周度周期。
- 50 条品类—地区需求序列，共 4,300 条平衡面板记录。
- 四周库存计划模型，以及实际需求揭示后的履约分配模型。
- 13 周滚动历史回测。
- 自动验证需求汇总、成本核算、库存平衡、求解器状态和结果一致性。

核心项目未使用 SKU 级深度学习、随机规划或车辆路径规划，也不将模拟仓库和成本参数表述为 Olist 的真实经营数据。

## Proposal

最终 proposal 位于 [`docs/Olist_Forecast_OR_Project_Proposal.docx`](docs/Olist_Forecast_OR_Project_Proposal.docx)。
