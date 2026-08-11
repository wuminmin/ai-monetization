#!/usr/bin/env python3
"""
Market Data — TAM/SAM
CAGR auto-calculated. Sources verified per Round 2 review.
Unverifiable entries removed.
"""

import pandas as pd
import math


def calc_cagr(start_value, end_value, years):
    return (end_value / start_value) ** (1 / years) - 1


# ============================================================
# Market data — only entries with verified source year + value + metric
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
        "cagr": None,  # auto
        "source_owner": "Mordor Intelligence",
        "source_url": "https://www.mordorintelligence.com/industry-reports/philippines-data-center-market",
        "source_accessed": "2026-08-11",
        "source_confidence": "B",
        "normalization_method": "none",
        "notes": "Source page states 2026 $0.85B, 2031 $2.37B, CAGR 22.88%",
    },
    {
        "claim_id": "MKT-02",
        "metric": "Philippines BPO Industry Revenue",
        "geography": "Philippines",
        "start_year": 2026,
        "start_value_b": 40.0,
        "end_year": 2028,
        "end_value_b": 50.5,
        "cagr": None,
        "source_owner": "IBPAP",
        "source_url": "https://ibpap.org/news-room/43",
        "source_accessed": "2026-08-11",
        "source_confidence": "B",
        "normalization_method": "none",
        "notes": "IBPAP 2028 outlook: ~$43.3B-$50.5B. Previous $102B/2034 was unverified — REMOVED.",
    },
    {
        "claim_id": "MKT-03",
        "metric": "Global GPUaaS Market (TAM reference)",
        "geography": "Global",
        "start_year": 2026,
        "start_value_b": 12.5,
        "end_year": 2031,
        "end_value_b": 35.0,
        "cagr": None,
        "source_owner": "MarketsandMarkets",
        "source_url": "https://www.marketsandmarkets.com/Market-Reports/gpu-as-a-service-market-153803419.html",
        "source_accessed": "2026-08-11",
        "source_confidence": "B",
        "normalization_method": "none",
        "notes": "MarketsandMarkets GPUaaS report. CAGR auto-calc ~22.9%",
    },
    # REMOVED entries:
    # - "Southeast Asia Public Cloud $8B->$30B" — source was Technavio DC market report, not public cloud. Metric mismatch.
    # - "Asia-Pacific AI Data Center $11.8B" — no verifiable start/end pair. Needs source verification.
    # - "Philippines BPO $102B/2034" — no IBPAP or first-tier source found. Replaced with verified 2026-2028 outlook.
]


def build_market_table():
    rows = []
    for d in MARKET_DATA:
        years = d["end_year"] - d["start_year"] if d["end_year"] else None
        cagr = None
        if years and d["start_value_b"] and d["end_value_b"]:
            cagr = calc_cagr(d["start_value_b"], d["end_value_b"], years)

        size_str = f"${d['start_value_b']:.1f}B"
        if d["end_value_b"]:
            size_str += f" -> ${d['end_value_b']:.1f}B"

        rows.append({
            "metric": d["metric"],
            "geography": d["geography"],
            "size": size_str,
            "period": f"{d['start_year']}-{d['end_year']}" if d["end_year"] else str(d["start_year"]),
            "cagr": f"{cagr:.1%}" if cagr else "N/A",
            "source": d["source_owner"],
            "confidence": d["source_confidence"],
            "url": d["source_url"],
        })
    return pd.DataFrame(rows)


def calc_som_note():
    return (
        "SOM requires bottom-up calculation from actual GPU capacity, power, "
        "ramp schedule and signed contracts. PLDT 65% is data center CAPACITY share, "
        "not revenue share or AI compute addressable share. This report does not provide a SOM figure."
    )


if __name__ == "__main__":
    pd.set_option("display.width", 200)

    print("=" * 100)
    print("  Market Data (TAM/SAM) — Verified sources only")
    print("=" * 100)

    df = build_market_table()
    print(df.to_string(index=False))

    print("\n--- CAGR verification ---")
    for d in MARKET_DATA:
        if d["end_value_b"] and d["start_value_b"]:
            years = d["end_year"] - d["start_year"]
            cagr = calc_cagr(d["start_value_b"], d["end_value_b"], years)
            print(f"  {d['metric']}: ${d['start_value_b']:.2f}B -> ${d['end_value_b']:.2f}B over {years}y = {cagr:.1%}")

    print("\n--- Removed entries (Round 2 review) ---")
    print("  REMOVED: 'SE Asia Public Cloud $8B->$30B' — source was Technavio DC market, metric mismatch")
    print("  REMOVED: 'Philippines DC $0.766B->$1.97B 2026-2030' — wrong year series; fixed to Mordor $0.85B->2.37B 2026-2031")
    print("  REMOVED: 'Philippines BPO $102B/2034' — unverified; replaced with IBPAP 2026-2028 outlook")
    print("  REMOVED: 'Asia-Pacific AI DC $11.8B' — no verifiable start/end pair")

    print(f"\n--- SOM ---")
    print(calc_som_note())
