#!/usr/bin/env python3
"""
MaaS Unit Economics — self-hosted open models
按审阅意见重建：输入/输出分拆, 标注精度, 标注来源
吞吐量为预估值（vLLM 连续批处理，非 SLA goodput），实际需 benchmark 验证
"""

# ============================================================
# GPU 成本基准 (来自 build_gpu_tco.py, 基准情景)
# ============================================================
GPU_COST_HR = 1.91  # $/GPU/hr, 70% load, PUE 1.4, mixed power (来自 TCO 模型)

# ============================================================
# 模型定义 — 含完整规格
# 来源: OpenRouter API model descriptions (accessed 2026-08-11)
# 吞吐量为估算值，基于 MoE 激活参数和公开 benchmark 趋势
# 实际生产吞吐取决于输入长度、输出长度、并发、精度和 SLA
# ============================================================

MODELS = [
    {
        "model": "DeepSeek V4 Flash",
        "provider_openrouter": "deepseek/deepseek-v4-flash",
        "total_params": "284B",
        "active_params": "13B",
        "arch": "MoE",
        "context": "1M",
        "gpu_config": "8xH100",
        "gpu_count": 8,
        "precision": "FP8",
        "est_throughput_tps": 35000,  # 估算, 非实测
        "throughput_note": "vLLM FP8, 大 batch 估算; 待 benchmark",
        "comp_in": 0.14,
        "comp_out": 0.28,
        "comp_provider": "DeepSeek API direct / OpenRouter",
        "positioning": "海量流量主力",
    },
    {
        "model": "DeepSeek V4 Pro",
        "provider_openrouter": "deepseek/deepseek-v4-pro",
        "total_params": "1.6T",
        "active_params": "49B",
        "arch": "MoE",
        "context": "1M",
        "gpu_config": "16xH100",
        "gpu_count": 16,
        "precision": "FP8",
        "est_throughput_tps": 22000,
        "throughput_note": "多机部署 (TP=8,PP=2); 待 benchmark",
        "comp_in": 0.63,
        "comp_out": 1.26,
        "comp_provider": "DeepSeek API direct / OpenRouter",
        "positioning": "高质量推理",
    },
    {
        "model": "Qwen 3.5 Flash",
        "provider_openrouter": "qwen/qwen3.5-flash-02-23",
        "total_params": "~30B",
        "active_params": "~3B",
        "arch": "MoE (线性注意力混合)",
        "context": "1M",
        "gpu_config": "1xH100",
        "gpu_count": 1,
        "precision": "FP8",
        "est_throughput_tps": 28000,
        "throughput_note": "线性注意力+MoE 极高效; 待 benchmark",
        "comp_in": 0.065,
        "comp_out": 0.26,
        "comp_provider": "Qwen API / OpenRouter",
        "positioning": "轻量高吞吐",
    },
    {
        "model": "Qwen 3.5 9B",
        "provider_openrouter": "qwen/qwen3.5-9b",
        "total_params": "9B",
        "active_params": "9B (dense)",
        "arch": "Dense",
        "context": "256K",
        "gpu_config": "1xH100",
        "gpu_count": 1,
        "precision": "BF16",
        "est_throughput_tps": 14000,
        "throughput_note": "稠密模型; 待 benchmark",
        "comp_in": 0.10,
        "comp_out": 0.15,
        "comp_provider": "Qwen API / OpenRouter",
        "positioning": "开发者入门",
    },
    {
        "model": "GPT-OSS 120B",
        "provider_openrouter": "openai/gpt-oss-120b",
        "total_params": "117B",
        "active_params": "5.1B",
        "arch": "MoE",
        "context": "128K",
        "gpu_config": "2xH100",
        "gpu_count": 2,
        "precision": "FP8 (单卡需 INT4, 117B*0.5B/8bit=58GB)",
        "est_throughput_tps": 20000,
        "throughput_note": "INT4 可单卡, 此处 2 卡为吞吐+KV Cache; 待 benchmark",
        "comp_in": 0.037,
        "comp_out": 0.17,
        "comp_provider": "OpenRouter",
        "positioning": "OpenAI 开源, 生态兼容",
    },
    {
        "model": "Gemma 4 31B",
        "provider_openrouter": "google/gemma-4-31b-it",
        "total_params": "30.7B",
        "active_params": "30.7B (dense)",
        "arch": "Dense",
        "context": "256K",
        "gpu_config": "1xH100",
        "gpu_count": 1,
        "precision": "BF16 (权重~62GB, KV Cache 空间有限)",
        "est_throughput_tps": 12000,
        "throughput_note": "BF16 权重占 62/80GB; 高并发需 INT8 或加卡; 待 benchmark",
        "comp_in": 0.10,
        "comp_out": 0.34,
        "comp_provider": "OpenRouter / Google AI",
        "positioning": "Google 开源, 多语言",
    },
    {
        "model": "GLM-5.2",
        "provider_openrouter": "z-ai/glm-5.2",
        "total_params": "~350B",
        "active_params": "~32B",
        "arch": "MoE (reasoning)",
        "context": "1M",
        "gpu_config": "8xH100",
        "gpu_count": 8,
        "precision": "FP8",
        "est_throughput_tps": 25000,
        "throughput_note": "推理模型, 含 thinking; 待 benchmark",
        "comp_in": 0.76,
        "comp_out": 2.42,
        "comp_provider": "Z.AI direct / OpenRouter",
        "positioning": "高端企业级",
    },
]


def calc_unit_economics(m, pricing_factor_in=0.85, pricing_factor_out=0.85):
    """
    计算单模型单位经济
    pricing_factor: 建议定价 = 竞品价 × factor
    返回输入/输出分拆的成本和定价
    """
    gpu_cost_hr = GPU_COST_HR * m["gpu_count"]
    tokens_per_hr = m["est_throughput_tps"] * 3600

    # 成本 $/M tokens (不分输入输出, GPU 时间等价)
    cost_per_m = gpu_cost_hr / (tokens_per_hr / 1e6)

    # 建议定价 — 输入输出分开
    suggested_in = m["comp_in"] * pricing_factor_in
    suggested_out = m["comp_out"] * pricing_factor_out

    # 毛利率 — 用混合价 (70% input, 30% output) 估算
    blended_price = suggested_in * 0.7 + suggested_out * 0.3
    gm = (blended_price - cost_per_m) / blended_price if blended_price > 0 else -1

    return {
        "model": m["model"],
        "total_params": m["total_params"],
        "active_params": m["active_params"],
        "arch": m["arch"],
        "context": m["context"],
        "gpu_config": m["gpu_config"],
        "precision": m["precision"],
        "est_throughput_tps": m["est_throughput_tps"],
        "cost_per_m": round(cost_per_m, 4),
        "comp_in": m["comp_in"],
        "comp_out": m["comp_out"],
        "comp_provider": m["comp_provider"],
        "suggested_in": round(suggested_in, 4),
        "suggested_out": round(suggested_out, 4),
        "blended_gm": round(gm, 4),
        "positioning": m["positioning"],
    }


def build_maas_table():
    """生成 MaaS 经济表"""
    import pandas as pd
    rows = []

    # 分层定价系数
    factors = {
        "DeepSeek V4 Flash": (0.95, 0.95),  # 海量流量: 平价+主权
        "DeepSeek V4 Pro": (0.70, 0.70),     # 高端: 大幅让利
        "Qwen 3.5 Flash": (0.85, 0.85),      # 中端
        "Qwen 3.5 9B": (0.85, 0.85),
        "GPT-OSS 120B": (0.95, 0.95),        # 海量流量
        "Gemma 4 31B": (0.85, 0.85),         # 中端
        "GLM-5.2": (0.70, 0.70),             # 高端
    }

    for m in MODELS:
        fi, fo = factors.get(m["model"], (0.85, 0.85))
        r = calc_unit_economics(m, fi, fo)
        rows.append(r)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import pandas as pd
    pd.set_option("display.width", 200)

    print("=" * 100)
    print("  MaaS Unit Economics (self-hosted, OpenRouter Rankings 2026-08)")
    print("  NOTE: throughput = estimate, not SLA goodput. Requires benchmark validation.")
    print("=" * 100)

    df = build_maas_table()

    for _, r in df.iterrows():
        print(f"\n  {r['model']} ({r['total_params']}/{r['active_params']} {r['arch']})")
        print(f"    GPU: {r['gpu_config']} ({r['precision']})")
        print(f"    Throughput: {r['est_throughput_tps']:,} tok/s (estimate)")
        print(f"    Cost: ${r['cost_per_m']:.4f}/M tok")
        print(f"    Competitor: ${r['comp_in']:.4f}/M_in, ${r['comp_out']:.4f}/M_out ({r['comp_provider']})")
        print(f"    Suggested: ${r['suggested_in']:.4f}/M_in, ${r['suggested_out']:.4f}/M_out")
        print(f"    Blended GM (70/30): {r['blended_gm']:.1%}  [{r['positioning']}]")
