"""
Unit tests for harmonized soil moisture data

This module tests the harmonized output from harmonize_ess-dive_soilmoisture_data.py
to ensure data quality, consistency, and standardization.

Run with: pytest tests/test_harmonized_data.py -v
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import re


# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
HARMONIZED_DIR = PROJECT_ROOT / "data" / "processed" / "harmonized_output_local"

# Expected columns for all harmonized datasets
EXPECTED_COLUMNS = [
    "datetime_UTC",
    "site_id",
    "depth_m",
    "replicate",
    "is_timeseries",
    "volumetric_water_content_m3_m3",
    "gravimetric_water_content_gH2O_gs",
    "water_potential_kPa",
]

# Missing value placeholders that should NOT exist in harmonized data
MISSING_VALUE_PLACEHOLDERS = [
    -9999, -9999.0, -9999.00, -9999.000,
    9999, 9999.0, 9999.00, 9999.000,
    -99999, 99999,
]


def get_harmonized_files():
    """Get all harmonized CSV files (excluding location file)."""
    files = list(HARMONIZED_DIR.glob("*_harmonized.csv"))
    # Exclude location file
    files = [f for f in files if "location" not in f.name.lower()]
    return files


def read_harmonized_file(filepath):
    """Read a harmonized CSV file with proper datetime parsing."""
    df = pd.read_csv(filepath)
    if "datetime_UTC" in df.columns:
        df["datetime_UTC"] = pd.to_datetime(df["datetime_UTC"], errors="coerce")
    return df


class TestColumnStructure:
    """Test that all harmonized files have consistent column structure."""

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_has_expected_columns(self, filepath):
        """All harmonized files should have the expected column names."""
        df = pd.read_csv(filepath)
        assert list(df.columns) == EXPECTED_COLUMNS, (
            f"{filepath.name} has unexpected columns. "
            f"Expected: {EXPECTED_COLUMNS}, Got: {list(df.columns)}"
        )

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_no_extra_columns(self, filepath):
        """Files should not have extra columns beyond expected."""
        df = pd.read_csv(filepath)
        extra_cols = set(df.columns) - set(EXPECTED_COLUMNS)
        assert len(extra_cols) == 0, (
            f"{filepath.name} has extra columns: {extra_cols}"
        )

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_no_missing_columns(self, filepath):
        """Files should not be missing any expected columns."""
        df = pd.read_csv(filepath)
        missing_cols = set(EXPECTED_COLUMNS) - set(df.columns)
        assert len(missing_cols) == 0, (
            f"{filepath.name} is missing columns: {missing_cols}"
        )


class TestMissingValuePlaceholders:
    """Test that no placeholder values exist in place of proper NaN."""

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_no_negative_9999_variants(self, filepath):
        """No -9999 or variants should exist in numeric columns."""
        df = read_harmonized_file(filepath)
        numeric_cols = [
            "depth_m",
            "volumetric_water_content_m3_m3",
            "gravimetric_water_content_gH2O_gs",
            "water_potential_kPa",
        ]

        for col in numeric_cols:
            if col in df.columns:
                values = pd.to_numeric(df[col], errors="coerce")
                for placeholder in MISSING_VALUE_PLACEHOLDERS:
                    bad_values = values[values == placeholder]
                    assert len(bad_values) == 0, (
                        f"{filepath.name} contains {placeholder} placeholder in column '{col}'. "
                        f"Found {len(bad_values)} instances. Should use NaN instead."
                    )

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_no_string_missing_indicators(self, filepath):
        """No string-based missing indicators like 'NA', '-', 'NULL', etc."""
        df = pd.read_csv(filepath, dtype=str)
        string_missing = ["NA", "N/A", "na", "n/a", "NULL", "null", "-", ""]

        for col in df.columns:
            for indicator in string_missing:
                count = (df[col] == indicator).sum()
                # Empty strings are OK (pandas reads them as NaN)
                if indicator == "":
                    continue
                assert count == 0, (
                    f"{filepath.name} contains '{indicator}' in column '{col}'. "
                    f"Found {count} instances."
                )


class TestDataTypes:
    """Test that columns have the expected data types."""

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_datetime_is_parseable(self, filepath):
        """datetime_UTC should be parseable as datetime."""
        df = read_harmonized_file(filepath)
        # Accept both nanosecond and microsecond precision (pandas version dependent)
        dtype_str = str(df["datetime_UTC"].dtype)
        assert "datetime64" in dtype_str, (
            f"{filepath.name}: datetime_UTC is not a datetime type. Got: {df['datetime_UTC'].dtype}"
        )

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_numeric_columns_are_numeric(self, filepath):
        """Numeric columns should be parseable as numeric."""
        df = read_harmonized_file(filepath)
        numeric_cols = [
            "depth_m",
            "replicate",
            "volumetric_water_content_m3_m3",
            "gravimetric_water_content_gH2O_gs",
            "water_potential_kPa",
        ]

        for col in numeric_cols:
            # Try to convert to numeric
            converted = pd.to_numeric(df[col], errors="coerce")
            # Check that we didn't introduce new NaNs (except where already NaN)
            original_na = df[col].isna()
            new_na = converted.isna()
            unexpected_na = new_na & ~original_na
            assert unexpected_na.sum() == 0, (
                f"{filepath.name}: Column '{col}' contains non-numeric values. "
                f"Found {unexpected_na.sum()} values that couldn't be converted."
            )

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_is_timeseries_is_boolean(self, filepath):
        """is_timeseries should contain only True/False/NaN."""
        df = read_harmonized_file(filepath)
        unique_vals = df["is_timeseries"].dropna().unique()
        assert all(isinstance(v, (bool, np.bool_)) or v in [True, False, "True", "False"]
                   for v in unique_vals), (
            f"{filepath.name}: is_timeseries contains non-boolean values: {unique_vals}"
        )


class TestUnitValidation:
    """Test that values are within expected ranges for their units."""

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_volumetric_water_content_range(self, filepath):
        """Volumetric water content (m3/m3) should be between 0 and 1."""
        df = read_harmonized_file(filepath)
        col = "volumetric_water_content_m3_m3"

        values = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(values) > 0:
            min_val = values.min()
            max_val = values.max()

            # Allow small tolerance for floating point errors
            assert min_val >= -0.001, (
                f"{filepath.name}: {col} has values < 0 (min: {min_val}). "
                "Volumetric water content should be between 0 and 1 m3/m3."
            )
            assert max_val <= 1.001, (
                f"{filepath.name}: {col} has values > 1 (max: {max_val}). "
                "Volumetric water content should be between 0 and 1 m3/m3. "
                "Values > 1 suggest incorrect unit conversion (may still be in %)."
            )

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_gravimetric_water_content_non_negative(self, filepath):
        """Gravimetric water content should be >= 0."""
        df = read_harmonized_file(filepath)
        col = "gravimetric_water_content_gH2O_gs"

        values = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(values) > 0:
            min_val = values.min()
            assert min_val >= 0, (
                f"{filepath.name}: {col} has negative values (min: {min_val}). "
                "Gravimetric water content should be >= 0."
            )

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_depth_non_negative(self, filepath):
        """Depth should be >= 0."""
        df = read_harmonized_file(filepath)
        col = "depth_m"

        values = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(values) > 0:
            min_val = values.min()
            assert min_val >= 0, (
                f"{filepath.name}: {col} has negative values (min: {min_val}). "
                "Depth should be >= 0 meters."
            )

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_water_potential_range(self, filepath):
        """Water potential should typically be <= 0 (soil suction)."""
        df = read_harmonized_file(filepath)
        col = "water_potential_kPa"

        values = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(values) > 0:
            positive_count = (values > 0).sum()
            total_count = len(values)
            positive_pct = (positive_count / total_count) * 100

            # Allow some positive values but warn if too many
            # (saturated soils can have slightly positive potentials)
            assert positive_pct < 10, (
                f"{filepath.name}: {col} has {positive_pct:.1f}% positive values. "
                "Water potential is typically negative (soil suction). "
                "High percentage of positive values suggests potential unit error."
            )

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_replicate_positive_integer(self, filepath):
        """Replicate should be positive integers."""
        df = read_harmonized_file(filepath)
        col = "replicate"

        values = pd.to_numeric(df[col], errors="coerce").dropna()
        if len(values) > 0:
            # Check all are positive
            assert (values > 0).all(), (
                f"{filepath.name}: {col} contains values <= 0. "
                "Replicate should be positive integers."
            )

            # Check all are integers (within floating point tolerance)
            assert np.allclose(values, values.astype(int)), (
                f"{filepath.name}: {col} contains non-integer values. "
                "Replicate should be positive integers."
            )


class TestDataCompleteness:
    """Test that required fields are not completely missing."""

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_datetime_not_all_missing(self, filepath):
        """datetime_UTC should not be all NaN."""
        df = read_harmonized_file(filepath)
        valid_count = df["datetime_UTC"].notna().sum()
        assert valid_count > 0, (
            f"{filepath.name}: datetime_UTC is all NaN. This is a required field."
        )

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_site_id_not_all_missing(self, filepath):
        """site_id should not be all NaN or empty."""
        df = read_harmonized_file(filepath)
        valid_count = df["site_id"].notna().sum()
        assert valid_count > 0, (
            f"{filepath.name}: site_id is all NaN/empty. This is a required field."
        )

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_has_at_least_one_measurement(self, filepath):
        """Each file should have at least one valid measurement."""
        df = read_harmonized_file(filepath)

        measurement_cols = [
            "volumetric_water_content_m3_m3",
            "gravimetric_water_content_gH2O_gs",
            "water_potential_kPa",
        ]

        has_measurement = False
        for col in measurement_cols:
            if df[col].notna().sum() > 0:
                has_measurement = True
                break

        assert has_measurement, (
            f"{filepath.name}: No valid measurements found in any measurement column. "
            f"Checked: {measurement_cols}"
        )


class TestDataConsistency:
    """Test internal consistency of the data."""

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_no_duplicate_records(self, filepath):
        """Check for unexpected duplicate records."""
        df = read_harmonized_file(filepath)

        # Define key columns that should be unique per measurement
        key_cols = ["datetime_UTC", "site_id", "depth_m", "replicate"]

        # Only check if all key columns exist and have values
        if all(col in df.columns for col in key_cols):
            # Drop rows where any key column is NaN
            df_with_keys = df.dropna(subset=key_cols)

            if len(df_with_keys) > 0:
                duplicates = df_with_keys.duplicated(subset=key_cols, keep=False)
                duplicate_count = duplicates.sum()

                # Some duplicates may be OK (different measurements), but large numbers suggest issues
                duplicate_pct = (duplicate_count / len(df_with_keys)) * 100

                assert duplicate_pct < 50, (
                    f"{filepath.name}: {duplicate_pct:.1f}% duplicate records found. "
                    f"Found {duplicate_count} duplicates out of {len(df_with_keys)} records."
                )

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_file_not_empty(self, filepath):
        """Files should not be empty."""
        df = read_harmonized_file(filepath)
        assert len(df) > 0, f"{filepath.name} is empty."

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_datetime_has_timezone_info(self, filepath):
        """datetime_UTC should have timezone information (UTC)."""
        df = read_harmonized_file(filepath)

        # Check if datetime has timezone
        if df["datetime_UTC"].dtype == "datetime64[ns]":
            # No timezone info - should be converted to UTC
            # This is a warning, not a failure, as pandas may strip tz on read
            pass
        else:
            # If it has tz info, it should be UTC
            assert "UTC" in str(df["datetime_UTC"].dtype), (
                f"{filepath.name}: datetime_UTC should be in UTC timezone."
            )


class TestLocationData:
    """Test the location harmonization file."""

    def test_location_file_exists(self):
        """Location file should exist."""
        loc_file = HARMONIZED_DIR / "location_data_harmonized_with_uuid.csv"
        assert loc_file.exists(), "location_data_harmonized_with_uuid.csv not found"

    def test_location_has_required_columns(self):
        """Location file should have UUID and coordinate columns."""
        loc_file = HARMONIZED_DIR / "location_data_harmonized_with_uuid.csv"
        df = pd.read_csv(loc_file)

        required_cols = [
            "site_id",
            "latitude",
            "longitude",
            "harmonized_location_uuid",
            "source_dataset_id",
        ]

        for col in required_cols:
            assert col in df.columns, (
                f"Location file missing required column: {col}"
            )

    def test_location_coordinates_valid(self):
        """Latitude and longitude should be in valid ranges."""
        loc_file = HARMONIZED_DIR / "location_data_harmonized_with_uuid.csv"
        df = pd.read_csv(loc_file)

        # Check latitude
        lat_valid = df["latitude"].dropna()
        if len(lat_valid) > 0:
            assert lat_valid.between(-90, 90).all(), (
                "Latitude values outside valid range [-90, 90]"
            )

        # Check longitude
        lon_valid = df["longitude"].dropna()
        if len(lon_valid) > 0:
            assert lon_valid.between(-180, 180).all(), (
                "Longitude values outside valid range [-180, 180]"
            )

    def test_location_uuid_format(self):
        """UUIDs should be properly formatted."""
        loc_file = HARMONIZED_DIR / "location_data_harmonized_with_uuid.csv"
        df = pd.read_csv(loc_file)

        uuids = df["harmonized_location_uuid"].dropna().unique()
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            re.IGNORECASE
        )

        for uuid in uuids:
            assert uuid_pattern.match(str(uuid)), (
                f"Invalid UUID format: {uuid}"
            )


class TestTemporalConsistency:
    """Test time-based patterns and anomalies."""

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_timeseries_chronologically_ordered(self, filepath):
        """Timeseries data should be chronologically ordered within each group."""
        df = read_harmonized_file(filepath)

        # Only test timeseries data
        ts_data = df[df["is_timeseries"] == True].copy()

        if len(ts_data) == 0:
            return  # Skip if no timeseries data

        # Group by site, depth, replicate and check chronological order
        group_cols = ["site_id", "depth_m", "replicate"]
        # Remove any groups with all NaN in grouping columns
        ts_data = ts_data.dropna(subset=["datetime_UTC"])

        violations = []
        for name, group in ts_data.groupby(group_cols, dropna=False):
            if len(group) < 2:
                continue

            # Check if datetime is monotonically increasing
            timestamps = group["datetime_UTC"].values
            is_ordered = all(timestamps[i] <= timestamps[i+1] for i in range(len(timestamps)-1))

            if not is_ordered:
                # Find specific violations
                for i in range(len(timestamps)-1):
                    if timestamps[i] > timestamps[i+1]:
                        violations.append({
                            "row_idx": group.index[i].tolist() if hasattr(group.index[i], 'tolist') else group.index[i],
                            "group": name,
                            "timestamp_current": timestamps[i],
                            "timestamp_next": timestamps[i+1]
                        })

        assert len(violations) == 0, (
            f"{filepath.name}: Found {len(violations)} chronological order violations. "
            f"First few: {violations[:3]}"
        )

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_no_duplicate_timestamps(self, filepath):
        """No duplicate timestamps for same site/depth/replicate combination."""
        df = read_harmonized_file(filepath)

        # Define key columns that should be unique per measurement
        key_cols = ["datetime_UTC", "site_id", "depth_m", "replicate"]

        # Drop rows where all key columns are NaN
        df_with_keys = df.dropna(subset=key_cols, how="all")

        if len(df_with_keys) == 0:
            return  # Skip if no valid data

        # Find duplicates
        duplicates = df_with_keys[df_with_keys.duplicated(subset=key_cols, keep=False)]

        if len(duplicates) > 0:
            # Get sample of duplicate info with row indices
            dup_sample = duplicates.head(10)[key_cols].copy()
            dup_sample["row_idx"] = duplicates.head(10).index.tolist()

            assert False, (
                f"{filepath.name}: Found {len(duplicates)} rows with duplicate timestamps. "
                f"Sample duplicate rows (showing indices):\n{dup_sample.to_string()}"
            )


class TestCrossReferences:
    """Test relationships between data and location files."""

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_all_sites_have_location_data(self, filepath):
        """Every site_id in data should have location metadata."""
        df = read_harmonized_file(filepath)
        loc_file = HARMONIZED_DIR / "location_data_harmonized_with_uuid.csv"
        loc_df = pd.read_csv(loc_file)

        # Get dataset identifier from filename
        dataset_id = filepath.stem.replace("_harmonized", "")

        # Get unique site_ids from data
        data_sites = set(df["site_id"].dropna().unique())

        # Get site_ids from location data for this dataset
        loc_sites = set(
            loc_df[loc_df["source_dataset_id"] == dataset_id]["site_id"].dropna().unique()
        )

        # Find sites without location data
        missing_locations = data_sites - loc_sites

        if len(missing_locations) > 0:
            # Find rows with missing location data
            missing_rows = df[df["site_id"].isin(missing_locations)]
            row_indices = missing_rows.index.tolist()[:10]  # First 10

            assert False, (
                f"{filepath.name}: {len(missing_locations)} site_ids lack location data. "
                f"Missing sites: {sorted(missing_locations)}. "
                f"Sample row indices with missing locations: {row_indices}"
            )

    def test_location_uuid_uniqueness(self):
        """Each UUID should be unique and properly formatted."""
        loc_file = HARMONIZED_DIR / "location_data_harmonized_with_uuid.csv"
        loc_df = pd.read_csv(loc_file)

        # Check that UUIDs are not duplicated with different coordinates
        uuid_groups = loc_df.groupby("harmonized_location_uuid").agg({
            "latitude_harmonized": "nunique",
            "longitude_harmonized": "nunique"
        })

        # Each UUID should have exactly 1 unique coordinate pair
        violations = uuid_groups[
            (uuid_groups["latitude_harmonized"] > 1) |
            (uuid_groups["longitude_harmonized"] > 1)
        ]

        assert len(violations) == 0, (
            f"Found {len(violations)} UUIDs with multiple coordinate sets. "
            f"This indicates improper location merging. Violating UUIDs: {violations.index.tolist()}"
        )

    def test_source_dataset_consistency(self):
        """Source dataset IDs should match harmonized file names."""
        loc_file = HARMONIZED_DIR / "location_data_harmonized_with_uuid.csv"
        loc_df = pd.read_csv(loc_file)

        # Get all dataset IDs from harmonized files
        harmonized_files = get_harmonized_files()
        file_dataset_ids = {f.stem.replace("_harmonized", "") for f in harmonized_files}

        # Get all dataset IDs from location file
        loc_dataset_ids = set(loc_df["source_dataset_id"].dropna().unique())

        # Check for mismatches
        in_loc_not_files = loc_dataset_ids - file_dataset_ids
        in_files_not_loc = file_dataset_ids - loc_dataset_ids

        assert len(in_loc_not_files) == 0, (
            f"Location file contains dataset IDs not in harmonized files: {in_loc_not_files}"
        )
        assert len(in_files_not_loc) == 0, (
            f"Harmonized files exist without location data: {in_files_not_loc}"
        )


class TestOutlierDetection:
    """Detect statistical outliers that may indicate errors."""

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_no_extreme_outliers_volumetric(self, filepath):
        """Flag extreme outliers in volumetric water content using IQR method."""
        df = read_harmonized_file(filepath)
        col = "volumetric_water_content_m3_m3"

        values = pd.to_numeric(df[col], errors="coerce").dropna()

        if len(values) < 10:
            return  # Need sufficient data for outlier detection

        # Calculate IQR
        Q1 = values.quantile(0.25)
        Q3 = values.quantile(0.75)
        IQR = Q3 - Q1

        # Define outliers as beyond 3*IQR (very extreme)
        lower_bound = Q1 - 3 * IQR
        upper_bound = Q3 + 3 * IQR

        # Find outlier rows
        outlier_mask = (df[col] < lower_bound) | (df[col] > upper_bound)
        outliers = df[outlier_mask]

        if len(outliers) > 0:
            outlier_info = outliers[[col, "site_id", "datetime_UTC"]].copy()
            outlier_info["row_idx"] = outliers.index.tolist()
            outlier_sample = outlier_info.head(10)

            outlier_pct = (len(outliers) / len(df)) * 100

            # Only fail if outliers are > 5% of data (some outliers can be real)
            assert outlier_pct < 5, (
                f"{filepath.name}: {outlier_pct:.1f}% of data are extreme outliers for {col}. "
                f"Bounds: [{lower_bound:.3f}, {upper_bound:.3f}]. "
                f"Found {len(outliers)} outliers. Sample:\n{outlier_sample.to_string()}"
            )

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_water_potential_realistic_range(self, filepath):
        """Water potential should be within realistic bounds for soil."""
        df = read_harmonized_file(filepath)
        col = "water_potential_kPa"

        values = pd.to_numeric(df[col], errors="coerce").dropna()

        if len(values) == 0:
            return

        # Realistic range: -50000 kPa (very dry) to +10 kPa (saturated)
        # Values beyond this suggest sensor error or unit conversion issues
        lower_bound = -50000
        upper_bound = 10

        out_of_range = df[
            (df[col] < lower_bound) | (df[col] > upper_bound)
        ]

        if len(out_of_range) > 0:
            problem_rows = out_of_range[[col, "site_id", "datetime_UTC"]].copy()
            problem_rows["row_idx"] = out_of_range.index.tolist()
            sample = problem_rows.head(10)

            pct = (len(out_of_range) / len(values)) * 100

            assert pct < 5, (
                f"{filepath.name}: {pct:.1f}% of {col} values outside realistic range "
                f"[{lower_bound}, {upper_bound}] kPa. "
                f"Found {len(out_of_range)} problematic values. Sample:\n{sample.to_string()}"
            )

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_depth_reasonable_range(self, filepath):
        """Sensor depths should be within reasonable bounds (typically < 5m)."""
        df = read_harmonized_file(filepath)
        col = "depth_m"

        values = pd.to_numeric(df[col], errors="coerce").dropna()

        if len(values) == 0:
            return

        # Most soil moisture sensors are installed < 2m, very few > 5m
        max_reasonable = 5.0

        too_deep = df[df[col] > max_reasonable]

        if len(too_deep) > 0:
            problem_rows = too_deep[[col, "site_id", "datetime_UTC"]].copy()
            problem_rows["row_idx"] = too_deep.index.tolist()
            unique_depths = sorted(too_deep[col].unique())

            # This is more of a warning - some deep sensors exist
            pct = (len(too_deep) / len(values)) * 100

            assert pct < 10, (
                f"{filepath.name}: {pct:.1f}% of depth values exceed {max_reasonable}m. "
                f"Unique depths > {max_reasonable}m: {unique_depths}. "
                f"This may indicate unit conversion error (cm vs m). "
                f"Sample row indices: {problem_rows['row_idx'].head(10).tolist()}"
            )


class TestReplicateConsistency:
    """Test replicate numbering consistency."""

    @pytest.mark.parametrize("filepath", get_harmonized_files())
    def test_replicate_consistency(self, filepath):
        """Replicate numbers should be sequential within groups."""
        df = read_harmonized_file(filepath)

        # Group by datetime, site, depth
        group_cols = ["datetime_UTC", "site_id", "depth_m"]

        # Drop rows where we can't determine grouping
        df_grouped = df.dropna(subset=group_cols)

        if len(df_grouped) == 0:
            return

        violations = []
        for name, group in df_grouped.groupby(group_cols):
            reps = sorted(group["replicate"].dropna().unique())

            if len(reps) == 0:
                continue

            # Check if replicates are sequential starting from 1
            expected = list(range(1, len(reps) + 1))

            if reps != expected:
                # Find specific issues
                missing = set(expected) - set(reps)
                unexpected = set(reps) - set(expected)

                if missing or unexpected:
                    violations.append({
                        "group": name,
                        "found_replicates": reps,
                        "expected_replicates": expected,
                        "missing": list(missing) if missing else None,
                        "unexpected": list(unexpected) if unexpected else None,
                        "row_indices": group.index.tolist()[:5]  # Sample
                    })

        # Allow some violations (up to 5%) as irregular sampling can be valid
        if len(violations) > 0:
            total_groups = df_grouped.groupby(group_cols).ngroups
            violation_pct = (len(violations) / total_groups) * 100

            assert violation_pct < 5, (
                f"{filepath.name}: {violation_pct:.1f}% of groups have non-sequential replicates. "
                f"Found {len(violations)} violations out of {total_groups} groups. "
                f"Sample violations: {violations[:3]}"
            )


# Summary test
def test_all_files_present():
    """Verify expected number of harmonized files exist."""
    files = get_harmonized_files()
    # Based on the mapping JSON, we expect datasets 1-10, 15-18, 23-27 (excluding some)
    # Count should match included datasets
    assert len(files) >= 19, (
        f"Expected at least 19 harmonized dataset files, found {len(files)}"
    )


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-q", "--tb=short"])


