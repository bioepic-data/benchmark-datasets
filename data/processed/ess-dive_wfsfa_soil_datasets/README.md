# WFSFA Harmonized Soil Moisture Data 
*Version 0.4-beta – 2026‑05‑12*  

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
  - 25 packages are candidates containing soil moisture measurements. 
  - 18 packages have been processed as of 2026-04-06
  - 14 packages contain valid soil moisture data
  - 4 are prior versions of other datasets included in the final harmonization or contain duplicated data from another package. 
---

## Data Summary  

| Asset | Description | Quantity | Format |
|-------|-------------|----------|--------|
| **Source sub‑directories** | Raw ESS‑DIVE packages (original files) | 25 directories; one per source package | Mixed (CSV, TXT, XLSX, JSON, etc.) |
| **Harmonized CSVs** | One per source package, merged, transformed, and reshaped to long format | 8 files | CSV |
| **Location metadata** | Consolidated site‑level geospatial and identifier data for all packages | 1 file | CSV |
| **Reproducible script** | Reproducible R script detailing all data transformations | 1 file | R |
| **Mapping JSON** | Detailed mapping of original variable names → harmonized variables, including transformations | 1 file | JSON |

All files are stored in the repository data directory (see the [Directory Structure](#directory-structure) section).

---

## Directory Structure  

```
.
├── data/
  ├── processed/
    ├── ess-dive_wfsfa_soil_dataset_urls.csv       --> CSV file containing URLs pointing to 27 directories on Google Drive, each containing source package data
    ├── ess-dive_harmonized_soil_urls.csv          --> CSV file containing URLs pointing to 13 CSV files on Google Drive, one per harmonized package
    ├── location_data_harmonized_with_uuid.csv     --> Single CSV containing site‑level metadata
    └── sm_data_harmonization_mapping.json         --> JSON describing variable mappings & transformations
```

*The complete directory tree can be visualized with `tree -L 2 .` on a Unix‑like system.*

---

## File Descriptions  

### 1. `ess-dive_wfsfa_soil_dataset_urls.csv`  

Contains 27 URLs pointing to Google Drive directories where the original ESS‑DIVE downloads source package are stored. The directories at the URL targets preserve the original file hierarchy (data payloads, ancillary metadata, documentation, etc.).  

### 2. `ess-dive_harmonized_soil_urls.csv`  

Contains 13 direct-download URLs pointing to CSV files on Google Drive. Each URL points to a single file associated with a source package that has been processed and harmonized to the standard schema. Individual files can be merged with simple row concatenation; they are stored separately for memory efficiency. Rows are **observations**; columns are the **harmonized variables** listed below. The schema is shared across all files. Files are named following the pattern:  

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
| `interval_min` | `float` | minutes (min) | Sampling interval for time‑series data (null if irregular). |
| `volumetric_water_content_m3_m3` | `float` | cubic meters per cubic meter (m³ m⁻³) | Volumetric water content (VWC). |
| `gravimetric_water_content_m3_m3` | `float` | g H2O g⁻¹ soil (m³ m⁻³) | Gravimetric water content (VWC). |
| `water_potential_kPa` | `float` | kilopascals (kPa) | Soil water potential or matric potential (reported as negative floating point). |
| `qc_flag` | `string` | – | Code indicating quality control flag: 'd1' = discrete depth is approximated from a sampling depth range reported in the source dataset; 'g1' = geolocations not reported in source dataset but retrieved from Varadharajan et al. location registration data; 'g2' = geolocations not reported in source dataset and not otherwise available |

All numeric fields are stored as **floating‑point** numbers; missing values are represented with NA.

### 3. `location_data_harmonized.csv`  

The harmonized data files are linked via ‘site_id’ to a concatenated table of site‑level metadata for all packages.

| Column | Description |
|--------|-------------|
| `site_id` | Unique, human‑readable identifier for the measurement site (e.g., `ER_SMN1B`). |
| `latitude` | Decimal degrees, WGS‑84. |
| `longitude` | Decimal degrees, WGS‑84. |
| `source_dataset_id` | ESS‑DIVE package identifier (e.g., `ess-dive-beca0be9bb38ece-20250516T122010234`). |

**First row (example):**  

```
site_id,latitude,longitude,source_dataset_id
ER_SMN1B,-106.948702080297,38.9207077343745,ess-dive-beca0be9bb38ece-20250516T122010234
```

### 4. `sm_data_harmonization_mapping.json`  

A JSON document that documents **how** each original variable was transformed into the standardized format. The mapping JSON follows a **nested object schema** that can be used programmatically to trace any harmonized variable back to its source. The schema is identical for every source package. The JSON is **self‑describing** and can be parsed with any JSON library (e.g., Python `json`, R `jsonlite`).  

The top‑level object is a list of mapping entries, one for each harmonized package. An entry contains:

```json
{
  "dataset_identifier": "<ESS‑DIVE package ID>",
  "doi": "<Package DOI>",
  "archive_repository": "ESS-DIVE",
  "data_payload_files": { "<original filename>": ["<variable1>", "<variable2>", …] },
  "location_metadata_files": { "<filename>": ["latitude", "longitude", …] },
  "harmonization_mappings": [
    {
      "pattern_id": "pattern_1",
      "source_pattern": "VWC|vol_water_cont",
      "source_files": [
        "soil_moisture_1.csv",
        "soil_moisture_2.csv"
      ],
      "destination_variable": "volumetric_water_content_m3_m3",
      "transformation": "Description of variable transformations",
      "unit_conversion": "Description of unit conversions"
    },
    …
  ]
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
   - Flag when `interval_min` is inconsistent within a time series.  
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
| 0.4-beta | 2026‑05‑12 | Internal review release: 25 packages, 19 harmonized payload files, 25 complete entries in mapping JSON, uuid-harmonized location metadata, README. |
| 0.4-beta | 2026‑05‑12 | Internal review release: 25 packages, 19 harmonized payload files, 25 complete entries in mapping JSON, location metadata, README. |
| 0.3-beta | 2026‑04‑06 | Internal review release: 18 packages processed, 14 harmonized payload files, 18 complete entries in mapping JSON, location metadata, README. |
| 0.2‑beta | 2026‑03‑10 | Prototype scripts and partial mapping (4 packages). |
| 0.1‑alpha | 2026‑02‑23 | Source ESS‑DIVE packages identified. |

