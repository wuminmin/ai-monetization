#!/usr/bin/env python3
"""
Market Data — TAM/SAM with scenario ranges.

BPO is loaded from a long-table snapshot (data/market_snapshots/ph_bpo.csv) so
that the 2025 actual, 2026 base forecast, and 2028 downside/upside figures are
distinct rows. Two CAGRs are reported with explicitly labeled base years:
  - 2025 actual -> 2028 (downside/upside)
  - 2026 forecast -> 2028 (downside/upside)
This prevents the base-year ambiguity flagged in the round-4 review.

Global GPUaaS figures are verified live data (MarketsandMarkets, accessed
2026-08-12) and serve only as industry context, NOT as PLDT's TAM.
"""

import os
import pandas as pd

SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "market_snapshots")
BPO_SNAPSHOT_PATH = os.path.join(SNAPSHOT_DIR, "ph_bpo.csv")


def calc_cagr(start_value, end_value, years):
    return (end_value / start_value) ** (1 / years) - 1


def load_bpo_snapshot():
    """Load the BPO long-table snapshot (single source of truth)."""
    return pd.read_csv(BPO_SNAPSHOT_PATH)


# ============================================================
# Non-BPO market data (Philippines DC + Global GPUaaS).
# Global GPUaaS verified live 2026-08-12 from MarketsandMarkets page
# gpu-as-a-service-market-153834402.html ($8.21B 2025 -> $26.62B 2030, 26.5%).
# ============================================================
MARKET_DATA = [
    {
        "claim_id": "MKT-01",
        "metric": "Philippines Data Center Market",
        "geography": "Philippines",
        "start_year": 2026,
        "start_value_b": 0.85,
        "end_year": 2031,
        "end_value_b": 2.37,
        "source_owner": "Mordor Intelligence",
        "source_url": "https://www.mordorintelligence.com/industry-reports/philippines-data-center-market",
        "source_accessed": "2026-08-12",
        "source_confidence": "B",
        "normalization_method": "none",
    },
    {
        "claim_id": "MKT-03",
        "metric": "Global GPUaaS Market (industry context only)",
        "geography": "Global",
        "start_year": 2025,
        "start_value_b": 8.21,
        "end_year": 2030,
        "end_value_b": 26.62,
        "source_owner": "MarketsandMarkets",
        "source_url": "https://www.marketsandmarkets.com/Market-Reports/gpu-as-a-service-market-153834402.html",
        "source_accessed": "2026-08-12",
        "source_confidence": "B",
        "normalization_method": "none",
        "notes": "Industry context only, NOT PLDT TAM. Verified live 2026-08-12.",
    },
]


def _bpo_size_str(df):
    """'$40.3B (2025 actual), $42.3B (2026 fcst) -> $43.3B-$50.5B (2028)'."""
    actual = df[df["scenario"] == "actual"].iloc[0]
    fcst = df[df["scenario"] == "base_forecast"].iloc[0]
    down = df[df["scenario"] == "downside"].iloc[0]
    up = df[df["scenario"] == "upside"].iloc[0]
    return (f"${actual['value_usd_b']:.1f}B ({int(actual['year'])} actual), "
            f"${fcst['value_usd_b']:.1f}B ({int(fcst['year'])} fcst) -> "
            f"${down['value_usd_b']:.1f}B-${up['value_usd_b']:.1f}B ({int(down['year'])})")


def _bpo_cagr_str(df):
    """Both base-year CAGRs, explicitly labeled."""
    actual = df[df["scenario"] == "actual"].iloc[0]
    fcst = df[df["scenario"] == "base_forecast"].iloc[0]
    down = df[df["scenario"] == "downside"].iloc[0]
    up = df[df["scenario"] == "upside"].iloc[0]
    yrs = int(down["year"]) - int(actual["year"])
    c25_down = calc_cagr(actual["value_usd_b"], down["value_usd_b"], yrs)
    c25_up = calc_cagr(actual["value_usd_b"], up["value_usd_b"], yrs)
    yrs26 = int(down["year"]) - int(fcst["year"])
    c26_down = calc_cagr(fcst["value_usd_b"], down["value_usd_b"], yrs26)
    c26_up = calc_cagr(fcst["value_usd_b"], up["value_usd_b"], yrs26)
    return (f"{c25_down:.1%}-{c25_up:.1%} (2025 base) / "
            f"{c26_down:.1%}-{c26_up:.1%} (2026 base)")


def _bpo_cagr_basis(df):
    return "2025 actual & 2026 forecast -> 2028 downside/upside"


def build_market_table():
    rows = []
    # --- BPO from long-table snapshot (dual base year) ---
    bpo = load_bpo_snapshot()
    rows.append({
        "metric": "Philippines BPO Industry Revenue",
        "geography": "Philippines",
        "size": _bpo_size_str(bpo),
        "period": f"{int(bpo['year'].min())}-{int(bpo['year'].max())}",
        "cagr": _bpo_cagr_str(bpo),
        "cagr_basis": _bpo_cagr_basis(bpo),
        "source": bpo.iloc[0]["source_owner"],
        "confidence": bpo.iloc[0]["confidence"],
    })

    # --- Non-BPO series (DC market + Global GPUaaS) ---
    for d in MARKET_DATA:
        years = d["end_year"] - d["start_year"]
        cagr = calc_cagr(d["start_value_b"], d["end_value_b"], years)
        rows.append({
            "metric": d["metric"],
            "geography": d["geography"],
            "size": f"${d['start_value_b']:.2f}B -> ${d['end_value_b']:.2f}B",
            "period": f"{d['start_year']}-{d['end_year']}",
            "cagr": cagr,
            "cagr_basis": f"{d['start_year']} -> {d['end_year']}",
            "source": d["source_owner"],
            "confidence": d["source_confidence"],
        })
    return pd.DataFrame(rows)


def build_bpo_detail_table():
    """One row per (year, scenario) — the raw long-table, for auditing."""
    return load_bpo_snapshot()


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    print("=" * 100)
    print("  Market Data — BPO dual-base CAGR, GPUaaS verified live 2026-08-12")
    print("=" * 100)

    df = build_market_table()
    print(df.to_string(index=False))

    print("\n--- BPO long-table (single source of truth) ---")
    print(build_bpo_detail_table().to_string(index=False))

    print("\n--- CAGR detail ---")
    bpo = load_bpo_snapshot()
    actual = bpo[bpo["scenario"] == "actual"].iloc[0]
    fcst = bpo[bpo["scenario"] == "base_forecast"].iloc[0]
    down = bpo[bpo["scenario"] == "downside"].iloc[0]
    up = bpo[bpo["scenario"] == "upside"].iloc[0]
    for label, base in [("2025 actual", actual), ("2026 forecast", fcst)]:
        yrs = int(down["year"]) - int(base["year"])
        cd = calc_cagr(base["value_usd_b"], down["value_usd_b"], yrs)
        cu = calc_cagr(base["value_usd_b"], up["value_usd_b"], yrs)
        print(f"  BPO ({label} -> 2028): downside {cd:.1%}, upside {cu:.1%}")
