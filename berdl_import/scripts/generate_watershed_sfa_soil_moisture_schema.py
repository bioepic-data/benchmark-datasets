#!/usr/bin/env python3
"""Generate schema markdown for the WFSFA soil moisture BERDL package."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "data/berdl_import/watershed_sfa_soil_moisture"
DEFAULT_SCHEMA_DIR = ROOT / "schema"
DATABASE_NAME = "bervodata_watershed_sfa_soil_moisture"
FULL_SCHEMA_FILE = "watershed_sfa_soil_moisture_schema.md"

TABLE_DESCRIPTIONS = {
    "ddt_ndarray": "Metadata for the WFSFA soil moisture observation array.",
    "sys_ddt_typedef": "Column definitions for the WFSFA soil moisture dynamic data table.",
    "ddt_soil_moisture_observation": "Combined harmonized WFSFA soil moisture observations from imported ESS-DIVE packages.",
    "sdt_dataset": "Dataset-level metadata for imported and reviewed ESS-DIVE WFSFA soil moisture packages.",
    "sdt_harmonized_location": "Harmonized location records keyed by harmonized location UUID.",
    "sdt_location": "Dataset-specific source locations mapped to harmonized locations.",
    "sys_oterm": "Ontology terms from the BERVO and UO sources used by this database.",
    "sys_typedef": "Column definitions for static data tables in this database.",
}

SYS_TABLE_COMMENTS = {
    "ddt_ndarray_id": "Unique identifier for the dynamic data array.",
    "ddt_ndarray_name": "Human-readable dynamic data array name.",
    "ddt_ndarray_description": "Description of the dynamic data array.",
    "ddt_ndarray_type_sys_oterm_id": "Ontology term CURIE for the dynamic data array type.",
    "ddt_ndarray_type_sys_oterm_name": "Ontology term name for the dynamic data array type.",
    "ddt_ndarray_shape": "Logical array shape.",
    "ddt_ndarray_dimension_names": "Comma-separated logical dimension names.",
    "ddt_ndarray_dimension_types_sys_oterm_id": "Comma-separated ontology term CURIEs for dimension types.",
    "ddt_ndarray_dimension_types_sys_oterm_name": "Comma-separated ontology term names for dimension types.",
    "ddt_ndarray_dimension_variable_names": "Comma-separated dimension variable column names.",
    "ddt_ndarray_dimension_variable_types_sys_oterm_id": "Comma-separated ontology term CURIEs for dimension variable types.",
    "ddt_ndarray_dimension_variable_types_sys_oterm_name": "Comma-separated ontology term names for dimension variable types.",
    "ddt_ndarray_variable_names": "Comma-separated measured or non-dimension variable names.",
    "ddt_ndarray_variable_types_sys_oterm_id": "Comma-separated ontology term CURIEs for measured or non-dimension variable types.",
    "ddt_ndarray_variable_types_sys_oterm_name": "Comma-separated ontology term names for measured or non-dimension variable types.",
    "ddt_ndarray_metadata": "JSON metadata for the dynamic data array.",
    "superceded_by_ddt_ndarray_id": "Replacement dynamic data array identifier, if superseded.",
    "sys_oterm_id": "Ontology term CURIE.",
    "parent_sys_oterm_id": "Parent ontology term CURIE.",
    "sys_oterm_ontology": "Ontology namespace for the term.",
    "sys_oterm_name": "Ontology term name.",
    "sys_oterm_synonyms": "JSON array of ontology term synonyms.",
    "sys_oterm_definition": "Ontology term definition.",
    "sys_oterm_links": "JSON array of ontology xrefs or links.",
    "sys_oterm_properties": "JSON object containing additional ontology properties.",
    "type_name": "Static data type name.",
    "field_name": "Source field name.",
    "berdl_column_name": "BERDL column name.",
    "scalar_type": "Logical scalar type.",
    "is_required": "Whether the field is required.",
    "is_pk": "Whether the field is a primary key.",
    "is_upk": "Whether the field is a unique public key.",
    "fk": "Referenced static data type or table.",
    "constraint": "Additional field constraint.",
    "comment": "Human-readable field comment.",
    "units_sys_oterm_id": "Unit ontology term CURIE.",
    "units_sys_oterm_name": "Unit ontology term name.",
    "type_sys_oterm_id": "Field type ontology term CURIE.",
    "type_sys_oterm_name": "Field type ontology term name.",
    "unit_sys_oterm_id": "Unit ontology term CURIE.",
    "unit_sys_oterm_name": "Unit ontology term name.",
    "dimension_number": "Logical dimension number.",
    "dimension_oterm_id": "Dimension ontology term CURIE.",
    "dimension_oterm_name": "Dimension ontology term name.",
    "variable_number": "Logical variable number.",
    "variable_oterm_id": "Variable ontology term CURIE.",
    "variable_oterm_name": "Variable ontology term name.",
    "original_csv_string": "Original source or mapping string used to define the column.",
    "berdl_column_data_type": "BERDL dynamic data column role or physical data type.",
    "foreign_key": "Foreign key target for object reference columns.",
}


def markdown_cell(value: Any) -> str:
    if value is None:
        rendered = "NULL"
    elif isinstance(value, (list, dict)):
        rendered = json.dumps(value, ensure_ascii=True)
    else:
        rendered = str(value)
        if rendered == "":
            rendered = "NULL"
    rendered = rendered.replace("\r\n", "\n").replace("\r", "\n")
    if "\n" in rendered:
        rendered = f"\"{rendered.replace('\n', '<br>')}\""
    return rendered.replace("|", "\\|")


def parse_schema_sql(path: Path) -> dict[str, list[dict[str, Any]]]:
    text = path.read_text(encoding="utf-8")
    tables: dict[str, list[dict[str, Any]]] = {}
    pattern = re.compile(r"CREATE TABLE\s+(\w+)\s*\((.*?)\);", re.DOTALL | re.IGNORECASE)
    for match in pattern.finditer(text):
        table_name = match.group(1)
        columns = []
        for raw_line in match.group(2).splitlines():
            line = raw_line.strip().rstrip(",")
            if not line:
                continue
            parts = line.split()
            column = parts[0].strip('"')
            data_type = parts[1] if len(parts) > 1 else "STRING"
            columns.append({
                "column": column,
                "type": data_type.lower(),
                "nullable": True,
                "comment": "",
            })
        tables[table_name] = columns
    return tables


def read_csv_rows(path: Path, limit: int | None = None) -> tuple[list[str], list[list[str]], int]:
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            return [], [], 0
        rows = []
        count = 0
        for row in reader:
            count += 1
            if limit is None or len(rows) < limit:
                rows.append(row)
        return header, rows, count


def read_dicts(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        return list(csv.DictReader(handle))


def load_summary(data_dir: Path) -> dict[str, Any]:
    path = data_dir / "build_summary.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def static_type_to_table(type_name: str) -> str:
    return {
        "Dataset": "sdt_dataset",
        "Harmonized_Location": "sdt_harmonized_location",
        "Location": "sdt_location",
    }.get(type_name, type_name)


def apply_metadata(schema: dict[str, list[dict[str, Any]]], data_dir: Path) -> None:
    sys_typedef_path = data_dir / "sys_typedef.csv"
    if sys_typedef_path.exists():
        for row in read_dicts(sys_typedef_path):
            table_name = static_type_to_table(row.get("type_name", ""))
            column_name = row.get("berdl_column_name", "")
            for coldef in schema.get(table_name, []):
                if coldef["column"] == column_name:
                    coldef["nullable"] = row.get("is_required", "").lower() != "true"
                    coldef["comment"] = typedef_comment(row)

    sys_ddt_typedef_path = data_dir / "sys_ddt_typedef.csv"
    if sys_ddt_typedef_path.exists():
        for row in read_dicts(sys_ddt_typedef_path):
            column_name = row.get("berdl_column_name", "")
            for coldef in schema.get("ddt_soil_moisture_observation", []):
                if coldef["column"] == column_name:
                    coldef["comment"] = ddt_typedef_comment(row)

    for table_columns in schema.values():
        for coldef in table_columns:
            if not coldef.get("comment"):
                coldef["comment"] = SYS_TABLE_COMMENTS.get(coldef["column"], "")

    required_columns = {
        "ddt_ndarray": {"ddt_ndarray_id"},
        "sys_ddt_typedef": {"ddt_ndarray_id", "berdl_column_name"},
        "sys_oterm": {"sys_oterm_id", "sys_oterm_ontology"},
        "sys_typedef": {"type_name", "field_name", "berdl_column_name"},
    }
    for table_name, column_names in required_columns.items():
        for coldef in schema.get(table_name, []):
            if coldef["column"] in column_names:
                coldef["nullable"] = False


def typedef_comment(row: dict[str, str]) -> str:
    parts = [row.get("comment", "")]
    if row.get("type_sys_oterm_id"):
        parts.append(f"type={row['type_sys_oterm_name']} <{row['type_sys_oterm_id']}>")
    if row.get("units_sys_oterm_id"):
        parts.append(f"unit={row['units_sys_oterm_name']} <{row['units_sys_oterm_id']}>")
    if row.get("fk"):
        parts.append(f"foreign_key={row['fk']}")
    return "; ".join(part for part in parts if part)


def ddt_typedef_comment(row: dict[str, str]) -> str:
    parts = [row.get("comment", "")]
    if row.get("variable_oterm_id"):
        parts.append(f"variable={row['variable_oterm_name']} <{row['variable_oterm_id']}>")
    if row.get("dimension_oterm_id"):
        parts.append(f"dimension={row['dimension_oterm_name']} <{row['dimension_oterm_id']}>")
    if row.get("unit_sys_oterm_id"):
        parts.append(f"unit={row['unit_sys_oterm_name']} <{row['unit_sys_oterm_id']}>")
    if row.get("foreign_key"):
        parts.append(f"foreign_key={row['foreign_key']}")
    return "; ".join(part for part in parts if part)


def write_schema_table(handle, columns: list[dict[str, Any]], include_comments: bool) -> None:
    if include_comments:
        handle.write("| Column Name | Data Type | Nullable | Comment |\n")
        handle.write("|-------------|-----------|----------|----------|\n")
        for coldef in columns:
            handle.write(
                "| "
                + " | ".join([
                    markdown_cell(coldef["column"]),
                    markdown_cell(coldef["type"]),
                    markdown_cell("Yes" if coldef.get("nullable", True) else "No"),
                    markdown_cell(coldef.get("comment", "")),
                ])
                + " |\n"
            )
    else:
        handle.write("| Column Name | Data Type | Nullable |\n")
        handle.write("|-------------|-----------|----------|\n")
        for coldef in columns:
            handle.write(
                "| "
                + " | ".join([
                    markdown_cell(coldef["column"]),
                    markdown_cell(coldef["type"]),
                    markdown_cell("Yes" if coldef.get("nullable", True) else "No"),
                ])
                + " |\n"
            )


def write_rows(handle, header: Iterable[str], rows: list[list[str]]) -> None:
    header = list(header)
    if not rows:
        handle.write("*Table is empty*\n")
        return
    handle.write("| " + " | ".join(markdown_cell(column) for column in header) + " |\n")
    handle.write("|" + "|".join("---" for _ in header) + "|\n")
    width = len(header)
    for row in rows:
        padded = row[:width] + [""] * max(0, width - len(row))
        handle.write("| " + " | ".join(markdown_cell(value) for value in padded) + " |\n")


def row_count_for(table_name: str, data_dir: Path, summary: dict[str, Any], counted: int) -> int:
    if table_name in summary:
        return int(summary[table_name])
    return counted


def export_table(
    schema: dict[str, list[dict[str, Any]]],
    data_dir: Path,
    schema_dir: Path,
    table_name: str,
) -> None:
    data_path = data_dir / f"{table_name}.csv"
    header, rows, row_count = read_csv_rows(data_path)
    with (schema_dir / f"{table_name}_table.md").open("w", encoding="utf-8", newline="") as handle:
        handle.write(f"# Table: {DATABASE_NAME}.{table_name}\n\n")
        description = TABLE_DESCRIPTIONS.get(table_name, "")
        if description:
            handle.write(f"**Description:** {markdown_cell(description)}\n\n")
        handle.write("## Schema\n\n")
        write_schema_table(handle, schema[table_name], include_comments=False)
        handle.write("\n")
        handle.write(f"**Total Rows:** {row_count}\n\n")
        handle.write("## Data\n\n")
        write_rows(handle, header, rows)


def export_database_schema(
    schema: dict[str, list[dict[str, Any]]],
    data_dir: Path,
    schema_dir: Path,
    sample_rows: int,
) -> None:
    summary = load_summary(data_dir)
    ordered_tables = [
        "ddt_ndarray",
        "sys_ddt_typedef",
        "ddt_soil_moisture_observation",
        "sdt_dataset",
        "sdt_harmonized_location",
        "sdt_location",
        "sys_oterm",
        "sys_typedef",
    ]
    with (schema_dir / FULL_SCHEMA_FILE).open("w", encoding="utf-8", newline="") as handle:
        handle.write(f"# Database Schema: {DATABASE_NAME}\n\n")
        handle.write(f"Total Tables: {len(ordered_tables)}\n\n")
        handle.write("---\n\n")
        for table_name in ordered_tables:
            data_path = data_dir / f"{table_name}.csv"
            header, samples, counted = read_csv_rows(data_path, sample_rows)
            handle.write(f"## Table: {table_name}\n\n")
            description = TABLE_DESCRIPTIONS.get(table_name, "")
            if description:
                handle.write(f"**Table Description:** {markdown_cell(description)}\n\n")
            handle.write("### Schema\n\n")
            write_schema_table(handle, schema[table_name], include_comments=True)
            handle.write("\n")
            row_count = row_count_for(table_name, data_dir, summary, counted)
            handle.write(f"**Total Rows:** {row_count}\n\n")
            handle.write(f"### Sample Data ({sample_rows} rows)\n\n")
            write_rows(handle, header, samples)
            handle.write("\n---\n\n")


def write_readme(schema_dir: Path) -> None:
    content = f"""# Schema

This directory stores schema markdown for the WFSFA soil moisture BERDL database.

## Generate or refresh

From the repository root:

```bash
python berdl_import/scripts/generate_watershed_sfa_soil_moisture_schema.py \\
  --data-dir berdl_import/data/berdl_import/watershed_sfa_soil_moisture \\
  --schema-dir berdl_import/schema
```

The generated files are `ddt_ndarray_table.md`,
`sys_ddt_typedef_table.md`, and `{FULL_SCHEMA_FILE}`.
"""
    (schema_dir / "README.md").write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--schema-dir", type=Path, default=DEFAULT_SCHEMA_DIR)
    parser.add_argument("--sample-rows", type=int, default=5)
    args = parser.parse_args()

    schema = parse_schema_sql(args.data_dir / "schema.sql")
    apply_metadata(schema, args.data_dir)

    args.schema_dir.mkdir(parents=True, exist_ok=True)
    write_readme(args.schema_dir)
    export_table(schema, args.data_dir, args.schema_dir, "ddt_ndarray")
    export_table(schema, args.data_dir, args.schema_dir, "sys_ddt_typedef")
    export_database_schema(schema, args.data_dir, args.schema_dir, args.sample_rows)
    print(f"Wrote schema markdown to {args.schema_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
