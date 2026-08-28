# Benchmark Datasets

A repository for creating AI-ready benchmark datasets from environmental and ecological data sources, with a focus on harmonizing heterogeneous datasets for machine learning and model benchmarking applications.

## Overview

This repository provides tools and workflows for:
- Discovering and retrieving datasets from environmental data repositories (ESS-DIVE)
- Harmonizing heterogeneous data into standardized, analysis-ready formats
- Creating curated benchmark datasets for hydrological and terrestrial ecosystem models
- Documenting data transformations and provenance for reproducibility

**Current focus:** Soil moisture data from the Watershed Function Science Focus Area (WFSFA) in Colorado's East River watershed, archived on ESS-DIVE.

## Repository Structure

```
benchmark-datasets/
├── berdl_import/          # BERDL import workflow for WFSFA soil moisture
│   ├── AGENT_LOG.md       # Chronological import notes and decisions
│   ├── scripts/           # Build, schema-generation, and BERDL import scripts
│   ├── schema/            # Generated BERDL schema documentation
│   ├── downloaded_data/   # Ignored downloaded source CSVs and local location UUID file
│   ├── data/              # Ignored generated BERDL import packages
│   └── local_logs/        # Ignored local pipeline logs
├── data/
│   ├── source/            # Third-party source data
│   │   ├── ess-dive_meta/ # ESS-DIVE package metadata (JSON)
│   │   ├── ess-dive_dois.txt
│   │   └── ess-dive_ids.txt
│   ├── intermediate/      # Filtered/processed intermediate outputs
│   │   ├── er_soil_meta.json
│   │   └── ess-dive_eastriver_*.tsv
│   └── processed/         # Tracked metadata for processed datasets
│       ├── ess-dive_wfsfa_soil_datasets/  # URLs to original source packages
│       ├── ess-dive_soilpH_datasets/      # URLs to original soil pH source packages
│       └── harmonized_soil_moisture_data/ # URLs to harmonized CSVs, mapping JSON
├── docs/                  # Documentation for various operations
├── notebooks/             # Data processing scripts
│   ├── generate_qc_reports.py
│   ├── scrape_ess-dive.py
│   └── harmonize_sm
│       ├── common.py      # Shared library with context class and helper functions
│       ├── dataset_*.py   # Processing files for individual datasets
│       ├── inclusions*.py # Registry mapping 19 dataset indices to harmonization functions
│       ├── README.md.     # Documentation with usage examples
│       └── run.py         # Orchestrator with CLI interface and holdout support for cross-val
├── skills/                # Claude Code skills for AI-assisted workflows
│   ├── wfsfa_sm_harmonization/  # Interactive harmonization skill
│   └── watershed-sfa-soil-moisture-berdl-query/  # BERDL query skill
├── src/
│   └── benchmark_datasets/  # Python package source
└── tests/                 # Unit and integration tests
```

## Key Datasets

### WFSFA Harmonized Soil Moisture Data

The primary output is a curated, standardized set of soil moisture observations from 25 ESS-DIVE data packages covering the East River watershed. The harmonized dataset includes:

- **19 harmonized data packages** with valid soil moisture measurements
- **Standardized schema** with common variable names, units, and temporal formats
- **Geospatial metadata** with UUID-based location harmonization across datasets
- **Complete provenance** via JSON mapping files linking harmonized variables to original sources

Key features:
- Long-format structure for easy aggregation and time-series analysis
- Volumetric water content, gravimetric water content, and water potential measurements
- Quality control flags for approximated depths and missing geolocation data
- ISO-8601 timestamps in UTC
- Linked site metadata with WGS-84 coordinates

For complete documentation, see [`data/processed/README.md`](data/processed/README.md).

### BERDL Watershed SFA Soil Moisture Import

The BERDL import workflow converts the harmonized WFSFA soil moisture files into the `bervodata_watershed_sfa_soil_moisture` BERDL database.

Tracked import files live under [`berdl_import/`](berdl_import/):

- [`berdl_import/scripts/build_watershed_sfa_soil_moisture_import.py`](berdl_import/scripts/build_watershed_sfa_soil_moisture_import.py) — builds BERDL-ready CSV tables from the harmonized source files and tracked metadata
- [`berdl_import/scripts/import_watershed_sfa_soil_moisture_to_berdl.py`](berdl_import/scripts/import_watershed_sfa_soil_moisture_to_berdl.py) — imports generated CSV tables into BERDL
- [`berdl_import/scripts/generate_watershed_sfa_soil_moisture_schema.py`](berdl_import/scripts/generate_watershed_sfa_soil_moisture_schema.py) — generates markdown schema documentation from the import package
- [`berdl_import/schema/`](berdl_import/schema/) — generated schema docs for query authors and skills
- [`berdl_import/AGENT_LOG.md`](berdl_import/AGENT_LOG.md) — record of import decisions, table design, ontology sources, and actions taken

Large or regenerated artifacts are intentionally ignored:

- `berdl_import/downloaded_data/` stores downloaded harmonized CSVs from Google Drive and the locally generated `location_data_harmonized_with_uuid.csv`
- `berdl_import/data/` stores generated BERDL import packages, including large table CSVs
- `berdl_import/local_logs/` stores local import and validation logs

The current BERDL table set is:

- `sdt_dataset`
- `sdt_location`
- `sdt_harmonized_location`
- `ddt_soil_moisture_observation`
- `ddt_ndarray`
- `sys_typedef`
- `sys_ddt_typedef`
- `sys_oterm`

## Scripts

### `notebooks/scrape_ess-dive.py`

ESS-DIVE dataset discovery and retrieval pipeline:

1. Fetches metadata for all public ESS-DIVE packages via API
2. Filters datasets by spatial extent (East River watershed bounding box)
3. Identifies soil and subsurface-related packages
4. Downloads selected data files and metadata

**Requirements:** ESS-DIVE API token (obtain from https://ess-dive.lbl.gov/)

**Key outputs:**
- `data/source/ess-dive_meta/` — JSON metadata for all discovered packages
- `data/source/ess-dive_ids.txt` — Dataset identifiers
- `data/intermediate/er_soil_meta.json` — Filtered East River soil datasets
- `data/intermediate/ess-dive_eastriver_soildatasets.tsv` — Candidate soil datasets

### `notebooks/harmonize_sm`

Modular data harmonization workflow that transforms heterogeneous soil moisture datasets into a unified schema:

**Harmonization steps:**
1. Metadata extraction from ESS-DIVE package records
2. File-level variable mapping and unit conversion
3. Timestamp standardization to UTC ISO-8601
4. Depth unit normalization (meters below surface)
5. Wide-to-long format reshaping (one measurement per row)
6. Location harmonization with UUID assignment via spatial clustering
7. Quality control and validation
8. JSON mapping documentation

**Key outputs:**
- Harmonized data files (available via Google Drive URLs)
- Location metadata with UUID harmonization (available via Google Drive)
- `data/processed/harmonized_soil_moisture_data/sm_data_harmonization_mapping.json` — Transformation provenance
- `data/processed/harmonized_soil_moisture_data/ess-dive_harmonized_soil_urls.csv` — URLs to harmonized CSV files
- `data/processed/ess-dive_wfsfa_soil_datasets/ess-dive_wfsfa_soil_dataset_urls.csv` — URLs to original source packages

**BERDL import inputs:**
- `berdl_import/downloaded_data/ess-dive_wfsfa_soil_datasets/harmonized_csv/*.csv` — Downloaded harmonized data files used by the BERDL import workflow; ignored by git
- `berdl_import/downloaded_data/ess-dive_wfsfa_soil_datasets/location_data_harmonized_with_uuid.csv` — Local UUID-based site metadata used by the BERDL import workflow; ignored by git

### `berdl_import/scripts/build_watershed_sfa_soil_moisture_import.py`

Builds the BERDL-ready table package from the tracked WFSFA metadata and ignored downloaded harmonized CSVs. Outputs are written under `berdl_import/data/berdl_import/watershed_sfa_soil_moisture/` and are ignored by git because they are large and reproducible.

### `berdl_import/scripts/import_watershed_sfa_soil_moisture_to_berdl.py`

Uploads the generated BERDL table package into the `bervodata_watershed_sfa_soil_moisture` database. This script expects the BERDL remote ingest environment to be configured.

### `berdl_import/scripts/generate_watershed_sfa_soil_moisture_schema.py`

Generates markdown schema documentation from the BERDL import package. The generated docs are tracked in [`berdl_import/schema/`](berdl_import/schema/) and copied into the query skill references.

## AI-Assisted Workflows

The [`skills/`](skills/) directory contains Claude Code skills for interactive, AI-assisted data harmonization:

### WFSFA Soil Moisture Harmonization Skill

**Location:** [`skills/wfsfa_sm_harmonization/`](skills/wfsfa_sm_harmonization/)

An interactive skill that guides Claude through evaluating, harmonizing, and documenting new ESS-DIVE soil moisture datasets into the WFSFA harmonization framework.

**Capabilities:**
- **Interactive evaluation**: Systematically assess new datasets for inclusion using established decision rules
- **Code generation**: Produce Python harmonization code conforming to project conventions
- **Mapping documentation**: Generate JSON mapping entries with full transformation provenance
- **Quality assurance**: Apply schema validation, unit conversion checks, and QC flag assignment

**Usage:** Invoke when adding a new ESS-DIVE soil moisture dataset to the harmonization pipeline. The skill handles dataset evaluation, variable mapping, location resolution, time series detection, and generates both Python code and JSON documentation.

**Outputs:**
- Python code block for the harmonization script
- JSON mapping entry for `sm_data_harmonization_mapping.json`
- Inclusion/exclusion decision with documented reasoning
- QC flags for approximated depths or locations

See [`skills/wfsfa_sm_harmonization/SKILL.md`](skills/wfsfa_sm_harmonization/SKILL.md) for complete documentation and [`soilmoisture_harmonization_general_insights.md`](skills/wfsfa_sm_harmonization/soilmoisture_harmonization_general_insights.md) for general insights from the harmonization process.

### Watershed SFA Soil Moisture BERDL Query Skill

**Location:** [`skills/watershed-sfa-soil-moisture-berdl-query/`](skills/watershed-sfa-soil-moisture-berdl-query/)

A query skill for the imported `bervodata_watershed_sfa_soil_moisture` BERDL database. It follows the pattern of the ENIGMA BERDL query skill and uses generated schema references from [`berdl_import/schema/`](berdl_import/schema/).

**Capabilities:**
- Compose BERDL SQL against the current WFSFA soil moisture table and column names
- Use generated schema references to avoid guessing table structure
- Join observation, dataset, and location tables consistently
- Query ontology and typedef metadata through `sys_oterm`, `sys_typedef`, and `sys_ddt_typedef`

The skill is repo-tracked under `skills/` and can be installed locally under `~/.codex/skills/watershed-sfa-soil-moisture-berdl-query/`.

## Setup

```bash
# Clone the repository
git clone https://github.com/your-org/benchmark-datasets.git
cd benchmark-datasets

# Install dependencies (if using as a package)
pip install -e .
```

**Dependencies:**
- Python 3.8+
- pandas
- numpy
- requests
- aiohttp
- pyproj (for coordinate transformations)

## Usage Examples

### Load harmonized soil moisture data

```python
import pandas as pd
from pathlib import Path

# First, download harmonized datasets from URLs
urls_file = Path("data/processed/harmonized_soil_moisture_data/ess-dive_harmonized_soil_urls.csv")
urls_df = pd.read_csv(urls_file)

# Download a single harmonized dataset (example using first file)
# Note: You'll need to implement download logic or manually download from Google Drive
file_url = urls_df.iloc[0]['url']
filename = urls_df.iloc[0]['filename']

# After downloading, load the harmonized data
df = pd.read_csv(filename, parse_dates=["datetime_UTC"])

# Load all harmonized datasets (after downloading)
# csv_files = sorted(urls_df['filename'].tolist())
# df_all = pd.concat([pd.read_csv(f, parse_dates=["datetime_UTC"]) 
#                     for f in csv_files], ignore_index=True)

# Merge with location metadata (also needs to be downloaded from Google Drive)
# locations = pd.read_csv("location_data_harmonized_with_uuid.csv")
# df_merged = df_all.merge(locations, on="site_id", how="left")
```

For the current BERDL import workflow, the downloaded harmonized CSVs are kept in:

```python
from pathlib import Path

downloaded_dir = Path("berdl_import/downloaded_data/ess-dive_wfsfa_soil_datasets")
harmonized_dir = downloaded_dir / "harmonized_csv"
locations = downloaded_dir / "location_data_harmonized_with_uuid.csv"
```

### Inspect data transformation provenance

```python
import json

# Load mapping JSON
with open("data/processed/harmonized_soil_moisture_data/sm_data_harmonization_mapping.json") as f:
    mappings = json.load(f)

# Find transformation details for a specific package
target_id = "ess-dive-beca0be9bb38ece-20250516T122010234"
package_mapping = next(m for m in mappings if m["dataset_identifier"] == target_id)

# View variable mappings (note: structure may vary by dataset)
if isinstance(package_mapping["harmonization_mappings"], dict):
    for category, patterns in package_mapping["harmonization_mappings"].items():
        print(f"\n{category}:")
        for pattern_key, mapping in patterns.items():
            print(f"  {mapping['source_pattern']} → {mapping['destination_variable']}")
            print(f"    Transformation: {mapping['transformation']}")
            print(f"    Unit conversion: {mapping['unit_conversion']}")
```

## Data Access

Harmonized datasets are available via Google Drive URLs documented in:
- `data/processed/harmonized_soil_moisture_data/ess-dive_harmonized_soil_urls.csv` — Direct download links to harmonized CSV files
- `data/processed/ess-dive_wfsfa_soil_datasets/ess-dive_wfsfa_soil_dataset_urls.csv` — Links to original source package directories
- `data/processed/ess-dive_soilpH_datasets/ess-dive_soilpH_dataset_urls.csv` — Links to original soil pH source package directories (files over 500 MB are excluded from the mirror; see `data/processed/ess-dive_soilpH_datasets/excluded_large_files.md` for their direct ESS-DIVE URLs)

## Development

```bash
# Run tests
pytest tests/

# Install in development mode
pip install -e ".[dev]"
```

## Citation

If you use these datasets in your research, please cite:

- The original ESS-DIVE data packages (DOIs available in mapping JSON)
- This harmonization effort: *[Citation details TBD]*

## License

Harmonized data and code are released under **Creative Commons Attribution 4.0 International (CC-BY 4.0)**.

Original ESS-DIVE datasets retain their respective licenses (typically CC-BY 4.0).

## Acknowledgments

- ESS-DIVE data repository and API
- Watershed Function Science Focus Area (WFSFA) research community
- Original data contributors (see individual package DOIs)

## Related Resources

- [ESS-DIVE Repository](https://ess-dive.lbl.gov/)
- [WFSFA Project Information](https://watershed.lbl.gov/)
- [Data harmonization workflow documentation](data/processed/README.md)
