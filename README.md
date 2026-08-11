# D. AI 产品商业化策略

菲律宾电信运营商/数据中心商 AI 产品商业化初步可行性研究。

## 状态

> **初步可行性研究 (Draft)**。不作为董事会、投委会或真实采购决策的依据。

## 目录结构

```
ai-monetization/
├── README.md                    # 本文件
├── LICENSE                      # 许可证
├── CHANGELOG.md                 # 变更日志
│
├── methodology/
│   ├── scope.md                 # 研究范围
│   ├── source_policy.md         # 来源政策与可信度分级
│   └── assumptions.yaml         # 可调参数
│
├── src/
│   ├── build_gpu_tco.py         # GPU TCO 计算 (服务器级功耗 + PUE)
│   ├── build_maas_economics.py  # MaaS 单位经济
│   ├── build_gpu_pricing.py     # GPUaaS 竞品标准化价格
│   ├── build_market_model.py    # 市场数据 (CAGR 自动计算)
│   └── validate_sources.py      # 来源验证
│
├── tests/
│   └── test_calculations.py     # 计算验证测试
│
├── data/
│   ├── sources.csv              # 可追溯来源清单 (claim-level)
│   ├── gpuaas_competitive_pricing.csv  # GPUaaS 竞品价格 (含规格)
│   ├── maas_competitive_pricing.csv    # MaaS 竞品价格
│   └── maas_token_economics.csv        # MaaS 单位经济
│
├── models/
│   ├── gpu_tco_breakdown.csv    # TCO 分解
│   └── gross_margin_sensitivity.csv  # 毛利率敏感性
│
└── reports/
    ├── D_AI_Monetization_Strategy_V2.md  # 主报告
    └── Resale_China_GPUaaS_Analysis.md   # 跨区域算力策略
```

## 运行

```bash
# 运行全部计算
python src/build_gpu_tco.py
python src/build_maas_economics.py
python src/build_gpu_pricing.py
python src/build_market_model.py

# 运行测试
python tests/test_calculations.py
```

## 数据来源与可信度

每项关键数据在 `data/sources.csv` 中记录来源 URL、获取时间和可信度分级：

- **A**: 厂商官方定价页、监管文件、财报、模型卡
- **B**: 可靠研究机构完整报告
- **C**: 媒体报道、搜索摘要
- **D**: 内部估算或未验证假设
- **E**: 纯假设

## 已知限制

- MaaS 吞吐量为估算值，非 SLA goodput，需 benchmark 验证
- TCO 中 PUE 和空闲功耗为行业估算 (可信度 D)，需当地实测
- 无收入/CapEx/现金流预测（需确定投资预算后另行建模）
- 无 SOM 数值（需 bottom-up 容量约束模型）
- 竞品价格为单次快照，无自动更新

## 变更日志

见 [CHANGELOG.md](CHANGELOG.md)。
