---
name: watershed-sfa-soil-moisture-berdl-query
description: Query WFSFA watershed SFA soil moisture data in BERDL using generated schema references; use when answering questions about bervodata_watershed_sfa_soil_moisture tables, harmonized soil moisture observations, datasets, locations, ontology mappings, or composing BERDL queries that must adhere to the current table and column list.
---

# Watershed SFA Soil Moisture BERDL Query

## Overview

Use this skill to answer WFSFA watershed SFA soil moisture questions by
querying the BERDL database `bervodata_watershed_sfa_soil_moisture` and using
only the generated schema references bundled with this skill for table and
column names.

The full schema reference is small enough to inspect directly, but still prefer
searching for the relevant table or column first.

## Required References

- `references/watershed_sfa_soil_moisture_schema.md` for the complete generated
  table/column list, comments, row counts, and sample rows.
- `references/ddt_ndarray_table.md` for the full `ddt_ndarray` extract that
  defines the observation array.
- `references/sys_ddt_typedef_table.md` for the full `sys_ddt_typedef` extract
  when mapping observation columns, dimensions, variables, units, and foreign
  keys.

## Finding Schema Details

- List table sections with:
  `rg -n "^## Table:" references/watershed_sfa_soil_moisture_schema.md`
- Find a specific table with:
  `rg -n "^## Table: <table>$" references/watershed_sfa_soil_moisture_schema.md`
- Search by column, term, or unit with:
  `rg -n "<column_or_term>" references/*.md`

## Tables

Core tables:

- `ddt_soil_moisture_observation`: 5,000,226 harmonized observation rows.
- `sdt_dataset`: dataset-level metadata and import decisions.
- `sdt_location`: dataset-specific source sites and geolocation resolution
  methods.
- `sdt_harmonized_location`: harmonized location UUIDs and harmonized
  coordinates.

Metadata tables:

- `ddt_ndarray`: logical array metadata for the observation table.
- `sys_ddt_typedef`: observation column definitions, dimensions, variables,
  units, and foreign keys.
- `sys_typedef`: static table column definitions and BERVO mappings.
- `sys_oterm`: full BERVO and UO ontology snapshot loaded for this database.

## Query Workflow

1. Locate the relevant table section in
   `references/watershed_sfa_soil_moisture_schema.md`.
2. Confirm exact table and column names before composing a query.
3. For observation-column semantics, inspect
   `references/sys_ddt_typedef_table.md`.
4. Build BERDL MCP API queries using only schema-listed tables and columns.
5. Keep `limit <= 1000` for interactive results; summarize or aggregate large
   results instead of returning many rows.

## BERDL MCP API Usage

- Base URL: `https://hub.berdl.kbase.us/apis/mcp`
- Auth: `Authorization: Bearer $KB_AUTH_TOKEN`
- Database: `bervodata_watershed_sfa_soil_moisture`

Common endpoints:

- List tables: `POST /delta/databases/tables/list`
- Table schema: `POST /delta/databases/tables/schema`
- Count rows: `POST /delta/tables/count`
- Query: `POST /delta/tables/select`

## Join Guidance

- Join `ddt_soil_moisture_observation.sdt_dataset_name` to
  `sdt_dataset.sdt_dataset_name`.
- Join `ddt_soil_moisture_observation.sdt_location_name` to
  `sdt_location.sdt_location_name`.
- Join `sdt_location.sdt_harmonized_location_name` to
  `sdt_harmonized_location.sdt_harmonized_location_name`.
- Use `sdt_location.geolocation_resolution_method` for row-level/site-level
  coordinate provenance; it can vary within a dataset.

## Guardrails

- Do not guess table or column names; use the bundled schema references.
- Do not use the downloaded local CSVs as the data source for user questions
  unless the user explicitly asks for local-file inspection.
- Treat `sys_oterm` as a full ontology snapshot, not as a list of only terms
  referenced by the dataset.
- Remember that water potential values were converted from kilopascals to
  pascals in `soil_micropore_matric_water_potential_pascal`.
