# QC Flagging Guide for Harmonized Data

## Overview

This guide explains how to identify failing rows from unit tests and implement QC flags to mark problematic data points in the harmonized soil moisture datasets.

## Finding Which Rows Failed Tests

### Method 1: From Test Failures (Direct)

When pytest runs, test failures include row indices. Example:

```bash
$ pytest tests/test_harmonized_data.py::TestUnitValidation::test_volumetric_water_content_range -v

FAILED - ess-dive-beca0be9bb38ece-20250516T122010234_harmonized.csv: 
volumetric_water_content_m3_m3 has values < 0 (min: -0.023222042).
Sample row indices: [145, 289, 543, 1024, ...]
```

The test output directly shows:
- **Dataset**: Which file has the problem
- **Row indices**: Specific rows that failed (0-indexed)
- **Values**: The problematic values
- **Context**: site_id, datetime_UTC for those rows

### Method 2: Using QC Report Scripts

Run the `generate_qc_reports.py` script to extract all failures systematically:

```bash
# Generate all types of reports
python scripts/generate_qc_reports.py --approach all

# Just generate detailed per-dataset reports
python scripts/generate_qc_reports.py --approach reports
```

This creates:
- **JSON reports**: `data/processed/qc_reports/{dataset_id}_qc_report.json`
- **CSV reports**: `data/processed/qc_reports/{dataset_id}_qc_failures.csv`
- **Summary**: `data/processed/qc_reports/qc_summary_all_datasets.json`

### Method 3: Programmatic Access

Use the `QCValidator` class directly in Python:

```python
from notebooks.generate_qc_reports import QCValidator
from pathlib import Path

# Load a dataset
filepath = Path("data/processed/harmonized_output_local/ess-dive-beca0be9bb38ece-20250516T122010234_harmonized.csv")
validator = QCValidator(filepath)

# Run all checks
results = validator.run_all_checks()

# Access failures
for failure in results["failures"]:
    print(f"Row {failure['row_index']}: {failure['message']}")
    print(f"  Site: {failure['site_id']}, DateTime: {failure['datetime_UTC']}")
    print(f"  Value: {failure['value']}")
```

## QC Flagging Approaches

### Approach 1: Add `qc_flag` Column to Data Files

**How it works**: Add a `qc_flag` column directly to each harmonized CSV, similar to the location file.

**Pros**:
- QC information travels with the data
- Simple to implement
- Easy to filter data based on QC flags
- Users immediately see which rows have issues

**Cons**:
- Modifies source files
- Multiple flags per row need encoding (e.g., comma-separated)
- Regenerating harmonized data overwrites flags

**Implementation**:

```python
import pandas as pd

df = pd.read_csv("dataset_harmonized.csv")
df["qc_flag"] = ""  # Initialize

# Flag negative VWC values
df.loc[df["volumetric_water_content_m3_m3"] < 0, "qc_flag"] = "E_NEGATIVE_VWC"

# Flag outliers (append to existing flags)
outlier_mask = (df["volumetric_water_content_m3_m3"] > 0.8)
df.loc[outlier_mask, "qc_flag"] += ",W_OUTLIER"

df.to_csv("dataset_harmonized_with_qc.csv", index=False)
```

**Flag codes** (suggested):
- `E_*`: Error (data should not be used)
- `W_*`: Warning (data suspicious but may be valid)
- `I_*`: Info (metadata note)

Example flags:
- `E_NEGATIVE_VWC`: Negative volumetric water content
- `E_VWC_RANGE`: VWC outside [0, 1]
- `W_OUTLIER`: Statistical outlier
- `W_DUPLICATE`: Duplicate timestamp
- `W_WP_RANGE`: Water potential outside typical range

### Approach 2: Separate QC Report Files

**How it works**: Create separate JSON/CSV files documenting QC failures, leaving original data unchanged.

**Pros**:
- Doesn't modify source data
- Detailed information about failures
- Easy to version control QC reports separately
- Can include rich metadata (why it failed, severity, recommendations)

**Cons**:
- Need to manage separate files
- Users must join QC reports with data
- Can get out of sync if data is regenerated

**File structure**:

```
data/processed/
├── harmonized_output_local/
│   └── ess-dive-{id}_harmonized.csv
└── qc_reports/
    ├── ess-dive-{id}_qc_report.json       # Detailed JSON
    ├── ess-dive-{id}_qc_failures.csv      # Rows with failures
    ├── qc_summary_all_datasets.json       # Cross-dataset summary
    └── qc_comparison.csv                  # Comparison table
```

**QC Report JSON structure**:

```json
{
  "generated_at": "2024-08-24T14:30:00",
  "dataset_id": "ess-dive-beca0be9bb38ece-20250516T122010234",
  "source_file": "path/to/file.csv",
  "total_rows": 100000,
  "summary": {
    "total_failures": 245,
    "rows_with_failures": 240,
    "failure_rate": "0.24%"
  },
  "failures_by_check": {
    "negative_vwc": {
      "count": 12,
      "severity": "error",
      "affected_rows": [145, 289, 543, ...]
    },
    "extreme_outlier": {
      "count": 233,
      "severity": "warning",
      "affected_rows": [...]
    }
  },
  "failures": [
    {
      "row_index": 145,
      "check": "negative_vwc",
      "column": "volumetric_water_content_m3_m3",
      "value": -0.023,
      "site_id": "ER_SMN4B",
      "datetime_UTC": "2019-10-13T00:00:00+00:00",
      "severity": "error",
      "message": "Negative volumetric water content: -0.0232"
    }
  ]
}
```

**Using QC reports**:

```python
import pandas as pd
import json

# Load data
data = pd.read_csv("dataset_harmonized.csv")

# Load QC report
with open("qc_report.json") as f:
    qc = json.load(f)

# Filter out error rows
error_rows = [f["row_index"] for f in qc["failures"] if f["severity"] == "error"]
clean_data = data.drop(error_rows)

# Or add flags from report
data["qc_flag"] = ""
for failure in qc["failures"]:
    idx = failure["row_index"]
    flag = f"{failure['severity'][0].upper()}_{failure['check'].upper()}"
    data.loc[idx, "qc_flag"] = flag
```

### Approach 3: Database/Annotation Layer

**How it works**: Store QC flags in a separate database or annotation file that references original data by unique keys.

**Pros**:
- Clean separation of data and QC
- Can have multiple QC versions
- Supports collaborative QC review
- Easy to update without touching data

**Cons**:
- More complex infrastructure
- Requires unique identifiers for each row
- Harder for casual users

**Structure**:

```python
# Create unique row identifiers
data["row_id"] = (
    data["dataset_id"] + "_" + 
    data["datetime_UTC"].astype(str) + "_" +
    data["site_id"] + "_" +
    data["depth_m"].astype(str) + "_" +
    data["replicate"].astype(str)
)

# Separate QC annotations
qc_annotations = pd.DataFrame({
    "row_id": [...],
    "qc_flag": [...],
    "qc_severity": [...],
    "qc_message": [...],
    "reviewed_by": [...],
    "review_date": [...]
})
```

## Recommended Workflow

For this project, I recommend a **hybrid approach**:

### 1. During Harmonization (Real-time QC)
Add basic `qc_flag` column to harmonized CSVs for critical errors:
- Negative VWC values → `E_NEGATIVE_VWC`
- VWC > 1 → `E_VWC_RANGE`
- Missing required fields → `E_MISSING_DATA`

```python
# In harmonize_ess-dive_soilmoisture_data.py
def add_qc_flags(df):
    df["qc_flag"] = ""
    
    # Flag critical errors
    df.loc[df["volumetric_water_content_m3_m3"] < 0, "qc_flag"] = "E_NEGATIVE_VWC"
    df.loc[df["volumetric_water_content_m3_m3"] > 1, "qc_flag"] += ",E_VWC_RANGE"
    
    # Clean up comma handling
    df["qc_flag"] = df["qc_flag"].str.strip(",")
    
    return df
```

### 2. After Harmonization (Comprehensive QC)
Generate detailed QC reports for deeper analysis:

```bash
# Run comprehensive QC
pytest tests/test_harmonized_data.py -v > qc_test_results.txt

# Generate reports
python scripts/generate_qc_reports.py --approach all
```

### 3. For Analysis
Users can:
- Filter by `qc_flag` for clean data
- Review QC reports for context on flagged data
- Decide whether to exclude or keep flagged data based on analysis needs

```python
# Example: Load data and filter by QC
import pandas as pd

df = pd.read_csv("dataset_harmonized.csv")

# Exclude all errors
clean_df = df[~df["qc_flag"].str.contains("E_", na=False)]

# Or just exclude specific errors
no_negative_vwc = df[~df["qc_flag"].str.contains("E_NEGATIVE_VWC", na=False)]

# Keep everything but note warnings
analysis_df = df.copy()
analysis_df["has_warning"] = df["qc_flag"].str.contains("W_", na=False)
```

## QC Flag Reference

| Flag | Severity | Description | Action |
|------|----------|-------------|--------|
| `E_NEGATIVE_VWC` | Error | Volumetric water content < 0 | Exclude from analysis |
| `E_VWC_RANGE` | Error | VWC outside [0, 1] | Check unit conversion |
| `E_MISSING_DATETIME` | Error | Missing timestamp | Cannot use |
| `W_OUTLIER` | Warning | Statistical outlier (3×IQR) | Review, may be valid |
| `W_DUPLICATE` | Warning | Duplicate timestamp | Review, may be repeated measurement |
| `W_WP_EXTREME` | Warning | Water potential < -50000 kPa | Review sensor |
| `W_DEPTH_UNUSUAL` | Warning | Depth > 5m | Verify sensor placement |
| `I_REPLICATE_GAP` | Info | Non-sequential replicate numbers | Metadata note |

## Next Steps

1. **Decide on approach**: Choose flags, reports, or hybrid
2. **Implement in harmonization script**: Add QC flagging to `harmonize_ess-dive_soilmoisture_data.py`
3. **Document for users**: Explain QC flags in data documentation
4. **Establish review process**: Who reviews QC failures and makes decisions?
5. **Track over time**: Monitor QC flag rates across dataset versions

## Example: Full QC Pipeline

```bash
# 1. Run harmonization with QC flags
python notebooks/harmonize_ess-dive_soilmoisture_data.py

# 2. Run unit tests to verify
pytest tests/test_harmonized_data.py -v --tb=short

# 3. Generate detailed QC reports
python scripts/generate_qc_reports.py --approach reports

# 4. Review reports and update harmonization if needed
# (iterate on steps 1-3)

# 5. Generate final summary
python scripts/generate_qc_reports.py --approach summary
```
