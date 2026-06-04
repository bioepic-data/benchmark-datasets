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
├── data/
│   ├── external/          # Third-party source data
│   │   ├── ess-dive_meta/ # ESS-DIVE package metadata (JSON)
│   │   ├── ess-dive_dois.txt
│   │   └── ess-dive_ids.txt
│   ├── intermediate/      # Filtered/processed intermediate outputs
│   │   ├── er_soil_meta.json
│   │   └── ess-dive_eastriver_*.tsv
│   └── processed/         # Final harmonized datasets
│       └── ess-dive_wfsfa_soil_datasets/  # See data README below
├── notebooks/             # Data processing scripts
│   ├── scrape_ess-dive.py
│   └── harmonize_ess-dive_soilmoisture_data.py
├── skills/                # Claude Code skills for AI-assisted workflows
│   └── wfsfa_sm_harmonization/  # Interactive harmonization skill
├── src/
│   └── benchmark_datasets/  # Python package source
└── tests/                 # Unit and integration tests
```

## Key Datasets

### WFSFA Harmonized Soil Moisture Data

The primary output is a curated, standardized set of soil moisture observations from 25 ESS-DIVE data packages covering the East River watershed. The harmonized dataset includes:

- **14 harmonized data packages** with valid soil moisture measurements
- **Standardized schema** with common variable names, units, and temporal formats
- **Geospatial metadata** with UUID-based location harmonization across datasets
- **Complete provenance** via JSON mapping files linking harmonized variables to original sources

Key features:
- Long-format structure for easy aggregation and time-series analysis
- Volumetric water content, gravimetric water content, and water potential measurements
- Quality control flags for approximated depths and missing geolocation data
- ISO-8601 timestamps in UTC
- Linked site metadata with WGS-84 coordinates

For complete documentation, see [`data/processed/ess-dive_wfsfa_soil_datasets/README.md`](data/processed/ess-dive_wfsfa_soil_datasets/README.md).

## Scripts

### `notebooks/scrape_ess-dive.py`

ESS-DIVE dataset discovery and retrieval pipeline:

1. Fetches metadata for all public ESS-DIVE packages via API
2. Filters datasets by spatial extent (East River watershed bounding box)
3. Identifies soil and subsurface-related packages
4. Downloads selected data files and metadata

**Requirements:** ESS-DIVE API token (obtain from https://ess-dive.lbl.gov/)

**Key outputs:**
- `data/external/ess-dive_meta/` — JSON metadata for all discovered packages
- `data/external/ess-dive_ids.txt` — Dataset identifiers
- `data/intermediate/er_soil_meta.json` — Filtered East River soil datasets
- `data/intermediate/ess-dive_eastriver_soildatasets.tsv` — Candidate soil datasets

### `notebooks/harmonize_ess-dive_soilmoisture_data.py`

Data harmonization workflow that transforms heterogeneous soil moisture datasets into a unified schema:

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
- `data/processed/ess-dive_wfsfa_soil_datasets/*.csv` — Harmonized data files
- `data/processed/ess-dive_wfsfa_soil_datasets/location_data_harmonized_with_uuid.csv` — Site metadata
- `data/processed/ess-dive_wfsfa_soil_datasets/sm_data_harmonization_mapping.json` — Transformation provenance

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

# Load a single harmonized dataset
data_dir = Path("data/processed/ess-dive_wfsfa_soil_datasets")
df = pd.read_csv(data_dir / "ess-dive-beca0be9bb38ece-20250516T122010234_harmonized.csv",
                 parse_dates=["datetime_UTC"])

# Load all harmonized datasets
import glob
csv_files = sorted(glob.glob(str(data_dir / "ess-dive_*_harmonized.csv")))
df_all = pd.concat([pd.read_csv(f, parse_dates=["datetime_UTC"]) 
                    for f in csv_files], ignore_index=True)

# Merge with location metadata
locations = pd.read_csv(data_dir / "location_data_harmonized_with_uuid.csv")
df_merged = df_all.merge(locations, on="site_id", how="left")
```

### Inspect data transformation provenance

```python
import json

# Load mapping JSON
with open("data/processed/ess-dive_wfsfa_soil_datasets/sm_data_harmonization_mapping.json") as f:
    mappings = json.load(f)

# Find transformation details for a specific package
target_id = "ess-dive-beca0be9bb38ece-20250516T122010234"
package_mapping = next(m for m in mappings if m["dataset_identifier"] == target_id)

# View variable mappings
for mapping in package_mapping["harmonization_mappings"]:
    print(f"{mapping['source_pattern']} → {mapping['destination_variable']}")
    print(f"  Transformation: {mapping['transformation']}")
    print(f"  Unit conversion: {mapping['unit_conversion']}\n")
```

## Data Access

Harmonized datasets are available via Google Drive URLs documented in:
- `data/processed/ess-dive_wfsfa_soil_datasets/ess-dive_harmonized_soil_urls.csv` — Direct download links to harmonized CSV files
- `data/processed/ess-dive_wfsfa_soil_datasets/ess-dive_wfsfa_soil_dataset_urls.csv` — Links to original source package directories

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
- [Data harmonization workflow documentation](data/processed/ess-dive_wfsfa_soil_datasets/README.md)
