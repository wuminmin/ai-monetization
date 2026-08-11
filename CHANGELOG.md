# 变更日志

## [2026-08-11 v4] Round 3 review corrections

### P0-1: MaaS 完全重构

- **所有 MaaS 毛利率标记为 🔴 无效**：无 benchmark，不计算毛利
- **GLM-5.2 价格修正**：$0.76/$2.42 → **$0.49/$1.54** (OpenRouter standard route)
- **Qwen 3.5 Flash 部署修正**：1×H100+1M+28K tok/s (无依据) → 8×H100+TP8+262K (官方示例)
- **竞品价格改为 per-route**：不再合并 "Direct API / OpenRouter"
- 新增 `model_deployment_profiles.yaml`：精确模型 ID, revision, native/extended context, TP/PP
- 删除 `maas_token_economics.csv`（含无效毛利）
- 新增 `maas_deployment_profiles.csv`（部署配置，benchmark_status=not_run）

### P0-2: BPO 情景模型

- 单一 $40B→$50.5B/12.4% CAGR → **$40.3B (2025 actual) → $43.3B-$50.5B (2028 downside-upside)**
- CAGR: 1.2%-9.3% (情景区间)

### P0-3: 可复现构建链

- 新增 `build_all.py`：从源数据生成全部 CSV + metadata
- 所有 CSV 由脚本原子写入 (temp + rename)
- 输出含 `build_metadata.json` (generated_at, assumptions_hash, sources_hash)
- 修正 Reliability Stress 漂移：报告 4,449 → CSV 正确值 4,494
- 报告数字引用 generated CSV 值，不再手工复制

### P1 修正

- TCO 功率模型增加输入校验 (0≤MFU≤1, clamp idle~nameplate)
- Spot 最低价改为保本价驱动: ≥$2.28 (Baseline)
- 新增独立 fixture 测试 (tests/fixtures/): gpu_price, maas_price, market_source
- 测试从 15 个增加到 16 个

### 工程

- 新增 `.github/workflows/validate.yml` (CI)
- Stage-gate 指标操作化 (formula + window + sample size)
- 报告状态标记统一为 ✅/🟡/🔴

## [2026-08-11 v3] Round 2 review corrections
- GPUaaS 价格单位修正 (二次除以 8 错误)
- TCO 分离 4 个利用率变量
- 市场数据来源修正
- Spot 价格与 TCO 一致性

## [2026-08-11 v2] Round 1 review corrections
- CAGR 自动计算
- DeepSeek V4 参数修正
- PLDT 容量份额口径
- 新增 src/, tests/, methodology/
