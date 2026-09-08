#!/usr/bin/env python3
"""Create or finalize BERDL ingest metadata for the WFSFA soil package."""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_DIR = (
    REPO_ROOT / "berdl_import/data/berdl_import/watershed_sfa_soil_moisture"
)
TABLES = (
    "ddt_ndarray",
    "ddt_soil_moisture_observation",
    "sdt_dataset",
    "sdt_harmonized_location",
    "sdt_location",
    "sys_ddt_typedef",
    "sys_oterm",
    "sys_typedef",
)
TITLES = {
    "ddt_ndarray": "WFSFA soil-moisture ndarray",
    "ddt_soil_moisture_observation": "WFSFA harmonized soil-moisture observations",
    "sdt_dataset": "WFSFA soil-moisture source datasets",
    "sdt_harmonized_location": "WFSFA harmonized locations",
    "sdt_location": "WFSFA source locations",
    "sys_ddt_typedef": "WFSFA soil-moisture dynamic-data typedef",
    "sys_oterm": "WFSFA soil-moisture ontology terms",
    "sys_typedef": "WFSFA soil-moisture static typedefs",
}
DESCRIPTIONS = {
    "ddt_ndarray": "One CORAL-style ndarray descriptor for the harmonized soil-moisture observation table.",
    "ddt_soil_moisture_observation": "Harmonized WFSFA soil-moisture observations from the 19 included ESS-DIVE datasets.",
    "sdt_dataset": "Dataset metadata and inclusion decisions for 28 reviewed ESS-DIVE WFSFA soil-moisture packages.",
    "sdt_harmonized_location": "Canonical harmonized location UUIDs used by the observation table.",
    "sdt_location": "Dataset-specific source locations and their mappings to canonical harmonized locations.",
    "sys_ddt_typedef": "BERVO and UO mappings for the nine variables in the soil-moisture ndarray.",
    "sys_oterm": "BERVO and UO ontology-term snapshot used by this import.",
    "sys_typedef": "BERVO and UO field mappings for the static soil-moisture tables.",
}


def metadata_source(table: str) -> str:
    repository = "https://github.com/bioepic-data/benchmark-datasets/"
    if table not in {"ddt_ndarray", "sys_ddt_typedef", "sys_oterm", "sys_typedef"}:
        return repository
    return (
        f"{repository}; "
        "BERVO=/h/jmc/data/bioepic/chess/ontologies/bervo_github/bervo.obo; "
        "UO=/h/jmc/data/bioepic/chess/ontologies/uo/uo.obo"
    )


def generate(data_dir: Path) -> None:
    metadata_dir = data_dir / "metadata"
    metadata_dir.mkdir(exist_ok=True)
    if any((metadata_dir / f"{table}.yaml").exists() for table in TABLES):
        raise SystemExit(
            f"Refusing to replace existing metadata in {metadata_dir}; remove it explicitly first."
        )

    started = datetime.now(timezone.utc).isoformat()
    schema_location = (
        "s3a://cdm-lake/tenant-general-warehouse/bervodata/datasets/"
        "watershed_sfa_soil_moisture/config/schema.sql"
    )
    for table in TABLES:
        record = {
            "schema_version": "0.2.0",
            "identifier": str(uuid.uuid4()),
            "tenant": "bervodata",
            "dataset": "watershed_sfa_soil_moisture",
            "namespace": "bervodata_watershed_sfa_soil_moisture",
            "table": table,
            "title": TITLES[table],
            "source": metadata_source(table),
            "date_accessed": date.today().isoformat(),
            "status": "in_progress",
            "ingested_by": "John-Marc Chandonia",
            "ingest_started_at": started,
            "data_schema_location": schema_location,
            "version": "0.5-beta/refreshed-v05",
            "description": DESCRIPTIONS[table],
            "ingest_contributors": [],
            "ingest_completed_at": None,
        }
        path = metadata_dir / f"{table}.yaml"
        path.write_text(
            yaml.safe_dump(record, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        print(f"wrote {path}")


def finalize(data_dir: Path, progress_log: Path) -> None:
    completed: dict[str, str] = {}
    for raw_line in progress_log.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        entry = json.loads(raw_line)
        if entry.get("status") == "complete" and entry.get("table") in TABLES:
            completed[entry["table"]] = entry["timestamp"]

    metadata_dir = data_dir / "metadata"
    for table in TABLES:
        path = metadata_dir / f"{table}.yaml"
        record = yaml.safe_load(path.read_text(encoding="utf-8"))
        record["ingest_completed_at"] = completed.get(table)
        record["status"] = "completed" if table in completed else "failed"
        path.write_text(
            yaml.safe_dump(record, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        print(f"{table}: status={record['status']} completed_at={record['ingest_completed_at']}")


def refresh_sources(data_dir: Path) -> None:
    metadata_dir = data_dir / "metadata"
    for table in TABLES:
        path = metadata_dir / f"{table}.yaml"
        record = yaml.safe_load(path.read_text(encoding="utf-8"))
        record["source"] = metadata_source(table)
        path.write_text(
            yaml.safe_dump(record, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        print(f"{table}: source={record['source']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("generate", "finalize", "refresh-sources")
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--progress-log", type=Path)
    args = parser.parse_args()
    if args.command == "generate":
        generate(args.data_dir)
    elif args.command == "refresh-sources":
        refresh_sources(args.data_dir)
    elif not args.progress_log:
        parser.error("finalize requires --progress-log")
    else:
        finalize(args.data_dir, args.progress_log)


if __name__ == "__main__":
    main()
