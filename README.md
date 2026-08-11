# D. AI 产品商业化策略

菲律宾电信运营商/数据中心商 AI 产品商业化初步可行性研究。

## 状态

> **Draft v4 — GPUaaS 模型基本可信, MaaS 毛利 🔴 无效 (待 benchmark)。**

## 构建

```bash
# 安装依赖
pip install pandas pyyaml

# 生成全部 CSV (从源数据, 含 metadata)
python src/build_all.py

# 验证来源
python src/validate_sources.py

# 运行测试 (16 项, 含独立 fixture)
python tests/test_calculations.py
```

## 目录结构

```
ai-monetization/
├── .github/workflows/validate.yml  # CI
├── methodology/
│   ├── assumptions.yaml            # 单一事实来源
│   └── model_deployment_profiles.yaml  # MaaS 部署配置
├── src/
│   ├── build_all.py                # 主构建脚本 (生成全部 CSV)
│   ├── build_gpu_tco.py            # GPU TCO (4 变量分离)
│   ├── build_gpu_pricing.py        # GPUaaS 竞品 (raw_price_unit)
│   ├── build_maas_economics.py     # MaaS 竞品价格 (per-route)
│   ├── build_market_model.py       # 市场数据 (CAGR 自动)
│   └── validate_sources.py         # 来源验证
├── tests/
│   ├── test_calculations.py        # 16 项验证
│   └── fixtures/                   # 独立价格快照
├── data/
│   ├── sources.csv                 # 可追溯来源 (claim-level)
│   ├── gpuaas_competitive_pricing.csv
│   ├── maas_competitive_pricing.csv     # per provider route
│   ├── maas_deployment_profiles.csv     # 部署配置 (benchmark=not_run)
│   └── market_data.csv
├── models/
│   ├── gpu_tco_breakdown.csv
│   ├── gross_margin_sensitivity.csv
│   └── build_metadata.json         # 构建元数据
└── reports/
    └── D_AI_Monetization_Strategy_V2.md
```

## 可信度分级

A=厂商官方 | B=研究机构 | C=媒体 | D=估算 | E=假设
