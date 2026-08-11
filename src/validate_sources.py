#!/usr/bin/env python3
"""
Source validation — checks data/sources.csv for completeness and consistency.
"""

import pandas as pd
import os
import sys


REQUIRED_FIELDS = [
    "claim_id", "metric", "value", "unit", "scope",
    "source_url", "accessed_at", "source_type", "confidence",
]

VALID_CONFIDENCE = {"A", "B", "C", "D", "E"}


def validate_sources(csv_path=None):
    if csv_path is None:
        csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "sources.csv")

    df = pd.read_csv(csv_path)

    errors = []

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in df.columns:
            errors.append(f"Missing required column: {field}")
        elif field != "source_url" and df[field].isna().any():
            missing = df[df[field].isna()]["claim_id"].tolist()
            errors.append(f"Field '{field}' missing for: {missing}")

    # Check confidence values
    if "confidence" in df.columns:
        invalid_conf = df[~df["confidence"].isin(VALID_CONFIDENCE)]
        if len(invalid_conf) > 0:
            errors.append(f"Invalid confidence values: {invalid_conf[['claim_id', 'confidence']].to_dict('records')}")

    # Check D/E entries have notes
    if "confidence" in df.columns and "notes" in df.columns:
        low_conf = df[df["confidence"].isin(["D", "E"])]
        for _, row in low_conf.iterrows():
            if pd.isna(row.get("notes")) or not str(row["notes"]).strip():
                errors.append(f"D/E entry {row['claim_id']} should have notes explaining the estimate")

    # Check URLs are not just domains (only for A/B/C confidence)
    if "source_url" in df.columns:
        for _, row in df.iterrows():
            conf = row.get("confidence", "")
            url = str(row.get("source_url", ""))
            # D/E entries (estimates) may not have URLs
            if conf in ("A", "B", "C") and (not url or url == "nan"):
                errors.append(f"{row['claim_id']}: A/B/C entry should have source_url")
            elif url and url != "nan":
                if not url.startswith("http") and "." not in url:
                    errors.append(f"{row['claim_id']}: source_url looks like just a domain name: {url}")

    return errors


if __name__ == "__main__":
    errors = validate_sources()
    if errors:
        print("VALIDATION ERRORS:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("Source validation passed.")
