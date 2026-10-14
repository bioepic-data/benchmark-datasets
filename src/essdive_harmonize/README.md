# essdive_harmonize

Select and harmonize soil variables from ESS-DIVE data packages. Each module documents itself (Google-style
docstrings with doctest examples); this page gives the overview.

## Workflow

| Step | Command (from the repo root, `PYTHONPATH=src`) | Output |
|---|---|---|
| 1. Package list and metadata | `python -m essdive_harmonize.fetch` | `data/source/ess-dive_meta/` |
| 2. Package files | `python -m essdive_harmonize.download_files` | `data/source/package_data/` |
| 3. Package selection | `python -m essdive_harmonize.selection.run` | `data/intermediate/package_selection/` |
| 4. Harmonization | `python -m essdive_harmonize.harmonize.run --category Carbon --write --compare` | `data/processed/harmonization/` |

- **Selection** looks for every variable of `data/soil_variable_list_input.csv` (`select` ignored) in the column
  headers of the downloaded files and in the package metadata (keywords, description, other metadata), for all
  packages, then splits the counts by soil context. No DOI is hard-coded: everything comes from the data.
- **Harmonization** handles the variables with `select = 1` (porewater metals and fluxes excluded), from scratch, for the
  candidate packages of the selection: data columns with numeric values, soil context (soil, sediment, peat,
  permafrost, horizon) and not excluded package-wide in `triage.csv`. It is generic: variable settings are data
  (`harmonize/variable_config.csv`), and no package-specific code is used for output.
- **Hand-written packages** (`packages/`, `registry.py`, `run.py`): the soil pH and carbon functions ported from
  `notebooks/harmonize_ph` and `notebooks/harmonize_carbon`. They are kept only as a check:
  `harmonize.run --compare` runs them in memory and writes `<key>/handwritten_check.csv`.

## Harmonization outputs: `data/processed/harmonization/`

```
harmonization/
  variables.csv                    one row per variable: candidates, packages written, rows, in review
  review_queue.csv                 every package / variable not written, with the reasons
  <key>/                           one folder per variable key (Acidity__Soil_pH, Carbon__Total_carbon, ...)
    <doi_slug>/<doi_slug>_soil_<key>.csv / .xlsx
    harmonized.csv / .xlsx         all packages of the variable
    dois_filtering.xlsx            every package with numeric column evidence: keep, inclusion_reason, n_rows,
                                   matched_columns, location_source, unit_assumed
    review_queue.csv               this variable's packages not written
    qc.csv                         rows outside the plausible range or with invalid coordinates
    handwritten_check.csv          with --compare: agreement with the hand-written pH / carbon packages
```

Columns of each table (the soil pH layout):

`doi, source_file, id, id_type, depth, date, <key>, <key lower>_method, [extra columns], latitude, longitude, IGSN, notes`

- Keys come from the category and variable labels: `'/'`, `'('` and `')'` are dropped, then `':'` becomes `'__'`
  and spaces `'_'` (`Physical:Dry bulk density` -> `Physical__Dry_bulk_density`). Short aliases (`TC`, `pH`,
  `Caexch`, ...) are accepted in code; outputs always use the long keys.
- Values are converted to the standard unit of the variable (`harmonize.run --list`); the source column, unit
  and conversion go to `notes`, after `lat/long source: ...`.
- Locations, in order: coordinates in the table (group 1), joined by a site / plot / sample key from another
  table, KML file or metadata point (group 3), UTM columns (group 4), a single metadata point (group 2), else the
  centre of the metadata bounding box, noted with its half-diagonal in km.
- Methods use a short vocabulary (`dry_combustion`, `salt_extraction`, `pH_H2O`, `ICP`, ...); instrument,
  extractant and ratio go to `notes`. Open questions per category are listed in `harmonize/open_issues.md`.

## Code

| Module | Role |
|---|---|
| `fetch.py`, `download_files.py` | ESS-DIVE package list, metadata and file downloads (size limits and the record of skipped files). |
| `variables.py`, `units.py` | Variable definitions (keys, units, columns) and unit parsing / conversion. |
| `common.py`, `extract.py`, `datatypes.py` | Shared readers, formatting, location helpers, the harmonized layout (`assemble`, `emit`) and writers. |
| `selection/` | Package selection: `rules` (matching rules per variable), `headers` (column-header scan), `matching`, `metadata`, `soil`, `report`, `run`. |
| `harmonize/` | Generic harmonization: `variables`, `candidates`, `tables`, `fields`, `locate`, `metadata`, `auto`, `qc`, `compare`, `run`. |
| `packages/group1-4_*.py` | Hand-written pH / carbon functions by location group; `registry.py` collects their `PACKAGES`. |
| `triage.py`, `triage.csv` | Package-level keep / exclude decisions (`variable = *` applies to every variable). |
| `reference/` | Offline copies of reference data (EXCHANGE-D kit coordinates, carbon exclusion notes). |

## Documentation and checks

Docstrings follow the Google style and PEP 257; tool settings are in the repo's `pyproject.toml`.

```bash
python -m pytest                                   # doctests of every module (--doctest-modules)
ruff check src/essdive_harmonize                   # pydocstyle rules (D), Google convention
mypy                                               # type annotations (strict definitions)
```

Examples that need the downloaded data are marked `# doctest: +SKIP`; the others run offline.

## History

- 2026-10-06: the 38 soil pH packages of `harmonize_ph` and 65 carbon packages of `harmonize_carbon` (75 DOIs)
  were ported to `packages/group1-4` (functions `ph_<id>` and `c_<id>`, joined per DOI with `extract.combine`),
  unchanged apart from the `assemble()` signature, and checked identical to the earlier outputs. `triage.csv`
  was built over the 418 packages of the earlier hit matrix (77 soil packages kept package-wide, 288 excluded).
- 2026-10-07: generic harmonization from the package selection (`harmonize/`); the hand-written packages became
  a check only.
- 2026-10-08: typing and documentation standardized across the package.
