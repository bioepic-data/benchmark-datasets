---
name: import-wfsfa-soil-datasets-to-berdl
description: Rebuild, overwrite, and verify the WFSFA harmonized soil-moisture dataset in the BERDL Lakehouse from this repository's Google Drive manifests and downloaded CSVs. Use when refreshing `bervodata_watershed_sfa_soil_moisture`, adapting the import to changed harmonized columns or mappings, regenerating its BERDL package/schema docs, auditing BERVO/UO mappings, or diagnosing its import and foreign-key relationships.
---

# Import WFSFA Soil Datasets to BERDL

Rebuild and publish the repository's harmonized WFSFA soil-moisture data without silently carrying forward a stale source schema, ontology mapping, progress log, or relationship model.

## Read first

Read both references before changing the builder or BERDL:

- [references/data-model.md](references/data-model.md) for table relationships, BERVO/UO mappings, conversions, and location-resolution policy.
- [references/current-import-notes.md](references/current-import-notes.md) for the latest verified source snapshot, counts, hashes, preflight, and known issues. Treat snapshot counts as comparison evidence, not permanent constants.

Also read `berdl_import/AGENT_LOG.md`, the current builder/importer, the tracked harmonization mapping JSON, and the URL manifest. Prefer the checked-out files over historical notes when they disagree.

## Workflow

### 1. Establish the source contract

1. Require a clean understanding of existing Git changes; preserve unrelated work.
2. Read `data/processed/harmonized_soil_moisture_data/ess-dive_harmonized_soil_urls.csv` and `sm_data_harmonization_mapping.json`.
3. Download every manifest-declared file into a staging directory, validate CSV parsing and nonzero row counts, then replace the ignored cache under `berdl_import/downloaded_data/ess-dive_wfsfa_soil_datasets/`.
4. Require exact equality among:
   - downloaded `*_harmonized.csv` dataset identifiers;
   - manifest harmonized filenames;
   - mapping entries whose `inclusion_decision` is `include`.
5. Compare the observed CSV header with `EXPECTED_HARMONIZED_COLUMNS` in the builder. If it differs, stop and explicitly update the BERDL model and this skill; never silently drop or manufacture a field.

The August 2026 manifest uses `name`, `id`, and `url`; the builder deliberately accepts legacy `filename` as a fallback.

### 2. Reconcile model changes

Use [references/data-model.md](references/data-model.md) as the semantic contract. In particular:

- Remove a BERDL field when the harmonized contract has removed it and there is no remaining evidence for it. Do not publish an all-null compatibility column without an explicit decision.
- Preserve source UTC strings, positive replicate indices, and missing values.
- Convert `water_potential_kPa` to pascals by multiplying by 1000.
- Keep one unique `sdt_location` target per `(source_dataset_id, site_id)`. If duplicate crosswalk rows have conflicting original coordinates but one shared harmonized UUID, omit the ambiguous original coordinates, retain the harmonized UUID, and record the reason.
- Do not invent a location when neither the exact pair nor an unambiguous site-to-UUID match exists; emit an explicit missing harmonized-location record.

### 3. Build and validate locally

From the repository root:

```bash
python berdl_import/scripts/build_watershed_sfa_soil_moisture_import.py
```

Require all of the following before preflight:

- `build_summary.json` counts agree with physical CSV data rows.
- All declared primary/unique keys are unique.
- Observation dataset and location references resolve.
- Source-location dataset and harmonized-location references resolve.
- Source/output row order and values agree, including the kPa-to-Pa conversion.
- `ddt_ndarray` name, term-ID, and term-name lists have equal lengths.
- Every referenced BERVO/UO term exists in `sys_oterm` with normalized CURIEs.
- `schema.sql`, `sys_typedef.csv`, and `sys_ddt_typedef.csv` agree on names and types.

Run the bundled deterministic audit (it streams the large observation table):

```bash
python skills/import-wfsfa-soil-datasets-to-berdl/scripts/validate_import_package.py
```

Run the repository harmonized-source QA suite against the downloaded cache:

```bash
python -m pytest -q
```

Treat range, crosswalk, duplicate, and empty-measurement failures as source-data decisions, not reasons to silently edit values in the BERDL builder. Quantify each failure and obtain an explicit publish/hold decision.

Regenerate and synchronize schema references:

```bash
python berdl_import/scripts/generate_watershed_sfa_soil_moisture_schema.py \
  --data-dir berdl_import/data/berdl_import/watershed_sfa_soil_moisture \
  --schema-dir berdl_import/schema
```

Copy the three generated schema Markdown files into `skills/watershed-sfa-soil-moisture-berdl-query/references/` and require `diff -q` equality.

### 4. Check the off-cluster BERDL environment

Never print credential values. Load the repository-root `.env` only into the process environment:

```bash
set -a
source .env
set +a
python /h/jmc/src/BERIL-research-observatory/scripts/berdl_env.py --check
```

The user must start missing SSH SOCKS tunnels on ports 1337 and 1338 in their own terminal. Start pproxy only after those tunnels exist. Confirm the `berdl-minio` alias without printing access or secret keys. Ensure the JupyterHub kernel is available, spawning it with `berdl-remote` if needed.

Before any write, prove Spark readiness through the proxy with `SELECT 1 AS ready`; a kernel-status message alone is insufficient.

### 5. Use a unique no-write preflight

Choose a stable run ID and reuse it for preflight and the actual import. Never reuse a prior progress key for a changed source package.

```bash
set -a
source .env
set +a
/h/jmc/src/BERIL-research-observatory/.venv-berdl/bin/python \
  berdl_import/scripts/import_watershed_sfa_soil_moisture_to_berdl.py \
  --data-dir berdl_import/data/berdl_import/watershed_sfa_soil_moisture \
  --tenant bervodata \
  --dataset watershed_sfa_soil_moisture \
  --mode overwrite \
  --chunk-target-gb 0.25 \
  --run-id <unique-run-id> \
  --preflight-only
```

Present the namespace, all table row counts, upload size, chunk plan, progress key, and schema changes. Inspect existing live tables and counts read-only. Obtain explicit user confirmation of the overwrite plan and table metadata before omitting `--preflight-only`.

### 6. Import and monitor

Before publication, run `scripts/manage_ingest_metadata.py generate` and upload the
resulting `metadata/` directory with `status: in_progress`. After publication,
download the run-specific progress JSONL, run
`scripts/manage_ingest_metadata.py finalize --progress-log <path>`, and upload the
metadata directory again. This preserves confirmed titles, descriptions, version,
source, physical namespace, and per-table completion evidence for future refreshes.

Run the same command with the confirmed run ID and without `--preflight-only`. The importer:

- reads `KBASE_AUTH_TOKEN` without printing it;
- uploads the package to the dataset's bronze path;
- overwrites tables in `bervodata_watershed_sfa_soil_moisture`;
- resumes only from the selected run-specific progress object;
- runs `SELECT 1 AS ready` before upload/ingest;
- verifies final table counts.

Do not call the import complete merely because upload or ingest returned successfully.

### 7. Verify live publication

Require live read-back evidence for every table:

1. Exact table set and row counts match `build_summary.json`.
2. Live columns and types match `schema.sql`; removed columns are absent.
3. Table and column comments contain the intended typedef/ndarray metadata.
4. Unique targets remain unique.
5. All four relationships have zero non-null orphans:
   - observations → `sdt_dataset.sdt_dataset_name`;
   - observations → `sdt_location.sdt_location_name`;
   - locations → `sdt_dataset.sdt_dataset_name`;
   - locations → `sdt_harmonized_location.sdt_harmonized_location_name`.
6. Required BERVO/UO rows, including `BERVO:0001810`, are present.
7. The run-specific progress log reports completion for every table.

Use the `berdl-query` workflow for bounded SQL and the `check-berdl-foreign-keys` workflow when the published JSON comments expose the declarations in a compatible ingest config. Otherwise run the exact anti-join and uniqueness checks above; do not retarget a failed relationship.

### 8. Leave a durable handoff

Append a dated entry to `berdl_import/AGENT_LOG.md` and update `references/current-import-notes.md` with:

- source commit and manifest schema;
- source and published counts;
- model changes and rationale;
- ontology file paths and hashes;
- run ID, progress/config paths, and completion status;
- live schema/comment/FK evidence;
- unresolved source-data limitations.

Run the skill validator after changing this skill.

## Safety

- Never expose `.env`, KBase tokens, or MinIO credentials.
- Never overwrite the existing namespace without showing the current preflight and receiving explicit confirmation.
- Never reuse an old progress log for changed source data.
- Never infer missing scientific provenance or coordinates.
- Never publish when local or live key/foreign-key checks fail.
