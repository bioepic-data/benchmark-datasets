"""Select and harmonize soil variables from ESS-DIVE data packages.

Subpackages:

- selection: find the packages that report each variable of data/soil_variable_list_input.csv, from column headers
  and package metadata (``python -m essdive_harmonize.selection.run``).
- harmonize: harmonize each selected variable from scratch into the soil pH layout
  (``python -m essdive_harmonize.harmonize.run``).
- packages: hand-written pH and carbon package functions (registry.py), kept as a check of the generic workflow.

Top-level modules: fetch (package list and metadata), download_files (package files), variables, units, common
and extract (shared definitions, unit conversion, readers, layout and column mapping), registry, triage and run
(the hand-written workflow).
"""
