#!/usr/bin/env python3
"""
Master build script — generates all CSVs from source data.
Outputs a DETERMINISTIC manifest (no wall-clock time) to the tracked
models/build_metadata.json, plus a runtime metadata file (with the real
build time) to build/runtime_metadata.json (gitignored).

Determinism: generated_at is derived from SOURCE_DATE_EPOCH (defaults to 0
= 1970-01-01) so that two builds from the same inputs produce byte-identical
tracked artifacts. CI sets SOURCE_DATE_EPOCH to the commit timestamp.
All scripts load from YAML/CSV inputs, never hardcode constants.
"""

import sys
import os
import json
import hashlib
import datetime
import subprocess

sys.path.insert(0, os.path.dirname(__file__))

GENERATOR_VERSION = "4.0.0"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_DIRS = {
    "models": os.path.join(REPO_ROOT, "models"),
    "data": os.path.join(REPO_ROOT, "data"),
    "build": os.path.join(REPO_ROOT, "build"),
}


def file_hash(path):
    """SHA256 hash of a file (first 12 hex chars), or None if missing."""
    if not path or not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]


def source_date_epoch_dt():
    """Deterministic timestamp from SOURCE_DATE_EPOCH (Unix seconds); defaults to 0."""
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "0") or "0")
    return datetime.datetime.fromtimestamp(epoch, tz=datetime.timezone.utc)


def git_commit():
    """Short commit hash of HEAD, or 'unknown' if git is unavailable."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT, stderr=subprocess.DEVNULL,
        ).decode().strip()
        return out or "unknown"
    except Exception:
        return "unknown"


def hash_src(rel_path):
    """Helper: hash a file relative to repo root."""
    return file_hash(os.path.join(REPO_ROOT, rel_path))


def write_csv_atomic(df, path):
    """Write CSV atomically (temp then replace).

    os.replace is used (not os.rename) so it works on Windows where the
    destination may already exist.
    """
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False, encoding="utf-8-sig")
    os.replace(tmp, path)
    print(f"  Written: {os.path.relpath(path)}")


def build_gpu_tco():
    """Generate TCO + margin sensitivity + node-price sensitivity CSVs."""
    from build_gpu_tco import build_tco_table, build_margin_sensitivity, build_node_price_sensitivity
    tco = build_tco_table()
    margins = build_margin_sensitivity()
    node_sens = build_node_price_sensitivity()
    write_csv_atomic(tco, os.path.join(OUTPUT_DIRS["models"], "gpu_tco_breakdown.csv"))
    write_csv_atomic(margins, os.path.join(OUTPUT_DIRS["models"], "gross_margin_sensitivity.csv"))
    write_csv_atomic(node_sens, os.path.join(OUTPUT_DIRS["models"], "gpu_node_price_sensitivity.csv"))
    return {"gpu_tco_rows": len(tco), "margin_rows": len(margins), "node_sensitivity_rows": len(node_sens)}


def build_gpu_pricing():
    """Generate GPUaaS competitive pricing CSV."""
    from build_gpu_pricing import build_gpu_pricing_table
    df = build_gpu_pricing_table()
    write_csv_atomic(df, os.path.join(OUTPUT_DIRS["data"], "gpuaas_competitive_pricing.csv"))
    return {"gpu_pricing_rows": len(df)}


def build_market():
    """Generate market data CSV + BPO long-table detail CSV."""
    from build_market_model import build_market_table, build_bpo_detail_table
    df = build_market_table()
    write_csv_atomic(df, os.path.join(OUTPUT_DIRS["data"], "market_data.csv"))
    # BPO long-table (one row per year/scenario) for auditing
    bpo_detail = build_bpo_detail_table()
    write_csv_atomic(bpo_detail, os.path.join(OUTPUT_DIRS["data"], "bpo_detail.csv"))
    return {"market_rows": len(df), "bpo_detail_rows": len(bpo_detail)}


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
    """Write a DETERMINISTIC manifest to models/build_metadata.json (tracked)
    and a runtime metadata file to build/runtime_metadata.json (gitignored).

    The tracked manifest contains NO wall-clock time — generated_at comes from
    SOURCE_DATE_EPOCH so two builds from identical inputs are byte-identical.
    """
    assumptions_path = os.path.join(os.path.dirname(__file__), "..", "methodology", "assumptions.yaml")
    sources_path = os.path.join(OUTPUT_DIRS["data"], "sources.csv")
    deployment_profiles_path = os.path.join(os.path.dirname(__file__), "..", "methodology", "model_deployment_profiles.yaml")

    # Input snapshot files (may not all exist yet — hash_src returns None if missing)
    input_hashes = {
        "assumptions_hash": hash_src("methodology/assumptions.yaml"),
        "sources_hash": hash_src("data/sources.csv"),
        "deployment_profiles_hash": hash_src("methodology/model_deployment_profiles.yaml"),
        "gpu_pricing_snapshot_hash": hash_src("data/pricing_snapshots/gpu_openrouter.csv"),
        "maas_pricing_snapshot_hash": hash_src("data/pricing_snapshots/maas_openrouter.csv"),
        "market_snapshot_hash": hash_src("data/market_snapshots/ph_bpo.csv"),
    }

    # Hash of all generator source code (this directory's .py files)
    src_dir = os.path.dirname(__file__)
    code_h = hashlib.sha256()
    for fname in sorted(os.listdir(src_dir)):
        if fname.endswith(".py"):
            with open(os.path.join(src_dir, fname), "rb") as f:
                code_h.update(f.read())
    generator_code_hash = code_h.hexdigest()[:12]

    # DETERMINISTIC manifest — no wall-clock time
    manifest = {
        "generator_version": GENERATOR_VERSION,
        "git_commit": git_commit(),
        "generated_at": source_date_epoch_dt().isoformat(),
        "source_date_epoch": int(os.environ.get("SOURCE_DATE_EPOCH", "0") or "0"),
        **input_hashes,
        "generator_code_hash": generator_code_hash,
        "results": results,
    }
    manifest_path = os.path.join(OUTPUT_DIRS["models"], "build_metadata.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    print(f"\n  Manifest (deterministic): {os.path.relpath(manifest_path)}")

    # RUNTIME metadata — real build time, gitignored
    os.makedirs(OUTPUT_DIRS["build"], exist_ok=True)
    runtime = {
        "build_wall_clock": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "git_commit": manifest["git_commit"],
        "generator_version": GENERATOR_VERSION,
    }
    runtime_path = os.path.join(OUTPUT_DIRS["build"], "runtime_metadata.json")
    with open(runtime_path, "w") as f:
        json.dump(runtime, f, indent=2, sort_keys=True)
    print(f"  Runtime metadata: {os.path.relpath(runtime_path)} (gitignored)")


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
