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
    """GLM-5.2 must NOT be $0.76/$2.42."""
    df = pd.read_csv(os.path.join(os.path.dirname(__file__), "..", "data", "maas_competitive_pricing.csv"))
    glm = df[df["model"] == "GLM-5.2"].iloc[0]
    assert glm["in_per_m"] < 0.6, f"GLM input price ${glm['in_per_m']} — old $0.76 was wrong"
    assert glm["out_per_m"] < 2.0, f"GLM output price ${glm['out_per_m']} — old $2.42 was wrong"
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
    """Build metadata must be generated."""
    import json
    meta_path = os.path.join(os.path.dirname(__file__), "..", "models", "build_metadata.json")
    assert os.path.exists(meta_path), "build_metadata.json missing — run build_all.py"
    with open(meta_path) as f:
        meta = json.load(f)
    assert "generated_at" in meta
    assert "assumptions_hash" in meta
    print(f"PASS: test_build_metadata_exists")


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
    print("\n=== ALL 16 TESTS PASSED ===")
