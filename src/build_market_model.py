#!/usr/bin/env python3
"""
Market Data — TAM/SAM/SOM
按审阅意见修复：保留来源原始年份，CAGR 自动计算，SOM 独立计算
"""

import math


def calc_cagr(start_value, end_value, years):
    """自动计算 CAGR"""
    return (end_value / start_value) ** (1 / years) - 1


def assert_cagr(start, end, years, reported_cagr, tol=0.005):
    """验证 CAGR 一致性"""
    actual = calc_cagr(start, end, years)
    assert abs(actual - reported_cagr) < tol, \
        f"CAGR mismatch: reported {reported_cagr:.1%}, actual {actual:.1%}"


# ============================================================
# 市场数据 — 严格保留来源原始年份
# ============================================================

MARKET_DATA = [
    {
        "claim_id": "M1",
        "metric": "全球 GPUaaS (TAM)",
        "start_value_b": 12.5,
        "end_value_b": 35.0,
        "start_year": 2026,
        "end_year": 2031,
        "cagr": None,  # auto-calc
        "source": "MarketsandMarkets GPUaaS Report",
        "source_url": "https://www.marketsandmarkets.com/Market-Reports/gpu-as-a-service-market-153803419.html",
        "source_type": "B",  # 研究机构报告
        "accessed": "2026-08-11",
        "confidence": "B",
    },
    {
        "claim_id": "M2",
        "metric": "亚太 AI 数据中心",
        "start_value_b": 11.8,
        "end_value_b": None,
        "start_year": 2026,
        "end_year": None,
        "cagr": 0.227,
        "source": "Asia-Pacific AI DC Report",
        "source_url": None,
        "source_type": "B",
        "accessed": "2026-08-11",
        "confidence": "C",
    },
    {
        "claim_id": "M3",
        "metric": "东南亚公有云",
        "start_value_b": 8.0,
        "end_value_b": 30.0,
        "start_year": 2026,
        "end_year": 2030,
        "cagr": None,
        "source": "Technavio / LinkedIn Industry Analysis",
        "source_url": "https://www.technavio.com/report/data-center-market-size-in-southeast-asia",
        "source_type": "B",
        "accessed": "2026-08-11",
        "confidence": "C",
    },
    {
        "claim_id": "M4",
        "metric": "菲律宾数据中心 (SAM 基准)",
        "start_value_b": 0.766,
        "end_value_b": 1.97,
        "start_year": 2026,
        "end_year": 2030,
        "cagr": None,
        "source": "Mordor Intelligence Philippines DC Report",
        "source_url": "https://www.mordorintelligence.com/industry-reports/philippines-data-center-market",
        "source_type": "B",
        "accessed": "2026-08-11",
        "confidence": "B",
    },
    {
        "claim_id": "M5",
        "metric": "菲律宾 BPO 产业",
        "start_value_b": 38.0,
        "end_value_b": 102.0,
        "start_year": 2026,
        "end_year": 2034,
        "cagr": None,
        "source": "IBPAP Industry Roadmap",
        "source_url": "https://www.ibpap.org/research",
        "source_type": "B",
        "accessed": "2026-08-11",
        "confidence": "B",
    },
]


def build_market_table():
    """生成市场数据表，自动计算 CAGR"""
    import pandas as pd
    rows = []
    for d in MARKET_DATA:
        years = (d["end_year"] - d["start_year"]) if d["end_year"] else None
        if years and d["start_value_b"] and d["end_value_b"]:
            cagr = calc_cagr(d["start_value_b"], d["end_value_b"], years)
        elif d["cagr"]:
            cagr = d["cagr"]
        else:
            cagr = None

        size_str = f"${d['start_value_b']:.1f}B"
        if d["end_value_b"]:
            size_str += f" -> ${d['end_value_b']:.1f}B"

        rows.append({
            "metric": d["metric"],
            "size": size_str,
            "period": f"{d['start_year']}-{d['end_year']}" if d['end_year'] else str(d['start_year']),
            "cagr": f"{cagr:.1%}" if cagr else "N/A",
            "source": d["source"],
            "confidence": d["confidence"],
        })
    return pd.DataFrame(rows)


# ============================================================
# SOM 计算 — 独立 bottom-up
# 注: 审阅指出 "不应直接用 市场规模 × PLDT市占率"
# ============================================================

def calc_som_note():
    """SOM 说明"""
    return (
        "SOM 需基于实际 GPU 容量、供电、上架节奏和已签合同做 bottom-up 计算。\n"
        "本报告不提供 SOM 数值；PLDT 65% 为数据中心容量口径，不等于收入份额或 AI 算力可获取份额。"
    )


if __name__ == "__main__":
    import pandas as pd
    pd.set_option("display.width", 200)

    print("=" * 100)
    print("  Market Data (TAM/SAM) — CAGR auto-calculated")
    print("=" * 100)

    df = build_market_table()
    print(df.to_string(index=False))

    print("\n--- CAGR 验证 ---")
    for d in MARKET_DATA:
        if d["end_value_b"] and d["start_value_b"]:
            years = d["end_year"] - d["start_year"]
            cagr = calc_cagr(d["start_value_b"], d["end_value_b"], years)
            print(f"  {d['metric']}: {d['start_value_b']:.2f} -> {d['end_value_b']:.2f} over {years}y = {cagr:.1%}")

    print(f"\n--- SOM ---")
    print(calc_som_note())
