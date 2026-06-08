# Table: bervodata_watershed_sfa_soil_moisture.sys_ddt_typedef

**Description:** Column definitions for the WFSFA soil moisture dynamic data table.

## Schema

| Column Name | Data Type | Nullable |
|-------------|-----------|----------|
| ddt_ndarray_id | string | No |
| berdl_column_name | string | No |
| berdl_column_data_type | string | Yes |
| scalar_type | string | Yes |
| foreign_key | string | Yes |
| comment | string | Yes |
| unit_sys_oterm_id | string | Yes |
| unit_sys_oterm_name | string | Yes |
| dimension_number | bigint | Yes |
| dimension_oterm_id | string | Yes |
| dimension_oterm_name | string | Yes |
| variable_number | bigint | Yes |
| variable_oterm_id | string | Yes |
| variable_oterm_name | string | Yes |
| original_csv_string | string | Yes |

**Total Rows:** 10

## Data

| ddt_ndarray_id | berdl_column_name | berdl_column_data_type | scalar_type | foreign_key | comment | unit_sys_oterm_id | unit_sys_oterm_name | dimension_number | dimension_oterm_id | dimension_oterm_name | variable_number | variable_oterm_id | variable_oterm_name | original_csv_string |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| watershed_sfa_soil_moisture_observation | sdt_dataset_name | string | object_ref | sdt_dataset.sdt_dataset_name | Source ESS-DIVE dataset package. | NULL | NULL | 1 | BERVO:8000528 | Identifier | 1 | BERVO:8000528 | Identifier | dataset from harmonized CSV filename |
| watershed_sfa_soil_moisture_observation | sdt_location_name | string | object_ref | sdt_location.sdt_location_name | Dataset-specific source location. | NULL | NULL | 2 | BERVO:8000394 | Location | 2 | BERVO:8000528 | Identifier | site_id plus source dataset |
| watershed_sfa_soil_moisture_observation | datetime_utc | string | string | NULL | Observation timestamp in UTC. | NULL | NULL | 3 | BERVO:8000240 | DateTime | 3 | BERVO:8000240 | DateTime | datetime_UTC |
| watershed_sfa_soil_moisture_observation | depth_below_soil_surface_meter | double | numeric | NULL | Depth below soil surface. | UO:0000008 | meter | 4 | BERVO:8000069 | Depth | 4 | BERVO:8000069 | Depth | depth_m |
| watershed_sfa_soil_moisture_observation | replicate_series_count_unit | integer | numeric | NULL | Replicate index or count for repeated sensors/measurements. | UO:0000189 | count unit | 5 | BERVO:8000237 | Count | 5 | BERVO:8000237 | Count | replicate |
| watershed_sfa_soil_moisture_observation | is_time_series | boolean | boolean | NULL | Whether the record is part of a regular time series. | NULL | NULL | NULL | NULL | NULL | 1 | BERVO:8000300 | Time series | is_timeseries |
| watershed_sfa_soil_moisture_observation | time_interval_minute | double | numeric | NULL | Sampling interval for regular time series data. | UO:0000031 | minute | NULL | NULL | NULL | 2 | BERVO:8000238 | Time | interval_min |
| watershed_sfa_soil_moisture_observation | volumetric_water_content_ratio_unit | double | numeric | NULL | Volumetric water content. | UO:0000190 | ratio unit | NULL | NULL | NULL | 3 | BERVO:0001743 | Volumetric water content | volumetric_water_content_m3_m3 |
| watershed_sfa_soil_moisture_observation | gravimetric_water_content_ratio_unit | double | numeric | NULL | Gravimetric water content. | UO:0000190 | ratio unit | NULL | NULL | NULL | 4 | BERVO:0001810 | Gravimetric water content | gravimetric_water_content_gH2O_gs |
| watershed_sfa_soil_moisture_observation | soil_micropore_matric_water_potential_pascal | double | numeric | NULL | Soil water potential converted from kilopascals to pascals. | UO:0000110 | pascal | NULL | NULL | NULL | 5 | BERVO:0001750 | Soil micropore matric water potential | water_potential_kPa; multiply by 1000 to convert kPa to Pa |
