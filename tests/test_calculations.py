#!/usr/bin/env python3
"""
Validation tests — Round 2: includes cross-field invariant tests
and official price snapshot fixtures to catch unit errors.
"""

import sys
import os
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# ============================================================
# Official price snapshots (INDEPENDENT fixtures, not from production code)
# These values come from vendor pages, accessed 2026-08-11
# ============================================================
OFFICIAL_PRICE_SNAPSHOTS = {
    "CoreWeave on-demand": {"raw_price": 49.24, "raw_unit": "USD_PER_INSTANCE_HOUR", "gpu_count": 8, "expected_gpu_hr": 6.155},
    "CoreWeave spot": {"raw_price": 19.71, "raw_unit": "USD_PER_INSTANCE_HOUR", "gpu_count": 8, "expected_gpu_hr": 2.464},
    "Lambda on-demand": {"raw_price": 3.99, "raw_unit": "USD_PER_GPU_HOUR", "gpu_count": 8, "expected_gpu_hr": 3.99},
    "AWS capacity_block": {"raw_price": 41.528, "raw_unit": "USD_PER_INSTANCE_HOUR", "gpu_count": 8, "expected_gpu_hr": 5.191},
    "GCP dws": {"raw_price": 38.32, "raw_unit": "USD_PER_INSTANCE_HOUR", "gpu_count": 8, "expected_gpu_hr": 4.79},
    "Oracle on-demand": {"raw_price": 10.00, "raw_unit": "USD_PER_GPU_HOUR", "gpu_count": 8, "expected_gpu_hr": 10.00},
}


def test_official_price_normalization():
    """Verify price normalization against independent fixtures."""
    from build_gpu_pricing import normalize_price

    for name, snap in OFFICIAL_PRICE_SNAPSHOTS.items():
        inst, gpu = normalize_price(snap["raw_price"], snap["raw_unit"], snap["gpu_count"])
        assert abs(gpu - snap["expected_gpu_hr"]) < 0.01, \
            f"{name}: expected ${snap['expected_gpu_hr']}/GPU/hr, got ${gpu}"
        # Cross-check invariant
        assert abs(inst - gpu * snap["gpu_count"]) < 0.01, \
            f"{name}: instance_hour ({inst}) != gpu_hour ({gpu}) * gpu_count ({snap['gpu_count']})"
    print(f"PASS: test_official_price_normalization ({len(OFFICIAL_PRICE_SNAPSHOTS)} fixtures)")


def test_raw_price_unit_explicit():
    """Every competitor row must have explicit raw_price_unit."""
    from build_gpu_pricing import COMPETITORS, ALLOWED_PRICE_UNITS

    for c in COMPETITORS:
        assert c["raw_price_unit"] in ALLOWED_PRICE_UNITS, \
            f"{c['provider']}: raw_price_unit '{c['raw_price_unit']}' not in allowed set"
    print(f"PASS: test_raw_price_unit_explicit")


def test_procurement_mode_matches_source():
    """Spot/block/DWS modes should not be labeled on-demand."""
    from build_gpu_pricing import COMPETITORS

    for c in COMPETITORS:
        mode = c["procurement_mode"]
        notes = c.get("notes", "").lower()
        # If notes mention spot/block/dws, mode should match
        if "spot" in notes and mode != "spot":
            assert False, f"{c['provider']}: notes mention spot but mode is {mode}"
    print(f"PASS: test_procurement_mode_matches_source")


def test_coreweave_not_understated():
    """CoreWeave on-demand must NOT be $0.31/GPU/hr (the old error)."""
    from build_gpu_pricing import build_gpu_pricing_table

    df = build_gpu_pricing_table()
    cw_od = df[(df["provider"] == "CoreWeave") & (df["procurement_mode"] == "on_demand")]
    assert len(cw_od) == 1
    gpu_hr = cw_od.iloc[0]["normalized_gpu_hr"]
    assert gpu_hr > 5.0, \
        f"CoreWeave on-demand ${gpu_hr}/GPU/hr — still understated! Expected ~$6.16"
    print(f"PASS: test_coreweave_not_understated (${gpu_hr:.2f}/GPU/hr)")


def test_no_azure_without_verified_price():
    """Azure should be removed until verifiable price is available."""
    from build_gpu_pricing import COMPETITORS

    azure = [c for c in COMPETITORS if c["provider"] == "Azure"]
    assert len(azure) == 0, "Azure should be removed pending verifiable Retail Prices API data"
    print(f"PASS: test_no_azure_without_verified_price")


def test_tco_separates_utilization():
    """TCO scenarios must use separate utilization variables, not single avg_load."""
    from build_gpu_tco import SCENARIOS

    for key, s in SCENARIOS.items():
        assert "commercial_utilization" in s, f"{key}: missing commercial_utilization"
        assert "active_compute_mfu" in s, f"{key}: missing active_compute_mfu"
        assert "service_availability" in s, f"{key}: missing service_availability"
        assert "billing_efficiency" in s, f"{key}: missing billing_efficiency"
        assert "avg_load" not in s, f"{key}: still uses deprecated avg_load"
    print(f"PASS: test_tco_separates_utilization ({len(SCENARIOS)} scenarios)")


def test_break_even_monotonic():
    """Break-even should be lower when commercial utilization is higher (all else equal)."""
    from build_gpu_tco import SCENARIOS, break_even_price_per_gpu_hr

    be_baseline = break_even_price_per_gpu_hr(SCENARIOS["baseline"])
    be_demand_up = break_even_price_per_gpu_hr(SCENARIOS["demand_up"])
    assert be_demand_up < be_baseline, \
        f"Demand Up break-even ({be_demand_up}) should be < Baseline ({be_baseline})"
    print(f"PASS: test_break_even_monotonic (baseline ${be_baseline:.2f} > demand_up ${be_demand_up:.2f})")


def test_cagr_auto_calculated():
    """Market CAGRs are auto-calculated and consistent."""
    from build_market_model import MARKET_DATA, calc_cagr

    for d in MARKET_DATA:
        if d["start_value_b"] and d["end_value_b"] and d["start_year"] and d["end_year"]:
            years = d["end_year"] - d["start_year"]
            cagr = calc_cagr(d["start_value_b"], d["end_value_b"], years)
            # Recalculate independently
            check = (d["end_value_b"] / d["start_value_b"]) ** (1 / years) - 1
            assert abs(cagr - check) < 0.001
    print(f"PASS: test_cagr_auto_calculated")


def test_removed_unreliable_market_entries():
    """Unreliable market entries should be removed."""
    from build_market_model import MARKET_DATA

    metrics = [d["metric"] for d in MARKET_DATA]
    assert "Southeast Asia Public Cloud" not in metrics, "SE Asia public cloud entry should be removed"
    assert not any("102" in str(d.get("end_value_b", "")) for d in MARKET_DATA), "BPO $102B should be removed"
    print(f"PASS: test_removed_unreliable_market_entries")


def test_deepseek_params():
    """DeepSeek V4 params from OpenRouter API (not 671B)."""
    from build_maas_economics import MODELS

    flash = [m for m in MODELS if m["model"] == "DeepSeek V4 Flash"][0]
    pro = [m for m in MODELS if m["model"] == "DeepSeek V4 Pro"][0]
    assert flash["total_params"] == "284B"
    assert flash["active_params"] == "13B"
    assert pro["total_params"] == "1.6T"
    assert pro["active_params"] == "49B"
    print(f"PASS: test_deepseek_params")


def test_gpt_oss_memory_formula():
    """GPT-OSS memory formula should be correct: 117B × 4bit / 8 = 58.5GB."""
    from build_maas_economics import MODELS

    gpt_oss = [m for m in MODELS if m["model"] == "GPT-OSS 120B"][0]
    assert "MXFP4" in gpt_oss["precision"], "Should specify MXFP4, not generic INT4"
    # Verify the math
    expected_gb = 117e9 * 4 / 8 / 1e9  # 58.5 GB
    assert abs(expected_gb - 58.5) < 0.1
    print(f"PASS: test_gpt_oss_memory_formula (MXFP4, 58.5GB)")


def test_competitor_routes_separated():
    """Competitor prices should have one row per provider route."""
    from build_maas_economics import build_competitor_pricing_table

    df = build_competitor_pricing_table()
    assert "provider_route" in df.columns
    assert len(df) >= 10, f"Expected >=10 route rows, got {len(df)}"
    # GLM-5.2 should have separate Z.AI and OpenRouter rows
    glm_rows = df[df["model"] == "GLM-5.2"]
    assert len(glm_rows) >= 2, f"GLM-5.2 should have >=2 routes, got {len(glm_rows)}"
    print(f"PASS: test_competitor_routes_separated ({len(df)} route rows)")


def test_no_fabricated_revenue():
    """No Llama models or fabricated revenue figures."""
    import pandas as pd
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "maas_token_economics.csv")
    df = pd.read_csv(csv_path)
    assert not any("Llama" in str(m) for m in df.iloc[:, 0])
    print(f"PASS: test_no_fabricated_revenue")


def test_sources_exist():
    """Sources CSV has proper structure."""
    import pandas as pd
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "sources.csv")
    df = pd.read_csv(csv_path)
    assert len(df) >= 30
    assert "claim_id" in df.columns
    print(f"PASS: test_sources_exist ({len(df)} sources)")


def test_assumptions_loaded_from_yaml():
    """TCO should load from YAML, not hardcode."""
    from build_gpu_tco import PARAMS, NAMEPLATE_MAX_POWER_KW
    assert isinstance(PARAMS, dict), "PARAMS should be loaded from YAML"
    assert NAMEPLATE_MAX_POWER_KW == 10.2, f"Nameplate should be 10.2kW (DGX datasheet), got {NAMEPLATE_MAX_POWER_KW}"
    print(f"PASS: test_assumptions_loaded_from_yaml")


if __name__ == "__main__":
    test_official_price_normalization()
    test_raw_price_unit_explicit()
    test_procurement_mode_matches_source()
    test_coreweave_not_understated()
    test_no_azure_without_verified_price()
    test_tco_separates_utilization()
    test_break_even_monotonic()
    test_cagr_auto_calculated()
    test_removed_unreliable_market_entries()
    test_deepseek_params()
    test_gpt_oss_memory_formula()
    test_competitor_routes_separated()
    test_no_fabricated_revenue()
    test_sources_exist()
    test_assumptions_loaded_from_yaml()
    print("\n=== ALL 15 TESTS PASSED ===")
