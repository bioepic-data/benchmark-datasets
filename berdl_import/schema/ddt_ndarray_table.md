# Table: bervodata_watershed_sfa_soil_moisture.ddt_ndarray

**Description:** Metadata for the WFSFA soil moisture observation array.

## Schema

| Column Name | Data Type | Nullable |
|-------------|-----------|----------|
| ddt_ndarray_id | string | No |
| ddt_ndarray_name | string | Yes |
| ddt_ndarray_description | string | Yes |
| ddt_ndarray_type_sys_oterm_id | string | Yes |
| ddt_ndarray_type_sys_oterm_name | string | Yes |
| ddt_ndarray_shape | string | Yes |
| ddt_ndarray_dimension_names | string | Yes |
| ddt_ndarray_dimension_types_sys_oterm_id | string | Yes |
| ddt_ndarray_dimension_types_sys_oterm_name | string | Yes |
| ddt_ndarray_dimension_variable_names | string | Yes |
| ddt_ndarray_dimension_variable_types_sys_oterm_id | string | Yes |
| ddt_ndarray_dimension_variable_types_sys_oterm_name | string | Yes |
| ddt_ndarray_variable_names | string | Yes |
| ddt_ndarray_variable_types_sys_oterm_id | string | Yes |
| ddt_ndarray_variable_types_sys_oterm_name | string | Yes |
| ddt_ndarray_metadata | string | Yes |
| superceded_by_ddt_ndarray_id | string | Yes |

**Total Rows:** 1

## Data

| ddt_ndarray_id | ddt_ndarray_name | ddt_ndarray_description | ddt_ndarray_type_sys_oterm_id | ddt_ndarray_type_sys_oterm_name | ddt_ndarray_shape | ddt_ndarray_dimension_names | ddt_ndarray_dimension_types_sys_oterm_id | ddt_ndarray_dimension_types_sys_oterm_name | ddt_ndarray_dimension_variable_names | ddt_ndarray_dimension_variable_types_sys_oterm_id | ddt_ndarray_dimension_variable_types_sys_oterm_name | ddt_ndarray_variable_names | ddt_ndarray_variable_types_sys_oterm_id | ddt_ndarray_variable_types_sys_oterm_name | ddt_ndarray_metadata | superceded_by_ddt_ndarray_id |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| watershed_sfa_soil_moisture_observation | watershed_sfa_soil_moisture_observation | Combined WFSFA harmonized soil moisture observation table. | BERVO:9000032 | Soil and water variable | NULL | dataset,location,time | BERVO:8000528,BERVO:8000394,BERVO:8000240 | Identifier,Location,DateTime | sdt_dataset_name,sdt_location_name,datetime_utc,depth_below_soil_surface_meter,replicate_series_count_unit | BERVO:8000528,BERVO:8000528,BERVO:8000240,BERVO:8000069,BERVO:8000237 | Identifier,Identifier,DateTime,Depth,Count | is_time_series,volumetric_water_content_ratio_unit,gravimetric_water_content_ratio_unit,soil_micropore_matric_water_potential_pascal | BERVO:8000300,BERVO:0001743,BERVO:0001810,BERVO:0001750 | Time series,Volumetric water content,Gravimetric water content,Soil micropore matric water potential | {"description": "Combined observation table for the manifest-declared harmonized ESS-DIVE soil moisture packages.", "source": "WFSFA harmonized soil moisture data"} | NULL |
