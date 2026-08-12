# 变更日志

## [2026-08-12 v6] Round 5 review corrections

### P0-1: 修复确定性构建的自引用缺陷 (CI 永远无法变绿的根因)

- **根因**：tracked manifest (`models/build_metadata.json`) 记录了 `git_commit`、`generated_at`、`source_date_epoch`。提交后新 commit 的 SHA 与 manifest 记录的不同 → CI 重建必然 diff → 永远失败。
- **修复**：tracked manifest 只保留**纯内容 hash** (assumptions_hash、sources_hash、generator_code_hash 等), 删除所有 VCS 身份和时间字段。
- 所有 provenance (git_commit、build_wall_clock、ci_run_id) 移至 gitignored `build/runtime_metadata.json`。
- **`check_generated.py` 完全重写**：在临时目录构建两次, hash 比较 byte-identical, 再与仓库已提交的 10 个产物比较 freshness。全程不修改真实工作区 (修掉了旧版原地 build + git diff 的实现/文档不一致)。
- `build_all.py` 新增 `build_all(output_dirs=...)` 函数式入口, 供 check_generated 和测试构建到临时目录。
- CI workflow 移除 `SOURCE_DATE_EPOCH` 注入, 改用 `check_generated.py`。
- **结果**：任何新 commit 后 CI 重建不再产生 manifest diff (自引用消除)。

### P0-2: DeepSeek V4 checkpoint 精度修正 (物理错误)

- **根因**：`model_deployment_profiles.yaml` 把 V4 Pro/Flash 标为 `weight_format: FP8`。但 V4 Pro 纯 FP8 (~1.6TB) > 16×H100 的 1.28TB HBM, 权重根本装不下。
- **修复** (来自 HuggingFace 模型卡实测)：
  - V4 Pro: `FP4_EXPERTS_FP8_OTHER` (混合精度), checkpoint 865GB, 可装入 16×H100 (1280GB) 权重
  - V4 Flash 0731: `FP4_EXPERTS_FP8_OTHER`, checkpoint 167GB, 可装入 8×H100 (640GB)
- 新增字段：`checkpoint_precision`、`checkpoint_size_gb`、`total_hbm_gb`、`weights_fit`、`runtime_fit`、`model_max_context`、`max_context_tested` (分离原生上下文 vs 已测上下文)。
- 部署状态从"Multi-node candidate"改为"**memory-feasibility candidate, 运行时未验证**"。
- `data/sources.csv` 新增 DSK-05/06/07 (HuggingFace checkpoint size + precision)。

### 附加 A (§10): 单一状态源 + 生成器 (消除漂移)

- **根因**：README 说 v4/16 测试, 报告说 v5/23 测试, CHANGELOG 说 CI 变绿 (实际红)。三处手工写、必然漂移。
- **新建 `project_status.yaml`** (唯一状态源) + **`src/render_status.py`** (生成器)。
- README 和报告的状态段用 `<!-- BEGIN/END STATUS -->` 标记包围, 由生成器从 YAML 注入。
- test_count 由生成器动态计算 (`grep -c "^def test_"`), 不手写。
- CI 状态永远写"以 GitHub Actions 当前状态为准", **绝不**手写"CI green"。

### 附加 B (§11): 节点价敏感的定价二维表

- **根因**：报告定价建议 Reserved $2.69 假设 $300k 节点价; 但 $400k 时保本 $2.82, $2.69 反而亏 4.8%。
- **新建 `models/pricing_recommendations.csv`**：行=节点价 ($300k/$400k/$500k) × 列=情景 × tier (Spot/Reserved/On-demand)。
- 公式：`建议价 = 保本价 ÷ (1 − 目标 CM)`。Reserved 目标 15% CM, Spot 保本底线。
- 结果：Reserved 在 $300k→$2.69, $400k→$3.32, $500k→$3.95 (随未验证 CapEx 浮动, 不再有负毛利)。

### 测试

- 测试从 23 增至 **31 项** (新增 8)：
  - `test_build_twice_is_byte_identical` (临时目录两次构建 hash 相等)
  - `test_check_generated_does_not_modify_worktree` (检查器不改工作区)
  - `test_deepseek_checkpoint_precision` (V4 Pro/Flash = FP4+FP8 mixed)
  - `test_checkpoint_size_fits_total_hbm` (每模型 ckpt < HBM)
  - `test_deployment_context_not_assumed` (max_context_tested = null)
  - `test_reserved_price_covers_break_even` (无负毛利)
  - `test_pricing_table_scales_with_node_price` (定价随节点价上升)
  - `test_project_status_consistent` (yaml test_count == 实际; 标记段一致)
- 强化 `test_build_metadata_exists` → 断言 manifest 无 VCS 身份。

### 不变性

- MaaS 毛利率仍为 🔴 无效 (未 benchmark, 不计算)
- GPUaaS 毛利率仍为基础设施贡献口径
- MaaS 路由价格仍为 2026-08-12 快照

### 明确排除 (留待下轮 P1)

- 外化 SCENARIOS / COMPETITORS / 非 BPO MARKET_DATA 到 YAML/CSV (manifest 仍有 null hash)
- 保存 raw OpenRouter JSON + 重算 content_hash
- validate_sources 强化 (published_at/route/region 检查)
- OpenRouter route → model_slug 重命名
- sources.csv 补齐 Qwen 9B / GPT-OSS / Gemma 的 claim ID
- 全报告 render_report.py (仅做状态段注入)

## [2026-08-12 v5] Round 4 review corrections

### P0-1: 确定性构建 + CI 变绿

- **删除 `datetime.now()` 时间戳**：tracked manifest (`models/build_metadata.json`) 改用 `SOURCE_DATE_EPOCH` (默认 0, CI 用 git commit time)
- manifest 现含 `generator_version`, `git_commit`, `source_date_epoch`, `generator_code_hash` + 各输入文件 hash
- 运行时墙上时钟移至 gitignored `build/runtime_metadata.json`
- 两次构建 byte-identical → `git diff --exit-code` 通过
- 新增 `src/check_generated.py` (hash-based 确定性检查)
- CI workflow 设置 `SOURCE_DATE_EPOCH`
- 修正 Windows 上 `os.rename` → `os.replace` (原子覆盖)

### P0-2: BPO 双基期 CAGR + 全球 GPUaaS 实测

- **BPO 改为长表**：`data/market_snapshots/ph_bpo.csv` (2025 actual / 2026 forecast / 2028 downside / 2028 upside)
- BPO 同时输出两个 CAGR 并标注基期：**2.4%–7.8% (2025 base) / 1.2%–9.3% (2026 base)**
- 报告新增 2026 forecast $42.3B (原仅存于 orphaned fixture)
- **全球 GPUaaS 修正**：$12.5B→$35B (2026-2031, 错误 URL) → **$8.21B→$26.62B (2025-2030, CAGR 26.5%)**
  - 来源 URL 改为 `153834402.html` (2026-08-12 实测)
  - 明确标注"行业背景, 非 PLDT TAM"
- `build_market_model.py` 删除硬编码 `MARKET_DATA`, 从 snapshot CSV 加载 BPO

### P0-3: MaaS 价格快照重建 (2026-08-12 实测)

- 新增 `data/pricing_snapshots/maas_openrouter.csv` (单一事实源, 含审计字段)
- 8 路由价格全部刷新为 2026-08-12 OpenRouter 实测值
- **修正路由归属错误**：DeepSeek V4 Flash 原 slug ($0.14/$0.28 系 Direct API 价误归 OpenRouter) → 实际 $0.0679/$0.168
- **促销状态记录**：DS Flash 0731 (43% off), DS Pro (75% off), GLM-5.2 (65% off)
- 每行含 `observed_at`, `content_hash`, `promotion`, `promotion_detail`
- `build_maas_economics.py` 删除硬编码 `COMPETITOR_PRICES`, 从 snapshot CSV 加载
- fixture (`tests/fixtures/maas_price_snapshots.csv`) 同步更新

### P0-4: DGX H100 节点价降级

- `$300,000` 节点价 confidence **A → D**, source_type `vendor → internal_estimate`
- NVIDIA DGX 用户指南仅提供硬件规格, 不含采购价
- 新增 `models/gpu_node_price_sensitivity.csv`：节点价 $300k–$500k 保本价区间
- 报告显示成本**区间** ($2.28→$3.36/GPU-hr) 而非单点
- 敏感性：节点价每 +$100k ≈ 保本价 +$0.54/GPU-hr

### P0-5: 工程清理

- `git rm --cached src/__pycache__` (3 个 .pyc 文件解除跟踪)
- `build/` 已在 .gitignore (runtime metadata)

### 测试

- 测试从 16 个增加到 **23 个**
- 新增：确定性 manifest 无墙上时钟、BPO 双基期 CAGR、GPUaaS 实测匹配、MaaS 快照精确匹配 fixture、MaaS 治理字段、DGX D 级、节点价敏感性
- 收紧：GLM 价格 `< 0.6` → 精确匹配 `0.4886`；BPO CAGR 必须标注基期

### 不变性

- MaaS 毛利率仍为 🔴 无效 (未 benchmark, 不计算)
- GPUaaS 毛利率仍为基础设施贡献口径

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
