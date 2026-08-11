#!/usr/bin/env python3
"""
Master build script — generates all CSVs from source data.
Outputs include metadata (generated_at, assumptions_hash).
All scripts load from YAML/CSV inputs, never hardcode constants.
"""

import sys
import os
import json
import hashlib
import datetime

sys.path.insert(0, os.path.dirname(__file__))

GENERATED_AT = datetime.datetime.now(datetime.timezone.utc).isoformat()
OUTPUT_DIRS = {
    "models": os.path.join(os.path.dirname(__file__), "..", "models"),
    "data": os.path.join(os.path.dirname(__file__), "..", "data"),
}


def file_hash(path):
    """SHA256 hash of a file."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]


def write_csv_atomic(df, path):
    """Write CSV atomically (temp then rename)."""
    import tempfile
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False, encoding="utf-8-sig")
    os.rename(tmp, path)
    print(f"  Written: {os.path.relpath(path)}")


def build_gpu_tco():
    """Generate TCO + margin sensitivity CSVs."""
    from build_gpu_tco import build_tco_table, build_margin_sensitivity
    tco = build_tco_table()
    margins = build_margin_sensitivity()
    write_csv_atomic(tco, os.path.join(OUTPUT_DIRS["models"], "gpu_tco_breakdown.csv"))
    write_csv_atomic(margins, os.path.join(OUTPUT_DIRS["models"], "gross_margin_sensitivity.csv"))
    return {"gpu_tco_rows": len(tco), "margin_rows": len(margins)}


def build_gpu_pricing():
    """Generate GPUaaS competitive pricing CSV."""
    from build_gpu_pricing import build_gpu_pricing_table
    df = build_gpu_pricing_table()
    write_csv_atomic(df, os.path.join(OUTPUT_DIRS["data"], "gpuaas_competitive_pricing.csv"))
    return {"gpu_pricing_rows": len(df)}


def build_market():
    """Generate market data CSV."""
    from build_market_model import build_market_table
    df = build_market_table()
    write_csv_atomic(df, os.path.join(OUTPUT_DIRS["data"], "market_data.csv"))
    return {"market_rows": len(df)}


def build_maas():
    """Generate MaaS competitor pricing CSV (per-route, no margins)."""
    from build_maas_economics import build_competitor_pricing_table
    df = build_competitor_pricing_table()
    write_csv_atomic(df, os.path.join(OUTPUT_DIRS["data"], "maas_competitive_pricing.csv"))
    return {"maas_pricing_rows": len(df)}


def build_maas_deployments():
    """Generate MaaS deployment profiles CSV from YAML."""
    import yaml
    import pandas as pd
    yaml_path = os.path.join(os.path.dirname(__file__), "..", "methodology", "model_deployment_profiles.yaml")
    with open(yaml_path) as f:
        profiles = yaml.safe_load(f)

    rows = []
    for m in profiles["models"]:
        for dep in m["deployments"]:
            rows.append({
                "model_id": m["model_id"],
                "openrouter_slug": m["openrouter_slug"],
                "total_params_b": m["total_params_b"],
                "active_params_b": m["active_params_b"],
                "arch": m["arch"],
                "native_context": m["native_context"],
                "weight_format": dep.get("weight_format", m.get("weight_format", "")),
                "deployment_name": dep["name"],
                "gpu_config": dep["gpu_config"],
                "gpu_count": dep["gpu_count"],
                "tensor_parallel": dep["tensor_parallel"],
                "pipeline_parallel": dep["pipeline_parallel"],
                "throughput_tps": dep.get("throughput_tps"),
                "throughput_source": dep.get("throughput_source"),
                "benchmark_status": dep["benchmark_status"],
                "has_valid_margin": m["has_valid_margin"],
                "note": dep.get("note", ""),
            })
    df = pd.DataFrame(rows)
    write_csv_atomic(df, os.path.join(OUTPUT_DIRS["data"], "maas_deployment_profiles.csv"))
    return {"maas_deployment_rows": len(df)}


def generate_metadata(results):
    """Write build metadata."""
    assumptions_path = os.path.join(os.path.dirname(__file__), "..", "methodology", "assumptions.yaml")
    sources_path = os.path.join(OUTPUT_DIRS["data"], "sources.csv")

    meta = {
        "generated_at": GENERATED_AT,
        "assumptions_hash": file_hash(assumptions_path) if os.path.exists(assumptions_path) else None,
        "sources_hash": file_hash(sources_path) if os.path.exists(sources_path) else None,
        "results": results,
    }

    meta_path = os.path.join(OUTPUT_DIRS["models"], "build_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"\n  Metadata: {os.path.relpath(meta_path)}")


def main():
    print("=" * 70)
    print("  BUILD ALL — Generating all outputs from source data")
    print("=" * 70)

    results = {}
    results.update(build_gpu_tco())
    results.update(build_gpu_pricing())
    results.update(build_market())
    results.update(build_maas())
    results.update(build_maas_deployments())
    generate_metadata(results)

    print("\n✅ Build complete. All CSVs generated.")


if __name__ == "__main__":
    main()
