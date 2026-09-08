#!/usr/bin/env python3
"""Import the WFSFA soil moisture package into BERDL."""

from __future__ import annotations

import argparse
import csv
import contextlib
import io
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
DEFAULT_DATA_DIR = ROOT / "data/berdl_import/watershed_sfa_soil_moisture"
BERIL_ROOT = Path("/h/jmc/src/BERIL-research-observatory")
BERIL_SCRIPTS = BERIL_ROOT / "scripts"

TABLE_DESCRIPTIONS = {
    "ddt_ndarray": "Metadata for the WFSFA soil moisture observation array.",
    "ddt_soil_moisture_observation": "Combined harmonized WFSFA soil moisture observations from imported ESS-DIVE packages.",
    "sdt_dataset": "Dataset-level metadata for imported and reviewed ESS-DIVE WFSFA soil moisture packages.",
    "sdt_harmonized_location": "Harmonized location records keyed by harmonized location UUID.",
    "sdt_location": "Dataset-specific source locations mapped to harmonized locations.",
    "sys_ddt_typedef": "Column definitions for the WFSFA soil moisture dynamic data table.",
    "sys_oterm": "Ontology terms from the BERVO and UO sources used by this database.",
    "sys_typedef": "Column definitions for static data tables in this database.",
}
FOREIGN_KEYS = {
    ("ddt_soil_moisture_observation", "sdt_dataset_name"):
        "sdt_dataset.sdt_dataset_name",
    ("ddt_soil_moisture_observation", "sdt_location_name"):
        "sdt_location.sdt_location_name",
    ("sdt_location", "sdt_dataset_name"): "sdt_dataset.sdt_dataset_name",
    ("sdt_location", "sdt_harmonized_location_name"):
        "sdt_harmonized_location.sdt_harmonized_location_name",
}


def load_env() -> None:
    for env_path in [REPO_ROOT / ".env", ROOT / ".env", BERIL_ROOT / ".env"]:
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def _read_csv_by_column(path: Path, column: str) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row[column]: row for row in csv.DictReader(handle)}


def enrich_schema_comments(schema_defs: dict, data_dir: Path) -> None:
    """Attach structured BERDL comments to the ingest configuration schema."""
    static_rows = {}
    with (data_dir / "sys_typedef.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            table = {
                "Dataset": "sdt_dataset",
                "Harmonized_Location": "sdt_harmonized_location",
                "Location": "sdt_location",
            }.get(row["type_name"])
            if table:
                static_rows[(table, row["berdl_column_name"])] = row
    dynamic_rows = _read_csv_by_column(
        data_dir / "sys_ddt_typedef.csv", "berdl_column_name"
    )

    for table, columns in schema_defs.items():
        for column in columns:
            name = column["column"]
            source = (
                dynamic_rows.get(name)
                if table == "ddt_soil_moisture_observation"
                else static_rows.get((table, name))
            )
            description = (
                (source or {}).get("comment")
                or name.replace("_", " ").capitalize() + "."
            )
            comment = {"description": description}
            reference = FOREIGN_KEYS.get((table, name))
            if reference:
                comment.update({"type": "foreign_key", "references": reference})
            if source:
                for key in (
                    "type_sys_oterm_id",
                    "type_sys_oterm_name",
                    "units_sys_oterm_id",
                    "units_sys_oterm_name",
                    "dimension_oterm_id",
                    "dimension_oterm_name",
                    "variable_oterm_id",
                    "variable_oterm_name",
                    "unit_sys_oterm_id",
                    "unit_sys_oterm_name",
                ):
                    if source.get(key):
                        comment[key] = source[key]
            column["comment"] = json.dumps(comment, sort_keys=True)


def existing_table_providers(spark, namespace: str, tables: list[str]) -> set[str]:
    providers = set()
    for table in tables:
        rows = spark.sql(f"DESCRIBE TABLE EXTENDED `{namespace}`.`{table}`").collect()
        provider = next(
            (
                row["data_type"]
                for row in rows
                if (row["col_name"] or "").strip() == "Provider"
            ),
            None,
        )
        if provider:
            providers.add(provider.lower())
    return providers


def install_legacy_delta_writer() -> None:
    """Preserve this dataset's legacy Delta provider under the underscore namespace."""
    from data_lakehouse_ingest.orchestrator import table_processor

    def write_delta_table(
        df,
        spark,
        namespace,
        name,
        partition_by,
        mode,
        rows_in,
        logger,
    ):
        full_table = f"`{namespace}`.`{name}`"
        logger.info(
            f"Writing legacy Delta table: {namespace}.{name} (mode={mode})"
        )
        writer = df.write.format("delta").mode(mode)
        if mode == "overwrite":
            writer = writer.option("overwriteSchema", "true")
        if partition_by:
            columns = [partition_by] if isinstance(partition_by, str) else partition_by
            writer = writer.partitionBy(*columns)
        writer.saveAsTable(full_table)
        return rows_in

    table_processor.write_table = write_delta_table


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--tenant", default="bervodata")
    parser.add_argument("--dataset", default="watershed_sfa_soil_moisture")
    parser.add_argument("--mode", default="overwrite", choices=["overwrite", "append"])
    parser.add_argument("--chunk-target-gb", type=float, default=0.25)
    parser.add_argument("--no-upload", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument(
        "--run-id",
        default=None,
        help="Unique run identifier used for resumable progress and config objects.",
    )
    parser.add_argument("--progress-key", default=None)
    parser.add_argument("--config-key", default=None)
    args = parser.parse_args()

    load_env()
    venv_bin = BERIL_ROOT / ".venv-berdl" / "bin"
    os.environ["PATH"] = f"{venv_bin}:{os.environ.get('PATH', '')}"
    if not os.environ.get("KBASE_AUTH_TOKEN"):
        raise SystemExit("KBASE_AUTH_TOKEN is not set; cannot run BERDL ingest.")

    sys.path.insert(0, str(BERIL_SCRIPTS))
    import ingest_lib  # noqa: WPS433
    from data_lakehouse_ingest.orchestrator import init_utils  # noqa: WPS433

    def create_underscore_namespace(
        spark,
        namespace=None,
        append_target=True,
        tenant_name=None,
        iceberg=True,
    ):
        if tenant_name:
            ns = f"{tenant_name}_{namespace}"
            target_location = (
                f"s3a://cdm-lake/tenant-general-warehouse/{tenant_name}/"
                f"datasets/{namespace}/silver"
            )
        else:
            ns = f"my_{namespace}"
            target_location = None

        if target_location:
            existing_location = None
            try:
                ns_info = spark.sql(f"DESCRIBE NAMESPACE EXTENDED {ns}").collect()
                matches = [
                    r.info_value for r in ns_info
                    if r.info_name.lower() == "location"
                ]
                existing_location = matches[0].rstrip("/") if matches else None
            except Exception:
                existing_location = None

            if existing_location and existing_location != target_location.rstrip("/"):
                tables = spark.sql(f"SHOW TABLES IN {ns}").collect()
                if tables:
                    raise RuntimeError(
                        f"Namespace {ns} already exists at {existing_location} "
                        f"and contains tables; refusing to recreate it at {target_location}."
                    )
                spark.sql(f"DROP NAMESPACE {ns}")
            spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {ns} LOCATION '{target_location}'")
        else:
            spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {ns}")
        print(f"Namespace {ns} ready")
        return ns

    sys.modules["berdl_notebook_utils.spark.database"].create_namespace_if_not_exists = (
        create_underscore_namespace
    )
    init_utils.create_namespace_if_not_exists = create_underscore_namespace

    from ingest_lib import (  # noqa: WPS433
        _build_dataset_config,
        build_table_stats,
        detect_source_files,
        initialize,
        parse_sql_schema,
        print_preflight_plan,
        run_ingest,
        upload_files,
        verify_ingest,
    )

    bucket = "cdm-lake"
    namespace = f"{args.tenant}_{args.dataset}"
    bronze_prefix = f"tenant-general-warehouse/{args.tenant}/datasets/{args.dataset}"
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", run_id):
        raise SystemExit("--run-id may contain only letters, digits, dot, underscore, and hyphen.")
    progress_key = args.progress_key or f"{bronze_prefix}/_ingest_progress/{run_id}.jsonl"
    config_key = args.config_key or f"{bronze_prefix}/config/{args.dataset}_{run_id}.json"

    source_mode, source_db, sql_schema, data_files, file_ext, delimiter = detect_source_files(args.data_dir)
    if source_mode != "csv":
        raise SystemExit(f"Expected CSV import package, found source mode: {source_mode}")
    if not sql_schema:
        raise SystemExit("schema.sql is required for this import package.")

    schemas, schema_defs = parse_sql_schema(sql_schema)
    enrich_schema_comments(schema_defs, args.data_dir)
    table_stats = build_table_stats(
        data_files,
        schemas,
        args.chunk_target_gb,
        chunked_ingest=True,
        delimiter=delimiter,
    )

    preflight_output = io.StringIO() if args.preflight_only else None
    with contextlib.redirect_stdout(preflight_output) if preflight_output else contextlib.nullcontext():
        print_preflight_plan(
            table_stats=table_stats,
            namespace=namespace,
            mode=args.mode,
            bucket=bucket,
            bronze_prefix=bronze_prefix,
            progress_key=progress_key,
            confirmed=True,
        )
    if preflight_output:
        print(preflight_output.getvalue().replace("CONFIRMED — proceeding.\n", ""), end="")
    print(f"Run ID: {run_id}")
    print(f"Config key: s3a://{bucket}/{config_key}")
    if args.preflight_only:
        print("Preflight only; no BERDL state was changed.")
        return

    spark, minio_client = initialize()
    readiness = spark.sql("SELECT 1 AS ready").collect()
    if not readiness or readiness[0]["ready"] != 1:
        raise RuntimeError("BERDL Spark readiness probe did not return ready=1")
    print("BERDL Spark readiness probe: ready=1")
    providers = existing_table_providers(spark, namespace, list(table_stats))
    if providers == {"delta"}:
        install_legacy_delta_writer()
        print("Detected legacy Delta tables; preserving Delta provider and underscore namespace.")
    elif providers and providers != {"iceberg"}:
        raise RuntimeError(f"Refusing mixed or unsupported existing table providers: {providers}")
    if not args.no_upload:
        upload_files(minio_client, bucket, table_stats, bronze_prefix, file_ext)
    spark = run_ingest(
        spark=spark,
        minio_client=minio_client,
        table_stats=table_stats,
        schemas=schemas,
        schema_defs=schema_defs,
        namespace=namespace,
        tenant=args.tenant,
        dataset=args.dataset,
        bucket=bucket,
        bronze_prefix=bronze_prefix,
        mode=args.mode,
        file_ext=file_ext,
        delimiter=delimiter,
        progress_key=progress_key,
        config_key=config_key,
    )
    canonical_config = _build_dataset_config(
        args.tenant,
        args.dataset,
        bucket,
        bronze_prefix,
        table_stats,
        schemas,
        schema_defs,
        args.mode,
        file_ext,
        delimiter,
    )
    canonical_config["physical_namespace"] = namespace
    canonical_config["storage_format"] = "delta" if providers == {"delta"} else "iceberg"
    for table in canonical_config["tables"]:
        table["comment"] = TABLE_DESCRIPTIONS[table["name"]]
    config_bytes = json.dumps(canonical_config, indent=2).encode()
    minio_client.put_object(
        bucket,
        config_key,
        io.BytesIO(config_bytes),
        len(config_bytes),
        content_type="application/json",
    )
    print(f"Canonical eight-table config -> s3a://{bucket}/{config_key}")
    for table, description in TABLE_DESCRIPTIONS.items():
        escaped = description.replace("'", "''")
        spark.sql(
            f"ALTER TABLE `{namespace}`.`{table}` "
            f"SET TBLPROPERTIES ('comment' = '{escaped}')"
        )
    verify_ingest(spark, namespace, table_stats, minio_client, bucket, progress_key)


if __name__ == "__main__":
    main()
