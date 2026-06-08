# WFSFA Soil Moisture BERDL Import Agent Log

This log records the work performed to convert the WFSFA harmonized soil moisture
files into a BERDL-ready package and import them into the BERDL Lakehouse.

## Target

- Tenant: `bervodata`
- Dataset/database: `watershed_sfa_soil_moisture`
- Spark namespace: `bervodata_watershed_sfa_soil_moisture`
- Silver path:
  `s3a://cdm-lake/tenant-general-warehouse/bervodata/datasets/watershed_sfa_soil_moisture/silver`

## Local Organization

All code and generated/import artifacts created for this workflow were moved
under `berdl_import/`.

- `berdl_import/scripts/`
  - `build_watershed_sfa_soil_moisture_import.py`
  - `import_watershed_sfa_soil_moisture_to_berdl.py`
  - `generate_watershed_sfa_soil_moisture_schema.py`
- `berdl_import/data/berdl_import/watershed_sfa_soil_moisture/`
  - generated BERDL import package
- `berdl_import/data/berdl_import/watershed_sfa_soil_moisture_sys_oterm_repair/`
  - one-table repair package used to overwrite `sys_oterm`
- `berdl_import/schema/`
  - generated Markdown schema documentation
- `berdl_import/local_logs/`
  - local BERDL ingest logs

Source WFSFA processed data are not duplicated under `berdl_import/`. The
builder reads tracked source metadata from the repository-level
`data/processed/` tree. Large downloaded external CSVs and downloaded
crosswalks are kept under `berdl_import/downloaded_data/`, which is ignored by
Git except for its README and `.gitignore`.

## Source Data

Downloaded 14 harmonized WFSFA soil moisture CSVs from the Google Drive URLs
provided in the project manifest into:

`berdl_import/downloaded_data/ess-dive_wfsfa_soil_datasets/harmonized_csv/`

Downloaded and used the harmonized location crosswalk:

`berdl_import/downloaded_data/ess-dive_wfsfa_soil_datasets/location_data_harmonized_with_uuid.csv`

Tracked source metadata used by the builder remain in:

`data/processed/ess-dive_wfsfa_soil_datasets/`

The location crosswalk has row-level `qc_flag` values by
`(source_dataset_id, site_id)`. This is why `geolocation_resolution_method` was
kept on `sdt_location` rather than `sdt_dataset`.

## Schema Decisions

The final database uses singular table names with CORAL/BERDL-style prefixes:

- `sdt_dataset`
- `sdt_harmonized_location`
- `sdt_location`
- `ddt_soil_moisture_observation`
- `ddt_ndarray`
- `sys_typedef`
- `sys_ddt_typedef`
- `sys_oterm`

Important naming and mapping decisions:

- `source_dataset_id` was represented as `sdt_dataset_name` foreign keys into
  `sdt_dataset`, not as a standalone source ID column.
- Boolean columns use `is_...` names, for example `is_imported` and
  `is_time_series`.
- Quality control flags were not exposed as a categorical `qc_flag`; the
  location resolution result is represented as `geolocation_resolution_method`
  on `sdt_location`.
- `depth_resolution_method` is dataset-level because the imported datasets each
  use a dataset-level depth mapping pattern.
- `harmonization_mapping_json` is retained in `sdt_dataset` and mapped as a
  BERVO comment-like term.
- `water_potential_kPa` was converted to pascals in
  `soil_micropore_matric_water_potential_pascal`, because the local UO source
  includes `UO:0000110` pascal and did not provide an appropriate kilopascal
  term for direct use.
- `sdt_harmonized_location` stores one row per harmonized UUID.
- `sdt_location` stores one row per dataset-specific source site and references
  `sdt_harmonized_location_name`.
- `ddt_soil_moisture_observation` references `sdt_dataset_name` and
  `sdt_location_name`.

## Ontology Work

Added `BERVO:0001810` Gravimetric water content to the local BERVO checkout
used by this workflow:

`/h/jmc/data/bioepic/chess/ontologies/bervo_github/bervo.obo`

The full `sys_oterm` repair later used these OBO sources:

- `/h/jmc/data/bioepic/chess/ontologies/bervo_github/bervo.obo`
- `/h/jmc/data/bioepic/chess/ontologies/uo/uo.obo`

Older BERVO copies were deliberately not used for the repair because they did
not contain the newly added gravimetric water content term.

## Generated Import Package

The builder generated:

`berdl_import/data/berdl_import/watershed_sfa_soil_moisture/`

Final package row counts:

| table | rows |
|---|---:|
| `ddt_ndarray` | 1 |
| `ddt_soil_moisture_observation` | 5,000,226 |
| `sdt_dataset` | 28 |
| `sdt_harmonized_location` | 628 |
| `sdt_location` | 1,513 |
| `sys_ddt_typedef` | 10 |
| `sys_oterm` | 2,918 |
| `sys_typedef` | 25 |

The generated `build_summary.json` records the OBO sources and table counts.

## BERDL Import

Imported the generated package into:

`bervodata_watershed_sfa_soil_moisture`

The observation table was ingested in three chunks. Final verification reported:

| table | verified rows |
|---|---:|
| `ddt_ndarray` | 1 |
| `ddt_soil_moisture_observation` | 5,000,226 |
| `sdt_dataset` | 28 |
| `sdt_harmonized_location` | 628 |
| `sdt_location` | 1,513 |
| `sys_ddt_typedef` | 10 |
| `sys_oterm` | 25 initially, then repaired to 2,918 |
| `sys_typedef` | 25 |

During import, the importer was patched to:

- create/use the underscore namespace
  `bervodata_watershed_sfa_soil_moisture`, matching BERDL Spark conventions;
- create the namespace at the tenant dataset location rather than the default
  user SQL warehouse;
- put the BERIL virtualenv `bin/` directory on `PATH` so `berdl-remote` could be
  found by subprocesses.

## `sys_oterm` Repair

The first import loaded only the terms directly referenced by this dataset.
After review, `sys_oterm` was corrected to include all terms from the active
BERVO and UO OBO sources.

Changes made:

- `build_watershed_sfa_soil_moisture_import.py` now parses full OBO files.
- BERVO IDs from the OBO are normalized to `BERVO:...` CURIE form.
- `sys_oterm` increased from 25 rows to 2,918 rows.
- A one-table repair package was generated at:
  `berdl_import/data/berdl_import/watershed_sfa_soil_moisture_sys_oterm_repair/`
- `import_watershed_sfa_soil_moisture_to_berdl.py` gained `--progress-key` and
  `--config-key` options so the repair could use a separate progress log.

The live BERDL repair overwrote only:

`bervodata_watershed_sfa_soil_moisture.sys_oterm`

Verification after repair:

- Expected rows: 2,918
- Delta rows: 2,918
- Status: OK

The observation table was not reimported during the `sys_oterm` repair.

## Schema Documentation

Generated a `schema/` directory modeled after
`/h/jmc/src/BERDL-ENIGMA-CORAL/schema`.

Generated files:

- `berdl_import/schema/README.md`
- `berdl_import/schema/ddt_ndarray_table.md`
- `berdl_import/schema/sys_ddt_typedef_table.md`
- `berdl_import/schema/watershed_sfa_soil_moisture_schema.md`

The schema generator reads:

- `schema.sql`
- `sys_typedef.csv`
- `sys_ddt_typedef.csv`
- generated table CSVs
- `build_summary.json`

and emits Markdown with table schemas, row counts, and sample rows.

## Query Skill

Created a repository-local Codex skill:

`skills/watershed-sfa-soil-moisture-berdl-query/`

The skill follows the same pattern as `enigma-berdl-query`: it includes a
`SKILL.md` workflow and bundled generated schema references:

- `references/watershed_sfa_soil_moisture_schema.md`
- `references/ddt_ndarray_table.md`
- `references/sys_ddt_typedef_table.md`

It was also installed locally at:

`/h/jmc/.codex/skills/watershed-sfa-soil-moisture-berdl-query/`

## Validation Performed

- Rebuilt the full local import package after adding OBO-backed `sys_oterm`.
- Confirmed generated `sys_oterm.csv` includes:
  - `BERVO:0001810`
  - `UO:0000110`
  - `UO:0000233`
- Confirmed generated `sys_oterm.csv` contains no lowercase
  `bervo:BERVO_...` identifiers.
- Ran `py_compile` on generated Python scripts after edits.
- BERDL importer verified row counts after initial import.
- BERDL importer verified row counts after `sys_oterm` repair.
- Generated schema Markdown and verified key row counts in the full schema.

## Re-run Commands

From this repository root:

```bash
python berdl_import/scripts/build_watershed_sfa_soil_moisture_import.py
```

```bash
python berdl_import/scripts/generate_watershed_sfa_soil_moisture_schema.py \
  --data-dir berdl_import/data/berdl_import/watershed_sfa_soil_moisture \
  --schema-dir berdl_import/schema
```

The BERDL import command requires BERDL network/Spark/MinIO access:

```bash
/h/jmc/src/BERIL-research-observatory/.venv-berdl/bin/python \
  berdl_import/scripts/import_watershed_sfa_soil_moisture_to_berdl.py \
  --data-dir berdl_import/data/berdl_import/watershed_sfa_soil_moisture \
  --chunk-target-gb 0.25
```
