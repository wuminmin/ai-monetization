# D. AI 产品商业化策略

菲律宾电信运营商/数据中心商 AI 产品商业化初步可行性研究。

## 状态

> **Draft v3 — 初步可行性研究**。不作为董事会、投委会或真实采购决策的依据。

## 目录结构

```
ai-monetization/
├── README.md
├── LICENSE
├── CHANGELOG.md
├── pyproject.toml
├── .gitignore
│
├── methodology/
│   ├── scope.md
│   ├── source_policy.md
│   └── assumptions.yaml         # 单一事实来源 (所有脚本从这里加载)
│
├── src/
│   ├── build_gpu_tco.py         # GPU TCO (分离4个利用率变量)
│   ├── build_maas_economics.py  # MaaS 单位经济 (理论敏感性)
│   ├── build_gpu_pricing.py     # GPUaaS 竞品 (raw_price_unit + normalize_price)
│   ├── build_market_model.py    # 市场数据 (CAGR 自动计算)
│   └── validate_sources.py      # 来源验证
│
├── tests/
│   └── test_calculations.py     # 15项验证测试 (含官方价格fixture)
│
├── data/
│   ├── sources.csv              # 可追溯来源 (claim-level)
│   ├── gpuaas_competitive_pricing.csv
│   ├── maas_competitive_pricing.csv  # 每provider route一行
│   └── maas_token_economics.csv
│
├── models/
│   ├── gpu_tco_breakdown.csv
│   └── gross_margin_sensitivity.csv
│
└── reports/
    ├── D_AI_Monetization_Strategy_V2.md
    └── Resale_China_GPUaaS_Analysis.md
```

## 运行

```bash
# 运行全部计算
python src/build_gpu_tco.py
python src/build_maas_economics.py
python src/build_gpu_pricing.py
python src/build_market_model.py

# 验证来源
python src/validate_sources.py

# 运行测试
python tests/test_calculations.py
```

## 可信度分级

A=厂商官方 | B=研究机构 | C=媒体/搜索摘要 | D=估算 | E=假设

## 已知限制

- GPUaaS 竞品价格为单次快照, AWS 用 Capacity Block, GCP 用 DWS (非标准按需)
- TCO 中 PUE/空闲功耗/活跃功耗为估算 (可信度 D), 需 PDU/BMC 实测
- MaaS 吞吐量为活跃状态估算, 非 SLA goodput, 需 benchmark
- 所有毛利率为基础设施贡献毛利率, 非完整企业毛利率
- 无收入/CapEx/现金流预测 (需确定投资预算)
- Azure 竞品价格暂缺 (需 Retail Prices API)
