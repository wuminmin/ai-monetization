#!/usr/bin/env python3
"""
Generate status sections in README.md and the strategy report from a single
source: project_status.yaml.

Why this exists: README, the report, and CHANGELOG drifted every round because
status claims (version, test count, "CI green") were hand-written in three
places. Now they are generated from one YAML file, so they cannot drift.

The generator rewrites the regions between these markers (inclusive content):
    <!-- BEGIN STATUS --> ... <!-- END STATUS -->
in README.md and reports/D_AI_Monetization_Strategy_V2.md.

CI status is NEVER written as a static "green" claim — it always says "see
GitHub Actions", because a static claim is stale the moment CI re-runs.

Usage:
    python src/render_status.py
"""

import os
import re
import subprocess
import sys

import yaml

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STATUS_YAML = os.path.join(REPO_ROOT, "project_status.yaml")
README = os.path.join(REPO_ROOT, "README.md")
REPORT = os.path.join(REPO_ROOT, "reports", "D_AI_Monetization_Strategy_V2.md")
TESTS_FILE = os.path.join(REPO_ROOT, "tests", "test_calculations.py")

BEGIN = "<!-- BEGIN STATUS -->"
END = "<!-- END STATUS -->"


def count_tests():
    """Count `def test_...` functions in the test file (dynamic, never hardcoded)."""
    with open(TESTS_FILE) as f:
        return sum(1 for line in f if re.match(r"^def test_", line))


def load_status():
    with open(STATUS_YAML) as f:
        return yaml.safe_load(f)


def ci_line(status):
    """CI status is ALWAYS 'see Actions' — never a static green/red claim."""
    return "CI 结果以 [GitHub Actions](../../actions) 当前状态为准。"


def readme_status_block(status):
    n = count_tests()
    lines = [
        f"> **{status['version']} — {status['round']}**",
        "",
        f"- 测试: **{n} 项** (`tests/test_calculations.py`)",
        f"- GPUaaS: {status['statuses']['gpuaas']}",
        f"- MaaS 毛利: {status['statuses']['maas_margin']}",
        f"- DGX 节点价: {status['statuses']['dgx_node_price']}",
        f"- 构建确定性: {status['statuses']['build_determinism']}",
        f"- {ci_line(status)}",
        "",
        f"_由 `project_status.yaml` + `src/render_status.py` 生成, 请勿手改此段。_",
    ]
    return "\n".join(lines)


def report_status_block(status):
    """One-line status summary injected into the report's data declaration."""
    n = count_tests()
    return (
        f"**状态 ({status['version']}):** {n} 项测试。"
        f"GPUaaS {status['statuses']['gpuaas']}。"
        f"MaaS 毛利 {status['statuses']['maas_margin']}。"
        f"DGX 节点价 {status['statuses']['dgx_node_price']}。"
        f"{ci_line(status)}"
    )


def replace_block(path, new_content):
    """Replace the content between BEGIN/END markers in a file."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(text):
        raise RuntimeError(f"No {BEGIN}...{END} markers found in {path}")
    replacement = f"{BEGIN}\n{new_content}\n{END}"
    new_text = pattern.sub(replacement, text)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_text)
    print(f"  Updated: {os.path.relpath(path, REPO_ROOT)}")


def main():
    status = load_status()
    print(f"Rendering status from {os.path.relpath(STATUS_YAML, REPO_ROOT)} "
          f"(version={status['version']}, tests={count_tests()})")
    replace_block(README, readme_status_block(status))
    replace_block(REPORT, report_status_block(status))
    print("Done. README and report status sections synced.")


if __name__ == "__main__":
    main()
