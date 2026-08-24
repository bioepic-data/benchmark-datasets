#!/usr/bin/env python3
"""
Comprehensive audit of Python vs R harmonization outputs.
Identifies all mismatches in row counts, NaN values, and data distributions.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import filecmp

# Directories
PY_DIR = Path("data/processed/harmonized_output_local")
R_DIR = Path("data/processed/harmonized_output_gold")

# Get file lists
py_files = sorted([f for f in PY_DIR.glob("*_harmonized.csv")])
r_files = sorted([f for f in R_DIR.glob("*_harmonized.csv")])

print("=" * 80)
print("HARMONIZATION AUDIT REPORT")
print("=" * 80)

# Check file counts
print(f"\nFile counts:")
print(f"  Python: {len(py_files)} files")
print(f"  R:      {len(r_files)} files")

py_names = {f.name for f in py_files}
r_names = {f.name for f in r_files}

if py_names != r_names:
    print(f"\n⚠️  FILE MISMATCH:")
    only_py = py_names - r_names
    only_r = r_names - py_names
    if only_py:
        print(f"  Only in Python: {only_py}")
    if only_r:
        print(f"  Only in R: {only_r}")

# Load mapping to get dataset names
with open("data/processed/harmonized_soil_moisture_data/sm_data_harmonization_mapping.json") as f:
    mapping = json.load(f)

# Create dataset ID to index mapping
ds_to_idx = {m["dataset_identifier"]: m["index"] for m in mapping}

print("\n" + "=" * 80)
print("DATASET-BY-DATASET COMPARISON")
print("=" * 80)

issues = []

for py_file in sorted(py_files):
    r_file = R_DIR / py_file.name

    if not r_file.exists():
        print(f"\n⚠️  {py_file.name}")
        print(f"    MISSING in R output - skip comparison")
        issues.append({
            'file': py_file.name,
            'issue': 'Missing in R output',
            'severity': 'INFO'
        })
        continue

    # Load both files
    py_df = pd.read_csv(py_file)
    r_df = pd.read_csv(r_file)

    # Extract dataset identifier from filename
    ds_id = py_file.stem.replace("_harmonized", "")
    idx = ds_to_idx.get(ds_id, "?")

    print(f"\nDataset {idx}: {py_file.name}")
    print(f"  Rows: Python={len(py_df):,} | R={len(r_df):,}", end="")

    has_issues = False

    # Returns True if contents match, False if they differ
    are_identical = filecmp.cmp(py_file, r_file, shallow=False)

    if are_identical:
        print(f"\nThe files are identical.")
    else:
        print(f"\nThe files are different.")

    # Check row count mismatch
    if len(py_df) != len(r_df):
        diff = len(r_df) - len(py_df)
        pct = abs(diff) / len(r_df) * 100
        print(f" ⚠️  MISMATCH: {diff:+,} rows ({pct:.1f}%)")
        has_issues = True
        issues.append({
            'file': py_file.name,
            'dataset_idx': idx,
            'issue': f'Row count mismatch: Python={len(py_df)}, R={len(r_df)}, diff={diff}',
            'severity': 'CRITICAL' if abs(pct) > 5 else 'MEDIUM'
        })
    else:
        print(" ✓")
        

    # Check for NaN depth_m
    py_nan_depth = py_df['depth_m'].isna().sum()
    r_nan_depth = r_df['depth_m'].isna().sum()

    if py_nan_depth != r_nan_depth:
        print(f"  ⚠️  DEPTH NaN: Python={py_nan_depth:,} | R={r_nan_depth:,}")
        has_issues = True
        issues.append({
            'file': py_file.name,
            'dataset_idx': idx,
            'issue': f'Depth NaN mismatch: Python={py_nan_depth}, R={r_nan_depth}',
            'severity': 'CRITICAL' if py_nan_depth > 0 and r_nan_depth == 0 else 'MEDIUM'
        })

    # Check for NaN site_id
    py_nan_site = py_df['site_id'].isna().sum()
    r_nan_site = r_df['site_id'].isna().sum()

    if py_nan_site != r_nan_site:
        print(f"  ⚠️  SITE_ID NaN: Python={py_nan_site:,} | R={r_nan_site:,}")
        has_issues = True
        issues.append({
            'file': py_file.name,
            'dataset_idx': idx,
            'issue': f'Site_id NaN mismatch: Python={py_nan_site}, R={r_nan_site}',
            'severity': 'CRITICAL' if py_nan_site > 0 and r_nan_site == 0 else 'MEDIUM'
        })

    # Check for NaN replicate
    py_nan_rep = py_df['replicate'].isna().sum()
    r_nan_rep = r_df['replicate'].isna().sum()

    if py_nan_rep != r_nan_rep:
        print(f"  ⚠️  REPLICATE NaN: Python={py_nan_rep:,} | R={r_nan_rep:,}")
        has_issues = True
        issues.append({
            'file': py_file.name,
            'dataset_idx': idx,
            'issue': f'Replicate NaN mismatch: Python={py_nan_rep}, R={r_nan_rep}',
            'severity': 'MEDIUM'
        })

    # Compare unique depths (if not all NaN)
    if py_nan_depth == 0 and r_nan_depth == 0:
        py_depths = set(py_df['depth_m'].dropna().unique())
        r_depths = set(r_df['depth_m'].dropna().unique())
        if py_depths != r_depths:
            print(f"  ⚠️  DEPTH VALUES: Different unique values")
            print(f"      Python: {sorted(py_depths)}")
            print(f"      R:      {sorted(r_depths)}")
            has_issues = True
            issues.append({
                'file': py_file.name,
                'dataset_idx': idx,
                'issue': f'Depth values differ',
                'severity': 'MEDIUM'
            })

    # Compare unique site_ids (if not all NaN)
    if py_nan_site == 0 and r_nan_site == 0:
        py_sites = set(py_df['site_id'].dropna().unique())
        r_sites = set(r_df['site_id'].dropna().unique())
        if py_sites != r_sites:
            print(f"  ⚠️  SITE_ID VALUES: Different unique values")
            only_py = py_sites - r_sites
            only_r = r_sites - py_sites
            if only_py:
                print(f"      Only in Python: {only_py}")
            if only_r:
                print(f"      Only in R: {only_r}")
            has_issues = True
            issues.append({
                'file': py_file.name,
                'dataset_idx': idx,
                'issue': f'Site_id values differ',
                'severity': 'MEDIUM'
            })

    # Compare replicate ranges
    if py_nan_rep == 0 and r_nan_rep == 0:
        py_max_rep = py_df['replicate'].max()
        r_max_rep = r_df['replicate'].max()
        if py_max_rep != r_max_rep:
            print(f"  ⚠️  REPLICATE MAX: Python={py_max_rep} | R={r_max_rep}")
            has_issues = True
            issues.append({
                'file': py_file.name,
                'dataset_idx': idx,
                'issue': f'Replicate max differs: Python={py_max_rep}, R={r_max_rep}',
                'severity': 'CRITICAL' if r_max_rep > py_max_rep * 1.5 else 'MEDIUM'
            })

    if not has_issues:
        print("  ✓ All checks passed")

# Summary
print("\n" + "=" * 80)
print("ISSUE SUMMARY")
print("=" * 80)

critical = [i for i in issues if i['severity'] == 'CRITICAL']
medium = [i for i in issues if i['severity'] == 'MEDIUM']
info = [i for i in issues if i['severity'] == 'INFO']

print(f"\nTotal issues found: {len(issues)}")
print(f"  CRITICAL: {len(critical)}")
print(f"  MEDIUM:   {len(medium)}")
print(f"  INFO:     {len(info)}")

if critical:
    print("\n🚨 CRITICAL ISSUES:")
    for i in critical:
        print(f"  Dataset {i.get('dataset_idx', '?')}: {i['file']}")
        print(f"    → {i['issue']}")

if medium:
    print("\n⚠️  MEDIUM ISSUES:")
    for i in medium:
        print(f"  Dataset {i.get('dataset_idx', '?')}: {i['file']}")
        print(f"    → {i['issue']}")

print("\n" + "=" * 80)
print("AUDIT COMPLETE")
print("=" * 80)
