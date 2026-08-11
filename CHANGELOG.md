# 变更日志

## [2026-08-11 v3] Round 2 review corrections

### P0 — GPUaaS 价格单位错误修正 (8倍偏差)

- **根因**：CoreWeave $2.49、AWS $6.88 等原始价格**本身就是 per-GPU 或 per-instance 价格**，但被统一当作 instance price 再除以 8，导致低估约 8 倍
- **修正**：重建 `build_gpu_pricing.py`，引入 `raw_price_unit` 字段和 `normalize_price()` 函数
  - CoreWeave on-demand: $0.31 → **$6.16/GPU/hr** (raw $49.24/instance-hr ÷ 8)
  - Lambda: $0.34 → **$3.99/GPU/hr** (raw 已是 per-GPU-hr, 不再除)
  - AWS (Cap Block): $0.86 → **$5.19/GPU/hr** (raw $41.53/instance-hr ÷ 8)
  - GCP (DWS): $0.46 → **$4.79/GPU/hr** (raw $38.32/instance-hr ÷ 8)
  - Oracle: $0.38 → **$10.00/GPU/hr** (raw 已是 per-GPU-hr)
- Azure 移除——需通过 Retail Prices API 获取可验证价格
- 新增 6 个官方价格 fixture 测试 (independent of production code)

### P0 — TCO 利用率变量分离

- **根因**：单一 `avg_load` 同时用于功耗估算、可计费小时和商业利用率, 导致"压力"情景保本价反更低
- **修正**：分离为 4 个独立变量:
  - `commercial_utilization` (商业销售利用率)
  - `active_compute_mfu` (活跃计算 MFU, 驱动功耗)
  - `service_availability` (服务可用率)
  - `billing_efficiency` (计费效率)
- 新增 5 个独立情景 (demand_down/baseline/demand_up/energy_stress/reliability_stress)
- Baseline 保本价: $1.91 → **$2.28/GPU/hr**
- 7kW 更名为 "active power at target MFU", nameplate max 改为 10.2kW (DGX datasheet)

### P0 — 市场数据来源修正

- 移除 "东南亚公有云 $8B→$30B" (来源为 Technavio DC 报告, 指标不匹配)
- 菲律宾 DC: $0.766B→$1.97B/2026-2030 → **$0.85B→$2.37B/2026-2031** (Mordor 原始年份)
- BPO $102B/2034 移除 (未验证) → 替换为 IBPAP 2026-2028 $40B→$50.5B
- 移除亚太 AI DC $11.8B (无可验证起止对)

### P0 — Spot 价格与 TCO 一致性

- 旧 Spot 建议 $1.50-2.00/GPU/hr 在 Baseline 情景下为亏损 (-52%~-14%)
- 修正为: Spot 最低价 ≥ Baseline 保本价 $2.28/GPU/hr

### P1 — MaaS 成本基础修正

- GPU 成本从 break-even-at-util 改为 **active cost per GPU hour** ($2.28/hr)
  - 区别于 calendar cost ($1.29/hr)
- DeepSeek V4 Flash 理论 GM: 30% → **16%** (因成本基础修正)
- GPT-OSS 内存公式修正: "117B×0.5B/8bit" → "117B × 4bit / 8 = 58.5GB, MXFP4"
- 竞品价格表改为每 provider route 一行 (11 行, 不再合并)
- 模型增加 revision 字段

### P1 — 基础设施贡献毛利率

- 所有 margin 统一更名为 **infrastructure contribution margin**
- 明确标注不含销售/支持/坏账/融资/进口/备件/网络 Fabric/存储/SLA 赔偿

### 工程

- 新增 `.gitignore`, `pyproject.toml`
- 新增 `src/validate_sources.py`
- assumptions.yaml 成为单一事实来源 (TCO 从 YAML 加载)
- 测试从 11 个增加到 15 个, 含官方价格 fixture

## [2026-08-11 v2] Round 1 review corrections

- CAGR 改为自动计算
- DeepSeek V4 参数修正 (671B → 284B/13B Flash, 1.6T/49B Pro)
- PLDT 65% 明确为容量份额
- VITRO 50MW/100MW 拆分为独立项目
- TCO 加入服务器级功耗 + PUE
- GPU 竞品增加 form_factor/pricing_type
- 删除凭空编造的收入预测
- 新增 src/, tests/, methodology/, README, LICENSE, CHANGELOG
