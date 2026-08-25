# WFSFA Soil-Moisture BERDL Data Model

## Namespace and table roles

Publish into Spark namespace `bervodata_watershed_sfa_soil_moisture`, backed by:

`s3a://cdm-lake/tenant-general-warehouse/bervodata/datasets/watershed_sfa_soil_moisture/silver`

Tables:

- `sdt_dataset`: all mapping-registry datasets, including excluded packages and import decisions.
- `sdt_harmonized_location`: one row per harmonized physical-location UUID.
- `sdt_location`: one unique row per source `(dataset, site)` used as the observation FK target.
- `ddt_soil_moisture_observation`: combined long-form measurement rows.
- `ddt_ndarray`: semantic description of the observation brick/table.
- `sys_typedef`: static-table fields and BERVO/UO metadata.
- `sys_ddt_typedef`: observation dimensions, variables, units, and foreign keys.
- `sys_oterm`: full current BERVO and UO term sets, not only directly referenced terms.

## Storage-provider compatibility

The live underscore namespace is a legacy `spark_catalog` namespace whose eight
external tables use the Delta provider at the `silver/` paths above. Preserve
that physical namespace and provider during a refresh. Do not silently migrate
these tables to the newer dotted Polaris/Iceberg layout.

The generic BERDL ingest library migrated to Iceberg in May 2026. Its
`DataFrame.writeTo(...).createOrReplace()` path cannot overwrite these existing
Delta tables and fails with `UNSUPPORTED_FEATURE.TABLE_OPERATION`. The bundled
importer therefore detects the live providers and substitutes a Delta
`saveAsTable` writer while retaining the current BERDL source loader, schema
alignment, chunking, comment application, and run-specific progress log.

After ingest, publish a canonical config containing all eight tables. The
generic non-chunked batch config omits the chunked observation table, whose
schema otherwise exists only in per-chunk configs. The canonical config records
`storage_format: delta` and the physical underscore namespace.

Treat the preflight chunk count as an estimate. In the 2026-08-25 run, a four-
chunk estimate produced four full chunks plus a final one-row fifth chunk at a
newline boundary. Completion is determined from cumulative rows, live counts,
and actual progress entries, not the displayed chunk denominator alone.

## Relationships

| Source | Target | Required property |
|---|---|---|
| `ddt_soil_moisture_observation.sdt_dataset_name` | `sdt_dataset.sdt_dataset_name` | target unique, zero orphans |
| `ddt_soil_moisture_observation.sdt_location_name` | `sdt_location.sdt_location_name` | target unique, zero orphans |
| `sdt_location.sdt_dataset_name` | `sdt_dataset.sdt_dataset_name` | target unique, zero orphans |
| `sdt_location.sdt_harmonized_location_name` | `sdt_harmonized_location.sdt_harmonized_location_name` | target unique, zero orphans |

The Delta tables do not enforce these relationships. Validate them after every overwrite.

## Observation mappings

| Harmonized source | BERDL column | Spark type | BERVO type | Unit | Transformation |
|---|---|---|---|---|---|
| filename dataset identifier | `sdt_dataset_name` | `STRING` | `BERVO:8000528` Identifier | none | Strip `_harmonized.csv`; FK to dataset |
| `(dataset, site_id)` | `sdt_location_name` | `STRING` | `BERVO:8000394` Location and `BERVO:8000528` Identifier | none | Safe composite name; FK to location |
| `datetime_UTC` | `datetime_utc` | `STRING` | `BERVO:8000240` DateTime | none | Preserve the source ISO-8601 UTC string, including offset |
| `depth_m` | `depth_below_soil_surface_meter` | `DOUBLE` | `BERVO:8000069` Depth | `UO:0000008` meter | Identity |
| `replicate` | `replicate_series_count_unit` | `BIGINT` | `BERVO:8000237` Count | `UO:0000189` count unit | Positive per-observation replicate index |
| `is_timeseries` | `is_time_series` | `BOOLEAN` | `BERVO:8000300` Time series | none | Normalize true/false spelling |
| `volumetric_water_content_m3_m3` | `volumetric_water_content_ratio_unit` | `DOUBLE` | `BERVO:0001743` Volumetric water content | `UO:0000190` ratio unit | Identity |
| `gravimetric_water_content_gH2O_gs` | `gravimetric_water_content_ratio_unit` | `DOUBLE` | `BERVO:0001810` Gravimetric water content | `UO:0000190` ratio unit | Identity; mass ratio represented by a dimensionless ratio unit |
| `water_potential_kPa` | `soil_micropore_matric_water_potential_pascal` | `DOUBLE` | `BERVO:0001750` Soil micropore matric water potential | `UO:0000110` pascal | Multiply by 1000 |

`interval_min` and BERDL `time_interval_minute` were present in the earlier import contract but are absent from the August 2026 eight-column harmonized contract. They were removed rather than retained as an all-null field.

### Ontology-mapping caveats

The assignments above are mechanically deterministic, but ontology-term presence does not by itself prove semantic equivalence. Reassess these mappings when the source contract or BERVO changes:

- `water_potential_kPa` is generic in several source packages, while `BERVO:0001750` is the narrower **Soil micropore matric water potential**. Some source variables explicitly say matric potential, but the harmonization registry does not uniformly establish the micropore qualifier. Treat this as the material unresolved semantic mapping; prefer a future generic soil-water-potential BERVO term if one becomes available, or preserve a documented per-source qualification.
- `sdt_location_name` intentionally has two roles: `BERVO:8000394` Location describes the logical dimension, while `BERVO:8000528` Identifier describes the stored object-reference value. This is not a competing assignment, but consumers need both typedef layers to interpret it correctly.
- Static mappings such as `harmonization_mapping_json` to `BERVO:8000305` Comment and `is_imported` to `BERVO:8000358` Presence are pragmatic generic approximations. The column names and JSON comments carry semantics that these BERVO terms do not fully express.
- `BERVO:8000528` Identifier, `BERVO:8000237` Count, `BERVO:8000303` Method, and `BERVO:8000391` Link are deliberately reused across contextual fields. Do not infer field-specific semantics from those generic terms alone.
- Both gravimetric and volumetric water content use dimensionless `UO:0000190` ratio unit. Their BERVO terms and column names, not the unit, distinguish mass ratio from volume ratio.

Do not silently replace an approximate mapping during a refresh. Record the source evidence, active ontology version, candidate terms, and compatibility impact before changing published identifiers or column names.

## Static-object modeling

- Use the ESS-DIVE package identifier as `sdt_dataset_name`; retain all mapping JSON verbatim in `harmonization_mapping_json`.
- Keep the DOI as a link and retain both included and excluded packages so import decisions remain auditable.
- Keep `depth_resolution_method` on the dataset because mappings describe depth transformation at dataset level.
- Keep geolocation resolution on `sdt_location` because `qc_flag` and source evidence vary by dataset/site.
- Represent the cross-dataset physical location through `sdt_harmonized_location_name`, normally the supplied UUID.
- Treat `sdt_dataset_name`, `sdt_location_name`, and `sdt_harmonized_location_name` as unique join targets even though Delta does not enforce uniqueness.

## Duplicate and missing location policy

The crosswalk may contain multiple rows for one `(source_dataset_id, site_id)`.

1. Require all rows in a duplicate group to resolve to no more than one nonempty harmonized UUID. Multiple UUIDs are a hard error.
2. Emit one `sdt_location` row per dataset/site.
3. If the group has exactly one reported original coordinate pair, retain it.
4. If it has conflicting original coordinate pairs, omit source latitude/longitude because observations contain no discriminator. Retain the shared harmonized UUID and explain the conflict in `geolocation_resolution_method`.
5. For an observed pair absent from the crosswalk, reuse a harmonized UUID only when the site identifier maps unambiguously to one UUID elsewhere.
6. Otherwise create an explicit missing harmonized-location record with blank coordinates.

This preserves query-safe keys without guessing which conflicting coordinate belongs to an observation.

## Ontology handling

Build `sys_oterm` from the active files:

- `/h/jmc/data/bioepic/chess/ontologies/bervo_github/bervo.obo`
- `/h/jmc/data/bioepic/chess/ontologies/uo/uo.obo`

Normalize local `bervo:BERVO_...` identifiers to `BERVO:...`. Require `BERVO:0001810`; older BERVO copies lacked the gravimetric-water-content term. Record current ontology hashes in the import notes because these external files can change independently of this repository.

## Naming conventions

- Use `sdt_` for static object tables, `ddt_` for dynamic/ndarray data, and `sys_` for type/ontology metadata.
- Use singular table names.
- Use `is_...` for booleans.
- Include units in numeric BERDL column names where practical.
- Preserve source provenance in `original_csv_string` and transformation comments.
