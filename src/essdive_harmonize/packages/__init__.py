"""Hand-written harmonization of individual packages (soil pH and carbon), used only as a check.

The functions were ported from notebooks/harmonize_ph and notebooks/harmonize_carbon (unchanged apart from the
assemble() signature). The generic workflow (essdive_harmonize.harmonize) never writes their output; compare.py runs
them in memory and compares them with the automatic results. Modules are grouped by where the sample coordinates
come from:

- group1_infile_coords: per-sample latitude / longitude columns in the data file.
- group2_metadata_coords: package metadata, methods text, a user guide or a data description.
- group3_joined_coords: joined from another table, KML file or package by a site / plot / core key.
- group4_projected_coords: converted from UTM or a local X/Y grid.

Each module lists its packages in PACKAGES: (DOI, package function, variables).
"""

