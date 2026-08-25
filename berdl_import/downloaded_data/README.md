# Downloaded Data

This directory is for source data downloaded from external services during the
BERDL import workflow.

The files here are intentionally ignored by Git because they include large raw
CSV inputs and downloaded crosswalks that can be restored from the source
manifests tracked in the repository.

## Data Sources

All data in this directory should be downloaded from Google Drive URLs documented in:
- `../../data/processed/harmonized_soil_moisture_data/ess-dive_harmonized_soil_urls.csv` — Harmonized CSV files
- `../../data/processed/ess-dive_wfsfa_soil_datasets/ess-dive_wfsfa_soil_dataset_urls.csv` — Original source packages

## Expected Local Contents

After downloading files for the BERDL import workflow:

```
downloaded_data/
└── ess-dive_wfsfa_soil_datasets/
    ├── harmonized_csv/                         # Harmonized CSV files (19 files)
    │   ├── ess-dive-*_harmonized.csv           # One per source package
    │   └── ...
    └── location_data_harmonized_with_uuid.csv  # Site metadata with UUID harmonization
```

## Downloading Files

To populate this directory:

1. Read the URL files from `data/processed/` to get Google Drive links
2. Download harmonized CSVs into `ess-dive_wfsfa_soil_datasets/harmonized_csv/`
3. Download location metadata as `ess-dive_wfsfa_soil_datasets/location_data_harmonized_with_uuid.csv`
4. (Optional) Download original source packages if needed for BERDL import

**Note:** These files are large (ignored by git) and can be re-downloaded from the URLs at any time.
