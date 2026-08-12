#!/usr/bin/env python3
"""
GPU TCO Calculator — H100 SXM5 8-GPU Node
Rebuilt per Round 2 review: separates 4 utilization variables.
  - service_availability: uptime fraction (when GPU can be sold)
  - commercial_utilization: fraction of available time actually sold/billed
  - active_compute_utilization (MFU proxy): drives power consumption
  - billing_efficiency: billed hours / running hours (deducts failures etc.)
"""

import yaml
import os
import hashlib
import pandas as pd

# ============================================================
# Load assumptions from YAML as single source of truth
# ============================================================
ASSUMPTIONS_PATH = os.path.join(os.path.dirname(__file__), "..", "methodology", "assumptions.yaml")

def load_assumptions():
    with open(ASSUMPTIONS_PATH, "r") as f:
        return yaml.safe_load(f)

PARAMS = load_assumptions()

# Extract hardware params
GPU_MODEL = PARAMS["gpu"]["model"]
GPU_PRICE = PARAMS["gpu"]["unit_price_usd"]
GPUS_PER_NODE = PARAMS["gpu"]["gpus_per_node"]
NODE_PRICE = PARAMS["gpu"]["dgx_price_usd"]
DEPREC_YEARS = PARAMS["gpu"]["depreciation_years"]
GPU_RESIDUAL = PARAMS["gpu"]["gpu_residual"]
SYSTEM_RESIDUAL = PARAMS["gpu"]["system_residual"]

# Power params
NAMEPLATE_MAX_POWER_KW = PARAMS["power"]["nameplate_max_kw"]  # 10.2 from DGX datasheet
IDLE_POWER_KW = PARAMS["power"]["idle_power_kw"]              # null = needs measurement
ACTIVE_POWER_AT_TARGET_MFU_KW = PARAMS["power"]["active_power_kw_at_target_mfu"]  # 7.0
POWER_CURVE_EXPONENT = PARAMS["power"]["load_power_exponent"]

POWER_PPA = PARAMS["power"]["ppa_rate"]
POWER_COMMERCIAL = PARAMS["power"]["commercial_rate"]

FIXED_COSTS = PARAMS["fixed_costs_per_gpu_year"]

# ============================================================
# Scenarios — now separate utilization dimensions
# ============================================================
SCENARIOS = {
    "demand_down": {
        "label": "Demand Down",
        "commercial_utilization": 0.35,
        "active_compute_mfu": 0.45,
        "service_availability": 0.99,
        "billing_efficiency": 0.95,
        "pue": 1.40,
        "power_rate": POWER_PPA,
    },
    "baseline": {
        "label": "Baseline",
        "commercial_utilization": 0.60,
        "active_compute_mfu": 0.50,
        "service_availability": 0.99,
        "billing_efficiency": 0.95,
        "pue": 1.40,
        "power_rate": POWER_PPA,
    },
    "demand_up": {
        "label": "Demand Up",
        "commercial_utilization": 0.80,
        "active_compute_mfu": 0.55,
        "service_availability": 0.99,
        "billing_efficiency": 0.95,
        "pue": 1.40,
        "power_rate": POWER_PPA,
    },
    "energy_stress": {
        "label": "Energy Stress",
        "commercial_utilization": 0.60,
        "active_compute_mfu": 0.50,
        "service_availability": 0.99,
        "billing_efficiency": 0.95,
        "pue": 1.60,
        "power_rate": POWER_COMMERCIAL,
    },
    "reliability_stress": {
        "label": "Reliability Stress",
        "commercial_utilization": 0.60,
        "active_compute_mfu": 0.50,
        "service_availability": 0.95,
        "billing_efficiency": 0.90,
        "pue": 1.40,
        "power_rate": POWER_PPA,
    },
}


def node_power_at_mfu(active_mfu: float) -> float:
    """IT power at given active compute MFU.
    Uses nameplate max as upper bound, idle as lower bound.
    active_mfu ~0.5 maps roughly to 7kW for DGX H100.
    """
    if not 0 <= active_mfu <= 1:
        raise ValueError(f"MFU must be between 0 and 1, got {active_mfu}")
    if IDLE_POWER_KW is None:
        raise ValueError("idle_power_kw is null in assumptions — needs measured value")
    calculated = IDLE_POWER_KW + (ACTIVE_POWER_AT_TARGET_MFU_KW - IDLE_POWER_KW) * (
        active_mfu / 0.50
    ) ** POWER_CURVE_EXPONENT
    # Clamp to physical bounds
    return min(NAMEPLATE_MAX_POWER_KW, max(IDLE_POWER_KW, calculated))


def avg_node_power(s: dict) -> float:
    """Average node IT power over calendar year, accounting for idle vs active time."""
    active_power = node_power_at_mfu(s["active_compute_mfu"])
    util = s["commercial_utilization"]
    avail = s["service_availability"]
    # When not commercially utilized but available: idle power
    # When commercially utilized: active power
    return avail * (util * active_power + (1 - util) * IDLE_POWER_KW) + (1 - avail) * IDLE_POWER_KW


def annual_power_cost_per_gpu(s: dict) -> float:
    """Annual electricity cost per GPU."""
    node_kw = avg_node_power(s)
    per_gpu_kw = node_kw / GPUS_PER_NODE
    return per_gpu_kw * s["pue"] * 8760 * s["power_rate"]


def annual_depreciation_per_gpu() -> float:
    return GPU_PRICE * (1 - GPU_RESIDUAL) / DEPREC_YEARS


def annual_system_depreciation_per_gpu(node_price: float = NODE_PRICE) -> float:
    system_cost = node_price - GPU_PRICE * GPUS_PER_NODE
    per_gpu = system_cost / GPUS_PER_NODE
    return per_gpu * (1 - SYSTEM_RESIDUAL) / DEPREC_YEARS


def annual_tco_per_gpu(s: dict, node_price: float = NODE_PRICE) -> float:
    dep = annual_depreciation_per_gpu()
    sys_dep = annual_system_depreciation_per_gpu(node_price)
    power = annual_power_cost_per_gpu(s)
    fixed = FIXED_COSTS["facility"] + FIXED_COSTS["network"] + FIXED_COSTS["ops"] + FIXED_COSTS["software"]
    return dep + sys_dep + power + fixed


def billable_gpu_hours_per_year(s: dict) -> float:
    """Billable GPU-hours per year per GPU."""
    return 8760 * s["service_availability"] * s["commercial_utilization"] * s["billing_efficiency"]


def break_even_price_per_gpu_hr(s: dict, node_price: float = NODE_PRICE) -> float:
    """Infrastructure break-even $/GPU/hr (contribution margin basis).

    node_price may be overridden for sensitivity analysis (baseline = NODE_PRICE).
    """
    annual_cost = annual_tco_per_gpu(s, node_price)
    billable_hours = billable_gpu_hours_per_year(s)
    return annual_cost / billable_hours


def contribution_margin(price: float, s: dict) -> float:
    """Infrastructure contribution margin (NOT full enterprise gross margin)."""
    be = break_even_price_per_gpu_hr(s)
    return (price - be) / price if price > 0 else -1.0


def build_tco_table():
    rows = []
    base_fixed = {
        "GPU depreciation": annual_depreciation_per_gpu(),
        "System depreciation": annual_system_depreciation_per_gpu(),
        "Facility (Tier-III DC)": FIXED_COSTS["facility"],
        "Network (PLDT backbone)": FIXED_COSTS["network"],
        "Ops/SRE": FIXED_COSTS["ops"],
        "Software/License/Insurance": FIXED_COSTS["software"],
    }
    for key, s in SCENARIOS.items():
        row = {
            "scenario": s["label"],
            "comm_util": s["commercial_utilization"],
            "active_mfu": s["active_compute_mfu"],
            "availability": s["service_availability"],
            "billing_eff": s["billing_efficiency"],
            "pue": s["pue"],
        }
        for item, cost in base_fixed.items():
            row[item] = round(cost, 2)
        power = annual_power_cost_per_gpu(s)
        row["Power (with PUE)"] = round(power, 2)
        row["Annual TCO"] = round(sum(base_fixed.values()) + power, 2)
        row["Billable hrs/yr"] = round(billable_gpu_hours_per_year(s))
        row["Break-even $/GPU/hr"] = round(break_even_price_per_gpu_hr(s), 2)
        rows.append(row)
    return pd.DataFrame(rows)


def build_margin_sensitivity():
    prices = [1.50, 2.00, 2.69, 3.20, 3.99, 5.00, 6.16]
    rows = []
    for key, s in SCENARIOS.items():
        for price in prices:
            cm = contribution_margin(price, s)
            be = break_even_price_per_gpu_hr(s)
            if cm < 0:
                verdict = "loss"
            elif cm < 0.10:
                verdict = "thin"
            elif cm < 0.30:
                verdict = "ok"
            else:
                verdict = "strong"
            rows.append({
                "scenario": s["label"],
                "price_per_gpu_hr": price,
                "break_even": round(be, 2),
                "contribution_margin": round(cm, 4),
                "verdict": verdict,
            })
    return pd.DataFrame(rows)


def build_node_price_sensitivity():
    """Break-even $/GPU/hr across a range of DGX node purchase prices.

    The node price is an unverified internal estimate (confidence D). This table
    shows how the break-even floor moves with the assumed purchase price, so the
    report can present a cost RANGE rather than a single point.
    """
    # Baseline = assumptions.yaml value; stressed cases probe higher quotes.
    node_prices = [NODE_PRICE, NODE_PRICE + 50000, NODE_PRICE + 100000,
                   NODE_PRICE + 150000, NODE_PRICE + 200000]
    rows = []
    for key, s in SCENARIOS.items():
        for np in node_prices:
            be = break_even_price_per_gpu_hr(s, node_price=np)
            rows.append({
                "scenario": s["label"],
                "node_price_usd": np,
                "break_even_per_gpu_hr": round(be, 2),
                "delta_vs_baseline": round(be - break_even_price_per_gpu_hr(s), 2),
            })
    return pd.DataFrame(rows)


def build_pricing_recommendations():
    """Recommended $/GPU/hr as a 2-D function of node price AND scenario.

    The node price is an unverified internal estimate (confidence D). A fixed
    pricing recommendation that assumes $300k becomes a loss if the real quote
    is $400k (break-even rises from $2.28 to $2.82). Instead we output, for
    each (node_price, scenario) pair, the minimum price that achieves a target
    infrastructure contribution margin:

        recommended_price = break_even(node_price, scenario) / (1 - target_cm)

    This guarantees no recommended price implies a negative margin, regardless
    of the eventual node-quote outcome.
    """
    # Target infrastructure contribution margins by procurement tier.
    TARGET_CM = {
        "spot": 0.00,       # covers break-even only (marginal floor)
        "reserved": 0.15,   # 15% contribution margin for committed term
        "on_demand": 0.40,  # 40% contribution margin for flexible on-demand
    }
    node_prices = [NODE_PRICE, NODE_PRICE + 100000, NODE_PRICE + 200000]  # 300k/400k/500k
    main_scenarios = ["demand_down", "baseline", "demand_up"]

    rows = []
    for tier, target_cm in TARGET_CM.items():
        for np_ in node_prices:
            for skey in main_scenarios:
                s = SCENARIOS[skey]
                be = break_even_price_per_gpu_hr(s, node_price=np_)
                rec = be / (1 - target_cm) if target_cm < 1 else be
                rows.append({
                    "tier": tier,
                    "target_cm": target_cm,
                    "node_price_usd": np_,
                    "scenario": s["label"],
                    "break_even_per_gpu_hr": round(be, 2),
                    "recommended_price_per_gpu_hr": round(rec, 2),
                })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    pd.set_option("display.float_format", lambda x: f"{x:,.2f}")
    pd.set_option("display.width", 200)

    print("=" * 100)
    print("  GPU TCO Calculator — H100 SXM5 8-GPU Node")
    print(f"  Nameplate max: {NAMEPLATE_MAX_POWER_KW} kW | Active at target MFU: {ACTIVE_POWER_AT_TARGET_MFU_KW} kW | Idle: {IDLE_POWER_KW} kW")
    print(f"  NOTE: This is INFRASTRUCTURE CONTRIBUTION MARGIN, not full enterprise gross margin.")
    print(f"  Missing: sales, support, bad debt, financing, import duties, spare parts, network fabric, storage, SLA penalties.")
    print("=" * 100)

    print("\n--- Power at various MFU ---")
    for mfu in [0.30, 0.40, 0.50, 0.55, 0.60]:
        p = node_power_at_mfu(mfu)
        print(f"  MFU {mfu:.0%}: {p:.2f} kW/node -> {p/GPUS_PER_NODE:.3f} kW/GPU")

    print("\n--- TCO breakdown (5 scenarios) ---")
    tco = build_tco_table()
    print(tco.to_string(index=False))

    print("\n--- Break-even comparison ---")
    for key, s in SCENARIOS.items():
        be = break_even_price_per_gpu_hr(s)
        hrs = billable_gpu_hours_per_year(s)
        print(f"  {s['label']:20s} comm={s['commercial_utilization']:.0%} "
              f"mfu={s['active_compute_mfu']:.0%} avail={s['service_availability']:.0%}: "
              f"break-even ${be:.2f}/GPU/hr ({hrs:.0f} billable hrs)")

    print("\n--- Contribution margin sensitivity ---")
    ms = build_margin_sensitivity()
    for scenario_key in SCENARIOS:
        s = SCENARIOS[scenario_key]
        sub = ms[ms["scenario"] == s["label"]]
        print(f"\n  [{s['label']}]")
        for _, r in sub.iterrows():
            print(f"    ${r['price_per_gpu_hr']:.2f}/hr -> CM {r['contribution_margin']:.1%} [{r['verdict']}]")
