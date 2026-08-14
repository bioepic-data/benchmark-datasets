# WFSFA Harmonized Soil Moisture Data 
*Version 0.5-beta – 2026‑08‑11*  

---

## Table of Contents  

1. [Project Overview](#project-overview)  
2. [Data Summary](#data-summary)  
3. [Directory Structure](#directory-structure)  
4. [File Descriptions](#file-descriptions)  
5. [Harmonized Variable Definitions](#harmonized-variable-definitions)  
6. [Data‑Processing Workflow](#data‑processing-workflow)  
7. [Location Harmonization and UUID Assignment](#location-harmonization-and-uuid-assignment)  
8. [JSON Mapping Schema](#json-mapping-schema)  
9. [Usage Examples](#usage-examples)  
10. [Known Issues & Limitations](#known-issues--limitations)  
11. [Citation & Acknowledgments](#citation--acknowledgments)  
12. [Related References](#related-references)  
13. [License](#license)  
14. [Contact](#contact)  
15. [Version History](#version-history)

---

## Dataset overview

The **Watershed Function Science Focus Area (WSFSA) Harmonized Soil Moisture Dataset** provides a curated, standardized set of soil‑moisture observations derived from WFSFA-associated data packages archived on ESS-DIVE. This AI-ready datastet enables straightforward data aggregation, time‑series analysis, cross-site comparison, and benchmarking for hydrological and terrestrial ecosystem models.

- **Objectives:** Convert heterogeneous soil‑moisture datasets from the East River Watershed into a common “long” format with consistent variable names, units, and metadata. Associate all measurement locations with a harmonized set of latitude and longitude coordinates.

- **Scope (as of 2026‑04-06):**  
  - 1415 ESS‑DIVE data packages exist for the watershed.  
  - 189 packages are associated with the WFSFA or are derived from observations in the East River area.  
  - 28 packages are candidates containing soil moisture measurements. 
  - 27 packages have been processed as of 2026-05-12
  - 19 packages contain valid soil moisture data
  - 8 are prior versions of other datasets included in the final harmonization or contain duplicated data from another package. 
---

## Data Summary  

| Asset | Description | Quantity | Format |
|-------|-------------|----------|--------|
| **Source sub‑directories** | Raw ESS‑DIVE packages (original files) | 25 directories; one per source package | Mixed (CSV, TXT, XLSX, JSON, etc.) |
| **Harmonized CSVs** | One per source package, merged, transformed, and reshaped to long format | 8 files | CSV |
| **Location metadata** | Consolidated site‑level geospatial and identifier data for all packages | 1 file | CSV |
| **Mapping JSON** | Detailed mapping of original variable names → harmonized variables, including transformations | 1 file | JSON |

All files are stored under the data package root (see the [Directory Structure](#directory-structure) section).

---

## Directory Structure  

```
.
├── ess-dive_wfsfa_soil_datasets/              --> 25 sub‑folders, each named by the source package ID
│   ├── ess-dive-<package_id>/                 --> raw files as downloaded from ESS‑DIVE
├── ess-dive-*_harmonized.csv                  --> 13 CSV files, one per harmonized package
│   ├── ess-dive-<package_id>_harmonized.csv   
│   └── …
├── location_data_harmonized_with_uuid.csv     --> Single CSV containing site‑level metadata
├── harmonize_ess-dive_soilmoisture_data       --> Reproducible R script documenting all data transformations
└── sm_data_harmonization_mapping.json         --> JSON describing variable mappings & transformations
```

*The complete directory tree can be visualized with `tree -L 2 .` on a Unix‑like system.*

---

## File Descriptions  

### 1. `ess-dive_soil_datasets/`  

Contains the original ESS‑DIVE download for each of the 25 source packages. The sub‑folders preserve the original file hierarchy (data payloads, ancillary metadata, documentation, etc.).  

### 2. `ess-dive-*_harmonized.csv`  

Each file corresponds to a single source package that has been processed and harmonized to the standard schema. Individual files can be merged with simple row concatenation; they are stored separately for memory efficiency. Rows are **observations**; columns are the **harmonized variables** listed below. The schema is shared across all files. Files are named following the pattern:  

```
ess-dive-<ESS‑DIVE‑package‑identifier>_harmonized.csv
```

#### Harmonized Variable Definitions  

| Variable | Type | Units | Description |
|----------|------|-------|-------------|
| `datetime_UTC` | `string` (ISO‑8601) | – | Date‑time of observation in UTC, formatted `YYYY‑MM‑DD HH:MM:SS`. |
| `site_id` | `string` | – | Unique identifier for the measurement site (links to `location_data_harmonized.csv`). |
| `depth_m` | `float` | meters (m) | Depth **below the soil surface** where the observation was taken. |
| `replicate` | `int` | – | Replicate identifier (e.g., multiple sensors at the same depth). |
| `is_timeseries` | `bool` | – | `true` if the record is part of a regular time‑series; `false` otherwise. |
| `volumetric_water_content_m3_m3` | `float` | cubic meters per cubic meter (m³ m⁻³) | Volumetric water content (VWC). |
| `gravimetric_water_content_m3_m3` | `float` | g H2O g⁻¹ soil (m³ m⁻³) | Gravimetric water content (VWC). |
| `water_potential_kPa` | `float` | kilopascals (kPa) | Soil water potential or matric potential (reported as negative floating point). |

All numeric fields are stored as **floating‑point** numbers; missing values are represented with NA.


### 3. `location_data_harmonized_with_uuid.csv`  

The harmonized data files are linked via `site_id` to a concatenated table of site‑level metadata for all packages. This file includes location deduplication using UUIDs to collapse sites from different datasets that represent the same physical location (based on identical site names or proximity <5 meters).

| Column | Description |
|--------|-------------|
| `site_id` | Unique, human‑readable identifier for the measurement site within a dataset (e.g., `ER_SMN1B`, `PLM1`). May be duplicated across different `source_dataset_id` values if the same site appears in multiple packages. |
| `latitude` | Decimal degrees, WGS‑84. Original latitude from source package. |
| `longitude` | Decimal degrees, WGS‑84. Original longitude from source package. |
| `source_dataset_id` | ESS‑DIVE package identifier (e.g., `ess-dive-beca0be9bb38ece-20250516T122010234`) from which this site record originates. |
| `qc_flag` | Quality control flag for geospatial data. `g1` = geolocation coordinates not reported in source dataset but retrieved from Varadharajan et al. location registration data; `g2` = geolocation coordinates not reported in source dataset and not otherwise available (populated as `NA`). |
| `harmonized_location_uuid` | Universally unique identifier (UUID) assigned to each distinct physical location. Sites with identical names across datasets or coordinates within 5 meters are assigned the same UUID. |
| `latitude_harmonized` | Mean latitude (decimal degrees, WGS‑84) of all records sharing the same `harmonized_location_uuid`. For single-record UUIDs, equals `latitude`. |
| `longitude_harmonized` | Mean longitude (decimal degrees, WGS‑84) of all records sharing the same `harmonized_location_uuid`. For single-record UUIDs, equals `longitude`. |
| `n_records_in_uuid` | Number of `site_id` × `source_dataset_id` combinations collapsed into this `harmonized_location_uuid`. Value > 1 indicates the same physical location appears in multiple datasets or under multiple site names. |
| `n_datasets_in_uuid` | Number of distinct `source_dataset_id` values contributing to this `harmonized_location_uuid`. Value > 1 indicates cross-dataset location matching. |

**First row (example):**  

```csv
site_id,latitude,longitude,source_dataset_id,qc_flag,harmonized_location_uuid,latitude_harmonized,longitude_harmonized,n_records_in_uuid,n_datasets_in_uuid
PLM1,38.919771,-106.949273,ess-dive-01092fc392bc46d-20240819T143818677,g1,12e58e3e-5709-4c2a-ae2d-217099391f02,38.919771,-106.949273,1,1
```

**Location deduplication algorithm:**

Two site records are assigned the same UUID if they meet **any** of the following criteria:
1. **Coordinate proximity**: Both records have valid coordinates (lat/lon not NA) and are ≤ 5 meters apart (Haversine distance).
2. **Identical site_id across datasets**: The `site_id` value is identical in different `source_dataset_id` packages (e.g., `ER-PHS1` appears in multiple datasets).

Connected components are identified using graph-based clustering (R package `igraph`), where each qualifying pair forms an edge. All records in a connected component receive the same UUID.

---

### 4. `sm_data_harmonization_mapping.json`  

A JSON document that documents how each original variable was transformed into the standardized format. The mapping JSON follows a nested object schema that can be used programmatically to trace any harmonized variable back to its source. The schema is identical for every source package. The JSON is self‑describing and can be parsed with any JSON library (e.g., Python `json`, R `jsonlite`).  

#### Top-level structure

The document is a JSON **array** of objects, one per source dataset. Each object contains:

| Field | Type | Description |
|-------|------|-------------|
| `index` | integer | Zero-based index of the dataset in the harmonization workflow. Used internally for dataset ordering. |
| `dataset_identifier` | string | ESS‑DIVE package identifier (e.g., `ess-dive-beca0be9bb38ece-20250516T122010234`). Matches the prefix of the corresponding `*_harmonized.csv` filename and the `source_dataset_id` in `location_data_harmonized_with_uuid.csv`. |
| `doi` | string | Digital Object Identifier for the source package (e.g., `doi:10.15485/2566877`). |
| `archive_repository` | string | Repository hosting the source data. Always `"ESS-DIVE"` for this collection. |
| `inclusion_decision` | string | Expert decision on whether to include dataset for harmonization; `include` or `exclude`. | 
| `exclusion_reason` | string | Justification for excluding the dataset from harmonization; `null` if `inclusion_decision` = `include`. | 
| `data_payload_files` | array of strings or `null` | List of original data file names from the source package that contain soil moisture observations (e.g., `["ER_SMN1B.csv", "ER_SMN3B.csv"]`). `null` if the dataset was excluded or is a metadata-only package. |
| `location_metadata_files` | array of strings or `null` | List of original files containing site coordinates and location identifiers. `null` if location data was not provided or sourced from a different package. |
| `sensor_metadata_files` | array of strings or `null` | List of files containing sensor installation depths, sensor IDs, or other sensor-specific metadata. `null` if not applicable. |
| `harmonization_mappings` | object or string | **Object**: Nested mapping structure (see below) for included datasets. **String**: Exclusion reason for datasets not harmonized (e.g., `"None. Dataset excluded because it duplicates soil moisture data reported in ess-dive-460e696d8210ed3-20260309T155937802."`). |

#### Harmonization mappings structure (for included datasets)

When `harmonization_mappings` is an object, it organizes transformations by destination variable category. Each category (e.g., `datetime`, `depth`, `volumetric_water_content`) contains one or more patterns describing different source file structures:

**Pattern fields:**

| Field | Type | Description |
|-------|------|-------------|
| `source_pattern` | string or `null` | Column name pattern or regex in the original file(s) that identifies this variable (e.g., `"*_at_jcm"` matches `Water_Content_1_at_10cm`). `null` if the variable is not present in source files or requires manual assignment. |
| `source_files` | array of strings or `null` | File(s) from `data_payload_files` or `location_metadata_files` where this pattern applies. `null` if not applicable. |
| `destination_variable` | string | Standardized column name in the harmonized output (e.g., `volumetric_water_content_m3_m3`, `datetime_UTC`). |
| `transformation` | string or `null` | Description of data reshaping, parsing, or lookup operations applied (e.g., `"Coerce from 'wide' to 'long' format"`, `"Parse float j from '*_at_jcm'"`). `null` if no transformation beyond unit conversion. |
| `unit_conversion` | string or `null` | Description of unit conversion applied (e.g., `"Divide by 1e2 to convert from cm to m"`). `null` if source units match destination units. |

#### Standard destination variable categories

All harmonized datasets map to the following categories (not all categories have measured values in every dataset):

- `datetime`: Timestamp variables → `datetime_UTC`
- `site_id`: Site identifiers
- `depth`: Measurement depth → `depth_m`
- `latitude`: Site latitude → `latitude`
- `longitude`: Site longitude → `longitude`
- `replicate`: Measurement replicate number → `replicate`
- `volumetric_water_content`: Volumetric water content → `volumetric_water_content_m3_m3`
- `gravimetric_water_content`: Gravimetric water content → `gravimetric_water_content_gH2O_gs`
- `soil_water_potential`: Soil water potential → `water_potential_kPa`

#### Example: Complete dataset entry

```json
{
  "index": 1,
  "dataset_identifier": "ess-dive-beca0be9bb38ece-20250516T122010234",
  "doi": "doi:10.15485/2566877",
  "archive_repository": "ESS-DIVE",
  "inclusion_decision": "include", 
  "exclusion_reason": null,
  "data_payload_files": [
    "ER_SMN1B.csv",
    "ER_SMN3B.csv",
    "ER_SMN4B.csv"
  ],
  "location_metadata_files": [
    "Sensor_Location.csv"
  ],
  "sensor_metadata_files": null,
  "harmonization_mappings": {
    "datetime": {
      "pattern_1": {
        "source_pattern": "Time",
        "source_files": ["ER_SMN1B.csv", "ER_SMN3B.csv", "ER_SMN4B.csv"],
        "destination_variable": "datetime_UTC",
        "transformation": "Convert to ISO 8601 UTC format.",
        "unit_conversion": null
      }
    },
    "depth": {
      "pattern_1": {
        "source_pattern": "*_at_jcm",
        "source_files": ["ER_SMN1B.csv", "ER_SMN3B.csv", "ER_SMN4B.csv"],
        "destination_variable": "depth_m",
        "transformation": "Parse float j from '*_at_jcm'.",
        "unit_conversion": "Divide by 1e2 to convert from cm to m."
      }
    },
    "volumetric_water_content": {
      "pattern_1": {
        "source_pattern": "m3_m3_Water_Content_i_at_jcm",
        "source_files": ["ER_SMN1B.csv", "ER_SMN3B.csv"],
        "destination_variable": "volumetric_water_content_m3_m3",
        "transformation": "Coerce from 'wide' format to 'long' format.",
        "unit_conversion": "None; source units are m3/m3."
      },
      "pattern_2": {
        "source_pattern": "m3_m3_VWC_at_jcm",
        "source_files": ["ER_SMN4B.csv"],
        "destination_variable": "volumetric_water_content_m3_m3",
        "transformation": "Coerce from 'wide' format to 'long' format.",
        "unit_conversion": "None; source units are m3/m3."
      }
    }
  }
}
```

#### Example: Excluded dataset entry

```json
{
  "index": 11,
  "dataset_identifier": "ess-dive-1438b7d6eaa70e1-20250707T153211523",
  "doi": "doi:10.15485/1618130",
  "archive_repository": "ESS-DIVE",
  "data_payload_files": ["sample_site.csv"],
  "location_metadata_files": ["sample_site.csv"],
  "sensor_metadata_files": null,
  "harmonization_mappings": "None. Dataset excluded because it duplicates soil moisture data reported in ess-dive-460e696d8210ed3-20260309T155937802."
}
```
---

## Data‑Processing Workflow  

1. **Discovery & Inventory:** Identify the 25 source packages that contain soil‑moisture data.  
2. **Metadata Harvesting:** Use the ESS-DIVE API to pull metadata from ESS‑DIVE package records and the data payload itself.  
3. **File‑Level Harmonization:** 
   – Identify package files that contain target data. 
   - Convert all timestamps to UTC ISO‑8601.  
   - Standardize sampling depth units to meters.  
   - Resolve duplicate or ambiguous column names (e.g., `VWC_10cm`, `site1_depth0.1`). 
   - Enforce unitary variable naming: each variable reports a single piece of information (e.g., Coerce from 'wide' format with column variables containing depth and replicate information to 'long' format with separate columns for depth, replicate, and volumetric water content). 
4. **Long‑Format Reshaping:** Transform each source file from wide (multiple variables per row) to *long* format where each row contains a single measurement value.  
5. **Unit Conversion & Transformation:** Apply documented conversion factors (e.g., `%` → `m³ m⁻³`, kPa ↔ MPa) and any required scaling.  
6. **Location Harmonization:**: Aggregate site geospatial metadata from payload files, ancillary files, package metadata, or reference sources. Apply proximity- and identifier-based clustering to assign `harmonized_location_uuid`.
7. **Quality Control:** 
   - Flag missing or out‑of‑range values (`<0` VWC, extreme potentials).  
   - Cross‑check `site_id` against the consolidated location file.  
   - Duplicate key checks
8. **Export:** Write the cleaned, long‑format dataframe to `ess-dive-<package_id>_harmonized.csv`.  
9. **Mapping Documentation:** Populate the JSON mapping entry for the package (see [JSON Mapping Schema](#json-mapping-schema)).  

All scripts used for these steps are available in the `scripts/` subdirectory.

---

## Location Harmonization and UUID Assignment

The same measurement site may appear in multiple packages with identical `site_id`, different `site_id` but same coordinates, or slightly offset coordinates. A location harmonization step assigns a shared `harmonized_location_uuid` to records likely representing the same real-world location.

To harmonize similar locations to a single UUID, we built candidate pairings across location records through configurable rules: (1) strict coordinate proximity (separately reported points closer than 5 m to each other) or (2) same `site_id` across datasets. We then built a graph of linked records to compute connected components and assigned one `harmonized_location_uuid` value and one uniform set of latitude and longitude coordinates to each component. The graph approach is transitive: if A matches B and B matches C, then all three receive one UUID. Thresholds are intentionally conservative. The process preserves the original `site_id` and coordinates for uniquely reported sites but adds a crosswalking identifier. We recommend using `harmonized_location_uuid` for joins across datasets or alternatively `site_id` + `source_dataset_id` to retrieve high-specificity provenance.

---

## Usage Examples  

### A. Load a single harmonized file with pandas  

```python
import pandas as pd

# Example: load the harmonized data for package ID "ess-dive-beca0be9bb38ece-20250516T122010234"
csv_path = "ess-dive-beca0be9bb38ece-20250516T122010234_harmonized.csv"
df = pd.read_csv(csv_path, parse_dates=["datetime_UTC"])

print(df.head())
```

### B. Concatenate all harmonized files  

```python
import glob
import pandas as pd

csv_files = sorted(glob.glob("ess-dive_*_harmonized.csv"))
df_all = pd.concat([pd.read_csv(f, parse_dates=["datetime_UTC"]) for f in csv_files],
                  ignore_index=True)

# Merge with location metadata
loc = pd.read_csv("location_data_harmonized.csv")
df_merged = df_all.merge(loc, on="site_id", how="left")

print(df_merged.head())
```

### C. Inspect the mapping for a specific package  

```python
import json
from pathlib import Path

mapping_path = Path("sm_data_harmonization_mapping.json")
with mapping_path.open() as f:
    mappings = json.load(f)

# Find mapping entry for a particular dataset
target_id = "ess-dive-beca0be9bb38ece-20250516T122010234"
entry = next(item for item in mappings if item["dataset_identifier"] == target_id)

print(json.dumps(entry, indent=2))
```

---

## Known Issues & Limitations  

- **Depth Resolution:** In a few packages depth is reported as a range (e.g., `0–5 cm`). The current workflow records the midpoint; this may introduce minor bias for shallow sensors.  
- **Missing Replicate IDs:** When replicate information is absent, the `replicate` field is populated with 1L.  
- **Missing geolocation information:** Two source packages do not report geospatial information for sampling locations. Latitude and longitude are reported as NA in `location_data_harmonized.csv`
- **Ambiguous site identity:** UUID grouping is probabilistic and threshold-based; borderline cases may require manual review.
- **Coordinate uncertainty:** Some source coordinates are low precision or offset.

---

## Citation & Acknowledgments

- TBD

--- 

## Related References
- TBD: List source DOIs?

---

## License  

The harmonized data and accompanying code are released under the **Creative Commons Attribution 4.0 International (CC‑BY 4.0)** license.  

```
You are free to:
  • Share — copy and redistribute the material in any medium or format
  • Adapt — remix, transform, and build upon the material for any purpose,
    even commercially.
```

*Attribution* requires citing the dataset as shown above and retaining the license notice.

---

## Contact

- TBD

---

## Version History  

| Version | Date | Notes |
|---------|------|-------|
| 0.5-beta| 2026-08-11 | Update corrects filename-source dataset mismatches | 
| 0.4-beta | 2026‑05‑12 | Internal review release: 25 packages, 19 harmonized payload files, 25 complete entries in mapping JSON, uuid-harmonized location metadata, README. |
| 0.4-beta | 2026‑05‑12 | Internal review release: 25 packages, 19 harmonized payload files, 25 complete entries in mapping JSON, location metadata, README. |
| 0.3-beta | 2026‑04‑06 | Internal review release: 18 packages processed, 14 harmonized payload files, 18 complete entries in mapping JSON, location metadata, README. |
| 0.2‑beta | 2026‑03‑10 | Prototype scripts and partial mapping (4 packages). |
| 0.1‑alpha | 2026‑02‑23 | Source ESS‑DIVE packages identified. |

