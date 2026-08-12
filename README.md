# D. AI 产品商业化策略

菲律宾电信运营商/数据中心商 AI 产品商业化初步可行性研究。

## 状态

<!-- BEGIN STATUS -->
> **draft_v6 — 第五轮评审修正**

- 测试: **31 项** (`tests/test_calculations.py`)
- GPUaaS: 公式结构已校正；核心 CapEx (节点价) 和运行输入待正式报价及实测验证
- MaaS 毛利: 🔴 无效 (待 benchmark)
- DGX 节点价: D 级内部估算 (待正式报价)
- 构建确定性: manifest 无 VCS 身份；两次临时构建 byte-identical
- CI 结果以 [GitHub Actions](../../actions) 当前状态为准。

_由 `project_status.yaml` + `src/render_status.py` 生成, 请勿手改此段。_
<!-- END STATUS -->

## 构建

```bash
# 安装依赖
pip install pandas pyyaml

# 生成全部 CSV (从源数据, 含 metadata)
python src/build_all.py

# 验证来源
python src/validate_sources.py

# 运行测试 (项数见 project_status.yaml)
python tests/test_calculations.py

# 同步 README/报告状态段 (由 project_status.yaml 生成)
python src/render_status.py

# 确定性检查 (临时目录构建两次, 不改工作区)
python src/check_generated.py
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
