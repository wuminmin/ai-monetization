#!/usr/bin/env python3
"""
MaaS Unit Economics — self-hosted open models
Round 2 fixes:
  - GPU cost uses calendar_cost_per_gpu_hour (annual_tco / 8760 / gpu_count)
  - Throughput labeled as active-state estimate, not SLA goodput
  - GPT-OSS memory formula corrected (117B × 4bit / 8 = 58.5GB, MXFP4)
  - Model revision added for reproducibility
  - Provider routes separated (one row per route)
  - Margin labeled "theoretical sensitivity" not production margin
"""

import pandas as pd
import sys
import os

# Import TCO for calendar cost
sys.path.insert(0, os.path.dirname(__file__))
from build_gpu_tco import (
    SCENARIOS, annual_tco_per_gpu, PARAMS
)


def calendar_cost_per_gpu_hour(scenario_key="baseline"):
    """Calendar-hour GPU cost = annual TCO / 8760 / gpu_count.
    This is the cost of owning one GPU for one calendar hour,
    regardless of utilization.
    """
    s = SCENARIOS[scenario_key]
    annual = annual_tco_per_gpu(s)
    return annual / 8760


def active_cost_per_gpu_hour(scenario_key="baseline"):
    """Active-hour GPU cost = calendar_cost / availability / comm_util / billing_eff.
    This is the cost of one GPU-hour that is actually billed to a customer.
    """
    s = SCENARIOS[scenario_key]
    cal = calendar_cost_per_gpu_hour(scenario_key)
    return cal / s["service_availability"] / s["commercial_utilization"] / s["billing_efficiency"]


# Using baseline scenario for MaaS cost basis
GPU_CALENDAR_COST_HR = calendar_cost_per_gpu_hour("baseline")
GPU_ACTIVE_COST_HR = active_cost_per_gpu_hour("baseline")


# ============================================================
# Models — with full specifications and revisions
# Source: OpenRouter API descriptions (accessed 2026-08-11)
# Throughput = ACTIVE-STATE estimate, not calendar-average or SLA goodput
# ============================================================

MODELS = [
    {
        "model": "DeepSeek V4 Flash",
        "model_revision": "deepseek-v4-flash (20260423)",
        "total_params": "284B",
        "active_params": "13B",
        "arch": "MoE",
        "context": "1M",
        "gpu_config": "8xH100",
        "gpu_count": 8,
        "precision": "FP8",
        "est_throughput_tps": 35000,
        "throughput_note": "Active-state estimate. Real goodput depends on workload profile (input/output len, concurrency, SLA). Needs benchmark.",
    },
    {
        "model": "DeepSeek V4 Pro",
        "model_revision": "deepseek-v4-pro (20260423)",
        "total_params": "1.6T",
        "active_params": "49B",
        "arch": "MoE",
        "context": "1M",
        "gpu_config": "16xH100",
        "gpu_count": 16,
        "precision": "FP8",
        "est_throughput_tps": 22000,
        "throughput_note": "Multi-node (TP=8, PP=2). Active-state estimate. Needs benchmark.",
    },
    {
        "model": "Qwen 3.5 Flash",
        "model_revision": "qwen3.5-flash (20260223)",
        "total_params": "~30B",
        "active_params": "~3B",
        "arch": "MoE (linear attention hybrid)",
        "context": "1M",
        "gpu_config": "1xH100",
        "gpu_count": 1,
        "precision": "FP8",
        "est_throughput_tps": 28000,
        "throughput_note": "Linear attention + MoE. Active-state estimate. Needs benchmark.",
    },
    {
        "model": "Qwen 3.5 9B",
        "model_revision": "qwen3.5-9b",
        "total_params": "9B",
        "active_params": "9B (dense)",
        "arch": "Dense",
        "context": "256K",
        "gpu_config": "1xH100",
        "gpu_count": 1,
        "precision": "BF16",
        "est_throughput_tps": 14000,
        "throughput_note": "Dense model. Active-state estimate. Needs benchmark.",
    },
    {
        "model": "GPT-OSS 120B",
        "model_revision": "gpt-oss-120b",
        "total_params": "117B",
        "active_params": "5.1B",
        "arch": "MoE",
        "context": "128K",
        "gpu_config": "2xH100",
        "gpu_count": 2,
        "precision": "MXFP4 (117B x 4bit / 8 = 58.5GB, fits 1x H100)",
        "est_throughput_tps": 20000,
        "throughput_note": "MXFP4 fits single H100. 2-card config is throughput deployment choice. Active-state estimate. Needs benchmark.",
    },
    {
        "model": "Gemma 4 31B",
        "model_revision": "gemma-4-31b-it",
        "total_params": "30.7B",
        "active_params": "30.7B (dense)",
        "arch": "Dense",
        "context": "256K",
        "gpu_config": "1xH100",
        "gpu_count": 1,
        "precision": "BF16 (weights ~62GB; KV cache limited on 80GB card; INT8 needed for high concurrency)",
        "est_throughput_tps": 12000,
        "throughput_note": "BF16 weights occupy 62/80GB. Active-state estimate. Needs benchmark.",
    },
    {
        "model": "GLM-5.2",
        "model_revision": "glm-5.2 (20260616)",
        "total_params": "~350B",
        "active_params": "~32B",
        "arch": "MoE (reasoning)",
        "context": "1M",
        "gpu_config": "8xH100",
        "gpu_count": 8,
        "precision": "FP8",
        "est_throughput_tps": 25000,
        "throughput_note": "Reasoning model with thinking. Active-state estimate. Needs benchmark.",
    },
]


# ============================================================
# Competitor pricing — one provider route per row
# Source: OpenRouter API + direct API pages (accessed 2026-08-11)
# ============================================================

COMPETITOR_PRICES = [
    {"model": "DeepSeek V4 Flash", "provider_route": "DeepSeek API direct", "in_per_m": 0.14, "out_per_m": 0.28, "url": "api-docs.deepseek.com"},
    {"model": "DeepSeek V4 Flash", "provider_route": "OpenRouter", "in_per_m": 0.14, "out_per_m": 0.28, "url": "openrouter.ai/deepseek/deepseek-v4-flash"},
    {"model": "DeepSeek V4 Pro", "provider_route": "DeepSeek API direct", "in_per_m": 0.63, "out_per_m": 1.26, "url": "api-docs.deepseek.com"},
    {"model": "DeepSeek V4 Pro", "provider_route": "OpenRouter", "in_per_m": 0.63, "out_per_m": 1.26, "url": "openrouter.ai/deepseek/deepseek-v4-pro"},
    {"model": "Qwen 3.5 Flash", "provider_route": "Qwen API (Alibaba)", "in_per_m": 0.065, "out_per_m": 0.26, "url": "dashscope.aliyun.com"},
    {"model": "Qwen 3.5 Flash", "provider_route": "OpenRouter", "in_per_m": 0.065, "out_per_m": 0.26, "url": "openrouter.ai/qwen/qwen3.5-flash"},
    {"model": "Qwen 3.5 9B", "provider_route": "OpenRouter", "in_per_m": 0.10, "out_per_m": 0.15, "url": "openrouter.ai/qwen/qwen3.5-9b"},
    {"model": "GPT-OSS 120B", "provider_route": "OpenRouter", "in_per_m": 0.037, "out_per_m": 0.17, "url": "openrouter.ai/openai/gpt-oss-120b"},
    {"model": "Gemma 4 31B", "provider_route": "OpenRouter", "in_per_m": 0.10, "out_per_m": 0.34, "url": "openrouter.ai/google/gemma-4-31b-it"},
    {"model": "GLM-5.2", "provider_route": "Z.AI API direct", "in_per_m": 0.76, "out_per_m": 2.42, "url": "docs.z.ai"},
    {"model": "GLM-5.2", "provider_route": "OpenRouter", "in_per_m": 0.76, "out_per_m": 2.42, "url": "openrouter.ai/z-ai/glm-5.2"},
]


def calc_unit_economics(m, comp_in, comp_out, pricing_factor=0.85):
    """Calculate unit economics using ACTIVE GPU cost (not calendar)."""
    # Cost per M tokens using active GPU cost
    gpu_cost_hr = GPU_ACTIVE_COST_HR * m["gpu_count"]
    tokens_per_hr = m["est_throughput_tps"] * 3600
    cost_per_m = gpu_cost_hr / (tokens_per_hr / 1e6)

    suggested_in = comp_in * pricing_factor
    suggested_out = comp_out * pricing_factor

    # Blended reference: 70% input, 30% output (scenario-specific, not universal)
    blended_price = suggested_in * 0.7 + suggested_out * 0.3
    blended_gm = (blended_price - cost_per_m) / blended_price if blended_price > 0 else -1

    return {
        "model": m["model"],
        "revision": m["model_revision"],
        "total_params": m["total_params"],
        "active_params": m["active_params"],
        "arch": m["arch"],
        "context": m["context"],
        "gpu_config": m["gpu_config"],
        "precision": m["precision"],
        "est_throughput_tps": m["est_throughput_tps"],
        "cost_per_m_active": round(cost_per_m, 4),
        "comp_in": comp_in,
        "comp_out": comp_out,
        "suggested_in": round(suggested_in, 4),
        "suggested_out": round(suggested_out, 4),
        "blended_gm_theoretical": round(blended_gm, 4),
        "throughput_note": m["throughput_note"],
    }


def build_maas_table():
    rows = []
    # Pricing factors by model tier
    factors = {
        "DeepSeek V4 Flash": 0.95,
        "DeepSeek V4 Pro": 0.70,
        "Qwen 3.5 Flash": 0.85,
        "Qwen 3.5 9B": 0.85,
        "GPT-OSS 120B": 0.95,
        "Gemma 4 31B": 0.85,
        "GLM-5.2": 0.70,
    }
    for m in MODELS:
        # Use first competitor price for main row
        comp = [c for c in COMPETITOR_PRICES if c["model"] == m["model"]][0]
        factor = factors.get(m["model"], 0.85)
        r = calc_unit_economics(m, comp["in_per_m"], comp["out_per_m"], factor)
        r["provider_route"] = comp["provider_route"]
        rows.append(r)
    return pd.DataFrame(rows)


def build_competitor_pricing_table():
    """One row per provider route."""
    rows = []
    model_map = {m["model"]: m for m in MODELS}
    for c in COMPETITOR_PRICES:
        m = model_map[c["model"]]
        rows.append({
            "model": c["model"],
            "revision": m["model_revision"],
            "provider_route": c["provider_route"],
            "in_per_m": c["in_per_m"],
            "out_per_m": c["out_per_m"],
            "total_params": m["total_params"],
            "active_params": m["active_params"],
            "arch": m["arch"],
            "source_url": c["url"],
            "accessed": "2026-08-11",
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    pd.set_option("display.width", 200)

    print("=" * 100)
    print("  MaaS Unit Economics (theoretical sensitivity, NOT production margin)")
    print(f"  GPU calendar cost: ${GPU_CALENDAR_COST_HR:.3f}/hr | Active cost: ${GPU_ACTIVE_COST_HR:.3f}/hr")
    print(f"  NOTE: Throughput = active-state ESTIMATE, not SLA goodput.")
    print(f"  NOTE: Blended GM uses 70/30 input/output — workload-specific, not universal.")
    print("=" * 100)

    df = build_maas_table()
    for _, r in df.iterrows():
        print(f"\n  {r['model']} ({r['total_params']}/{r['active_params']})")
        print(f"    Revision: {r['revision']}")
        print(f"    GPU: {r['gpu_config']} ({r['precision']})")
        print(f"    Throughput: {r['est_throughput_tps']:,} tok/s (active estimate)")
        print(f"    Cost: ${r['cost_per_m_active']:.4f}/M tok (active GPU cost)")
        print(f"    Competitor ({r['provider_route']}): ${r['comp_in']:.4f}/M_in, ${r['comp_out']:.4f}/M_out")
        print(f"    Suggested: ${r['suggested_in']:.4f}/M_in, ${r['suggested_out']:.4f}/M_out")
        print(f"    Blended GM (theoretical): {r['blended_gm_theoretical']:.1%}")
