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

## 2026-08-25 Refreshed Harmonized Data Rebuild

Prepared a full re-import after the tracked Google Drive manifest and harmonized
data were refreshed. The live BERDL overwrite remains pending because the
off-cluster SSH tunnels on ports 1337 and 1338 were not running.

Source/model changes reconciled:

- the harmonized manifest now uses `name` and `id` rather than `filename` and
  `object_id`;
- processed metadata moved under
  `data/processed/harmonized_soil_moisture_data/`;
- downloaded harmonized CSVs remain under `harmonized_csv/`;
- the supported harmonized contract is eight columns and no longer contains
  `interval_min`;
- `time_interval_minute` was therefore removed from the observation table,
  ndarray metadata, SQL schema, and `sys_ddt_typedef`;
- replicate values now reflect the corrected harmonization factorization and
  are positive integers from 1 through 3 in the refreshed source;
- source UTC strings, including explicit offsets, are preserved;
- the established BERVO/UO mappings and kPa-to-Pa conversion are retained.

Location modeling was updated after finding 26 duplicate dataset/site groups
in the refreshed crosswalk. All groups shared exactly one harmonized UUID, but
23 reported conflicting original coordinates. The builder now emits one unique
`sdt_location` per dataset/site, omits ambiguous original coordinates, retains
the shared harmonized UUID, and records the decision in
`geolocation_resolution_method`. Fifteen observed dataset/site pairs absent
from the exact crosswalk also lacked an exact site-identifier match; the builder
created explicit coordinate-free missing-harmonized-location records rather
than inferring locations.

Refreshed local package counts:

| table | rows |
|---|---:|
| `ddt_ndarray` | 1 |
| `ddt_soil_moisture_observation` | 6,424,075 |
| `sdt_dataset` | 28 |
| `sdt_harmonized_location` | 624 |
| `sdt_location` | 1,069 |
| `sys_ddt_typedef` | 9 |
| `sys_oterm` | 2,918 |
| `sys_typedef` | 25 |

The deterministic validator at
`skills/import-wfsfa-soil-datasets-to-berdl/scripts/validate_import_package.py`
passed exact source/output transformation checks, unique-key checks, local
relationship checks, ndarray-list checks, and ontology checks. It verified
596,396 non-null water-potential values were converted from kPa to Pa.

No-write preflight:

- namespace: `bervodata_watershed_sfa_soil_moisture`;
- mode: overwrite;
- run ID: `20260825-refreshed-v05`;
- upload: approximately 1.0 GB;
- observation table: four chunks of about 1,682,209 rows;
- other seven tables: single-ingest;
- progress object:
  `tenant-general-warehouse/bervodata/datasets/watershed_sfa_soil_moisture/_ingest_progress/20260825-refreshed-v05.jsonl`;
- no BERDL state changed during preflight.

A reusable skill was created at
`skills/import-wfsfa-soil-datasets-to-berdl/` with the workflow, data model,
BERVO/UO mappings, source-change gate, validation script, unique progress-log
policy, and required live verification steps.

The repository harmonized-data tests were pointed at the current ignored
download cache rather than the removed `data/processed/harmonized_output_local/`
path. The activated source QA exposed supplied-data limitations, including 74
negative volumetric-water-content rows, two values greater than 1, one water
potential greater than 10 kPa, and 131,480 rows with all three measurement
fields empty. These values were preserved rather than silently filtered. An
explicit publish-versus-upstream-correction decision is required before the
live overwrite.

A complete focused QA pass later identified additional retained source
conditions: 17,872 water-potential values below -50,000 kPa, 234,811 rows
participating in duplicate `(datetime, site, depth, replicate)` keys across five
datasets, 6,527 exact full-row duplicates among them, and 171 groups in
`b924878...` whose observed replicate labels are nonsequential or start above
one. The tests now pin all
reviewed anomalies by file and count. They emit `SourceDataQualityWarning` for
the acknowledged snapshot but fail if a refreshed source changes those counts.
The 15 missing exact dataset/site crosswalk pairs are accepted only while each
has exactly one explicit coordinate-free missing-location record.

## 2026-08-25 Refreshed BERDL Publication

The user approved preserving the quantified source limitations and the full
eight-table overwrite. Spark readiness was proven with `SELECT 1 AS ready`.
The pre-overwrite live observation count was 5,000,226; the completed refreshed
count is 6,424,075.

Publication used run ID `20260825-refreshed-v05`. All eight live counts now
match the package: 1 ndarray, 6,424,075 observations, 28 datasets, 624
harmonized locations, 1,069 locations, 9 dynamic typedef rows, 2,918 ontology
terms, and 25 static typedef rows. The observation schema has nine columns and
no `time_interval_minute`.

The live namespace is legacy Delta in `spark_catalog`, not Iceberg. The current
generic BERDL pipeline rejected `createOrReplace` against these Delta tables,
so the importer now detects the provider and substitutes a Delta
`saveAsTable` writer without changing the namespace or storage format. It was
also updated for current ingest signatures (`silver_base` removed) and the
namespace helper's `iceberg` keyword.

Structured JSON comments were applied to all live columns and table
descriptions to all eight tables. The independent BERDL foreign-key validator
passed 4/4 declared relationships, with no declaration errors and unique
referenced targets. All 22 referenced BERVO/UO terms exist in `sys_oterm`.

The run-specific progress log has completion entries for every table. The
chunker estimated four observation chunks but emitted a final one-row fifth
chunk; cumulative and live counts are exact. The importer now republishes one
canonical eight-table config after ingest because the generic non-chunked
config otherwise omits the chunked observation table.

Eight dataset metadata YAML files were uploaded before ingest as `in_progress`
and after verification as `completed`. Live read-back of the retained source
limitations matched the local audit: 74 negative VWC rows, two VWC rows above
1, one water-potential row above 10,000 Pa, zero negative GWC/depth rows, and
131,480 rows with all three measurement values empty.
