#!/usr/bin/env python3
"""Import the WFSFA soil moisture package into BERDL."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data/berdl_import/watershed_sfa_soil_moisture"
BERIL_ROOT = Path("/h/jmc/src/BERIL-research-observatory")
BERIL_SCRIPTS = BERIL_ROOT / "scripts"


def load_env() -> None:
    for env_path in [ROOT / ".env", BERIL_ROOT / ".env"]:
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--tenant", default="bervodata")
    parser.add_argument("--dataset", default="watershed_sfa_soil_moisture")
    parser.add_argument("--mode", default="overwrite", choices=["overwrite", "append"])
    parser.add_argument("--chunk-target-gb", type=float, default=0.25)
    parser.add_argument("--no-upload", action="store_true")
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

    def create_underscore_namespace(spark, namespace=None, append_target=True, tenant_name=None):
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
    silver_base = f"s3a://{bucket}/tenant-general-warehouse/{args.tenant}/"
    progress_key = args.progress_key or f"{bronze_prefix}/_ingest_progress.jsonl"
    config_key = args.config_key or f"{bronze_prefix}/config/{args.dataset}.json"

    source_mode, source_db, sql_schema, data_files, file_ext, delimiter = detect_source_files(args.data_dir)
    if source_mode != "csv":
        raise SystemExit(f"Expected CSV import package, found source mode: {source_mode}")
    if not sql_schema:
        raise SystemExit("schema.sql is required for this import package.")

    schemas, schema_defs = parse_sql_schema(sql_schema)
    table_stats = build_table_stats(
        data_files,
        schemas,
        args.chunk_target_gb,
        chunked_ingest=True,
        delimiter=delimiter,
    )

    print_preflight_plan(
        table_stats=table_stats,
        namespace=namespace,
        mode=args.mode,
        bucket=bucket,
        bronze_prefix=bronze_prefix,
        progress_key=progress_key,
        confirmed=True,
    )

    spark, minio_client = initialize()
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
        silver_base=silver_base,
        mode=args.mode,
        file_ext=file_ext,
        delimiter=delimiter,
        progress_key=progress_key,
        config_key=config_key,
    )
    verify_ingest(spark, namespace, table_stats, minio_client, bucket, progress_key, silver_base)


if __name__ == "__main__":
    main()
