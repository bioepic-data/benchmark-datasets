"""Find the ESS-DIVE packages that report the variables of data/soil_variable_list_input.csv.

Modules, in workflow order:

- config: paths and limits.
- variable_list: the variables to search for (the select column is ignored).
- rules: matching rules per variable (copied from the soil-variable-list scripts).
- metadata: package metadata text by source (keywords, description, other).
- headers: column headers of the downloaded files (cached) and data-dictionary definitions.
- soil: soil-related classification of packages.
- matching: column and metadata matching -> evidence rows.
- report: output tables, for all packages and split soil / non-soil.
- run: command line (``python -m essdive_harmonize.selection.run``).
"""
