#!/usr/bin/env python3
"""
GPUaaS Competitive Pricing — Standardized
Raw prices from vendor pages, with explicit raw_price_unit.
Normalization handles USD_PER_INSTANCE_HOUR vs USD_PER_GPU_HOUR.
"""

import pandas as pd

ALLOWED_PRICE_UNITS = {
    "USD_PER_INSTANCE_HOUR",
    "USD_PER_GPU_HOUR",
    "USD_PER_ACCELERATOR_HOUR",
}

ALLOWED_PROCUREMENT_MODES = {
    "on_demand",
    "spot",
    "reserved",
    "capacity_block",
    "marketplace",
    "dws",
}

# ============================================================
# Vendor data — prices from official pages (accessed 2026-08-11)
# Each row records the EXACT unit as shown on the page
# ============================================================
COMPETITORS = [
    {
        "provider": "CoreWeave",
        "product_name": "HGX H100 8-GPU Node",
        "source_sku": "hgx-h100-8gpu",
        "gpu_model": "H100 SXM",
        "gpu_form_factor": "SXM",
        "gpu_count": 8,
        "raw_price": 49.24,
        "raw_price_unit": "USD_PER_INSTANCE_HOUR",
        "billing_scope": "node",
        "procurement_mode": "on_demand",
        "commitment_term": None,
        "region": "US-East",
        "sla": "Business SLA",
        "source_url": "https://www.coreweave.com/pricing",
        "source_confidence": "A",
    },
    {
        "provider": "CoreWeave",
        "product_name": "HGX H100 8-GPU Node (Spot)",
        "source_sku": "hgx-h100-8gpu-spot",
        "gpu_model": "H100 SXM",
        "gpu_form_factor": "SXM",
        "gpu_count": 8,
        "raw_price": 19.71,
        "raw_price_unit": "USD_PER_INSTANCE_HOUR",
        "billing_scope": "node",
        "procurement_mode": "spot",
        "commitment_term": None,
        "region": "US-East",
        "sla": "Business SLA (interruptible)",
        "source_url": "https://www.coreweave.com/pricing",
        "source_confidence": "A",
    },
    {
        "provider": "Lambda",
        "product_name": "H100 SXM5",
        "source_sku": "h100-sxm",
        "gpu_model": "H100 SXM",
        "gpu_form_factor": "SXM",
        "gpu_count": 8,
        "raw_price": 3.99,
        "raw_price_unit": "USD_PER_GPU_HOUR",
        "billing_scope": "gpu",
        "procurement_mode": "on_demand",
        "commitment_term": None,
        "region": "US multi-region",
        "sla": "Business SLA",
        "source_url": "https://lambda.ai/pricing",
        "source_confidence": "A",
        "notes": "Lambda page lists price as per-GPU-hour; 8-GPU node = $31.92/hr",
    },
    {
        "provider": "AWS",
        "product_name": "p5.48xlarge (Capacity Block)",
        "source_sku": "p5.48xlarge",
        "gpu_model": "H100 SXM",
        "gpu_form_factor": "SXM",
        "gpu_count": 8,
        "raw_price": 41.528,
        "raw_price_unit": "USD_PER_INSTANCE_HOUR",
        "billing_scope": "vm",
        "procurement_mode": "capacity_block",
        "commitment_term": None,
        "region": "us-east-1",
        "sla": "Enterprise SLA",
        "source_url": "https://aws.amazon.com/ec2/capacityblocks/pricing/",
        "source_confidence": "A",
        "notes": "Capacity Block pricing, not standard on-demand. Standard on-demand ~$98.32/hr",
    },
    {
        "provider": "GCP",
        "product_name": "a3-highgpu-8g (DWS)",
        "source_sku": "a3-highgpu-8g",
        "gpu_model": "H100 SXM",
        "gpu_form_factor": "SXM",
        "gpu_count": 8,
        "raw_price": 38.32,
        "raw_price_unit": "USD_PER_INSTANCE_HOUR",
        "billing_scope": "vm",
        "procurement_mode": "dws",
        "commitment_term": None,
        "region": "us-central1",
        "sla": "Enterprise SLA",
        "source_url": "https://cloud.google.com/products/dws/pricing",
        "source_confidence": "A",
        "notes": "DWS (Dynamic Workload Scheduler), not standard on-demand. May have queue/scheduling constraints",
    },
    {
        "provider": "Oracle",
        "product_name": "BM.GPU.H100.8",
        "source_sku": "BM.GPU.H100.8",
        "gpu_model": "H100 SXM",
        "gpu_form_factor": "SXM",
        "gpu_count": 8,
        "raw_price": 10.00,
        "raw_price_unit": "USD_PER_GPU_HOUR",
        "billing_scope": "gpu",
        "procurement_mode": "on_demand",
        "commitment_term": None,
        "region": "us-ashburn-1",
        "sla": "Enterprise SLA",
        "source_url": "https://blogs.oracle.com/cloud-infrastructure/now-ga-largest-ai-supercomputer-oci-nvidia-h200",
        "source_confidence": "A",
        "notes": "Oracle blog states $10/GPU/hr; 8-GPU BM instance = $80/hr",
    },
    # NOTE: Azure removed — no verifiable current price with fixed region/SKU/mode.
    # Re-add after fetching from Azure Retail Prices API.
]


def normalize_price(raw_price: float, raw_unit: str, gpu_count: int):
    """
    Normalize raw price to both instance-hour and gpu-hour.
    Raises ValueError for unsupported units or invalid prices.
    """
    if raw_price <= 0:
        raise ValueError(f"raw_price must be positive, got {raw_price}")
    if gpu_count <= 0:
        raise ValueError(f"gpu_count must be positive, got {gpu_count}")
    if raw_unit not in ALLOWED_PRICE_UNITS:
        raise ValueError(f"Unsupported price unit: {raw_unit}")

    if raw_unit == "USD_PER_INSTANCE_HOUR":
        instance_hour = raw_price
        gpu_hour = raw_price / gpu_count
    elif raw_unit in ("USD_PER_GPU_HOUR", "USD_PER_ACCELERATOR_HOUR"):
        gpu_hour = raw_price
        instance_hour = raw_price * gpu_count
    else:
        raise ValueError(f"Unsupported price unit: {raw_unit}")

    return round(instance_hour, 2), round(gpu_hour, 4)


def validate_row(row: dict):
    """Validate a single competitor row."""
    assert row["raw_price_unit"] in ALLOWED_PRICE_UNITS, \
        f"{row['provider']}: invalid raw_price_unit '{row['raw_price_unit']}'"
    assert row["procurement_mode"] in ALLOWED_PROCUREMENT_MODES, \
        f"{row['provider']}: invalid procurement_mode '{row['procurement_mode']}'"
    assert row["region"], f"{row['provider']}: missing region"
    assert row["source_url"], f"{row['provider']}: missing source_url"
    assert row["source_sku"], f"{row['provider']}: missing source_sku"
    assert row["raw_price"] > 0, f"{row['provider']}: invalid raw_price"

    inst, gpu = normalize_price(row["raw_price"], row["raw_price_unit"], row["gpu_count"])
    # Cross-check: instance_hour == gpu_hour * gpu_count
    assert abs(inst - gpu * row["gpu_count"]) < 0.01, \
        f"{row['provider']}: instance_hour ({inst}) != gpu_hour ({gpu}) * gpu_count ({row['gpu_count']})"


def build_gpu_pricing_table():
    """Build standardized competitive pricing table."""
    rows = []
    for c in COMPETITORS:
        validate_row(c)
        inst_hr, gpu_hr = normalize_price(c["raw_price"], c["raw_price_unit"], c["gpu_count"])

        rows.append({
            "provider": c["provider"],
            "product_name": c["product_name"],
            "source_sku": c["source_sku"],
            "gpu_model": c["gpu_model"],
            "gpu_form_factor": c["gpu_form_factor"],
            "gpu_count": c["gpu_count"],
            "raw_price": c["raw_price"],
            "raw_price_unit": c["raw_price_unit"],
            "procurement_mode": c["procurement_mode"],
            "normalized_instance_hr": inst_hr,
            "normalized_gpu_hr": gpu_hr,
            "sla": c["sla"],
            "region": c["region"],
            "source_url": c["source_url"],
            "effective_at": "2026-08-11",
            "source_confidence": c["source_confidence"],
            "notes": c.get("notes", ""),
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 20)
    pd.set_option("display.float_format", lambda x: f"${x:.2f}")

    print("=" * 120)
    print("  GPUaaS Competitive Pricing -- Corrected (raw prices with explicit units)")
    print("  All prices accessed 2026-08-11 from vendor official pages")
    print("=" * 120)

    df = build_gpu_pricing_table()

    cols = ["provider", "product_name", "gpu_count", "raw_price", "raw_price_unit",
            "procurement_mode", "normalized_gpu_hr", "normalized_instance_hr", "source_confidence"]
    print("\n--- Standardized pricing ---")
    print(df[cols].to_string(index=False))

    print("\n--- Key findings ---")
    on_demand = df[df["procurement_mode"] == "on_demand"]
    for _, r in on_demand.iterrows():
        print(f"  {r['provider']:12s} on-demand: ${r['normalized_gpu_hr']:.2f}/GPU/hr  "
              f"(${r['normalized_instance_hr']:.2f}/8-GPU-node)")

    spot = df[df["procurement_mode"] == "spot"]
    for _, r in spot.iterrows():
        print(f"  {r['provider']:12s} spot:     ${r['normalized_gpu_hr']:.2f}/GPU/hr  "
              f"(${r['normalized_instance_hr']:.2f}/8-GPU-node)")

    print(f"\n  NOTE: AWS uses Capacity Block; GCP uses DWS — neither is standard on-demand.")
    print(f"  Azure REMOVED pending verifiable Retail Prices API data.")
    print(f"\n  Previous error: prices like CoreWeave $2.49 were already per-GPU,")
    print(f"  but were divided by 8 again. Correct CoreWeave on-demand = $6.16/GPU/hr.")
