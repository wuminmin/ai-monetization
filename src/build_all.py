#!/usr/bin/env python3
"""
Master build script — generates all CSVs from source data.

Determinism design (round 5 fix):
  The TRACKED manifest (models/build_metadata.json) contains ONLY content
  hashes — NO git commit, NO timestamps, NO VCS identity of any kind. This is
  essential because writing the current commit SHA into a file that is itself
  committed creates a self-reference that can never converge: every commit
  changes the SHA, so CI rebuilding on the new commit always produces a diff.

  All provenance (git_commit, build_wall_clock, source_date_epoch, ci_run_id)
  lives ONLY in build/runtime_metadata.json, which is gitignored.

  A build into any output directory therefore depends only on the input files
  and generator code — never on which commit or what time it is.

All scripts load from YAML/CSV inputs, never hardcode business constants.
"""

import sys
import os
import json
import hashlib
import datetime
import subprocess

sys.path.insert(0, os.path.dirname(__file__))

GENERATOR_VERSION = "5.0.0"
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


def hash_src(rel_path):
    """Helper: hash a file relative to repo root."""
    return file_hash(os.path.join(REPO_ROOT, rel_path))


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
    """Generate TCO + margin sensitivity + node-price sensitivity + pricing recommendations CSVs."""
    from build_gpu_tco import (build_tco_table, build_margin_sensitivity,
                               build_node_price_sensitivity, build_pricing_recommendations)
    tco = build_tco_table()
    margins = build_margin_sensitivity()
    node_sens = build_node_price_sensitivity()
    pricing = build_pricing_recommendations()
    write_csv_atomic(tco, os.path.join(OUTPUT_DIRS["models"], "gpu_tco_breakdown.csv"))
    write_csv_atomic(margins, os.path.join(OUTPUT_DIRS["models"], "gross_margin_sensitivity.csv"))
    write_csv_atomic(node_sens, os.path.join(OUTPUT_DIRS["models"], "gpu_node_price_sensitivity.csv"))
    write_csv_atomic(pricing, os.path.join(OUTPUT_DIRS["models"], "pricing_recommendations.csv"))
    return {"gpu_tco_rows": len(tco), "margin_rows": len(margins),
            "node_sensitivity_rows": len(node_sens), "pricing_rows": len(pricing)}


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
                "weight_format": m.get("weight_format", ""),
                "checkpoint_precision": m.get("checkpoint_precision", ""),
                "checkpoint_size_gb": m.get("checkpoint_size_gb"),
                "total_hbm_gb": m.get("total_hbm_gb"),
                "weights_fit": m.get("weights_fit"),
                "runtime_fit": m.get("runtime_fit", "unverified"),
                "model_max_context": m.get("model_max_context", m["native_context"]),
                "max_context_tested": dep.get("max_context_tested"),
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


def generate_metadata(results, output_dirs=None):
    """Write a DETERMINISTIC manifest to <models>/build_metadata.json and a
    runtime metadata file to <build>/runtime_metadata.json.

    The TRACKED manifest contains ONLY content hashes + the generator version.
    It deliberately contains NO git commit, NO timestamp, NO VCS identity —
    writing the current commit into a committed file is a self-reference that
    can never converge (every commit changes the SHA → CI always diffs).

    All provenance (commit, wall-clock, CI run id) lives ONLY in the runtime
    file, which is gitignored.

    output_dirs: optional dict {models, data, build} overriding the default
                 OUTPUT_DIRS — used by check_generated.py to build into temp
                 directories without touching the real worktree.
    """
    dirs = output_dirs or OUTPUT_DIRS

    # Input snapshot files (hash_src returns None if missing — e.g. GPU pricing
    # snapshot does not exist yet because COMPETITORS is still in Python).
    input_hashes = {
        "assumptions_hash": hash_src("methodology/assumptions.yaml"),
        "sources_hash": hash_src("data/sources.csv"),
        "deployment_profiles_hash": hash_src("methodology/model_deployment_profiles.yaml"),
        "gpu_pricing_snapshot_hash": hash_src("data/pricing_snapshots/gpu_openrouter.csv"),
        "maas_pricing_snapshot_hash": hash_src("data/pricing_snapshots/maas_openrouter.csv"),
        "market_snapshot_hash": hash_src("data/market_snapshots/ph_bpo.csv"),
    }

    # Hash of all generator source code (this directory's .py files).
    src_dir = os.path.dirname(__file__)
    code_h = hashlib.sha256()
    for fname in sorted(os.listdir(src_dir)):
        if fname.endswith(".py"):
            with open(os.path.join(src_dir, fname), "rb") as f:
                code_h.update(f.read())
    generator_code_hash = code_h.hexdigest()[:12]

    # TRACKED manifest — pure content hashes, NO VCS identity, NO time.
    manifest = {
        "generator_version": GENERATOR_VERSION,
        **input_hashes,
        "generator_code_hash": generator_code_hash,
        "results": results,
    }
    manifest_path = os.path.join(dirs["models"], "build_metadata.json")
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
    print(f"\n  Manifest (deterministic, no VCS identity): {os.path.relpath(manifest_path)}")

    # RUNTIME metadata — gitignored; carries all provenance.
    os.makedirs(dirs["build"], exist_ok=True)
    runtime = {
        "build_wall_clock": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "git_commit": os.environ.get("GITHUB_SHA") or git_commit(),
        "generator_version": GENERATOR_VERSION,
        "ci_run_id": os.environ.get("GITHUB_RUN_ID"),
    }
    sde = os.environ.get("SOURCE_DATE_EPOCH")
    if sde is not None:
        runtime["source_date_epoch"] = int(sde or "0")
    runtime_path = os.path.join(dirs["build"], "runtime_metadata.json")
    with open(runtime_path, "w") as f:
        json.dump(runtime, f, indent=2, sort_keys=True)
    print(f"  Runtime metadata (gitignored): {os.path.relpath(runtime_path)}")


def build_all(output_dirs=None, verbose=True):
    """Function-style entry: run all build steps and write metadata.

    output_dirs: optional {models, data, build} override (for temp-dir builds).
    Returns the results dict. Used by check_generated.py and tests.
    """
    global OUTPUT_DIRS
    saved = dict(OUTPUT_DIRS)
    if output_dirs is not None:
        OUTPUT_DIRS.clear()
        OUTPUT_DIRS.update(output_dirs)
    try:
        if verbose:
            print("=" * 70)
            print("  BUILD ALL — Generating all outputs from source data")
            print("=" * 70)
        results = {}
        results.update(build_gpu_tco())
        results.update(build_gpu_pricing())
        results.update(build_market())
        results.update(build_maas())
        results.update(build_maas_deployments())
        generate_metadata(results, output_dirs)
        if verbose:
            print("\n✅ Build complete. All CSVs generated.")
        return results
    finally:
        if output_dirs is not None:
            OUTPUT_DIRS.clear()
            OUTPUT_DIRS.update(saved)


def main():
    build_all()


if __name__ == "__main__":
    main()
