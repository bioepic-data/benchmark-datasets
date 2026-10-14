"""Harmonize the selected soil variables from scratch, one variable at a time.

The workflow is generic: variable-specific settings are data (variable_config.csv), and package-specific code is
never used for output (the hand-written functions in essdive_harmonize/packages are only a check, compare.py).

Modules, in workflow order:

- config, variables: paths, settings and the variables to harmonize.
- candidates: candidate packages and matched columns, from data/intermediate/package_selection.
- tables, fields: reading package tables and detecting their sample fields and units.
- locate: sample locations (in-file, joined, UTM, metadata point, bounding-box centre).
- metadata: package text for method detection.
- auto: harmonization of one variable in one package.
- qc, compare: quality checks and the check against the hand-written packages.
- run: command line (``python -m essdive_harmonize.harmonize.run``).
"""

