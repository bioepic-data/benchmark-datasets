# Current WFSFA Soil-Moisture Import Notes

## 2026-08-25 refreshed source snapshot

Status: published and independently verified in BERDL on 2026-08-25.

- Repository commit inspected: `8573b8d7e39e06b1e4b9d06e86f09acf6fbe6b8c` (`fix replicate factorization`).
- Manifest: `data/processed/harmonized_soil_moisture_data/ess-dive_harmonized_soil_urls.csv`.
- Current manifest columns: index, `name`, `id`, `url`.
- Downloaded source: 19 harmonized CSVs plus `location_data_harmonized_with_uuid.csv`.
- Harmonized contract: eight columns; `interval_min` is no longer present.
- Harmonized observation rows: 6,424,075.
- Mapping registry: 28 datasets, exactly 19 marked `include`, matching the 19 files.
- Location crosswalk: 1,113 rows.

### Source changes handled

- Corrected builder metadata path after the processed-data directory reorganization.
- Corrected downloaded-data path to `harmonized_csv/`.
- Accepted the new manifest `name` field while retaining legacy `filename` fallback.
- Removed obsolete BERDL `time_interval_minute` and its ndarray typedef entry.
- Preserved explicit UTC offsets in `datetime_utc`.
- Reflected the corrected replicate factorization; refreshed values are positive integers 1–3.
- Used `exclusion_reason` from the current mapping schema.

### Location findings

- 26 dataset/site pairs had duplicate crosswalk rows (85 rows total).
- Every duplicate group resolved to exactly one harmonized UUID.
- 23 groups reported conflicting original coordinate pairs; their source coordinates are omitted in `sdt_location` and the ambiguity is recorded in `geolocation_resolution_method`.
- Three duplicate groups had only one reported coordinate pair and retain it.
- Fifteen observed pairs in dataset `ess-dive-a99be52b7a6114c-20230504T210134503379` were absent from the exact crosswalk pair set but matched one unambiguous harmonized UUID by site identifier.

### Locally built package

| Table | Rows |
|---|---:|
| `ddt_ndarray` | 1 |
| `ddt_soil_moisture_observation` | 6,424,075 |
| `sdt_dataset` | 28 |
| `sdt_harmonized_location` | 624 |
| `sdt_location` | 1,069 |
| `sys_ddt_typedef` | 9 |
| `sys_oterm` | 2,918 |
| `sys_typedef` | 25 |

Local verification included exact source/output row correspondence, unique static join targets, zero local relationship orphans, consistent ndarray lists, and exact kPa-to-Pa conversion for 596,396 non-null water-potential values.

Re-run the durable audit with:

```bash
python skills/import-wfsfa-soil-datasets-to-berdl/scripts/validate_import_package.py
```

### Ontology snapshot

- BERVO SHA-256: `07fea31b8e805b91460304671d189d78121a19f13b4055d85417519e6d53d58b`
- UO SHA-256: `a9d9fe43416f1fc8e07dc9c1cf968443f317cc0bc2f0a9c28f53505853898815`
- `sys_oterm` contains normalized `BERVO:0001810`, `BERVO:0001743`, `BERVO:0001750`, and all required UO units.

### No-write preflight

- Destination: `bervodata_watershed_sfa_soil_moisture`.
- Mode: overwrite.
- Package size: approximately 1.0 GB.
- Observation ingest: four chunks of about 1,682,209 rows at a 0.25 GB target.
- Other seven tables: single ingest each.
- Run ID: `20260825-refreshed-v05`.
- Progress: `s3a://cdm-lake/tenant-general-warehouse/bervodata/datasets/watershed_sfa_soil_moisture/_ingest_progress/20260825-refreshed-v05.jsonl`.
- Config: `s3a://cdm-lake/tenant-general-warehouse/bervodata/datasets/watershed_sfa_soil_moisture/config/watershed_sfa_soil_moisture_20260825-refreshed-v05.json`.
- The preflight changed no BERDL state.

Package fingerprints:

- `ddt_soil_moisture_observation.csv`: `8ef2a72fd3ef029ec819305ff60f1723e647a7b12cb43c02d3ae5f64f4c9d4d6`
- `schema.sql`: `baced4210052d6a27b040a9fc260a8233f4662463e2cb0f40d7fdc5bf6a31b46`
- Package disk usage: approximately 913 MiB.

### Live publication

- User confirmed the full overwrite, metadata, location-collapse policy, and
  preservation of the quantified supplied-data limitations.
- `SELECT 1 AS ready` returned `ready=1` through the off-cluster proxy.
- The pre-overwrite live counts were 1 ndarray, 5,000,226 observations, 28
  datasets, 628 harmonized locations, 1,513 locations, 10 dynamic typedef rows,
  2,918 ontology terms, and 25 static typedef rows.
- Run ID: `20260825-refreshed-v05`.
- Final live counts exactly match all eight local package counts above.
- The physical namespace remains
  `bervodata_watershed_sfa_soil_moisture`, and all tables remain external Delta
  tables under the existing `silver/` location.
- The observation table has exactly nine columns; obsolete
  `time_interval_minute` is absent.
- All eight table descriptions and every column comment were applied. Comments
  are JSON objects that retain BERVO/UO identifiers and declare four foreign
  keys in the format consumed by the BERDL relationship validator.
- The independent live relationship audit checked four relationships, passed
  all four, found no declaration errors, and confirmed all three referenced
  key targets are unique.
- All 22 BERVO/UO terms referenced by `sys_typedef` and `sys_ddt_typedef` were
  present as 22 distinct live `sys_oterm` rows.
- The run-specific progress object has 25 entries and a completion record for
  every table. The byte splitter created five actual observation chunks even
  though its estimate and final summary said four; the fifth contained one row
  and the cumulative/live total is exactly 6,424,075.
- The canonical config was republished after completion with all eight tables,
  the four relationship declarations, `storage_format: delta`, and the physical
  underscore namespace.
- Eight metadata YAML files were uploaded first as `in_progress` and then as
  `completed`. The observation completion timestamp is
  `2026-08-25T22:50:28.178483+00:00`.

The current generic BERDL pipeline is Iceberg-oriented and initially failed
against these legacy Delta tables. The importer now detects the live Delta
provider and substitutes a Delta writer while retaining the current loader,
chunker, structured-schema comments, and progress machinery. It also accepts
the current `iceberg` namespace-helper keyword and the current `run_ingest` and
`verify_ingest` signatures, which no longer accept `silver_base`.

### Unresolved harmonized-source QA

The repository test input path was updated from the removed `data/processed/harmonized_output_local/` directory to the documented ignored download cache. This caused the suite to exercise the 19 real refreshed files instead of skipping them.

The suite's first genuine failure was a negative volumetric-water-content value. A separate streaming range audit found:

- 74 negative volumetric-water-content rows: 67 in `beca0...`, five in `e67ab...`, and two in `f782...`;
- two volumetric-water-content rows greater than 1: one each in `e67ab...` and `f782...`;
- one positive water-potential value greater than 10 kPa in `4c182...`;
- zero negative gravimetric-water-content or depth rows;
- 131,480 rows with all three measurement fields empty, retained because they exist in the supplied harmonized files.

No values were filtered or corrected during BERDL package generation. The user
explicitly approved publishing them as supplied. Live read-back reproduced 74
negative volumetric-water-content rows, two values above 1, one water-potential
value above 10,000 Pa, zero negative gravimetric-water-content or depth rows,
and 131,480 rows with all three measurement fields empty.

### Remaining limitation

The source-range and empty-measurement findings above remain upstream data
limitations; publication preserves and documents them rather than asserting
that the values are scientifically valid.

The published ontology assignments are structurally consistent, but the generic
source `water_potential_kPa` is mapped to the narrower `BERVO:0001750` Soil
micropore matric water potential. The harmonization registry does not uniformly
establish the micropore qualifier. Treat this as an unresolved semantic mapping
for future ontology curation; see `data-model.md` for the full mapping caveats.
