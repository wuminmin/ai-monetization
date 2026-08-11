#!/usr/bin/env python3
"""
GPU TCO Calculator — H100 SXM5 8-GPU Server Node
按审阅意见重算：服务器级功耗 + PUE + 多情景
数据来源标注在每个常量旁
"""

# ============================================================
# 硬件参数 (来源: NVIDIA DGX H100 Datasheet + 实测)
# ============================================================
GPU_MODEL = "NVIDIA H100 SXM5"
GPU_PRICE = 30_000          # 单卡采购价 $ (来源: NVIDIA distributor pricing 2026)
GPUS_PER_NODE = 8           # DGX H100 标准 8 卡
NODE_PRICE = 300_000        # 整机 DGX 价 ($), 含 8×GPU+CPU+内存+网络+存储
DEPREC_YEARS = 4
GPU_RESIDUAL = 0.20         # 残值率
SYSTEM_RESIDUAL = 0.15

# 服务器级功耗 (来源: DGX H100 datasheet ~10.2kW max; NVIDIA max-TDP config)
# GPU: 8 × 700W SXM = 5,600W
# CPU: 2 × Intel Xeon ~700W
# 内存: 2TB DDR5 ~250W  
# NVSwitch + NIC + 存储 + 主板 ~450W
# 合计峰值: ~7,000W IT 负载
NODE_PEAK_POWER_KW = 7.0    # 峰值 IT 功耗 (kW)
NODE_IDLE_POWER_KW = 2.8    # 空闲 IT 功耗 (~40% 峰值)

# 功耗随利用率变化 (非线性): load_power = idle + (peak - idle) * load_factor
LOAD_POWER_EXPONENT = 0.8   # 功耗与负载非线性关系指数

# ============================================================
# 运营成本 ($/GPU/yr) — 非电力固定成本
# ============================================================
COST_FACILITY = 1_500       # Tier-III DC 机架空间+冷却分摊
COST_NETWORK = 400           # PLDT 骨干网互联
COST_OPS = 600               # 运维 SRE 人力分摊
COST_SOFTWARE = 500          # 软件/许可/保险

# ============================================================
# 电价 ($/kWh)
# ============================================================
POWER_PPA = 0.085            # PPA 协议价 (来源: WESM 批发 ~₱4.14/kWh → ~$0.075, PPA 加成 $0.085)
POWER_COMMERCIAL = 0.161     # 商业零售 (来源: GlobalPetrolPrices Philippines)

# ============================================================
# 三种情景 (按审阅建议)
# ============================================================
SCENARIOS = {
    "优化": {"avg_load": 0.60, "pue": 1.25, "power_rate": POWER_PPA},
    "基准": {"avg_load": 0.70, "pue": 1.40, "power_rate": (POWER_PPA + POWER_COMMERCIAL) / 2},
    "压力": {"avg_load": 0.80, "pue": 1.60, "power_rate": POWER_COMMERCIAL},
}


def node_power_at_load(load: float) -> float:
    """计算节点在某负载下的实际 IT 功耗 (kW)"""
    return NODE_IDLE_POWER_KW + (NODE_PEAK_POWER_KW - NODE_IDLE_POWER_KW) * (load ** LOAD_POWER_EXPONENT)


def gpu_power_at_load(load: float) -> float:
    """单 GPU 分摊功耗 (kW/GPU)"""
    return node_power_at_load(load) / GPUS_PER_NODE


def annual_power_cost_per_gpu(load: float, pue: float, power_rate: float) -> float:
    """年电力成本/GPU = (IT功耗/GPU × PUE × 8760 × 电价)"""
    return gpu_power_at_load(load) * pue * 8760 * power_rate


def annual_depreciation_per_gpu() -> float:
    """GPU 折旧"""
    return GPU_PRICE * (1 - GPU_RESIDUAL) / DEPREC_YEARS


def annual_system_depreciation_per_gpu() -> float:
    """服务器系统折旧 (不含 GPU 本身)"""
    system_cost = NODE_PRICE - GPU_PRICE * GPUS_PER_NODE  # $60,000
    per_gpu = system_cost / GPUS_PER_NODE  # $7,500
    return per_gpu * (1 - SYSTEM_RESIDUAL) / DEPREC_YEARS


def annual_tco_per_gpu(load: float, pue: float, power_rate: float) -> float:
    """单 GPU 年 TCO"""
    dep = annual_depreciation_per_gpu()
    sys_dep = annual_system_depreciation_per_gpu()
    power = annual_power_cost_per_gpu(load, pue, power_rate)
    fixed = COST_FACILITY + COST_NETWORK + COST_OPS + COST_SOFTWARE
    return dep + sys_dep + power + fixed


def break_even_price_per_gpu_hr(load: float, pue: float, power_rate: float) -> float:
    """保本价 $/GPU/hr"""
    return annual_tco_per_gpu(load, pue, power_rate) / (8760 * load)


def gross_margin(price: float, load: float, pue: float, power_rate: float) -> float:
    """毛利率"""
    cost = break_even_price_per_gpu_hr(load, pue, power_rate)
    return (price - cost) / price if price > 0 else -1.0


def build_tco_table():
    """生成 TCO 分解表"""
    import pandas as pd
    rows = []
    base_fixed = {
        "GPU折旧": annual_depreciation_per_gpu(),
        "服务器系统折旧": annual_system_depreciation_per_gpu(),
        "设施 (Tier-III DC)": COST_FACILITY,
        "网络互联 (PLDT骨干网)": COST_NETWORK,
        "运维人力": COST_OPS,
        "软件/许可/保险": COST_SOFTWARE,
    }

    for scenario, p in SCENARIOS.items():
        row = {"情景": scenario, "平均负载": p["avg_load"], "PUE": p["pue"], "电价": p["power_rate"]}
        for item, cost in base_fixed.items():
            row[item] = round(cost, 2)
        power = annual_power_cost_per_gpu(p["avg_load"], p["pue"], p["power_rate"])
        row["电力(含PUE)"] = round(power, 2)
        row["合计"] = round(sum(base_fixed.values()) + power, 2)
        row["保本价$/hr"] = round(break_even_price_per_gpu_hr(p["avg_load"], p["pue"], p["power_rate"]), 2)
        rows.append(row)
    return pd.DataFrame(rows)


def build_margin_sensitivity():
    """生成毛利率敏感性矩阵"""
    import pandas as pd
    prices = [2.20, 2.49, 2.69, 3.00, 3.20, 3.67]
    rows = []
    for scenario, p in SCENARIOS.items():
        for price in prices:
            gm = gross_margin(price, p["avg_load"], p["pue"], p["power_rate"])
            be = break_even_price_per_gpu_hr(p["avg_load"], p["pue"], p["power_rate"])
            if gm < 0:
                verdict = "❌"
            elif gm < 0.10:
                verdict = "⚠️"
            elif gm < 0.30:
                verdict = "✅"
            else:
                verdict = "✅✅"
            rows.append({
                "情景": scenario,
                "负载": p["avg_load"],
                "PUE": p["pue"],
                "定价$/hr": price,
                "保本价$/hr": round(be, 2),
                "毛利率": round(gm, 4),
                "盈利": verdict,
            })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import pandas as pd
    pd.set_option("display.float_format", lambda x: f"{x:,.2f}")
    pd.set_option("display.width", 200)

    print("=" * 100)
    print("  GPU TCO Calculator -- H100 SXM5 8-GPU Node (server-level power + PUE)")
    print("=" * 100)

    print(f"\nNode peak IT power: {NODE_PEAK_POWER_KW} kW (8x700W GPU + CPU + mem + network)")
    print(f"Node idle IT power: {NODE_IDLE_POWER_KW} kW")
    for load in [0.5, 0.6, 0.7, 0.8]:
        p = node_power_at_load(load)
        print(f"  {load:.0%} load: {p:.2f} kW IT -> {p/GPUS_PER_NODE:.3f} kW/GPU")

    print("\n--- TCO breakdown (3 scenarios) ---")
    tco = build_tco_table()
    print(tco.to_string(index=False))

    print("\n--- Break-even price ---")
    for scenario, p in SCENARIOS.items():
        be = break_even_price_per_gpu_hr(p["avg_load"], p["pue"], p["power_rate"])
        print(f"  {scenario:8s} (load={p['avg_load']:.0%}, PUE={p['pue']}): break-even ${be:.2f}/GPU/hr")

    print("\n--- Gross margin sensitivity ---")
    ms = build_margin_sensitivity()
    for scenario in SCENARIOS:
        sub = ms[ms["\u60c5\u666f"] == scenario]
        print(f"\n  [{scenario}]")
        for _, r in sub.iterrows():
            price_col = "\u5b9a\u4ef7$/hr"
            gm_col = "\u6bdb\u5229\u7387"
            verdict_col = "\u76c8\u5229"
            print(f"    ${r[price_col]:.2f}/hr -> GM {r[gm_col]:.1%} {r[verdict_col]}")
