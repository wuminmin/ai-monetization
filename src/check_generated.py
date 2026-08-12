#!/usr/bin/env python3
"""
Determinism + freshness checker for generated artifacts.

Does NOT modify the developer worktree. Instead it:
  1. Builds the full output set into temp dir A (with SOURCE_DATE_EPOCH unset
     so the manifest is purely content-derived).
  2. Builds again into temp dir B.
  3. Asserts A and B are byte-identical for every TRACKED_OUTPUT (determinism).
  4. Asserts the committed (repo) copy of each TRACKED_OUTPUT matches A/B
     (freshness — committed artifacts are up to date).

Exits non-zero if any check fails. This replaces the old `git diff --exit-code`
approach, which was both in-place (mutated the worktree) and unable to detect
the manifest self-reference bug.

Run locally:  python src/check_generated.py
CI:          used as the final step in validate.yml
"""

import os
import sys
import shutil
import tempfile

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Files that are build outputs and must be (a) deterministic across rebuilds
# and (b) kept in sync with the committed copies.
TRACKED_OUTPUTS = [
    "build_metadata.json",                              # in models/
    "gpu_tco_breakdown.csv",
    "gross_margin_sensitivity.csv",
    "gpu_node_price_sensitivity.csv",
    "pricing_recommendations.csv",
    "gpuaas_competitive_pricing.csv",                   # in data/
    "maas_competitive_pricing.csv",
    "maas_deployment_profiles.csv",
    "market_data.csv",
    "bpo_detail.csv",
]


def sha256_file(path):
    """Full sha256 hex digest of a file, or None if missing."""
    if not os.path.exists(path):
        return None
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def _output_dirs(tmp_root):
    """Build an {models, data, build} dict rooted at tmp_root."""
    return {
        "models": os.path.join(tmp_root, "models"),
        "data": os.path.join(tmp_root, "data"),
        "build": os.path.join(tmp_root, "build"),
    }


def _build_once(tmp_root, verbose=False):
    """Run build_all into a temp dir; return the output_dirs used."""
    sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
    # Force a clean SOURCE_DATE_EPOCH so the runtime file is deterministic too.
    os.environ["SOURCE_DATE_EPOCH"] = "0"
    dirs = _output_dirs(tmp_root)
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)
    import build_all
    build_all.build_all(output_dirs=dirs, verbose=verbose)
    return dirs


def _hash_outputs(dirs):
    """Return {relative_name: sha256} for each TRACKED_OUTPUT found under dirs."""
    out = {}
    for name in TRACKED_OUTPUTS:
        # TRACKED_OUTPUTS[0] (build_metadata.json) + the 3 models CSVs live in models/
        models_outputs = {"build_metadata.json", "gpu_tco_breakdown.csv",
                          "gross_margin_sensitivity.csv", "gpu_node_price_sensitivity.csv",
                          "pricing_recommendations.csv"}
        subdir = "models" if name in models_outputs else "data"
        path = os.path.join(dirs[subdir], name)
        out[name] = sha256_file(path)
    return out


def main():
    print("Determinism + freshness check (temp-dir builds, no worktree mutation)")

    tmp_a = tempfile.mkdtemp(prefix="build_a_")
    tmp_b = tempfile.mkdtemp(prefix="build_b_")
    try:
        print("  Build #1 into temp dir A ...")
        dirs_a = _build_once(tmp_a, verbose=False)
        print("  Build #2 into temp dir B ...")
        dirs_b = _build_once(tmp_b, verbose=False)

        hash_a = _hash_outputs(dirs_a)
        hash_b = _hash_outputs(dirs_b)

        # --- Check 1: A vs B must be byte-identical (determinism) ---
        diffs_ab = [n for n in TRACKED_OUTPUTS if hash_a[n] != hash_b[n]]
        if diffs_ab:
            print(f"\nFAIL: builds A and B differ (non-deterministic): {diffs_ab}")
            return 1
        print("  ✅ Two temp builds are byte-identical (deterministic).")

        # --- Check 2: committed repo copy must match the fresh build ---
        repo_hash = {}
        for name in TRACKED_OUTPUTS:
            models_outputs = {"build_metadata.json", "gpu_tco_breakdown.csv",
                              "gross_margin_sensitivity.csv", "gpu_node_price_sensitivity.csv",
                              "pricing_recommendations.csv"}
            subdir = "models" if name in models_outputs else "data"
            repo_hash[name] = sha256_file(os.path.join(REPO_ROOT, subdir, name))

        stale = [n for n in TRACKED_OUTPUTS if hash_a[n] != repo_hash[n]]
        if stale:
            print(f"\nFAIL: committed artifacts are stale (do not match a clean build): {stale}")
            print("Regenerate with:  python src/build_all.py")
            return 1
        print(f"  ✅ All {len(TRACKED_OUTPUTS)} committed artifacts match a clean build (fresh).")
        print("\nPASS: determinism + freshness verified.")
        return 0
    finally:
        shutil.rmtree(tmp_a, ignore_errors=True)
        shutil.rmtree(tmp_b, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
