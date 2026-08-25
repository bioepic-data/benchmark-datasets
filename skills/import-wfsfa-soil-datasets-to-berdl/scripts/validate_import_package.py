#!/usr/bin/env python3
"""Validate the WFSFA BERDL package against its downloaded harmonized sources."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


OBSERVATION_COLUMNS = [
    "sdt_dataset_name",
    "sdt_location_name",
    "datetime_utc",
    "depth_below_soil_surface_meter",
    "replicate_series_count_unit",
    "is_time_series",
    "volumetric_water_content_ratio_unit",
    "gravimetric_water_content_ratio_unit",
    "soil_micropore_matric_water_potential_pascal",
]
REQUIRED_TERMS = {
    "BERVO:0001743",
    "BERVO:0001750",
    "BERVO:0001810",
    "BERVO:8000069",
    "BERVO:8000237",
    "BERVO:8000240",
    "BERVO:8000300",
    "BERVO:8000394",
    "BERVO:8000528",
    "UO:0000008",
    "UO:0000110",
    "UO:0000185",
    "UO:0000189",
    "UO:0000190",
    "UO:0000233",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def unique_key(rows: list[dict[str, str]], key: str, table: str) -> set[str]:
    values = [row[key] for row in rows]
    require(len(values) == len(set(values)), f"{table}.{key} is not unique")
    return set(values)


def validate(repo_root: Path) -> dict[str, int | str]:
    source_dir = (
        repo_root
        / "berdl_import/downloaded_data/ess-dive_wfsfa_soil_datasets/harmonized_csv"
    )
    package_dir = repo_root / "berdl_import/data/berdl_import/watershed_sfa_soil_moisture"
    metadata_dir = repo_root / "data/processed/harmonized_soil_moisture_data"

    source_paths = sorted(source_dir.glob("*_harmonized.csv"))
    require(bool(source_paths), f"No source CSVs found under {source_dir}")

    with (metadata_dir / "ess-dive_harmonized_soil_urls.csv").open(
        newline="", encoding="utf-8"
    ) as fh:
        manifest_rows = list(csv.DictReader(fh))
    manifest_names = {
        (row.get("name") or row.get("filename") or "").removesuffix("_harmonized.csv")
        for row in manifest_rows
        if (row.get("name") or row.get("filename") or "").endswith("_harmonized.csv")
    }
    source_names = {path.name.removesuffix("_harmonized.csv") for path in source_paths}
    require(source_names == manifest_names, "Source CSV set does not match the URL manifest")

    mapping = json.loads((metadata_dir / "sm_data_harmonization_mapping.json").read_text())
    mapped_names = {
        entry["dataset_identifier"]
        for entry in mapping
        if str(entry.get("inclusion_decision", "")).lower() == "include"
    }
    require(source_names == mapped_names, "Source CSV set does not match included mappings")

    datasets = read_rows(package_dir / "sdt_dataset.csv")
    locations = read_rows(package_dir / "sdt_location.csv")
    harmonized_locations = read_rows(package_dir / "sdt_harmonized_location.csv")
    sys_ddt = read_rows(package_dir / "sys_ddt_typedef.csv")
    sys_oterm = read_rows(package_dir / "sys_oterm.csv")

    dataset_names = unique_key(datasets, "sdt_dataset_name", "sdt_dataset")
    location_names = unique_key(locations, "sdt_location_name", "sdt_location")
    harmonized_location_names = unique_key(
        harmonized_locations,
        "sdt_harmonized_location_name",
        "sdt_harmonized_location",
    )
    require(
        sum(row["is_imported"] == "true" for row in datasets) == len(source_names),
        "sdt_dataset imported count does not match the source file set",
    )
    require(
        all(row["sdt_dataset_name"] in dataset_names for row in locations),
        "sdt_location contains an orphan dataset reference",
    )
    require(
        all(
            row["sdt_harmonized_location_name"] in harmonized_location_names
            for row in locations
        ),
        "sdt_location contains an orphan harmonized-location reference",
    )

    ddt_columns = {row["berdl_column_name"] for row in sys_ddt}
    require(ddt_columns == set(OBSERVATION_COLUMNS), "sys_ddt_typedef columns differ from observations")
    require("time_interval_minute" not in ddt_columns, "Obsolete interval column is still declared")

    term_ids = unique_key(sys_oterm, "sys_oterm_id", "sys_oterm")
    require(REQUIRED_TERMS <= term_ids, f"Missing required terms: {sorted(REQUIRED_TERMS - term_ids)}")
    require(
        not any(term.startswith("bervo:BERVO_") for term in term_ids),
        "sys_oterm contains non-normalized BERVO identifiers",
    )

    ndarray_rows = read_rows(package_dir / "ddt_ndarray.csv")
    require(len(ndarray_rows) == 1, "ddt_ndarray must contain exactly one row")
    ndarray = ndarray_rows[0]
    for keys in (
        (
            "ddt_ndarray_dimension_variable_names",
            "ddt_ndarray_dimension_variable_types_sys_oterm_id",
            "ddt_ndarray_dimension_variable_types_sys_oterm_name",
        ),
        (
            "ddt_ndarray_variable_names",
            "ddt_ndarray_variable_types_sys_oterm_id",
            "ddt_ndarray_variable_types_sys_oterm_name",
        ),
    ):
        require(
            len({len(ndarray[key].split(",")) for key in keys}) == 1,
            f"ddt_ndarray parallel lists have different lengths: {keys}",
        )

    observation_path = package_dir / "ddt_soil_moisture_observation.csv"
    observation_count = 0
    potential_count = 0
    with observation_path.open(newline="", encoding="utf-8") as out_fh:
        output = csv.DictReader(out_fh)
        require(output.fieldnames == OBSERVATION_COLUMNS, "Unexpected observation header")
        for source_path in source_paths:
            dataset_name = source_path.name.removesuffix("_harmonized.csv")
            with source_path.open(newline="", encoding="utf-8") as source_fh:
                for source in csv.DictReader(source_fh):
                    target = next(output, None)
                    require(target is not None, "Observation output ended before the source set")
                    observation_count += 1
                    require(target["sdt_dataset_name"] == dataset_name, "Dataset row order/value mismatch")
                    require(target["sdt_dataset_name"] in dataset_names, "Observation dataset orphan")
                    require(target["sdt_location_name"] in location_names, "Observation location orphan")
                    require(target["datetime_utc"] == source["datetime_UTC"], "Timestamp mismatch")
                    require(
                        target["replicate_series_count_unit"] == source["replicate"]
                        and int(target["replicate_series_count_unit"]) > 0,
                        "Replicate mismatch or non-positive replicate",
                    )
                    require(
                        target["is_time_series"] == source["is_timeseries"].lower(),
                        "Time-series flag mismatch",
                    )
                    for source_key, target_key, multiplier in (
                        ("depth_m", "depth_below_soil_surface_meter", 1.0),
                        (
                            "volumetric_water_content_m3_m3",
                            "volumetric_water_content_ratio_unit",
                            1.0,
                        ),
                        (
                            "gravimetric_water_content_gH2O_gs",
                            "gravimetric_water_content_ratio_unit",
                            1.0,
                        ),
                        (
                            "water_potential_kPa",
                            "soil_micropore_matric_water_potential_pascal",
                            1000.0,
                        ),
                    ):
                        source_value = source[source_key]
                        target_value = target[target_key]
                        require(
                            (source_value == "") == (target_value == ""),
                            f"Null mismatch for {source_key}",
                        )
                        if source_value:
                            require(
                                math.isclose(
                                    float(target_value),
                                    float(source_value) * multiplier,
                                    rel_tol=1e-12,
                                    abs_tol=1e-12,
                                ),
                                f"Numeric transformation mismatch for {source_key}",
                            )
                            if source_key == "water_potential_kPa":
                                potential_count += 1
        require(next(output, None) is None, "Observation output has rows absent from sources")

    summary = json.loads((package_dir / "build_summary.json").read_text())
    require(
        summary["ddt_soil_moisture_observation"] == observation_count,
        "build_summary observation count mismatch",
    )
    require(summary["sys_ddt_typedef"] == len(sys_ddt), "build_summary typedef count mismatch")
    require(
        "time_interval_minute" not in (package_dir / "schema.sql").read_text(),
        "Obsolete interval column remains in schema.sql",
    )

    return {
        "status": "ok",
        "source_files": len(source_paths),
        "observation_rows": observation_count,
        "water_potential_rows_converted_kpa_to_pa": potential_count,
        "datasets": len(datasets),
        "locations": len(locations),
        "harmonized_locations": len(harmonized_locations),
        "sys_ddt_typedef": len(sys_ddt),
        "sys_oterm": len(sys_oterm),
    }


def main() -> None:
    default_repo = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=default_repo)
    args = parser.parse_args()
    print(json.dumps(validate(args.repo_root.resolve()), indent=2))


if __name__ == "__main__":
    main()
