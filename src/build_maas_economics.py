#!/usr/bin/env python3
"""
MaaS Economics — competitor pricing only.
NO margin calculations: all margins INVALID pending benchmark.
GPU cost from TCO model (fully_allocated_cost_per_billable_gpu_hour).
"""

import pandas as pd
import yaml
import os

# Load deployment profiles from YAML
YAML_PATH = os.path.join(os.path.dirname(__file__), "..", "methodology", "model_deployment_profiles.yaml")


def load_deployment_profiles():
    with open(YAML_PATH, "r") as f:
        return yaml.safe_load(f)


# ============================================================
# Competitor pricing — per provider route, verified from OpenRouter API
# accessed 2026-08-11
# ============================================================
COMPETITOR_PRICES = [
    # DeepSeek V4 Flash — two OpenRouter routes
    {"model": "DeepSeek V4 Flash", "model_id": "DeepSeek-V4-Flash-0731",
     "provider_route": "OpenRouter (0731 latest)", "region": "provider_routed",
     "in_per_m": 0.08, "out_per_m": 0.18, "cached_in_per_m": None,
     "source_url": "https://openrouter.ai/deepseek/deepseek-v4-flash-0731",
     "accessed_at": "2026-08-11", "promotion": False,
     "notes": "Latest revision. Mapped to DeepSeek-V4-Flash-0731."},
    {"model": "DeepSeek V4 Flash", "model_id": "DeepSeek-V4-Flash-0731",
     "provider_route": "OpenRouter (original slug)", "region": "provider_routed",
     "in_per_m": 0.14, "out_per_m": 0.28, "cached_in_per_m": None,
     "source_url": "https://openrouter.ai/deepseek/deepseek-v4-flash",
     "accessed_at": "2026-08-11", "promotion": False,
     "notes": "Original slug being phased out in favor of 0731."},
    # DeepSeek V4 Pro
    {"model": "DeepSeek V4 Pro", "model_id": "DeepSeek-V4-Pro",
     "provider_route": "OpenRouter", "region": "provider_routed",
     "in_per_m": 0.6317, "out_per_m": 1.2634, "cached_in_per_m": None,
     "source_url": "https://openrouter.ai/deepseek/deepseek-v4-pro",
     "accessed_at": "2026-08-11", "promotion": False,
     "notes": "DeepSeek Direct API may differ (~$0.435/$0.87 per api-docs). Needs separate verification."},
    # Qwen 3.5 Flash
    {"model": "Qwen 3.5 Flash", "model_id": "Qwen3.5-35B-A3B",
     "provider_route": "OpenRouter", "region": "provider_routed",
     "in_per_m": 0.065, "out_per_m": 0.26, "cached_in_per_m": None,
     "source_url": "https://openrouter.ai/qwen/qwen3.5-flash-02-23",
     "accessed_at": "2026-08-11", "promotion": True,
     "notes": "Promotional route. Alibaba Cloud Singapore direct ~$0.10/$0.40."},
    # Qwen 3.5 9B
    {"model": "Qwen 3.5 9B", "model_id": "Qwen3.5-9B",
     "provider_route": "OpenRouter", "region": "provider_routed",
     "in_per_m": 0.10, "out_per_m": 0.15, "cached_in_per_m": None,
     "source_url": "https://openrouter.ai/qwen/qwen3.5-9b",
     "accessed_at": "2026-08-11", "promotion": False,
     "notes": ""},
    # GPT-OSS 120B
    {"model": "GPT-OSS 120B", "model_id": "gpt-oss-120b",
     "provider_route": "OpenRouter", "region": "provider_routed",
     "in_per_m": 0.037, "out_per_m": 0.17, "cached_in_per_m": None,
     "source_url": "https://openrouter.ai/openai/gpt-oss-120b",
     "accessed_at": "2026-08-11", "promotion": False,
     "notes": ""},
    # Gemma 4 31B
    {"model": "Gemma 4 31B", "model_id": "gemma-4-31b-it",
     "provider_route": "OpenRouter", "region": "provider_routed",
     "in_per_m": 0.10, "out_per_m": 0.34, "cached_in_per_m": None,
     "source_url": "https://openrouter.ai/google/gemma-4-31b-it",
     "accessed_at": "2026-08-11", "promotion": False,
     "notes": ""},
    # GLM-5.2 — corrected from $0.76/$2.42 to actual $0.4886/$1.5356
    {"model": "GLM-5.2", "model_id": "GLM-5.2",
     "provider_route": "OpenRouter (standard)", "region": "provider_routed",
     "in_per_m": 0.4886, "out_per_m": 1.5356, "cached_in_per_m": None,
     "source_url": "https://openrouter.ai/z-ai/glm-5.2",
     "accessed_at": "2026-08-11", "promotion": False,
     "notes": "Previous $0.76/$2.42 was incorrect. Z.AI Direct ~$1.40/$4.40 per docs.z.ai."},
]


def build_competitor_pricing_table():
    """One row per provider route."""
    return pd.DataFrame(COMPETITOR_PRICES)


def build_deployment_summary():
    """Summary of deployment profiles from YAML."""
    profiles = load_deployment_profiles()
    rows = []
    for m in profiles["models"]:
        for dep in m["deployments"]:
            rows.append({
                "model_id": m["model_id"],
                "total_params_b": m["total_params_b"],
                "active_params_b": m["active_params_b"],
                "arch": m["arch"],
                "deployment": dep["gpu_config"],
                "benchmark_status": dep["benchmark_status"],
                "has_valid_margin": m["has_valid_margin"],
            })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    pd.set_option("display.width", 200)

    print("=" * 100)
    print("  MaaS Competitor Pricing (per provider route)")
    print("  NOTE: ALL margins are INVALID pending benchmark. No margin calculations shown.")
    print("=" * 100)

    df = build_competitor_pricing_table()
    print("\n--- Competitor prices (per route) ---")
    for _, r in df.iterrows():
        cache = f", cache=${r['cached_in_per_m']:.4f}" if r["cached_in_per_m"] else ""
        promo = " [PROMO]" if r["promotion"] else ""
        print(f"  {r['model']:20s} [{r['provider_route']:30s}] "
              f"${r['in_per_m']:.4f}/M_in, ${r['out_per_m']:.4f}/M_out{cache}{promo}")
        if r["notes"]:
            print(f"    → {r['notes']}")

    print("\n--- Deployment profiles ---")
    dep = build_deployment_summary()
    for _, r in dep.iterrows():
        status = "🔴 INVALID" if not r["has_valid_margin"] else "🟡"
        print(f"  {r['model_id']:30s} {r['total_params_b']:>5}B/{r['active_params_b']}B "
              f"{r['arch']:20s} {r['deployment']:20s} benchmark={r['benchmark_status']:10s} {status}")
