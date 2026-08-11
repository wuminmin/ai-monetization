#!/usr/bin/env python3
"""
MaaS Economics — competitor pricing loaded from a single price snapshot.

Prices are NOT hardcoded here; they are loaded from
data/pricing_snapshots/maas_openrouter.csv (the single source of truth).
NO margin calculations: all margins remain INVALID pending benchmark.
GPU cost from TCO model (fully_allocated_cost_per_billable_gpu_hour).

Snapshot governance:
  - Each row carries observed_at, effective_at, content_hash and promotion flag.
  - Snapshot age is reported; CI/tests flag snapshots older than SNAPSHOT_TTL_DAYS.
"""

import pandas as pd
import yaml
import os
import datetime

SNAPSHOT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "pricing_snapshots", "maas_openrouter.csv"
)
YAML_PATH = os.path.join(os.path.dirname(__file__), "..", "methodology", "model_deployment_profiles.yaml")

# Snapshots older than this are considered stale (advisory, not blocking).
SNAPSHOT_TTL_DAYS = 7


def load_maas_price_snapshots():
    """Load the MaaS price snapshot CSV (single source of truth)."""
    return pd.read_csv(SNAPSHOT_PATH)


def _snapshot_age_days(df):
    """Days between observed_at and today (advisory staleness check)."""
    if df.empty or "observed_at" not in df.columns:
        return None
    observed = pd.to_datetime(df["observed_at"]).dt.tz_localize(None)
    return (datetime.datetime.now() - observed.iloc[0]).days


def load_deployment_profiles():
    with open(YAML_PATH, "r") as f:
        return yaml.safe_load(f)


# Map snapshot model_id -> human-readable model name (for the pricing table).
# Deployment specs come from model_deployment_profiles.yaml.
_MODEL_NAMES = {
    "DeepSeek-V4-Flash-0731": "DeepSeek V4 Flash",
    "DeepSeek-V4-Flash-0423": "DeepSeek V4 Flash",
    "DeepSeek-V4-Pro": "DeepSeek V4 Pro",
    "Qwen3.5-35B-A3B": "Qwen 3.5 Flash",
    "Qwen3.5-9B": "Qwen 3.5 9B",
    "gpt-oss-120b": "GPT-OSS 120B",
    "gemma-4-31b-it": "Gemma 4 31B",
    "GLM-5.2": "GLM-5.2",
}


def build_competitor_pricing_table():
    """One row per provider route, derived from the price snapshot."""
    snaps = load_maas_price_snapshots()
    rows = []
    for _, r in snaps.iterrows():
        # promotion may be TRUE/FALSE strings or bool; normalize to bool
        promo = str(r.get("promotion", "")).strip().upper() in ("TRUE", "1", "YES")
        rows.append({
            "model": _MODEL_NAMES.get(r["model_id"], r["model_id"]),
            "model_id": r["model_id"],
            "route_id": r["route_id"],
            "provider_route": f"OpenRouter ({r['route_id']})",
            "region": r["region"],
            "in_per_m": r["input_price_per_m"],
            "out_per_m": r["output_price_per_m"],
            "cached_in_per_m": r.get("cached_input_price_per_m") if not pd.isna(r.get("cached_input_price_per_m", "")) else None,
            "promotion": promo,
            "promotion_detail": r.get("promotion_detail", ""),
            "observed_at": r["observed_at"],
            "content_hash": r["content_hash"],
            "source_url": r["source_url"],
            "route_note": r.get("route_note", ""),
        })
    return pd.DataFrame(rows)


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
    print("  MaaS Competitor Pricing (loaded from price snapshot)")
    print("  NOTE: ALL margins are INVALID pending benchmark. No margin calculations shown.")
    print("=" * 100)

    df = build_competitor_pricing_table()
    age = _snapshot_age_days(df)
    stale = age is not None and age > SNAPSHOT_TTL_DAYS
    print(f"\n  Snapshot observed_at: {df.iloc[0]['observed_at']}  (age {age}d, "
          f"{'STALE' if stale else 'fresh'}, TTL {SNAPSHOT_TTL_DAYS}d)")

    print("\n--- Competitor prices (per route) ---")
    for _, r in df.iterrows():
        cache = f", cache=${r['cached_in_per_m']:.4f}" if r["cached_in_per_m"] else ""
        promo = f" [{r['promotion_detail']}]" if r["promotion"] else ""
        print(f"  {r['model']:20s} [{r['route_id']:35s}] "
              f"${r['in_per_m']:.4f}/M_in, ${r['out_per_m']:.4f}/M_out{cache}{promo}")
        if r["route_note"]:
            print(f"    -> {r['route_note']}")

    print("\n--- Deployment profiles ---")
    dep = build_deployment_summary()
    for _, r in dep.iterrows():
        status = "🔴 INVALID" if not r["has_valid_margin"] else "🟡"
        print(f"  {r['model_id']:30s} {r['total_params_b']:>5}B/{r['active_params_b']}B "
              f"{r['arch']:20s} {r['deployment']:20s} benchmark={r['benchmark_status']:10s} {status}")
