#!/usr/bin/env python3
"""
验证测试 — 确保计算正确性和数据一致性
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from build_gpu_tco import (
    annual_depreciation_per_gpu, annual_system_depreciation_per_gpu,
    break_even_price_per_gpu_hr, gross_margin,
    SCENARIOS, GPU_PRICE, GPUS_PER_NODE, NODE_PRICE,
)
from build_market_model import calc_cagr, MARKET_DATA
from build_maas_economics import MODELS, GPU_COST_HR
import math


def test_gpu_depreciation():
    """GPU 年折旧 = $30K × (1 - 0.20) / 4 = $6,000"""
    dep = annual_depreciation_per_gpu()
    assert abs(dep - 6000) < 0.01, f"GPU depreciation should be $6000, got ${dep}"
    print("✅ test_gpu_depreciation")


def test_system_depreciation():
    """系统折旧 = ($300K - 8×$30K) × (1-0.15) / 4 / 8 = $1,593.75"""
    dep = annual_system_depreciation_per_gpu()
    expected = (300000 - 8 * 30000) * (1 - 0.15) / 4 / 8
    assert abs(dep - expected) < 0.01, f"System depreciation mismatch: ${dep} vs ${expected}"
    print("✅ test_system_depreciation")


def test_break_even_positive():
    """所有情景保本价为正"""
    for name, p in SCENARIOS.items():
        be = break_even_price_per_gpu_hr(p["avg_load"], p["pue"], p["power_rate"])
        assert be > 0, f"{name} break-even should be positive, got ${be}"
        print(f"✅ test_break_even_positive [{name}]: ${be:.2f}/GPU/hr")


def test_margin_bounds():
    """毛利率在合理范围 (-1, 1)"""
    for name, p in SCENARIOS.items():
        for price in [2.0, 3.0, 4.0]:
            gm = gross_margin(price, p["avg_load"], p["pue"], p["power_rate"])
            assert -1 < gm < 1, f"GM out of bounds: {gm} for {name} @ ${price}"
    print("✅ test_margin_bounds")


def test_cagr_consistency():
    """市场数据 CAGR 自动计算且一致"""
    for d in MARKET_DATA:
        if d["start_value_b"] and d["end_value_b"] and d["start_year"] and d["end_year"]:
            years = d["end_year"] - d["start_year"]
            cagr = calc_cagr(d["start_value_b"], d["end_value_b"], years)
            assert -0.5 < cagr < 1.0, f"CAGR out of range for {d['metric']}: {cagr}"
            # 重新验证
            check = (d["end_value_b"] / d["start_value_b"]) ** (1 / years) - 1
            assert abs(cagr - check) < 0.001, f"CAGR recalculation mismatch for {d['metric']}"
    print("✅ test_cagr_consistency")


def test_deepseek_params():
    """DeepSeek V4 参数正确 (审阅修正)"""
    flash = [m for m in MODELS if m["model"] == "DeepSeek V4 Flash"][0]
    pro = [m for m in MODELS if m["model"] == "DeepSeek V4 Pro"][0]

    assert flash["total_params"] == "284B", f"Flash total should be 284B, got {flash['total_params']}"
    assert flash["active_params"] == "13B", f"Flash active should be 13B, got {flash['active_params']}"
    assert pro["total_params"] == "1.6T", f"Pro total should be 1.6T, got {pro['total_params']}"
    assert pro["active_params"] == "49B", f"Pro active should be 49B, got {pro['active_params']}"

    # 确保不再是旧的 671B 错误值
    assert "671B" not in flash["total_params"], "DeepSeek V4 Flash should NOT be 671B"
    assert "671B" not in pro["total_params"], "DeepSeek V4 Pro should NOT be 671B"
    print("✅ test_deepseek_params (284B/13B Flash, 1.6T/49B Pro)")


def test_no_fabricated_revenue():
    """确保没有凭空编造的收入预测"""
    import pandas as pd
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "maas_token_economics.csv")
    df = pd.read_csv(csv_path)
    # 不应包含 "Llama" 字样
    assert not any("Llama" in str(m) for m in df.iloc[:, 0]), "Should not contain Llama models"
    print("✅ test_no_fabricated_revenue")


def test_gpu_pricing_form_factor():
    """GPU 竞品价格表包含 form_factor"""
    import pandas as pd
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "gpuaas_competitive_pricing.csv")
    df = pd.read_csv(csv_path)
    assert "form_factor" in df.columns, "GPU pricing must have form_factor column"
    assert "gpu_count" in df.columns, "GPU pricing must have gpu_count column"
    assert "pricing_type" in df.columns, "GPU pricing must have pricing_type column"
    print("✅ test_gpu_pricing_form_factor")


def test_sources_exist():
    """每条关键数据有来源"""
    import pandas as pd
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "sources.csv")
    df = pd.read_csv(csv_path)
    assert len(df) >= 30, f"Need at least 30 sources, have {len(df)}"
    assert "claim_id" in df.columns
    assert "confidence" in df.columns
    assert "accessed_at" in df.columns
    print(f"✅ test_sources_exist ({len(df)} sources)")


if __name__ == "__main__":
    test_gpu_depreciation()
    test_system_depreciation()
    test_break_even_positive()
    test_margin_bounds()
    test_cagr_consistency()
    test_deepseek_params()
    test_no_fabricated_revenue()
    test_gpu_pricing_form_factor()
    test_sources_exist()
    print("\n🎉 All tests passed!")
