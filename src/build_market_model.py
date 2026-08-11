#!/usr/bin/env python3
"""
Market Data — TAM/SAM with scenario ranges.
CAGR auto-calculated. BPO uses downside/upside range per IBPAP.
"""

import pandas as pd


def calc_cagr(start_value, end_value, years):
    return (end_value / start_value) ** (1 / years) - 1


# ============================================================
# Market data
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
        "source_accessed": "2026-08-11",
        "source_confidence": "B",
        "normalization_method": "none",
    },
    {
        "claim_id": "MKT-02",
        "metric": "Philippines BPO Industry Revenue",
        "geography": "Philippines",
        "start_year": 2025,
        "start_value_b": 40.3,
        "end_year": 2028,
        "end_value_b": None,  # range
        "end_value_downside_b": 43.3,
        "end_value_upside_b": 50.5,
        "source_owner": "IBPAP",
        "source_url": "https://ibpap.org/news-room/43",
        "source_accessed": "2026-08-11",
        "source_confidence": "B",
        "normalization_method": "none",
        "notes": "2025 actual $40.3B. 2028 projection range $43.3B-$50.5B (downside-upside).",
    },
    {
        "claim_id": "MKT-03",
        "metric": "Global GPUaaS Market (TAM reference)",
        "geography": "Global",
        "start_year": 2026,
        "start_value_b": 12.5,
        "end_year": 2031,
        "end_value_b": 35.0,
        "source_owner": "MarketsandMarkets",
        "source_url": "https://www.marketsandmarkets.com/Market-Reports/gpu-as-a-service-market-153803419.html",
        "source_accessed": "2026-08-11",
        "source_confidence": "B",
    },
]


def build_market_table():
    rows = []
    for d in MARKET_DATA:
        years = d["end_year"] - d["start_year"] if d.get("end_year") else None

        if d.get("end_value_b"):
            cagr = calc_cagr(d["start_value_b"], d["end_value_b"], years)
            size_str = f"${d['start_value_b']:.1f}B -> ${d['end_value_b']:.1f}B"
        elif d.get("end_value_downside_b") and d.get("end_value_upside_b"):
            cagr_down = calc_cagr(d["start_value_b"], d["end_value_downside_b"], years)
            cagr_up = calc_cagr(d["start_value_b"], d["end_value_upside_b"], years)
            cagr = f"{cagr_down:.1%}-{cagr_up:.1%}"
            size_str = f"${d['start_value_b']:.1f}B -> ${d['end_value_downside_b']:.1f}B-${d['end_value_upside_b']:.1f}B"
        else:
            cagr = "N/A"
            size_str = f"${d['start_value_b']:.1f}B"

        rows.append({
            "metric": d["metric"],
            "geography": d["geography"],
            "size": size_str,
            "period": f"{d['start_year']}-{d['end_year']}",
            "cagr": cagr,
            "source": d["source_owner"],
            "confidence": d["source_confidence"],
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    print("=" * 100)
    print("  Market Data — Verified sources, BPO as scenario range")
    print("=" * 100)

    df = build_market_table()
    print(df.to_string(index=False))

    print("\n--- CAGR detail ---")
    for d in MARKET_DATA:
        if d.get("end_value_b"):
            years = d["end_year"] - d["start_year"]
            cagr = calc_cagr(d["start_value_b"], d["end_value_b"], years)
            print(f"  {d['metric']}: {cagr:.1%}")
        elif d.get("end_value_downside_b"):
            years = d["end_year"] - d["start_year"]
            cagr_down = calc_cagr(d["start_value_b"], d["end_value_downside_b"], years)
            cagr_up = calc_cagr(d["start_value_b"], d["end_value_upside_b"], years)
            print(f"  {d['metric']}: downside {cagr_down:.1%}, upside {cagr_up:.1%}")
