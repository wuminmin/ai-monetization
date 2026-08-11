#!/usr/bin/env python3
"""
GPUaaS Competitive Pricing — 标准化规格对比
按审阅意见：增加 form_factor, gpu_count, pricing_type, sla 等
"""

# 来源标注: accessed 2026-08-11
# 可信度: A=厂商官网, B=研究机构, C=媒体/搜索摘要, D=估算

COMPETITORS = [
    # (vendor, gpu_model, form_factor, gpu_count, instance, cpu, memory_gb, 
    #  local_storage, network, price_hr, pricing_type, sla, region, source, confidence)

    # --- 超大规模云 (8卡整机) ---
    ("AWS", "H100 SXM", "SXM", 8, "p5.48xlarge", "448 vCPU", "6,144", "12.6TB",
     "3.2Tbps EFA", 6.88, "on-demand", "Enterprise SLA", "us-east-1",
     "aws.amazon.com/ec2/pricing", "A"),
    ("Azure", "H100 SXM", "SXM", 8, "ND H100 v5", "96 vCPU", "1,920", "17.6TB",
     "3.2Tbps", 12.29, "on-demand", "Enterprise SLA", "East US",
     "azure.microsoft.com/pricing", "A"),
    ("GCP", "H100 SXM", "SXM", 8, "a3-highgpu-8g", "208 vCPU", "1,872", "17.1TB",
     "3.2Tbps", 3.67, "on-demand", "Enterprise SLA", "us-central1",
     "cloud.google.com/compute/gpu-pricing", "A"),

    # --- 专业 AI 云 ---
    ("CoreWeave", "H100 SXM", "SXM", 8, "8x H100 server", "192 vCPU", "2,048", "15TB",
     "InfiniBand", 2.49, "on-demand", "Business SLA", "US-East",
     "coreweave.com/pricing", "A"),
    ("Lambda Labs", "H100 SXM", "SXM", 8, "8x H100 server", "180 vCPU", "2,000", "15TB",
     "InfiniBand", 2.69, "on-demand", "Business SLA", "US multi-region",
     "lambda.ai/pricing", "A"),

    # --- 市场型/竞价平台 ---
    ("Spheron", "H100 PCIe", "PCIe", 1, "single GPU", "varies", "80", "varies",
     "shared", 2.01, "market/spot", "No SLA", "decentralized",
     "spheron.network", "B"),
    ("Vast.ai", "H100", "varies", 1, "single GPU", "varies", "80", "varies",
     "shared", 2.00, "spot/bid", "No SLA", "decentralized",
     "vast.ai/pricing", "C"),

    # --- 传统云 ---
    ("Oracle", "H100 SXM", "SXM", 8, "BM.GPU.H100.8", "128 OCPU", "2,048", "29TB",
     "RDMA", 3.00, "on-demand", "Enterprise SLA", "us-ashburn-1",
     "oracle.com/cloud/compute", "A"),

    # --- PLDT (内部估算) ---
    ("PLDT VITRO", "H100 SXM", "SXM", 8, "VITRO GPU node", "TBD", "TBD", "TBD",
     "PLDT backbone", None, "TBD", "TBD", "Manila, PH",
     "internal estimate", "D"),
]


def build_gpu_pricing_table():
    """生成标准化竞品价格表"""
    import pandas as pd
    rows = []
    for c in COMPETITORS:
        vendor, gpu_model, form, gpu_count, instance, cpu, mem, storage, net, price, ptype, sla, region, source, conf = c

        # 计算 normalized $/GPU/hr
        norm = price / gpu_count if price and gpu_count else None

        rows.append({
            "vendor": vendor,
            "gpu_model": gpu_model,
            "form_factor": form,
            "gpu_count": gpu_count,
            "instance": instance,
            "cpu": cpu,
            "memory_gb": mem,
            "local_storage": storage,
            "network": net,
            "instance_price_hr": price,
            "per_gpu_hr": round(norm, 2) if norm else None,
            "pricing_type": ptype,
            "sla": sla,
            "region": region,
            "source": source,
            "accessed": "2026-08-11",
            "confidence": conf,
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import pandas as pd
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 20)

    print("=" * 120)
    print("  GPUaaS Competitive Pricing -- Standardized")
    print("  NOTE: per-GPU-hr = instance_price / gpu_count. NOT equivalent across form factors.")
    print("=" * 120)

    df = build_gpu_pricing_table()

    # 简洁视图
    cols = ["vendor", "form_factor", "gpu_count", "instance", "instance_price_hr", "per_gpu_hr", "pricing_type", "sla", "confidence"]
    print("\n--- Nominal pricing ---")
    print(df[cols].to_string(index=False))

    print("\n--- Key insight ---")
    print("8-GPU SXM 整机实例 (AWS/Azure/GCP/CoreWeave/Lambda/Oracle):")
    for _, r in df[df["gpu_count"] == 8].iterrows():
        if r["instance_price_hr"]:
            print(f"  {r['vendor']:15s} ${r['instance_price_hr']:.2f}/hr/instance -> ${r['per_gpu_hr']:.2f}/GPU/hr")
    print("\nSingle GPU market/spot (Spheron/Vast.ai):")
    for _, r in df[df["gpu_count"] == 1].iterrows():
        if r["per_gpu_hr"]:
            print(f"  {r['vendor']:15s} ${r['per_gpu_hr']:.2f}/GPU/hr ({r['pricing_type']})")
