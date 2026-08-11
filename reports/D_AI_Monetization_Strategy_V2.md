# D. AI 产品商业化策略

## 初步可行性研究 (Draft v3)

> **数据声明**：本报告使用截至 2026年8月11日的公开数据快照。价格和产品状态可能变化。每项关键结论标明来源和可信度分级（A-E）。本报告为初步可行性研究，不作为董事会、投委会或真实采购决策的依据。所有毛利率为**基础设施贡献毛利率**（infrastructure contribution margin），非完整企业毛利率。

---

## 1. 执行摘要

本报告为菲律宾电信运营商/数据中心商设计 AI 产品商业化路线图，涵盖 GPUaaS/MaaS 单位经济和定价分析。竞品数据来自厂商官网（可信度 A）和 OpenRouter 排行榜（2026年8月11日访问）。

---

## 2. 产品路线图 (Stage-Gate)

| Gate | 产品 | 进入条件 | 退出条件 |
|------|------|---------|---------|
| Gate 0 | GPUaaS 试点 | 基础设施就绪, ≥1 锚定客户 LOI | billable utilization ≥45% 连续8周 |
| Gate 1 | Managed Inference | ≥2 有约束合同客户, SLA 体系建立 | 客户留存 ≥80%, 错误率 <0.5% |
| Gate 2 | MaaS Preview | benchmark 完成, goodput 达标 | ≥10 付费客户, utilization ≥55% |
| Gate 3 | MaaS GA | 计量/账单/多租户就绪 | 基础设施贡献毛利转正 |
| Gate 4 | AIaaS / 行业方案 / Agent | 平台层成熟 | 新产品线贡献毛利 >50% |

> MaaS 需额外建设模型路由、API Gateway、计量账单、内容安全、多租户隔离。不应与 GPUaaS 同步启动。

---

## 3. GPUaaS 竞品价格

### 标准化价格表 (raw price + explicit unit)

| 供应商 | 产品 | GPU数 | 原始价格 | 原始单位 | 采购模式 | 标准化 $/GPU/hr | 标准化 $/节点/hr | 可信度 |
|--------|------|-------|---------|---------|---------|----------------|-----------------|--------|
| Lambda | H100 SXM5 | 8 | $3.99 | per-GPU-hr | on-demand | **$3.99** | $31.92 | A |
| CoreWeave | HGX H100 8GPU | 8 | $49.24 | per-instance-hr | on-demand | **$6.16** | $49.24 | A |
| CoreWeave | HGX H100 8GPU (Spot) | 8 | $19.71 | per-instance-hr | spot | **$2.46** | $19.71 | A |
| GCP | a3-highgpu-8g | 8 | $38.32 | per-instance-hr | DWS | **$4.79** | $38.32 | A |
| AWS | p5.48xlarge | 8 | $41.53 | per-instance-hr | Capacity Block | **$5.19** | $41.53 | A |
| Oracle | BM.GPU.H100.8 | 8 | $10.00 | per-GPU-hr | on-demand | **$10.00** | $80.00 | A |

> 来源：各厂商官网，accessed 2026-08-11。Azure 暂未列入——需通过 Azure Retail Prices API 获取可验证的区域/SKU/采购模式价格后补入。
>
> **口径说明**：Lambda 和 Oracle 页面明确标注为 per-GPU-hour，不能再除以 GPU 数。CoreWeave/AWS/GCP 页面标注为 instance-hour，需除以 8。AWS Capacity Block 和 GCP DWS 非标准按需模式，可能有排队/调度约束。

### 关键发现

| 对比维度 | 范围 | 说明 |
|---------|------|------|
| On-demand per-GPU | $3.99–$10.00 | Lambda 最低, Oracle 最高 |
| Spot per-GPU | $2.46 (CoreWeave) | 可中断, 无保证 |
| Capacity Block / DWS | $4.79–$5.19 | 有调度约束, 非标准按需 |

> PLDT 建议价格 $2.69–$3.20/GPU/hr 对比 Lambda $3.99/GPU/hr (on-demand) 有一定竞争力, 但需在同等规格 (8-GPU SXM, Enterprise SLA) 下验证。

---

## 4. GPU TCO (H100 SXM5, 8-GPU Node)

### 功率模型

| 参数 | 值 | 来源 |
|------|-----|------|
| Nameplate max system power | 10.2 kW | NVIDIA DGX H100 datasheet (可信度 A) |
| Active power at ~50% MFU | 7.0 kW | 估算 (可信度 D), 需 PDU/BMC 实测 |
| Idle power | 2.8 kW | 估算 (可信度 D), 需实测 |

> 7.0kW 是活跃运行估算功率, **不是** nameplate peak。DGX H100 官方最大功率为 10.2kW。

### 情景分析 (分离 4 个利用率变量)

| 情景 | 商业利用率 | MFU | 可用率 | 计费效率 | PUE | 保本 $/GPU/hr | 可计费 hr/yr |
|------|----------|-----|-------|---------|-----|-------------|------------|
| Demand Down | 35% | 45% | 99% | 95% | 1.40 | **$3.86** | 2,884 |
| Baseline | 60% | 50% | 99% | 95% | 1.40 | **$2.28** | 4,943 |
| Demand Up | 80% | 55% | 99% | 95% | 1.40 | **$1.73** | 6,591 |
| Energy Stress | 60% | 50% | 99% | 95% | 1.60 | **$2.45** | 4,943 |
| Reliability Stress | 60% | 50% | 95% | 90% | 1.40 | **$2.51** | 4,449 |

> 变量说明：商业利用率 = 可售时间中实际售出比例; MFU = 活跃计算利用率 (驱动功耗); 可用率 = 服务可用时间比例; 计费效率 = 可计费小时 / 运行小时。这些变量分别影响功耗、可计费小时和成本回收。

### 贡献毛利率敏感性

| 定价 $/GPU/hr | Demand Down (35%) | Baseline (60%) | Demand Up (80%) | Energy Stress | Reliability Stress |
|--------------|-------------------|----------------|-----------------|--------------|-------------------|
| $2.00 | ❌ loss | ❌ loss | 13.3% | ❌ loss | ❌ loss |
| $2.69 | ❌ loss | 15.1% | 35.5% | 9.1% | 6.8% |
| $3.20 | ❌ loss | 28.7% | 45.8% | 23.6% | 21.6% |
| $3.99 | 3.2% | 42.8% | 56.5% | 38.7% | 37.1% |
| $5.00 | 22.8% | 54.4% | 65.3% | 51.1% | 49.8% |
| $6.16 | 37.3% | 62.9% | 71.9% | 60.3% | 59.3% |

> 以上为**基础设施贡献毛利率**。不含销售、支持、坏账、融资、进口、备件、网络 Fabric、存储和 SLA 赔偿等成本。

### 定价建议 (分层数, 公式驱动)

| 产品层级 | 规格 | 建议价格 | Baseline CM |
|---------|------|---------|------------|
| 单卡 Reserved (12月) | 1×H100, Business SLA | $2.69–$3.20/GPU/hr | 15–29% |
| 8卡 On-demand | 8×H100 SXM, Enterprise SLA | $3.99–$5.00/GPU/hr | 43–54% |
| 8卡 Reserved (12月) | 8×H100 SXM, Enterprise SLA | $3.20–$3.99/GPU/hr | 29–43% |
| Spot (可中断) | 1–8×H100, 无保证 | ≥$2.28/GPU/hr (保本价) | 0–10% |

> Spot 最低价不应低于 Baseline 保本价 $2.28/GPU/hr。原报告建议的 $1.50/GPU/hr 在 Baseline 情景下为亏损 (-52%)。

---

## 5. MaaS 单位经济 (理论敏感性)

> ⚠️ 以下毛利率为**理论敏感性结果**，非生产毛利率。吞吐量为活跃状态估算值，非 SLA goodput。GPU 成本使用活跃小时成本 ($2.28/hr) 而非日历小时成本 ($1.29/hr)。所有数值需 benchmark 验证。

| 模型 | 总参/激活 | GPU | 精度 | 估算 tok/s | 成本 $/M | 竞品 $/M_in/out | 建议 $/M_in/out | 理论混合 GM |
|------|----------|-----|------|-----------|---------|----------------|----------------|------------|
| DeepSeek V4 Flash | 284B/13B | 8×H100 | FP8 | 35,000 | $0.14 | $0.14/$0.28 | $0.13/$0.27 | 16% |
| DeepSeek V4 Pro | 1.6T/49B | 16×H100 | FP8 | 22,000 | $0.46 | $0.63/$1.26 | $0.44/$0.88 | 20% |
| Qwen 3.5 Flash | ~30B/~3B | 1×H100 | FP8 | 28,000 | $0.02 | $0.065/$0.26 | $0.055/$0.22 | 78% |
| Qwen 3.5 9B | 9B/9B | 1×H100 | BF16 | 14,000 | $0.05 | $0.10/$0.15 | $0.085/$0.13 | 54% |
| GPT-OSS 120B | 117B/5.1B | 2×H100 | MXFP4 | 20,000 | $0.06 | $0.037/$0.17 | $0.035/$0.16 | 13% |
| Gemma 4 31B | 30.7B/30.7B | 1×H100 | BF16 | 12,000 | $0.05 | $0.10/$0.34 | $0.085/$0.29 | 64% |
| GLM-5.2 | ~350B/~32B | 8×H100 | FP8 | 25,000 | $0.20 | $0.76/$2.42 | $0.53/$1.69 | 77% |

> 混合 GM 假设 70% 输入 / 30% 输出。不同工作负载比例差异大 (RAG 95:5, 代码生成 30:70)。成本未按 prefill/decode 分拆——两者资源特征不同, 当前为粗略估算。

### 部署说明

| 模型 | 关键约束 |
|------|---------|
| GPT-OSS 120B | MXFP4 量化 (117B × 4bit / 8 ≈ 58.5GB) 可单卡。2 卡配置为吞吐部署选择。 |
| Gemma 4 31B | BF16 权重 ~62/80GB, KV Cache 有限。高并发需 INT8 或加卡。 |
| DeepSeek V4 Pro | 1.6T 总参数需多机 (TP=8, PP=2), 最低 16 卡。 |

---

## 6. 市场背景 (TAM/SAM/SOM)

| 指标 | 地理范围 | 规模 | 周期 | CAGR | 来源 | 可信度 |
|------|---------|------|------|------|------|--------|
| Philippines DC Market | 菲律宾 | $0.85B → $2.37B | 2026-2031 | 22.8% | Mordor Intelligence | B |
| Philippines BPO Revenue | 菲律宾 | $40B → $50.5B | 2026-2028 | 12.4% | IBPAP | B |
| Global GPUaaS Market | 全球 | $12.5B → $35B | 2026-2031 | 22.9% | MarketsandMarkets | B |

> CAGR 由公式自动计算。BPO 全行业收入不等于 BPO 的 AI 算力采购预算。
>
> **已移除**：东南亚公有云 $8B→$30B (来源为 Technavio DC 报告, 指标不匹配); BPO $102B/2034 (未验证); 亚太 AI DC $11.8B (无可验证起止对)。

### SOM

> SOM 需基于实际 GPU 容量、供电、上架节奏和已签合同做 bottom-up 计算。PLDT 65% 为数据中心**容量**份额, 不代表收入份额或 AI 算力可获取份额。本报告不提供 SOM 数值。

---

## 7. PLDT VITRO 定位

- 11 个数据中心, 计划第 12 个 (≥100MW, $10 亿投资)
- VITRO Sta. Rosa: 50MW 设计容量, 已运营
- PLDT 另披露 ≥100MW 后续 DC 计划 (与 Sta. Rosa 为不同项目)
- PLDT 总收入 ₱196.2B, EBITDA ₱111.2B (FY2025, 来源: PLDT 财报, 可信度 A)

> VITRO 披露的 65% 为数据中心**容量**份额, 不代表收入份额、AI 算力份额或 GPUaaS 可获取市场份额。

| 维度 | PLDT VITRO | 超大规模云 | 专业 AI 云 | 市场型平台 |
|------|-----------|-----------|-----------|-----------|
| 数据驻留 | 支持本地部署 | 取决于区域/架构 | 同左 | 同左 |
| 本地延迟 | 对 Manila 客户低 | 需实测 p50/p95 | 需实测 | 不可控 |
| 网络 | 自有骨干网 | 第三方 | 第三方 | 差异较大 |
| SLA | 待建 | 成熟 | 基础 | 差异较大 |
| BPO 生态 | 深度 | 有限 | 无 | 无 |

> 以上需逐项验证。延迟应实测; 数据合规取决于租户架构、日志、备份和合同控制。

---

## 8. 关键风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| GPU 利用率不足 | 高 | 致命 | 先获锚定客户 LOI 再采购 |
| GPU 贬值 | 高 | 高 | 分阶段采购; 二手回购条款 |
| 电价上涨 | 中 | 高 | 太阳能 PPA + RECs |
| 竞品降价 | 高 | 中 | 本地化差异化 |
| 吞吐量不达预期 | 中 | 高 | 先 benchmark 再承诺 SLA |
| 数据合规变化 | 低 | 高 | 聘请法律顾问 |

> 折旧年限和残值是会计假设, 不构成实际对冲。

---

## 9. 状态清单

### P0 — 已修正
- [x] 🟡 GPUaaS 价格单位修正 (raw_price_unit + normalize_price)
- [x] 🟡 TCO 分离 4 个利用率变量 (comm_util, MFU, availability, billing_eff)
- [x] 🟡 DeepSeek V4 参数 (284B/13B, 1.6T/49B)
- [x] 🟡 VITRO 容量份额 vs 收入份额区分
- [x] 🟡 VITRO Sta.Rosa 50MW + 新 DC ≥100MW 拆分
- [x] 🟡 市场数据移除不可靠来源 (SE Asia cloud, BPO $102B, PH DC 年份)
- [x] 🟡 "实时校准" → "截至日期的数据快照"
- [x] 🟡 Spot 最低价改为保本价驱动 (≥$2.28/GPU/hr)

> 🟡 = 已实现, 待实测数据验证

### P1 — 待完成
- [ ] 🔴 MaaS benchmark (TTFT/TPOT/goodput)
- [ ] 🔴 输入/输出 token 成本按 prefill/decode 分拆
- [ ] 🔴 Bottom-up SOM
- [ ] 🔴 CapEx / OpEx / NPV / IRR
- [ ] 🔴 客户访谈 / LOI / 销售漏斗
- [ ] 🔴 延迟实测 (Manila → 各云区域)
- [ ] 🔴 TCO 功耗实测 (PDU/BMC telemetry)
- [ ] 🔴 Azure 竞品价格 (Retail Prices API)

### P2 — 提升专业度
- [ ] 🔴 CI / GitHub Actions
- [ ] 🔴 pyproject.toml + 依赖锁定
- [ ] 🔴 自动生成 DOCX
- [ ] 🔴 数据快照归档 + content hash

---

## 附录：数据来源

完整来源清单见 `data/sources.csv`（33 条, 含 claim_id, 来源 URL, 获取时间, 可信度分级）。

可信度分级：A=厂商官方 | B=研究机构 | C=媒体/搜索摘要 | D=估算 | E=假设

---

*Draft v3, Generated 2026-08-11. Data snapshot as of access date.*
