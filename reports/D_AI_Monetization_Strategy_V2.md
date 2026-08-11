# D. AI 产品商业化策略

## 初步可行性研究 (Draft v4)

> **数据声明**：截至 2026年8月11日的公开数据快照。所有 CSV 由 `src/build_all.py` 从源数据自动生成 (见 `models/build_metadata.json`)。报告为初步可行性研究，不作为投资决策依据。所有 GPUaaS 毛利率为**基础设施贡献毛利率**。**所有 MaaS 毛利率为 🔴 无效**——待 benchmark 后重算。

---

## 1. 执行摘要

本报告为菲律宾电信运营商/数据中心商设计 AI 产品商业化路线图。GPUaaS 单位经济已完成结构性修正；MaaS 部分因缺少 benchmark，当前仅列出模型配置和竞品价格，不计算毛利。

---

## 2. 产品路线图 (Stage-Gate)

| Gate | 产品 | 进入条件 | 退出条件 |
|------|------|---------|---------|
| Gate 0 | GPUaaS 试点 | 基础设施就绪, ≥2 有约束合同客户 | billable GPU hours / sellable GPU hours ≥45%, 连续8周 |
| Gate 1 | Managed Inference | benchmark完成, SLA体系建立 | 成功作业率 ≥98% (≥500作业), 客户留存 ≥80% |
| Gate 2 | MaaS Preview | goodput benchmark完成 | TTFT p95 <1.5s @2048/512, TPOT p95 <80ms, 错误率 <0.5% |
| Gate 3 | MaaS GA | 计量/账单/多租户就绪 | 基础设施贡献毛利转正 |
| Gate 4 | AIaaS / 行业方案 | 平台层成熟 | 新产品线贡献毛利 >50% |

---

## 3. GPUaaS 竞品价格

### 标准化价格表

| 供应商 | 产品 | 原始价格 | 原始单位 | 采购模式 | $/GPU/hr | $/节点/hr |
|--------|------|---------|---------|---------|---------|----------|
| Lambda | H100 SXM | $3.99 | per-GPU-hr | on-demand | **$3.99** | $31.92 |
| CoreWeave | HGX H100 8GPU | $49.24 | per-instance-hr | on-demand | **$6.16** | $49.24 |
| CoreWeave | HGX H100 Spot | $19.71 | per-instance-hr | spot | **$2.46** | $19.71 |
| GCP | a3-highgpu-8g | $38.32 | per-instance-hr | DWS | **$4.79** | $38.32 |
| AWS | p5.48xlarge | $41.53 | per-instance-hr | Capacity Block | **$5.19** | $41.53 |
| Oracle | BM.GPU.H100.8 | $10.00 | per-GPU-hr | on-demand | **$10.00** | $80.00 |

> 来源：各厂商官网, accessed 2026-08-11。Azure 暂缺——需 Retail Prices API。
> AWS Capacity Block 和 GCP DWS 非标准按需模式, 可能有调度约束。

---

## 4. GPU TCO (H100 SXM5, 8-GPU Node)

### 功率模型

| 参数 | 值 | 来源 |
|------|-----|------|
| Nameplate max (DGX datasheet) | 10.2 kW | NVIDIA DGX H100 user guide (可信度 A) |
| Active power @ ~50% MFU | 7.0 kW | 估算 (可信度 D), 需 PDU/BMC |
| Idle power | 2.8 kW | 估算 (可信度 D), 需实测 |

### 情景分析 (4 个分离变量)

| 情景 | 商业利用率 | MFU | 可用率 | 计费效率 | PUE | 保本 $/GPU/hr | 可计费 hr/yr |
|------|----------|-----|-------|---------|-----|-------------|------------|
| Demand Down | 35% | 45% | 99% | 95% | 1.40 | $3.86 | 2,884 |
| Baseline | 60% | 50% | 99% | 95% | 1.40 | $2.28 | 4,943 |
| Demand Up | 80% | 55% | 99% | 95% | 1.40 | $1.73 | 6,591 |
| Energy Stress | 60% | 50% | 99% | 95% | 1.60 | $2.45 | 4,943 |
| Reliability Stress | 60% | 50% | 95% | 90% | 1.40 | $2.51 | 4,494 |

### 贡献毛利率 (基础设施口径)

| 定价 $/GPU/hr | Demand Down | Baseline | Demand Up | Energy Stress | Rel. Stress |
|--------------|-------------|----------|-----------|--------------|-------------|
| $2.69 | ❌ loss | 15.1% | 35.5% | 9.1% | 6.8% |
| $3.20 | ❌ loss | 28.7% | 45.8% | 23.6% | 21.6% |
| $3.99 | 3.2% | 42.8% | 56.5% | 38.7% | 37.1% |
| $5.00 | 22.8% | 54.4% | 65.3% | 51.1% | 49.8% |

> 基础设施贡献毛利率, 不含销售/支持/坏账/融资/进口/备件/网络 Fabric/存储/SLA 赔偿。

### 定价建议

| 层级 | 规格 | 建议 $/GPU/hr | Baseline CM |
|------|------|-------------|------------|
| Reserved (12月) | 1-8×H100, Business SLA | $2.69–$3.20 | 15–29% |
| On-demand | 8×H100 SXM, Enterprise SLA | $3.99–$5.00 | 43–54% |
| Spot (可中断) | ≥保本价 | ≥$2.28 (Baseline) | 0–10% |

> Spot 最低价 = Baseline 保本价 $2.28/GPU/hr。目标 10% CM → $2.53/GPU/hr。

---

## 5. MaaS 模型配置 (🔴 毛利无效, 待 benchmark)

> ⚠️ **所有 MaaS 毛利率当前为 🔴 无效。** 没有模型完成 benchmark。以下仅列出部署配置和竞品价格。

### 部署配置 (来自 methodology/model_deployment_profiles.yaml)

| 模型 | 总参/激活 | 架构 | 原生上下文 | GPU 配置 | TP | benchmark |
|------|----------|------|----------|---------|-----|-----------|
| DeepSeek V4 Flash (0731) | 284B/13B | MoE | 1M | 8×H100 SXM5 | 8 | 🔴 not_run |
| DeepSeek V4 Pro | 1.6T/49B | MoE | 1M | 16×H100 (2 nodes) | 8+PP2 | 🔴 not_run |
| Qwen 3.5 Flash (35B-A3B) | 35B/3B | MoE混合 | 262K | 8×H100 SXM5 | 8 | 🔴 not_run |
| Qwen 3.5 9B | 9B/9B | Dense | 262K | 1×H100 | 1 | 🔴 not_run |
| GPT-OSS 120B | 117B/5.1B | MoE | 128K | 1×H100 (MXFP4) | 1 | 🔴 not_run |
| Gemma 4 31B | 30.7B/30.7B | Dense | 262K | 1×H100 (BF16) | 1 | 🔴 not_run |
| GLM-5.2 | ~350B/~32B | MoE推理 | 1M | 8×H100 SXM5 | 8 | 🔴 not_run |

> Qwen 3.5 Flash 已修正：原方案 1×H100 + 1M 上下文 + 28K tok/s 缺乏官方部署依据。现采用官方长上下文示例 (TP=8, 262K native context) 作为保守基线。

### 竞品价格 (per provider route)

| 模型 | Route | $/M_in | $/M_out | 促销 | 备注 |
|------|-------|--------|---------|------|------|
| DeepSeek V4 Flash | OpenRouter (0731) | $0.08 | $0.18 | — | 最新版本 |
| DeepSeek V4 Flash | OpenRouter (original) | $0.14 | $0.28 | — | 逐步替换为 0731 |
| DeepSeek V4 Pro | OpenRouter | $0.63 | $1.26 | — | Direct API 可能不同 (~$0.435/$0.87) |
| Qwen 3.5 Flash | OpenRouter | $0.065 | $0.26 | Yes | 促销价; Alibaba Singapore direct ~$0.10/$0.40 |
| Qwen 3.5 9B | OpenRouter | $0.10 | $0.15 | — | |
| GPT-OSS 120B | OpenRouter | $0.037 | $0.17 | — | |
| Gemma 4 31B | OpenRouter | $0.10 | $0.34 | — | |
| GLM-5.2 | OpenRouter (standard) | $0.49 | $1.54 | — | 已修正: 原 $0.76/$2.42 错误 |

### 待完成

1. 每个 GPU 配置跑 vLLM benchmark (输入/输出长度, 并发, TTFT/TPOT p95)
2. 基于 SLA goodput 计算 cost_per_1m_input/output_tokens
3. 按工作负载 (RAG/chat/code/agent) 分别计算毛利
4. 验证 DeepSeek Pro / GLM-5.2 的 Direct API 价格

---

## 6. 市场背景

| 指标 | 地理 | 规模 | 周期 | CAGR | 来源 | 可信度 |
|------|-----|------|------|------|------|--------|
| Philippines DC | 菲律宾 | $0.85B → $2.37B | 2026-2031 | 22.8% | Mordor Intelligence | B |
| Philippines BPO | 菲律宾 | $40.3B → $43.3B-$50.5B | 2025-2028 | 1.2%–9.3% | IBPAP | B |
| Global GPUaaS | 全球 | $12.5B → $35B | 2026-2031 | 22.9% | MarketsandMarkets | B |

> BPO 为情景区间：2025 实际 $40.3B, 2028 下行 $43.3B (CAGR 1.2%), 上行 $50.5B (CAGR 9.3%)。BPO 全行业收入不等于 AI 算力 TAM。

---

## 7. PLDT VITRO 定位

- 11 个 DC, 计划第 12 个 (≥100MW)
- VITRO Sta. Rosa: 50MW (独立项目)
- PLDT 总收入 ₱196.2B, EBITDA ₱111.2B (FY2025)
- VITRO 披露的 65% 为数据中心**容量**份额, 不代表收入/AI 算力份额

| 维度 | PLDT VITRO | 超大规模云 | 专业 AI 云 | 市场型 |
|------|-----------|-----------|-----------|-------|
| 数据驻留 | 支持本地 | 取决于区域/架构 | 同左 | 同左 |
| 延迟 | 对 Manila 客户低 | 需实测 p50/p95 | 需实测 | 不可控 |
| 网络 | 自有骨干 | 第三方 | 第三方 | 差异大 |
| SLA | 待建 | 成熟 | 基础 | 差异大 |

---

## 8. 关键风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| GPU 利用率不足 | 高 | 致命 | 先获锚定客户 LOI |
| MaaS 吞吐不达预期 | 高 | 高 | benchmark 验证后再承诺 |
| GPU 贬值 | 高 | 高 | 分阶段采购 |
| 电价上涨 | 中 | 高 | PPA 对冲 |
| 竞品降价 | 高 | 中 | 本地化差异化 |

---

## 9. 状态清单

### ✅ 已完成并独立验证
- [x] GPUaaS 价格单位修正 (raw_price_unit + fixture 测试)
- [x] TCO 分离 4 个利用率变量
- [x] TCO 功率校验 (MFU 0-1, clamp idle~nameplate)
- [x] 市场数据 CAGR 自动计算
- [x] 构建链生成 CSV (build_all.py + metadata)
- [x] 独立 fixture 测试 (tests/fixtures/)

### 🔴 当前结果无效或未完成
- [ ] 🔴 MaaS 所有毛利率 (待 benchmark)
- [ ] 🔴 MaaS 模型 benchmark (TTFT/TPOT/goodput)
- [ ] 🔴 MaaS 输入/输出成本分拆 (prefill vs decode)
- [ ] 🔴 DeepSeek Pro / GLM-5.2 Direct API 价格验证
- [ ] 🔴 Bottom-up SOM
- [ ] 🔴 CapEx / OpEx / NPV / IRR
- [ ] 🔴 客户访谈 / LOI
- [ ] 🔴 TCO 功耗实测 (PDU/BMC)
- [ ] 🔴 Azure 竞品价格
- [ ] 🔴 延迟实测

### 🟡 已实现, 待数据验证
- [ ] 🟡 TCO 情景中的 PUE/功耗参数 (需实测替换)
- [ ] 🟡 Qwen 3.5 Flash 部署配置 (需 benchmark 确认 TP/GPU 数)
- [ ] 🟡 Stage-gate 进入/退出指标 (需与运营团队对齐)

---

*Draft v4, Generated 2026-08-11. All CSVs generated by build_all.py. See models/build_metadata.json.*
