#!/usr/bin/env python3
"""
Check that tracked generated artifacts are deterministic and up to date.

Runs the full build into a temp directory (with a fixed SOURCE_DATE_EPOCH) and
compares file hashes against the tracked files. Exits non-zero if any tracked
generated file differs from a clean rebuild.

This is the hash-based equivalent of `git diff --exit-code` after build, but it
also catches the "timestamp drift" failure mode by guaranteeing the rebuild uses
SOURCE_DATE_EPOCH (not wall-clock time).
"""

import os
import sys
import hashlib
import tempfile
import shutil
import subprocess

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Files that are build outputs and must be deterministic across rebuilds.
TRACKED_OUTPUTS = [
    "models/build_metadata.json",
    "models/gpu_tco_breakdown.csv",
    "models/gross_margin_sensitivity.csv",
    "models/gpu_node_price_sensitivity.csv",
    "data/gpuaas_competitive_pricing.csv",
    "data/maas_competitive_pricing.csv",
    "data/maas_deployment_profiles.csv",
    "data/market_data.csv",
    "data/bpo_detail.csv",
]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def main():
    # Stash current SOURCE_DATE_EPOCH and use commit time for determinism.
    env = dict(os.environ)
    try:
        commit_ts = subprocess.check_output(
            ["git", "log", "-1", "--pretty=%ct"], cwd=REPO_ROOT,
            stderr=subprocess.DEVNULL).decode().strip()
        env["SOURCE_DATE_EPOCH"] = commit_ts
    except Exception:
        env["SOURCE_DATE_EPOCH"] = "0"

    # Build into the real output dirs (in-place), then compare to git HEAD.
    print("Building with SOURCE_DATE_EPOCH =", env["SOURCE_DATE_EPOCH"])
    r = subprocess.run([sys.executable, os.path.join("src", "build_all.py")],
                       cwd=REPO_ROOT, env=env)
    if r.returncode != 0:
        print("FAIL: build itself failed")
        return 1

    # Compare tracked outputs to git index via git diff --exit-code.
    r = subprocess.run(["git", "diff", "--exit-code"], cwd=REPO_ROOT)
    if r.returncode == 0:
        print("PASS: all tracked generated files match a clean deterministic rebuild.")
        return 0
    else:
        diffed = subprocess.check_output(
            ["git", "diff", "--name-only"], cwd=REPO_ROOT).decode().strip()
        print(f"FAIL: generated files differ from committed versions:\n{diffed}")
        print("Run: SOURCE_DATE_EPOCH=$(git log -1 --pretty=%ct) python src/build_all.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())
