# Schema

This directory stores schema markdown for the WFSFA soil moisture BERDL database.

## Generate or refresh

From the repository root:

```bash
python berdl_import/scripts/generate_watershed_sfa_soil_moisture_schema.py \
  --data-dir berdl_import/data/berdl_import/watershed_sfa_soil_moisture \
  --schema-dir berdl_import/schema
```

The generated files are `ddt_ndarray_table.md`,
`sys_ddt_typedef_table.md`, and `watershed_sfa_soil_moisture_schema.md`.
