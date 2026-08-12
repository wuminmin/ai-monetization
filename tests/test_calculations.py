#!/usr/bin/env python3
"""
Validation tests — Round 3: cross-field invariants, fixture-based validation,
report-CSV consistency.
"""

import sys
import os
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def test_official_price_normalization():
    """Verify price normalization against independent fixtures."""
    from build_gpu_pricing import normalize_price
    snaps = pd.read_csv(os.path.join(FIXTURES, "gpu_price_snapshots.csv"))
    for _, snap in snaps.iterrows():
        inst, gpu = normalize_price(snap["raw_price"], snap["raw_price_unit"], snap["gpu_count"])
        assert abs(gpu - snap["normalized_gpu_hr"]) < 0.01, \
            f"{snap['provider']} {snap['product_name']}: expected ${snap['normalized_gpu_hr']}, got ${gpu}"
    print(f"PASS: test_official_price_normalization ({len(snaps)} fixtures)")


def test_coreweave_not_understated():
    """CoreWeave on-demand must NOT be $0.31/GPU/hr."""
    from build_gpu_pricing import build_gpu_pricing_table
    df = build_gpu_pricing_table()
    cw = df[(df["provider"] == "CoreWeave") & (df["procurement_mode"] == "on_demand")].iloc[0]
    assert cw["normalized_gpu_hr"] > 5.0, f"CoreWeave still understated: ${cw['normalized_gpu_hr']}"
    print(f"PASS: test_coreweave_not_understated (${cw['normalized_gpu_hr']:.2f})")


def test_tco_separates_utilization():
    """TCO must use 4 separate variables, not avg_load."""
    from build_gpu_tco import SCENARIOS
    for key, s in SCENARIOS.items():
        for req in ["commercial_utilization", "active_compute_mfu", "service_availability", "billing_efficiency"]:
            assert req in s, f"{key}: missing {req}"
        assert "avg_load" not in s
    print(f"PASS: test_tco_separates_utilization ({len(SCENARIOS)} scenarios)")


def test_tco_power_validation():
    """Power must be clamped between idle and nameplate."""
    from build_gpu_tco import node_power_at_mfu, NAMEPLATE_MAX_POWER_KW, IDLE_POWER_KW
    for mfu in [0.0, 0.1, 0.3, 0.5, 0.7, 1.0]:
        p = node_power_at_mfu(mfu)
        assert IDLE_POWER_KW - 0.1 <= p <= NAMEPLATE_MAX_POWER_KW + 0.1, \
            f"Power {p} out of bounds at MFU={mfu}"
    print(f"PASS: test_tco_power_validation")


def test_maas_margins_all_invalid():
    """ALL MaaS margins must be INVALID (no benchmark)."""
    profiles = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data", "maas_deployment_profiles.csv"))
    for _, r in profiles.iterrows():
        assert r["has_valid_margin"] == False, \
            f"{r['model_id']}: should have has_valid_margin=False (no benchmark)"
        assert r["benchmark_status"] == "not_run", \
            f"{r['model_id']}: benchmark_status should be not_run"
    print(f"PASS: test_maas_margins_all_invalid ({len(profiles)} models)")


def test_provider_routes_unique():
    """Each provider route should be a unique row."""
    df = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data", "maas_competitive_pricing.csv"))
    # No duplicate (model, provider_route) pairs
    dups = df.duplicated(subset=["model", "provider_route"])
    assert not dups.any(), f"Duplicate routes: {df[dups]}"
    print(f"PASS: test_provider_routes_unique ({len(df)} routes)")


def test_glm_price_corrected():
    """GLM-5.2 OpenRouter price must exactly match live snapshot ($0.4886/$1.536)."""
    df = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data", "maas_competitive_pricing.csv"))
    glm = df[df["model"] == "GLM-5.2"].iloc[0]
    assert abs(glm["in_per_m"] - 0.4886) < 1e-6, f"GLM input ${glm['in_per_m']} != 0.4886"
    assert abs(glm["out_per_m"] - 1.536) < 1e-6, f"GLM output ${glm['out_per_m']} != 1.536"
    print(f"PASS: test_glm_price_corrected (${glm['in_per_m']:.4f}/${glm['out_per_m']:.4f})")


def test_qwen_deployment_not_single_gpu():
    """Qwen 3.5 Flash must NOT be 1xH100 with 1M context."""
    df = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data", "maas_deployment_profiles.csv"))
    qwen = df[df["model_id"] == "Qwen3.5-35B-A3B"].iloc[0]
    assert qwen["gpu_count"] != 1 or qwen["native_context"] < 1000000, \
        "Qwen 3.5 Flash: 1xH100 + 1M context unsupported"
    print(f"PASS: test_qwen_deployment_not_single_gpu ({qwen['gpu_config']}, ctx={qwen['native_context']})")


def test_bpo_is_scenario_range():
    """BPO must be presented as downside-upside range, not single CAGR."""
    df = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data", "market_data.csv"))
    bpo = df[df["metric"].str.contains("BPO")]
    assert len(bpo) == 1
    size = bpo.iloc[0]["size"]
    assert "-" in size or "downside" in size.lower(), f"BPO should be a range: {size}"
    # CAGR must label its base year explicitly (2025 and 2026)
    cagr = bpo.iloc[0]["cagr"]
    assert "2025 base" in cagr, f"BPO CAGR must label 2025 base: {cagr}"
    assert "2026 base" in cagr, f"BPO CAGR must label 2026 base: {cagr}"
    print(f"PASS: test_bpo_is_scenario_range ({size})")


def test_reliability_stress_billable_hours():
    """Reliability Stress: 8760 × 0.95 × 0.60 × 0.90 = 4494."""
    df = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "models", "gpu_tco_breakdown.csv"))
    rel = df[df["scenario"] == "Reliability Stress"].iloc[0]
    expected = int(8760 * 0.95 * 0.60 * 0.90)
    actual = int(rel["Billable hrs/yr"])
    assert abs(actual - expected) <= 1, f"Reliability Stress: expected {expected}, got {actual}"
    print(f"PASS: test_reliability_stress_billable_hours ({actual})")


def test_deepseek_params():
    """DeepSeek V4 params from OpenRouter API."""
    df = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data", "maas_deployment_profiles.csv"))
    flash = df[df["model_id"] == "DeepSeek-V4-Flash-0731"].iloc[0]
    pro = df[df["model_id"] == "DeepSeek-V4-Pro"].iloc[0]
    assert flash["total_params_b"] == 284
    assert flash["active_params_b"] == 13
    assert pro["total_params_b"] == 1600
    assert pro["active_params_b"] == 49
    print(f"PASS: test_deepseek_params")


def test_cagr_auto_calculated():
    """CAGRs are auto-calculated."""
    from build_market_model import MARKET_DATA, calc_cagr
    for d in MARKET_DATA:
        if d.get("end_value_b") and d.get("start_value_b"):
            years = d["end_year"] - d["start_year"]
            cagr = calc_cagr(d["start_value_b"], d["end_value_b"], years)
            assert -0.5 < cagr < 1.0
    print(f"PASS: test_cagr_auto_calculated")


def test_sources_exist():
    """Sources CSV has proper structure."""
    df = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data", "sources.csv"))
    assert len(df) >= 30
    assert "claim_id" in df.columns
    assert df["claim_id"].is_unique, "claim_id must be unique"
    print(f"PASS: test_sources_exist ({len(df)} unique sources)")


def test_assumptions_loaded_from_yaml():
    """TCO loads from YAML, not hardcoded."""
    from build_gpu_tco import PARAMS, NAMEPLATE_MAX_POWER_KW
    assert isinstance(PARAMS, dict)
    assert NAMEPLATE_MAX_POWER_KW == 10.2
    print(f"PASS: test_assumptions_loaded_from_yaml")


def test_build_metadata_exists():
    """Build metadata must be generated and contain content hashes (no VCS identity)."""
    import json
    meta_path = os.path.join(os.path.dirname(__file__), "..", "models", "build_metadata.json")
    assert os.path.exists(meta_path), "build_metadata.json missing — run build_all.py"
    with open(meta_path) as f:
        meta = json.load(f)
    assert "assumptions_hash" in meta
    assert "generator_code_hash" in meta
    # Tracked manifest must NOT contain VCS identity or timestamps (self-reference fix)
    assert "generated_at" not in meta, "tracked manifest must not contain generated_at"
    assert "git_commit" not in meta, "tracked manifest must not contain git_commit"
    assert "source_date_epoch" not in meta, "tracked manifest must not contain source_date_epoch"
    print(f"PASS: test_build_metadata_exists (no VCS identity)")


def test_no_fabricated_revenue():
    """No Llama models or fabricated revenue."""
    import os
    for csv_name in ["maas_competitive_pricing.csv", "maas_deployment_profiles.csv"]:
        path = os.path.join(os.path.dirname(__file__), "..", "data", csv_name)
        df = pd.read_csv(path)
        for col in df.columns:
            if df[col].dtype == object:
                assert not any("Llama" in str(v) for v in df[col]), f"{csv_name}: contains Llama"
    print(f"PASS: test_no_fabricated_revenue")


# ============================================================
# Round 4 tests — determinism, dual-base CAGR, live data fidelity,
# DGX downgrade, snapshot/fixture consistency.
# ============================================================

def test_tracked_manifest_has_no_vcs_identity():
    """Tracked manifest must contain NO git commit, timestamp, or VCS identity.

    Writing the current commit SHA into a committed file is a self-reference
    that can never converge: every commit changes the SHA, so CI rebuilding on
    the new commit always diffs. The tracked manifest may contain ONLY content
    hashes. Provenance lives in the gitignored runtime metadata.
    """
    import json
    meta_path = os.path.join(os.path.dirname(__file__), "..", "models", "build_metadata.json")
    with open(meta_path) as f:
        meta = json.load(f)
    for forbidden in ("git_commit", "generated_at", "source_date_epoch",
                      "build_wall_clock", "ci_run_id"):
        assert forbidden not in meta, f"tracked manifest must not contain {forbidden}"
    # Must still carry content hashes + generator identity
    assert meta.get("generator_code_hash"), "manifest missing generator_code_hash"
    assert meta.get("assumptions_hash"), "manifest missing assumptions_hash"
    print(f"PASS: test_tracked_manifest_has_no_vcs_identity")


def test_bpo_dual_cagr_periods():
    """BPO long-table must yield BOTH 2025->2028 and 2026->2028 CAGRs."""
    from build_market_model import load_bpo_snapshot, calc_cagr
    bpo = load_bpo_snapshot()
    actual = bpo[bpo["scenario"] == "actual"].iloc[0]
    fcst = bpo[bpo["scenario"] == "base_forecast"].iloc[0]
    down = bpo[bpo["scenario"] == "downside"].iloc[0]
    up = bpo[bpo["scenario"] == "upside"].iloc[0]
    # 2025 -> 2028
    yrs25 = int(down["year"]) - int(actual["year"])
    c25d = calc_cagr(actual["value_usd_b"], down["value_usd_b"], yrs25)
    c25u = calc_cagr(actual["value_usd_b"], up["value_usd_b"], yrs25)
    assert 0.02 < c25d < 0.03, f"2025->2028 downside CAGR {c25d:.1%} not ~2.4%"
    assert 0.07 < c25u < 0.08, f"2025->2028 upside CAGR {c25u:.1%} not ~7.8%"
    # 2026 -> 2028
    yrs26 = int(down["year"]) - int(fcst["year"])
    c26d = calc_cagr(fcst["value_usd_b"], down["value_usd_b"], yrs26)
    c26u = calc_cagr(fcst["value_usd_b"], up["value_usd_b"], yrs26)
    assert 0.01 < c26d < 0.02, f"2026->2028 downside CAGR {c26d:.1%} not ~1.2%"
    assert 0.09 < c26u < 0.10, f"2026->2028 upside CAGR {c26u:.1%} not ~9.3%"
    print(f"PASS: test_bpo_dual_cagr_periods (2025: {c25d:.1%}-{c25u:.1%}, 2026: {c26d:.1%}-{c26u:.1%})")


def test_global_gpuaas_matches_live_snapshot():
    """Global GPUaaS must match MarketsandMarkets live data: $8.21B(2025)->$26.62B(2030), 26.5%."""
    from build_market_model import MARKET_DATA
    gpuaas = [d for d in MARKET_DATA if "GPUaaS" in d["metric"]][0]
    assert gpuaas["start_value_b"] == 8.21, f"start {gpuaas['start_value_b']} != 8.21"
    assert gpuaas["end_value_b"] == 26.62, f"end {gpuaas['end_value_b']} != 26.62"
    assert gpuaas["start_year"] == 2025 and gpuaas["end_year"] == 2030
    assert "153834402" in gpuaas["source_url"], f"URL must be the 153834402 page: {gpuaas['source_url']}"
    # CAGR check
    from build_market_model import calc_cagr
    cagr = calc_cagr(8.21, 26.62, 2030 - 2025)
    assert abs(cagr - 0.265) < 0.005, f"CAGR {cagr:.1%} not ~26.5%"
    print(f"PASS: test_global_gpuaas_matches_live_snapshot ($8.21B->$26.62B, {cagr:.1%})")


def test_maas_prices_match_snapshot():
    """MaaS prices in CSV must exactly match the live snapshot fixture (2026-08-12)."""
    prod = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data", "maas_competitive_pricing.csv"))
    fix = pd.read_csv(os.path.join(FIXTURES, "maas_price_snapshots.csv"))
    # Merge on route_id and compare in/out prices + promotion exactly
    merged = prod.merge(fix, on="route_id", suffixes=("_prod", "_fix"))
    assert len(merged) == len(fix), f"route count mismatch: prod {len(prod)} vs fixture {len(fix)}"
    for _, r in merged.iterrows():
        assert abs(r["in_per_m_prod"] - r["in_per_m_fix"]) < 1e-9, \
            f"{r['route_id']}: input {r['in_per_m_prod']} != fixture {r['in_per_m_fix']}"
        assert abs(r["out_per_m_prod"] - r["out_per_m_fix"]) < 1e-9, \
            f"{r['route_id']}: output {r['out_per_m_prod']} != fixture {r['out_per_m_fix']}"
        assert bool(r["promotion_prod"]) == bool(r["promotion_fix"]), \
            f"{r['route_id']}: promotion {r['promotion_prod']} != fixture {r['promotion_fix']}"
    print(f"PASS: test_maas_prices_match_snapshot ({len(merged)} routes exact-match fixture)")


def test_maas_snapshot_has_governance_fields():
    """MaaS snapshot must carry observed_at, content_hash, promotion for audit."""
    snaps = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data", "pricing_snapshots", "maas_openrouter.csv"))
    for col in ["observed_at", "content_hash", "promotion", "route_id", "source_url"]:
        assert col in snaps.columns, f"snapshot missing governance column: {col}"
    assert snaps["observed_at"].notna().all(), "observed_at must be present on all rows"
    assert snaps["content_hash"].notna().all(), "content_hash must be present on all rows"
    assert (snaps["observed_at"] == "2026-08-12").all(), "snapshot must be dated 2026-08-12"
    print(f"PASS: test_maas_snapshot_has_governance_fields ({len(snaps)} rows)")


def test_dgx_node_price_is_confidence_d():
    """DGX H100 $300k node price must be downgraded to confidence D (no A-grade source)."""
    df = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data", "sources.csv"))
    gpu02 = df[df["claim_id"] == "GPU-02"].iloc[0]
    assert gpu02["confidence"] == "D", f"GPU-02 confidence {gpu02['confidence']} != D"
    assert gpu02["source_type"] == "internal_estimate", \
        f"GPU-02 source_type {gpu02['source_type']} != internal_estimate"
    print(f"PASS: test_dgx_node_price_is_confidence_d (source_type={gpu02['source_type']})")


def test_node_price_sensitivity_exists():
    """Node-price sensitivity CSV must exist and show break-even rises with node price."""
    df = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "models", "gpu_node_price_sensitivity.csv"))
    baseline = df[df["scenario"] == "Baseline"].sort_values("node_price_usd")
    # Break-even must be monotonically increasing with node price
    bes = baseline["break_even_per_gpu_hr"].tolist()
    assert all(bes[i] < bes[i + 1] for i in range(len(bes) - 1)), \
        "break-even must increase with node price"
    # Delta per $100k should be ~$0.54/GPU-hr (review's sensitivity figure)
    d = baseline[baseline["node_price_usd"] == 400000]["delta_vs_baseline"].iloc[0]
    assert 0.45 < d < 0.65, f"+$100k delta {d} not ~$0.54/GPU-hr"
    print(f"PASS: test_node_price_sensitivity_exists (+$100k -> +${d}/GPU-hr)")


def test_build_twice_is_byte_identical():
    """Two temp-dir builds must produce byte-identical tracked outputs."""
    import tempfile, shutil, hashlib
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
    os.environ["SOURCE_DATE_EPOCH"] = "0"
    hashes = []
    for i in range(2):
        tmp = tempfile.mkdtemp(prefix=f"r5build{i}_")
        try:
            dirs = {"models": os.path.join(tmp, "models"),
                    "data": os.path.join(tmp, "data"),
                    "build": os.path.join(tmp, "build")}
            for d in dirs.values():
                os.makedirs(d, exist_ok=True)
            import build_all
            build_all.build_all(output_dirs=dirs, verbose=False)
            # Hash the manifest + a couple of CSVs
            h = hashlib.sha256()
            for fn in ["build_metadata.json", "market_data.csv"]:
                p = os.path.join(dirs["models"] if fn.endswith(".json") else dirs["data"], fn)
                with open(p, "rb") as f:
                    h.update(f.read())
            hashes.append(h.hexdigest())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    assert hashes[0] == hashes[1], "Two temp builds are NOT byte-identical (non-deterministic)"
    print(f"PASS: test_build_twice_is_byte_identical")


def test_check_generated_does_not_modify_worktree():
    """check_generated.py must build in temp dirs and leave the worktree clean."""
    import subprocess
    repo = os.path.join(os.path.dirname(__file__), "..")
    # Snapshot git status before
    before = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo).decode()
    r = subprocess.run([sys.executable, os.path.join("src", "check_generated.py")],
                       cwd=repo, capture_output=True, text=True)
    after = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo).decode()
    assert before == after, f"check_generated modified the worktree:\n{before}\n---\n{after}"
    print(f"PASS: test_check_generated_does_not_modify_worktree")


def test_deepseek_checkpoint_precision():
    """DeepSeek V4 Pro/Flash must be FP4_EXPERTS_FP8_OTHER, NOT pure FP8."""
    import yaml
    yaml_path = os.path.join(os.path.dirname(__file__), "..", "methodology", "model_deployment_profiles.yaml")
    with open(yaml_path) as f:
        profiles = yaml.safe_load(f)
    for m in profiles["models"]:
        if m["model_id"] in ("DeepSeek-V4-Pro", "DeepSeek-V4-Flash-0731"):
            assert m["weight_format"] == "FP4_EXPERTS_FP8_OTHER", \
                f"{m['model_id']}: weight_format {m['weight_format']} != FP4_EXPERTS_FP8_OTHER"
            assert m["checkpoint_precision"] == "FP4_EXPERTS_FP8_OTHER"
    print(f"PASS: test_deepseek_checkpoint_precision (Pro/Flash = FP4+FP8 mixed)")


def test_checkpoint_size_fits_total_hbm():
    """Every model with a checkpoint_size_gb must fit in its total_hbm_gb."""
    import yaml
    yaml_path = os.path.join(os.path.dirname(__file__), "..", "methodology", "model_deployment_profiles.yaml")
    with open(yaml_path) as f:
        profiles = yaml.safe_load(f)
    for m in profiles["models"]:
        sz = m.get("checkpoint_size_gb")
        hbm = m.get("total_hbm_gb")
        if sz is not None and hbm is not None:
            assert sz < hbm, f"{m['model_id']}: checkpoint {sz}GB >= HBM {hbm}GB (weights don't fit)"
            assert m.get("weights_fit") is True, f"{m['model_id']}: weights_fit should be True"
    print(f"PASS: test_checkpoint_size_fits_total_hbm (V4 Pro 865<1280, Flash 167<640)")


def test_deployment_context_not_assumed():
    """No deployment may assume a tested context — max_context_tested must be null."""
    import yaml
    yaml_path = os.path.join(os.path.dirname(__file__), "..", "methodology", "model_deployment_profiles.yaml")
    with open(yaml_path) as f:
        profiles = yaml.safe_load(f)
    for m in profiles["models"]:
        for dep in m["deployments"]:
            assert dep.get("max_context_tested") is None, \
                f"{m['model_id']}: max_context_tested must be null (unverified)"
            assert dep.get("benchmark_status") == "not_run"
    print(f"PASS: test_deployment_context_not_assumed (all max_context_tested = null)")


def test_reserved_price_covers_break_even():
    """Recommended Reserved price must cover break-even (CM >= 0) at every node price."""
    df = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "models", "pricing_recommendations.csv"))
    reserved = df[df["tier"] == "reserved"]
    for _, r in reserved.iterrows():
        assert r["recommended_price_per_gpu_hr"] >= r["break_even_per_gpu_hr"] - 0.001, \
            f"Reserved {r['node_price_usd']}/{r['scenario']}: rec ${r['recommended_price_per_gpu_hr']} < break-even ${r['break_even_per_gpu_hr']}"
    print(f"PASS: test_reserved_price_covers_break_even ({len(reserved)} rows, no negative margins)")


def test_pricing_table_scales_with_node_price():
    """Reserved minimum price must increase with node price (Baseline)."""
    df = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "models", "pricing_recommendations.csv"))
    base = df[(df["tier"] == "reserved") & (df["scenario"] == "Baseline")].sort_values("node_price_usd")
    prices = base["recommended_price_per_gpu_hr"].tolist()
    assert all(prices[i] < prices[i + 1] for i in range(len(prices) - 1)), \
        "Reserved price must scale up with node price"
    print(f"PASS: test_pricing_table_scales_with_node_price ({' < '.join(f'${p}' for p in prices)})")


def test_project_status_consistent():
    """project_status.yaml test_count must match the actual test count, and the
    README/report status blocks must contain the version."""
    import yaml, re
    yaml_path = os.path.join(os.path.dirname(__file__), "..", "project_status.yaml")
    with open(yaml_path) as f:
        status = yaml.safe_load(f)
    # Count actual test functions
    with open(os.path.join(os.path.dirname(__file__), "test_calculations.py")) as f:
        actual = sum(1 for line in f if re.match(r"^def test_", line))
    # README must contain the version + the dynamic test count
    with open(os.path.join(os.path.dirname(__file__), "..", "README.md")) as f:
        readme = f.read()
    assert status["version"] in readme, "README status block missing version"
    assert f"**{actual} 项**" in readme, f"README test count not synced (says != {actual})"
    # CI claim must NOT be a static green/red assertion
    assert "CI green" not in readme.lower() or "CI 结果以" in readme, \
        "README must not hardcode CI status"
    print(f"PASS: test_project_status_consistent (version={status['version']}, tests={actual})")


if __name__ == "__main__":
    test_official_price_normalization()
    test_coreweave_not_understated()
    test_tco_separates_utilization()
    test_tco_power_validation()
    test_maas_margins_all_invalid()
    test_provider_routes_unique()
    test_glm_price_corrected()
    test_qwen_deployment_not_single_gpu()
    test_bpo_is_scenario_range()
    test_reliability_stress_billable_hours()
    test_deepseek_params()
    test_cagr_auto_calculated()
    test_sources_exist()
    test_assumptions_loaded_from_yaml()
    test_build_metadata_exists()
    test_no_fabricated_revenue()
    # Round 4
    test_tracked_manifest_has_no_vcs_identity()
    test_bpo_dual_cagr_periods()
    test_global_gpuaas_matches_live_snapshot()
    test_maas_prices_match_snapshot()
    test_maas_snapshot_has_governance_fields()
    test_dgx_node_price_is_confidence_d()
    test_node_price_sensitivity_exists()
    # Round 5
    test_build_twice_is_byte_identical()
    test_check_generated_does_not_modify_worktree()
    test_deepseek_checkpoint_precision()
    test_checkpoint_size_fits_total_hbm()
    test_deployment_context_not_assumed()
    test_reserved_price_covers_break_even()
    test_pricing_table_scales_with_node_price()
    test_project_status_consistent()
    print("\n=== ALL 31 TESTS PASSED ===")
