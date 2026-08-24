"""
Generate QC reports from test failures

This script demonstrates how to identify failing rows from the test suite
and generate QC flags or reports that can be used to mark problematic data.

Three approaches are shown:
1. Add qc_flag column to harmonized CSVs (like location file)
2. Generate separate QC report files per dataset
3. Generate summary QC report across all datasets

Usage:
    python scripts/generate_qc_reports.py --approach [flags|reports|summary]
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse
import json
from datetime import datetime


PROJECT_ROOT = Path(__file__).parent.parent
HARMONIZED_DIR = PROJECT_ROOT / "data" / "processed" / "harmonized_output_local"
QC_REPORTS_DIR = PROJECT_ROOT / "data" / "processed" / "qc_reports"


def get_harmonized_files():
    """Get all harmonized CSV files (excluding location file)."""
    files = list(HARMONIZED_DIR.glob("*_harmonized.csv"))
    return [f for f in files if "location" not in f.name.lower()]


class QCValidator:
    """
    Run QC checks and collect failures at row level.

    Each check method returns a dict with:
    - passed: bool
    - failures: list of dicts with row indices and failure details
    """

    def __init__(self, filepath):
        self.filepath = filepath
        self.dataset_id = filepath.stem.replace("_harmonized", "")
        self.df = pd.read_csv(filepath)
        self.df["datetime_UTC"] = pd.to_datetime(self.df["datetime_UTC"], errors="coerce")

    def check_negative_volumetric_water_content(self):
        """Check for negative VWC values."""
        col = "volumetric_water_content_m3_m3"
        values = pd.to_numeric(self.df[col], errors="coerce")

        # Find negative values
        negative_mask = values < 0
        failures = []

        for idx in self.df[negative_mask].index:
            failures.append({
                "row_index": int(idx),
                "check": "negative_vwc",
                "column": col,
                "value": float(self.df.loc[idx, col]),
                "site_id": self.df.loc[idx, "site_id"],
                "datetime_UTC": str(self.df.loc[idx, "datetime_UTC"]),
                "severity": "error",
                "message": f"Negative volumetric water content: {self.df.loc[idx, col]:.4f}"
            })

        return {
            "passed": len(failures) == 0,
            "failures": failures
        }

    def check_vwc_out_of_range(self):
        """Check for VWC values outside [0, 1]."""
        col = "volumetric_water_content_m3_m3"
        values = pd.to_numeric(self.df[col], errors="coerce")

        # Find out of range values
        out_of_range_mask = (values < 0) | (values > 1)
        failures = []

        for idx in self.df[out_of_range_mask].index:
            val = float(self.df.loc[idx, col])
            failures.append({
                "row_index": int(idx),
                "check": "vwc_range",
                "column": col,
                "value": val,
                "site_id": self.df.loc[idx, "site_id"],
                "datetime_UTC": str(self.df.loc[idx, "datetime_UTC"]),
                "severity": "error" if (val < -0.01 or val > 1.1) else "warning",
                "message": f"VWC out of range [0, 1]: {val:.4f}"
            })

        return {
            "passed": len(failures) == 0,
            "failures": failures
        }

    def check_water_potential_unrealistic(self):
        """Check for unrealistic water potential values."""
        col = "water_potential_kPa"
        values = pd.to_numeric(self.df[col], errors="coerce").dropna()

        if len(values) == 0:
            return {"passed": True, "failures": []}

        # Unrealistic range
        lower_bound = -50000
        upper_bound = 10

        out_of_range_mask = (self.df[col] < lower_bound) | (self.df[col] > upper_bound)
        failures = []

        for idx in self.df[out_of_range_mask].index:
            val = float(self.df.loc[idx, col])
            failures.append({
                "row_index": int(idx),
                "check": "water_potential_range",
                "column": col,
                "value": val,
                "site_id": self.df.loc[idx, "site_id"],
                "datetime_UTC": str(self.df.loc[idx, "datetime_UTC"]),
                "severity": "warning",
                "message": f"Water potential outside typical range [{lower_bound}, {upper_bound}]: {val:.1f}"
            })

        return {
            "passed": len(failures) == 0,
            "failures": failures
        }

    def check_duplicate_timestamps(self):
        """Check for duplicate timestamps."""
        key_cols = ["datetime_UTC", "site_id", "depth_m", "replicate"]
        df_with_keys = self.df.dropna(subset=key_cols, how="all")

        if len(df_with_keys) == 0:
            return {"passed": True, "failures": []}

        # Find duplicates
        duplicates = df_with_keys[df_with_keys.duplicated(subset=key_cols, keep=False)]
        failures = []

        for idx in duplicates.index:
            failures.append({
                "row_index": int(idx),
                "check": "duplicate_timestamp",
                "column": "datetime_UTC",
                "value": str(self.df.loc[idx, "datetime_UTC"]),
                "site_id": self.df.loc[idx, "site_id"],
                "datetime_UTC": str(self.df.loc[idx, "datetime_UTC"]),
                "depth_m": float(self.df.loc[idx, "depth_m"]) if pd.notna(self.df.loc[idx, "depth_m"]) else None,
                "replicate": int(self.df.loc[idx, "replicate"]) if pd.notna(self.df.loc[idx, "replicate"]) else None,
                "severity": "warning",
                "message": "Duplicate timestamp for this site/depth/replicate"
            })

        return {
            "passed": len(failures) == 0,
            "failures": failures
        }

    def check_extreme_outliers(self):
        """Check for extreme statistical outliers in VWC."""
        col = "volumetric_water_content_m3_m3"
        values = pd.to_numeric(self.df[col], errors="coerce").dropna()

        if len(values) < 10:
            return {"passed": True, "failures": []}

        # Calculate IQR
        Q1 = values.quantile(0.25)
        Q3 = values.quantile(0.75)
        IQR = Q3 - Q1

        lower_bound = Q1 - 3 * IQR
        upper_bound = Q3 + 3 * IQR

        outlier_mask = (self.df[col] < lower_bound) | (self.df[col] > upper_bound)
        failures = []

        for idx in self.df[outlier_mask].index:
            val = float(self.df.loc[idx, col])
            failures.append({
                "row_index": int(idx),
                "check": "extreme_outlier",
                "column": col,
                "value": val,
                "site_id": self.df.loc[idx, "site_id"],
                "datetime_UTC": str(self.df.loc[idx, "datetime_UTC"]),
                "severity": "warning",
                "message": f"Extreme outlier (IQR method): {val:.4f} outside [{lower_bound:.3f}, {upper_bound:.3f}]"
            })

        return {
            "passed": len(failures) == 0,
            "failures": failures
        }

    def run_all_checks(self):
        """Run all QC checks and return combined results."""
        checks = [
            self.check_negative_volumetric_water_content,
            self.check_vwc_out_of_range,
            self.check_water_potential_unrealistic,
            self.check_duplicate_timestamps,
            self.check_extreme_outliers,
        ]

        all_failures = []
        for check in checks:
            result = check()
            all_failures.extend(result["failures"])

        return {
            "dataset_id": self.dataset_id,
            "filepath": str(self.filepath),
            "total_rows": len(self.df),
            "total_failures": len(all_failures),
            "failures": all_failures
        }


def approach_1_add_qc_flags():
    """
    Approach 1: Add qc_flag column to each harmonized CSV.

    Similar to how location file has qc_flag for missing coordinates.
    Advantages: QC info travels with the data
    Disadvantages: Modifies source files, multiple flags hard to represent
    """
    print("\n=== Approach 1: Add qc_flag column to harmonized CSVs ===\n")

    for filepath in get_harmonized_files()[:3]:  # Demo with first 3 files
        print(f"Processing {filepath.name}...")

        validator = QCValidator(filepath)
        results = validator.run_all_checks()

        # Read the CSV
        df = pd.read_csv(filepath)

        # Initialize qc_flag column
        df["qc_flag"] = ""

        # Map failures to rows and assign flags
        for failure in results["failures"]:
            row_idx = failure["row_index"]
            check_name = failure["check"]
            severity = failure["severity"]

            # Create flag code (e.g., "E01" for error, "W02" for warning)
            flag_code = f"{'E' if severity == 'error' else 'W'}{check_name[:2].upper()}"

            # Append to existing flags (comma-separated)
            existing = df.loc[row_idx, "qc_flag"]
            if existing:
                df.loc[row_idx, "qc_flag"] = f"{existing},{flag_code}"
            else:
                df.loc[row_idx, "qc_flag"] = flag_code

        print(f"  Total rows: {len(df)}")
        print(f"  Rows with QC flags: {(df['qc_flag'] != '').sum()}")
        print(f"  Sample flags: {df[df['qc_flag'] != '']['qc_flag'].head().tolist()}")

        # Would write back to file (commented out for safety)
        # output_path = filepath.parent / f"{filepath.stem}_with_qc{filepath.suffix}"
        # df.to_csv(output_path, index=False)
        # print(f"  Would write to: {output_path}")
        print()


def approach_2_separate_qc_reports():
    """
    Approach 2: Generate separate QC report files per dataset.

    Creates JSON/CSV files with detailed QC information.
    Advantages: Detailed, doesn't modify source data, easy to review
    Disadvantages: Separate files to manage
    """
    print("\n=== Approach 2: Generate separate QC report files ===\n")

    QC_REPORTS_DIR.mkdir(exist_ok=True, parents=True)

    for filepath in get_harmonized_files()[:3]:  # Demo with first 3 files
        print(f"Processing {filepath.name}...")

        validator = QCValidator(filepath)
        results = validator.run_all_checks()

        # Generate report
        report = {
            "generated_at": datetime.now().isoformat(),
            "dataset_id": results["dataset_id"],
            "source_file": results["filepath"],
            "total_rows": results["total_rows"],
            "summary": {
                "total_failures": results["total_failures"],
                "rows_with_failures": len(set(f["row_index"] for f in results["failures"])),
                "failure_rate": f"{(len(set(f['row_index'] for f in results['failures'])) / results['total_rows'] * 100):.2f}%"
            },
            "failures_by_check": {},
            "failures": results["failures"]
        }

        # Summarize by check type
        for failure in results["failures"]:
            check = failure["check"]
            if check not in report["failures_by_check"]:
                report["failures_by_check"][check] = {
                    "count": 0,
                    "severity": failure["severity"],
                    "affected_rows": []
                }
            report["failures_by_check"][check]["count"] += 1
            report["failures_by_check"][check]["affected_rows"].append(failure["row_index"])

        # Write JSON report
        report_path = QC_REPORTS_DIR / f"{results['dataset_id']}_qc_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"  Total failures: {results['total_failures']}")
        print(f"  Unique rows affected: {report['summary']['rows_with_failures']}")
        print(f"  Failure rate: {report['summary']['failure_rate']}")
        print(f"  Report saved to: {report_path}")

        # Also create CSV version for easy viewing
        if results["failures"]:
            failures_df = pd.DataFrame(results["failures"])
            csv_path = QC_REPORTS_DIR / f"{results['dataset_id']}_qc_failures.csv"
            failures_df.to_csv(csv_path, index=False)
            print(f"  CSV report saved to: {csv_path}")

        print()


def approach_3_summary_report():
    """
    Approach 3: Generate summary QC report across all datasets.

    Creates a high-level overview of data quality.
    Advantages: Quick overview, easy to compare datasets
    Disadvantages: Less detailed, harder to trace specific rows
    """
    print("\n=== Approach 3: Generate summary QC report ===\n")

    summary = {
        "generated_at": datetime.now().isoformat(),
        "datasets": []
    }

    for filepath in get_harmonized_files():
        print(f"Processing {filepath.name}...")

        validator = QCValidator(filepath)
        results = validator.run_all_checks()

        # Summarize for this dataset
        failure_counts = {}
        for failure in results["failures"]:
            check = failure["check"]
            failure_counts[check] = failure_counts.get(check, 0) + 1

        dataset_summary = {
            "dataset_id": results["dataset_id"],
            "total_rows": results["total_rows"],
            "total_failures": results["total_failures"],
            "unique_rows_with_failures": len(set(f["row_index"] for f in results["failures"])),
            "failure_rate": f"{(len(set(f['row_index'] for f in results['failures'])) / results['total_rows'] * 100):.2f}%",
            "failures_by_check": failure_counts
        }

        summary["datasets"].append(dataset_summary)

        print(f"  Failures: {results['total_failures']} ({dataset_summary['failure_rate']} of rows)")

    # Write summary report
    QC_REPORTS_DIR.mkdir(exist_ok=True, parents=True)
    summary_path = QC_REPORTS_DIR / "qc_summary_all_datasets.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\nSummary report saved to: {summary_path}")

    # Also create comparison table
    comparison_df = pd.DataFrame([
        {
            "dataset_id": d["dataset_id"],
            "total_rows": d["total_rows"],
            "failures": d["total_failures"],
            "failure_rate": d["failure_rate"]
        }
        for d in summary["datasets"]
    ])

    comparison_path = QC_REPORTS_DIR / "qc_comparison.csv"
    comparison_df.to_csv(comparison_path, index=False)
    print(f"Comparison table saved to: {comparison_path}")

    print("\nTop datasets by failure rate:")
    comparison_df_sorted = comparison_df.sort_values("failures", ascending=False)
    print(comparison_df_sorted.head(10).to_string(index=False))


def main():
    parser = argparse.ArgumentParser(description="Generate QC reports from test failures")
    parser.add_argument(
        "--approach",
        choices=["flags", "reports", "summary", "all"],
        default="all",
        help="Which QC reporting approach to demonstrate"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("QC Report Generation - Demonstration")
    print("=" * 70)

    if args.approach in ["flags", "all"]:
        approach_1_add_qc_flags()

    if args.approach in ["reports", "all"]:
        approach_2_separate_qc_reports()

    if args.approach in ["summary", "all"]:
        approach_3_summary_report()

    print("\n" + "=" * 70)
    print("Demonstration complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
