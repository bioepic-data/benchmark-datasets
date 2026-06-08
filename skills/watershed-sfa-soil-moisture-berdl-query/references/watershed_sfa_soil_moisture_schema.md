# Database Schema: bervodata_watershed_sfa_soil_moisture

Total Tables: 8

---

## Table: ddt_ndarray

**Table Description:** Metadata for the WFSFA soil moisture observation array.

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| ddt_ndarray_id | string | No | Unique identifier for the dynamic data array. |
| ddt_ndarray_name | string | Yes | Human-readable dynamic data array name. |
| ddt_ndarray_description | string | Yes | Description of the dynamic data array. |
| ddt_ndarray_type_sys_oterm_id | string | Yes | Ontology term CURIE for the dynamic data array type. |
| ddt_ndarray_type_sys_oterm_name | string | Yes | Ontology term name for the dynamic data array type. |
| ddt_ndarray_shape | string | Yes | Logical array shape. |
| ddt_ndarray_dimension_names | string | Yes | Comma-separated logical dimension names. |
| ddt_ndarray_dimension_types_sys_oterm_id | string | Yes | Comma-separated ontology term CURIEs for dimension types. |
| ddt_ndarray_dimension_types_sys_oterm_name | string | Yes | Comma-separated ontology term names for dimension types. |
| ddt_ndarray_dimension_variable_names | string | Yes | Comma-separated dimension variable column names. |
| ddt_ndarray_dimension_variable_types_sys_oterm_id | string | Yes | Comma-separated ontology term CURIEs for dimension variable types. |
| ddt_ndarray_dimension_variable_types_sys_oterm_name | string | Yes | Comma-separated ontology term names for dimension variable types. |
| ddt_ndarray_variable_names | string | Yes | Comma-separated measured or non-dimension variable names. |
| ddt_ndarray_variable_types_sys_oterm_id | string | Yes | Comma-separated ontology term CURIEs for measured or non-dimension variable types. |
| ddt_ndarray_variable_types_sys_oterm_name | string | Yes | Comma-separated ontology term names for measured or non-dimension variable types. |
| ddt_ndarray_metadata | string | Yes | JSON metadata for the dynamic data array. |
| superceded_by_ddt_ndarray_id | string | Yes | Replacement dynamic data array identifier, if superseded. |

**Total Rows:** 1

### Sample Data (5 rows)

| ddt_ndarray_id | ddt_ndarray_name | ddt_ndarray_description | ddt_ndarray_type_sys_oterm_id | ddt_ndarray_type_sys_oterm_name | ddt_ndarray_shape | ddt_ndarray_dimension_names | ddt_ndarray_dimension_types_sys_oterm_id | ddt_ndarray_dimension_types_sys_oterm_name | ddt_ndarray_dimension_variable_names | ddt_ndarray_dimension_variable_types_sys_oterm_id | ddt_ndarray_dimension_variable_types_sys_oterm_name | ddt_ndarray_variable_names | ddt_ndarray_variable_types_sys_oterm_id | ddt_ndarray_variable_types_sys_oterm_name | ddt_ndarray_metadata | superceded_by_ddt_ndarray_id |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| watershed_sfa_soil_moisture_observation | watershed_sfa_soil_moisture_observation | Combined WFSFA harmonized soil moisture observation table. | BERVO:9000032 | Soil and water variable | NULL | dataset,location,time | BERVO:8000528,BERVO:8000394,BERVO:8000240 | Identifier,Location,DateTime | sdt_dataset_name,sdt_location_name,datetime_utc,depth_below_soil_surface_meter,replicate_series_count_unit | BERVO:8000528,BERVO:8000528,BERVO:8000240,BERVO:8000069,BERVO:8000237 | Identifier,Identifier,DateTime,Depth,Count | is_time_series,time_interval_minute,volumetric_water_content_ratio_unit,gravimetric_water_content_ratio_unit,soil_micropore_matric_water_potential_pascal | BERVO:8000300,BERVO:8000238,BERVO:0001743,BERVO:0001810,BERVO:0001750 | Time series,Time,Volumetric water content,Gravimetric water content,Soil micropore matric water potential | {"description": "Combined observation table for 14 harmonized ESS-DIVE soil moisture packages.", "source": "WFSFA harmonized soil moisture data"} | NULL |

---

## Table: sys_ddt_typedef

**Table Description:** Column definitions for the WFSFA soil moisture dynamic data table.

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| ddt_ndarray_id | string | No | Unique identifier for the dynamic data array. |
| berdl_column_name | string | No | BERDL column name. |
| berdl_column_data_type | string | Yes | BERDL dynamic data column role or physical data type. |
| scalar_type | string | Yes | Logical scalar type. |
| foreign_key | string | Yes | Foreign key target for object reference columns. |
| comment | string | Yes | Human-readable field comment. |
| unit_sys_oterm_id | string | Yes | Unit ontology term CURIE. |
| unit_sys_oterm_name | string | Yes | Unit ontology term name. |
| dimension_number | bigint | Yes | Logical dimension number. |
| dimension_oterm_id | string | Yes | Dimension ontology term CURIE. |
| dimension_oterm_name | string | Yes | Dimension ontology term name. |
| variable_number | bigint | Yes | Logical variable number. |
| variable_oterm_id | string | Yes | Variable ontology term CURIE. |
| variable_oterm_name | string | Yes | Variable ontology term name. |
| original_csv_string | string | Yes | Original source or mapping string used to define the column. |

**Total Rows:** 10

### Sample Data (5 rows)

| ddt_ndarray_id | berdl_column_name | berdl_column_data_type | scalar_type | foreign_key | comment | unit_sys_oterm_id | unit_sys_oterm_name | dimension_number | dimension_oterm_id | dimension_oterm_name | variable_number | variable_oterm_id | variable_oterm_name | original_csv_string |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| watershed_sfa_soil_moisture_observation | sdt_dataset_name | string | object_ref | sdt_dataset.sdt_dataset_name | Source ESS-DIVE dataset package. | NULL | NULL | 1 | BERVO:8000528 | Identifier | 1 | BERVO:8000528 | Identifier | dataset from harmonized CSV filename |
| watershed_sfa_soil_moisture_observation | sdt_location_name | string | object_ref | sdt_location.sdt_location_name | Dataset-specific source location. | NULL | NULL | 2 | BERVO:8000394 | Location | 2 | BERVO:8000528 | Identifier | site_id plus source dataset |
| watershed_sfa_soil_moisture_observation | datetime_utc | string | string | NULL | Observation timestamp in UTC. | NULL | NULL | 3 | BERVO:8000240 | DateTime | 3 | BERVO:8000240 | DateTime | datetime_UTC |
| watershed_sfa_soil_moisture_observation | depth_below_soil_surface_meter | double | numeric | NULL | Depth below soil surface. | UO:0000008 | meter | 4 | BERVO:8000069 | Depth | 4 | BERVO:8000069 | Depth | depth_m |
| watershed_sfa_soil_moisture_observation | replicate_series_count_unit | integer | numeric | NULL | Replicate index or count for repeated sensors/measurements. | UO:0000189 | count unit | 5 | BERVO:8000237 | Count | 5 | BERVO:8000237 | Count | replicate |

---

## Table: ddt_soil_moisture_observation

**Table Description:** Combined harmonized WFSFA soil moisture observations from imported ESS-DIVE packages.

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_dataset_name | string | Yes | Source ESS-DIVE dataset package.; variable=Identifier <BERVO:8000528>; dimension=Identifier <BERVO:8000528>; foreign_key=sdt_dataset.sdt_dataset_name |
| sdt_location_name | string | Yes | Dataset-specific source location.; variable=Identifier <BERVO:8000528>; dimension=Location <BERVO:8000394>; foreign_key=sdt_location.sdt_location_name |
| datetime_utc | string | Yes | Observation timestamp in UTC.; variable=DateTime <BERVO:8000240>; dimension=DateTime <BERVO:8000240> |
| depth_below_soil_surface_meter | double | Yes | Depth below soil surface.; variable=Depth <BERVO:8000069>; dimension=Depth <BERVO:8000069>; unit=meter <UO:0000008> |
| replicate_series_count_unit | bigint | Yes | Replicate index or count for repeated sensors/measurements.; variable=Count <BERVO:8000237>; dimension=Count <BERVO:8000237>; unit=count unit <UO:0000189> |
| is_time_series | boolean | Yes | Whether the record is part of a regular time series.; variable=Time series <BERVO:8000300> |
| time_interval_minute | double | Yes | Sampling interval for regular time series data.; variable=Time <BERVO:8000238>; unit=minute <UO:0000031> |
| volumetric_water_content_ratio_unit | double | Yes | Volumetric water content.; variable=Volumetric water content <BERVO:0001743>; unit=ratio unit <UO:0000190> |
| gravimetric_water_content_ratio_unit | double | Yes | Gravimetric water content.; variable=Gravimetric water content <BERVO:0001810>; unit=ratio unit <UO:0000190> |
| soil_micropore_matric_water_potential_pascal | double | Yes | Soil water potential converted from kilopascals to pascals.; variable=Soil micropore matric water potential <BERVO:0001750>; unit=pascal <UO:0000110> |

**Total Rows:** 5000226

### Sample Data (5 rows)

| sdt_dataset_name | sdt_location_name | datetime_utc | depth_below_soil_surface_meter | replicate_series_count_unit | is_time_series | time_interval_minute | volumetric_water_content_ratio_unit | gravimetric_water_content_ratio_unit | soil_micropore_matric_water_potential_pascal |
|---|---|---|---|---|---|---|---|---|---|
| ess-dive-01092fc392bc46d-20240819T143818677 | ess-dive-01092fc392bc46d-20240819T143818677__PLM1 | 2017-05-06 06:00:00 | 0.3 | 1 | true | NULL | 0.387 | NULL | NULL |
| ess-dive-01092fc392bc46d-20240819T143818677 | ess-dive-01092fc392bc46d-20240819T143818677__PLM2 | 2017-05-06 06:00:00 | 0.28 | 1 | true | NULL | 0.39 | NULL | NULL |
| ess-dive-01092fc392bc46d-20240819T143818677 | ess-dive-01092fc392bc46d-20240819T143818677__PLM3 | 2017-05-06 06:00:00 | 0.2 | 1 | true | NULL | 0.39 | NULL | NULL |
| ess-dive-01092fc392bc46d-20240819T143818677 | ess-dive-01092fc392bc46d-20240819T143818677__PLM1 | 2017-05-15 06:00:00 | 0.3 | 1 | true | 12960 | 0.391 | NULL | NULL |
| ess-dive-01092fc392bc46d-20240819T143818677 | ess-dive-01092fc392bc46d-20240819T143818677__PLM2 | 2017-05-15 06:00:00 | 0.28 | 1 | true | 12960 | 0.391 | NULL | NULL |

---

## Table: sdt_dataset

**Table Description:** Dataset-level metadata for imported and reviewed ESS-DIVE WFSFA soil moisture packages.

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_dataset_id | string | No | Unique identifier for the dataset.; type=Identifier <BERVO:8000528> |
| sdt_dataset_name | string | No | Unique dataset name using the ESS-DIVE package identifier.; type=Identifier <BERVO:8000528> |
| doi_link | string | Yes | DOI link for the archived ESS-DIVE dataset.; type=Link <BERVO:8000391> |
| is_imported | boolean | No | Whether the dataset is included in the BERDL observation import.; type=Presence <BERVO:8000358> |
| import_decision_comment | string | Yes | Dataset-level inclusion or exclusion rationale.; type=Comment <BERVO:8000305> |
| depth_resolution_method | string | Yes | Dataset-level method used to resolve depth values.; type=Method <BERVO:8000303> |
| harmonized_file_name | string | Yes | Harmonized CSV filename.; type=Identifier <BERVO:8000528> |
| harmonized_file_download_link | string | Yes | Download URL for the harmonized CSV file.; type=Link <BERVO:8000391> |
| harmonized_file_size_byte | bigint | Yes | Size of the harmonized CSV file in bytes.; type=Size <BERVO:8000350>; unit=byte <UO:0000233> |
| harmonized_file_row_count | bigint | Yes | Number of observation rows in the harmonized CSV file.; type=Count <BERVO:8000237>; unit=count unit <UO:0000189> |
| harmonization_mapping_json | string | Yes | Raw harmonization mapping JSON for the source dataset.; type=Comment <BERVO:8000305> |

**Total Rows:** 28

### Sample Data (5 rows)

| sdt_dataset_id | sdt_dataset_name | doi_link | is_imported | import_decision_comment | depth_resolution_method | harmonized_file_name | harmonized_file_download_link | harmonized_file_size_byte | harmonized_file_row_count | harmonization_mapping_json |
|---|---|---|---|---|---|---|---|---|---|---|
| Dataset0000001 | ess-dive_b924ba040ecefee_20250707T154402200 | https://doi.org/10.15485/1660962 | false | None. This is a location identifier dataset from which we try to retrieve site locations when they are not reported in a data package. | NULL | NULL | NULL | NULL | NULL | {"archive_repository":"ESS-DIVE","data_payload_files":null,"dataset_identifier":"ess-dive_b924ba040ecefee_20250707T154402200","doi":"doi:10.15485/1660962","harmonization_mappings":"None. This is a location identifier dataset from which we try to retrieve site locations when they are not reported in a data package.","index":0,"location_metadata_files":["data/East_Taylor_Watershed_Community_Observatory_Sites___Point_Locations__Surface_v3_2_20250327.csv"],"sensor_metadata_files":null} |
| Dataset0000002 | ess-dive-beca0be9bb38ece-20250516T122010234 | https://doi.org/10.15485/2566877 | true | Included in BERDL import because a harmonized soil moisture CSV is available and parsed successfully. | Parse float j from '*_at_jcm'. Divide by 1e2 to convert from cm to m. | ess-dive-beca0be9bb38ece-20250516T122010234_harmonized.csv | https://drive.google.com/uc?id=1BBow4cLdOBG5JFB0lBsf2lUwwCvERHUU&export=download | 82783123 | 1324440 | {"archive_repository":"ESS-DIVE","data_payload_files":["ER_SMN1B.csv","ER_SMN3B.csv","ER_SMN4B.csv","ER_SMN5B.csv","ER_SMN10.csv","ER_SMN30.csv","ER_SMS1.csv","ER_SMS2.csv","ER_SMS3.csv"],"dataset_identifier":"ess-dive-beca0be9bb38ece-20250516T122010234","doi":"doi:10.15485/2566877","harmonization_mappings":{"datetime":{"pattern_1":{"destination_variable":"datetime_UTC","source_files":["ER_SMN1B.csv","ER_SMN3B.csv","ER_SMN4B.csv","ER_SMN5B.csv","ER_SMN10.csv","ER_SMN30.csv","ER_SMS1.csv","ER_SMS2.csv","ER_SMS3.csv"],"source_pattern":"Time","transformation":"Convert to ISO 8601 UTC format.","unit_conversion":null}},"depth":{"pattern_1":{"destination_variable":"depth_m","source_files":["ER_SMN1B.csv","ER_SMN3B.csv","ER_SMN4B.csv","ER_SMN5B.csv","ER_SMN10.csv","ER_SMN30.csv","ER_SMS1.csv","ER_SMS2.csv","ER_SMS3.csv"],"source_pattern":"*_at_jcm","transformation":"Parse float j from '*_at_jcm'.","unit_conversion":"Divide by 1e2 to convert from cm to m."}},"latitude":{"pattern_1":{"destination_variable":"latitude","source_files":["Sensor_Location.csv"],"source_pattern":"Northing","transformation":"Look up 'Northing' for 'site_id' in Sensor_Location.csv.","unit_conversion":"Reproject from EPSG:32613 (WGS84 UTM Zone 13N, meters) to EPSG:4326 (WGS84, decimal degrees)."}},"longitude":{"pattern_1":{"destination_variable":"longitude","source_files":["Sensor_Location.csv"],"source_pattern":"Easting","transformation":"Look up 'Easting' for 'site_id' in Sensor_Location.csv.","unit_conversion":"Reproject from EPSG:32613 (WGS84 UTM Zone 13N, meters) to EPSG:4326 (WGS84, decimal degrees)."}},"replicate":{"pattern_1":{"destination_variable":"replicate","source_files":["ER_SMN1B.csv","ER_SMN3B.csv","ER_SMN4B.csv","ER_SMN5B.csv","ER_SMN10.csv","ER_SMN30.csv","ER_SMS1.csv","ER_SMS2.csv","ER_SMS3.csv"],"source_pattern":"*_i_at_jcm","transformation":"Parse integer i from '*_i_at_jcm'.","unit_conversion":null}},"site_id":{"pattern_1":{"destination_variable":"site_id","source_files":null,"source_pattern":null,"transformation":"Parse site_id from source filename (e.g., 'ER_SMN1B' from 'ER_SMN1B.csv').","unit_conversion":null}},"soil_water_potential":{"pattern_1":{"destination_variable":"water_potential_kPa","source_files":["ER_SMN1B.csv","ER_SMN3B.csv","ER_SMN4B.csv","ER_SMN5B.csv","ER_SMN10.csv","ER_SMN30.csv","ER_SMS1.csv","ER_SMS2.csv","ER_SMS3.csv"],"source_pattern":"kPa_Potential_i_at_jcm","transformation":"Coerce from 'wide' format with column variables containing depth and replicate information to 'long' format with separate columns for depth, replicate, and water potential.","unit_conversion":"None; source units are kPa."}},"volumetric_water_content":{"pattern_1":{"destination_variable":"volumetric_water_content_m3_m3","source_files":["ER_SMN1B.csv","ER_SMN3B.csv","ER_SMN10.csv","ER_SMN30.csv","ER_SMS1.csv","ER_SMS2.csv","ER_SMS3.csv"],"source_pattern":"m3_m3_Water_Content_i_at_jcm","transformation":"Coerce from 'wide' format with column variables containing depth and replicate information to 'long' format with separate columns for depth, replicate, and volumetric water content.","unit_conversion":"None; source units are m3/m3."},"pattern_2":{"destination_variable":"volumetric_water_content_m3_m3","source_files":["ER_SMN4B.csv","ER_SMN5B.csv"],"source_pattern":"m3_m3_VWC_at_jcm","transformation":"Coerce from 'wide' format with column variables containing depth and replicate information to 'long' format with separate columns for depth, replicate, and volumetric water content.","unit_conversion":"None; source units are m3/m3."}}},"index":1,"location_metadata_files":["Sensor_Location.csv"],"sensor_metadata_files":null} |
| Dataset0000003 | ess-dive-9fd65df885a8e87-20250715T064942543 | https://doi.org/10.15485/1646477 | true | Included in BERDL import because a harmonized soil moisture CSV is available and parsed successfully. | Parse float j from '*_at_jcm'. Divide by 1e2 to convert from cm to m. | ess-dive-9fd65df885a8e87-20250715T064942543_harmonized.csv | https://drive.google.com/uc?id=1IXIu8PWXvBED2z8HasTK1Swz2esmGg5f&export=download | 8853783 | 154242 | {"archive_repository":"ESS-DIVE","data_payload_files":["ER_SMN1.csv","ER_SMN3.csv","ER_SMN4.csv","ER_SMN5.csv"],"dataset_identifier":"ess-dive-9fd65df885a8e87-20250715T064942543","doi":"doi:10.15485/1646477","harmonization_mappings":{"datetime":{"pattern_1":{"destination_variable":"datetime_UTC","source_files":["ER_SMN1.csv","ER_SMN3.csv","ER_SMN4.csv","ER_SMN5.csv"],"source_pattern":"DateTime","transformation":"Convert to ISO 8601 UTC format.","unit_conversion":null}},"depth":{"pattern_1":{"destination_variable":"depth_m","source_files":["ER_SMN1.csv","ER_SMN3.csv","ER_SMN4.csv","ER_SMN5.csv"],"source_pattern":"*_at_jcm","transformation":"Parse float j from '*_at_jcm'.","unit_conversion":"Divide by 1e2 to convert from cm to m."}},"latitude":{"pattern_1":{"destination_variable":"latitude","source_files":["SM_loc.csv"],"source_pattern":"Northing","transformation":"Look up 'Northing' for 'site_id' in SM_loc.csv.","unit_conversion":null}},"longitude":{"pattern_1":{"destination_variable":"longitude","source_files":["SM_loc.csv"],"source_pattern":"Easting","transformation":"Look up 'Easting' for 'site_id' in SM_loc.csv.","unit_conversion":null}},"replicate":{"pattern_1":{"destination_variable":"replicate","source_files":["ER_SMN1.csv","ER_SMN3.csv","ER_SMN4.csv","ER_SMN5.csv"],"source_pattern":"*_i_at_jcm","transformation":"Parse integer i from '*_i_at_jcm'.","unit_conversion":null}},"site_id":{"pattern_1":{"destination_variable":"site_id","source_files":null,"source_pattern":null,"transformation":"Parse site_id from source filename (e.g., 'ER_SMN1' from 'ER_SMN1.csv').","unit_conversion":null}},"soil_water_potential":{"pattern_1":{"destination_variable":"water_potential_kPa","source_files":null,"source_pattern":null,"transformation":null,"unit_conversion":null}},"volumetric_water_content":{"pattern_1":{"destination_variable":"volumetric_water_content_m3_m3","source_files":["ER_SMN1.csv","ER_SMN3.csv","ER_SMN4.csv","ER_SMN5.csv"],"source_pattern":"m3_m3_Water_Content_i_at_jcm","transformation":"Coerce from 'wide' format with column variables containing depth and replicate information to 'long' format with separate columns for depth, replicate, and volumetric water content.","unit_conversion":"None; source units are m3/m3."}}},"index":2,"location_metadata_files":["SM_loc.csv"],"sensor_metadata_files":null} |
| Dataset0000004 | ess-dive-4c1829de1b8a2ec-20260220T045039633 | https://doi.org/10.15485/2998779 | true | Included in BERDL import because a harmonized soil moisture CSV is available and parsed successfully. | Parse float j from '*.jcm_*'. Divide by 1e2 to convert from cm to m. | ess-dive-4c1829de1b8a2ec-20260220T045039633_harmonized.csv | https://drive.google.com/uc?id=1k3-KU_q6VoSnS6htPzctsI8fOcSAt8w4&export=download | 7819634 | 139770 | {"archive_repository":"ESS-DIVE","data_payload_files":["Soil_water_potential.csv"],"dataset_identifier":"ess-dive-4c1829de1b8a2ec-20260220T045039633","doi":"doi:10.15485/2998779","harmonization_mappings":{"datetime":{"pattern_1":{"destination_variable":"datetime_UTC","source_files":["Soil_water_potential.csv"],"source_pattern":"TIMESTAMP","transformation":"Convert to ISO 8601 UTC format.","unit_conversion":null}},"depth":{"pattern_1":{"destination_variable":"depth_m","source_files":["Soil_water_potential.csv"],"source_pattern":"*.jcm_*","transformation":"Parse float j from '*.jcm_*'.","unit_conversion":"Divide by 1e2 to convert from cm to m."}},"latitude":{"pattern_1":{"destination_variable":"latitude","source_files":["locations.csv"],"source_pattern":"Latitude","transformation":"Look up 'Latitude' for 'site_id' in locations.csv.","unit_conversion":null}},"longitude":{"pattern_1":{"destination_variable":"longitude","source_files":["locations.csv"],"source_pattern":"Longitude","transformation":"Look up 'Longitude' for 'site_id' in locations.csv.","unit_conversion":null}},"replicate":{"pattern_1":{"destination_variable":"replicate","source_files":["Soil_water_potential.csv"],"source_pattern":"SDi.jcm_*","transformation":"Group by 'datetime_UTC' and 'depth_m' and increment number of observations per grouping.","unit_conversion":null}},"site_id":{"pattern_1":{"destination_variable":"site_id","source_files":null,"source_pattern":null,"transformation":"Parse site_id from 'Location_ID' in locations.csv.","unit_conversion":null}},"soil_water_potential":{"pattern_1":{"destination_variable":"water_potential_kPa","source_files":["Soil_water_potential.csv"],"source_pattern":"SDi.jcm_MP","transformation":"Coerce from 'wide' format with column variables containing depth and replicate information to 'long' format with separate columns for depth, replicate, and water potential.","unit_conversion":"None; source units are kPa."},"pattern_2":{"destination_variable":"water_potential_kPa","source_files":["Soil_water_potential.csv"],"source_pattern":"SD1.25cm_sagebrush_rhizo_MP_5_Avg","transformation":"Coerce from 'wide' format with column variables containing depth and replicate information to 'long' format with separate columns for depth, replicate, and water potential.","unit_conversion":"None; source units are kPa."}},"volumetric_water_content":{"pattern_1":{"destination_variable":"volumetric_water_content_m3_m3","source_files":null,"source_pattern":null,"transformation":"None; volumetric water content not reported in source. Populate with NA.","unit_conversion":null}}},"index":3,"location_metadata_files":["locations.csv"],"sensor_metadata_files":null} |
| Dataset0000005 | ess-dive-6c7085e9c544cc6-20250424T164534831 | https://doi.org/10.15485/2561511 | true | Included in BERDL import because a harmonized soil moisture CSV is available and parsed successfully. | None; depth information not provided in source. Populate with NA. | ess-dive-6c7085e9c544cc6-20250424T164534831_harmonized.csv | https://drive.google.com/uc?id=1cGFs8XcprrK2LoEh3360kM2fpGbNHecV&export=download | 32018 | 552 | {"archive_repository":"ESS-DIVE","data_payload_files":["Johnsen_Bi_2025_DAE_Manuscript_Data_Package/df_data.csv"],"dataset_identifier":"ess-dive-6c7085e9c544cc6-20250424T164534831","doi":"doi:10.15485/2561511","harmonization_mappings":{"datetime":{"pattern_1":{"destination_variable":"datetime_UTC","source_files":["Johnsen_Bi_2025_DAE_Manuscript_Data_Package/df_data.csv"],"source_pattern":"datetime","transformation":"Convert to ISO 8601 UTC format.","unit_conversion":null}},"depth":{"pattern_1":{"destination_variable":"depth_m","source_files":null,"source_pattern":null,"transformation":"None; depth information not provided in source. Populate with NA.","unit_conversion":null}},"latitude":{"pattern_1":{"destination_variable":"latitude","source_files":null,"source_pattern":null,"transformation":"Geospatial information not provided in data files. Look up in ESS-DIVE package metadata.","unit_conversion":null}},"longitude":{"pattern_1":{"destination_variable":"longitude","source_files":null,"source_pattern":null,"transformation":"Geospatial information not provided in data files. Look up in ESS-DIVE package metadata.","unit_conversion":null}},"replicate":{"pattern_1":{"destination_variable":"replicate","source_files":null,"source_pattern":null,"transformation":"None; replicate information not provided in source. Populate with 1.","unit_conversion":null}},"site_id":{"pattern_1":{"destination_variable":"site_id","source_files":["Johnsen_Bi_2025_DAE_Manuscript_Data_Package/df_meta.csv"],"source_pattern":"site","transformation":"Parse site_id from 'site' in df_meta.csv.","unit_conversion":null}},"soil_water_potential":{"pattern_1":{"destination_variable":"water_potential_kPa","source_files":["Johnsen_Bi_2025_DAE_Manuscript_Data_Package/df_data.csv"],"source_pattern":"swp","transformation":"Rename variable.","unit_conversion":"None; source units are kPa."}},"volumetric_water_content":{"pattern_1":{"destination_variable":"volumetric_water_content_m3_m3","source_files":["Johnsen_Bi_2025_DAE_Manuscript_Data_Package/df_data.csv"],"source_pattern":"swc","transformation":"Rename variable.","unit_conversion":"None; source units are m3/m3."}}},"index":4,"location_metadata_files":["Johnsen_Bi_2025_DAE_Manuscript_Data_Package/df_meta.csv"],"sensor_metadata_files":null} |

---

## Table: sdt_harmonized_location

**Table Description:** Harmonized location records keyed by harmonized location UUID.

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_harmonized_location_id | string | No | Unique identifier for the harmonized location.; type=Identifier <BERVO:8000528> |
| sdt_harmonized_location_name | string | No | Unique harmonized location name.; type=Identifier <BERVO:8000528> |
| latitude_degree | double | Yes | Harmonized latitude in decimal degrees.; type=Latitude <BERVO:8000395>; unit=degree <UO:0000185> |
| longitude_degree | double | Yes | Harmonized longitude in decimal degrees.; type=Longitude <BERVO:8000396>; unit=degree <UO:0000185> |
| records_in_harmonized_location_count_unit | bigint | Yes | Number of source location records in this harmonized location.; type=Count <BERVO:8000237>; unit=count unit <UO:0000189> |
| datasets_in_harmonized_location_count_unit | bigint | Yes | Number of source datasets represented in this harmonized location.; type=Count <BERVO:8000237>; unit=count unit <UO:0000189> |

**Total Rows:** 628

### Sample Data (5 rows)

| sdt_harmonized_location_id | sdt_harmonized_location_name | latitude_degree | longitude_degree | records_in_harmonized_location_count_unit | datasets_in_harmonized_location_count_unit |
|---|---|---|---|---|---|
| HarmonizedLocation0000001 | d056fc12-7cc4-436f-aee1-cb02fbdc449e | 38.9314213 | -106.98524 | 1 | 1 |
| HarmonizedLocation0000002 | c89da75b-748d-447e-841d-1b2382d66a94 | 38.9261964 | -106.97144 | 1 | 1 |
| HarmonizedLocation0000003 | 29ee28ea-0f43-44a0-be3a-eeff39e22f1d | 38.9283998 | -106.97812 | 1 | 1 |
| HarmonizedLocation0000004 | 71fc9bdc-641f-4799-8c88-ea1865b13367 | 38.9274479 | -106.97852 | 1 | 1 |
| HarmonizedLocation0000005 | 14c81ef7-d65d-4d4b-bb95-05e642b685a4 | 38.98715 | -107.003863 | 1 | 1 |

---

## Table: sdt_location

**Table Description:** Dataset-specific source locations mapped to harmonized locations.

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sdt_location_id | string | No | Unique identifier for the dataset-specific source location.; type=Identifier <BERVO:8000528> |
| sdt_location_name | string | No | Unique source location name used by observation rows.; type=Identifier <BERVO:8000528> |
| sdt_harmonized_location_name | string | No | Harmonized location reference.; type=Identifier <BERVO:8000528>; foreign_key=Harmonized_Location |
| sdt_dataset_name | string | No | Source dataset reference.; type=Identifier <BERVO:8000528>; foreign_key=Dataset |
| site_identifier | string | No | Source site identifier from the harmonized location file.; type=Identifier <BERVO:8000528> |
| latitude_degree | double | Yes | Source location latitude in decimal degrees.; type=Latitude <BERVO:8000395>; unit=degree <UO:0000185> |
| longitude_degree | double | Yes | Source location longitude in decimal degrees.; type=Longitude <BERVO:8000396>; unit=degree <UO:0000185> |
| geolocation_resolution_method | string | Yes | Method used to resolve source geolocation.; type=Method <BERVO:8000303> |

**Total Rows:** 1513

### Sample Data (5 rows)

| sdt_location_id | sdt_location_name | sdt_harmonized_location_name | sdt_dataset_name | site_identifier | latitude_degree | longitude_degree | geolocation_resolution_method |
|---|---|---|---|---|---|---|---|
| Location0000001 | ess-dive-18e91eb74405882-20241017T173226640__high_conifer | d056fc12-7cc4-436f-aee1-cb02fbdc449e | ess-dive-18e91eb74405882-20241017T173226640 | high_conifer | 38.9314213 | -106.98524 | Geolocation reported or directly resolved in the source package harmonization. |
| Location0000002 | ess-dive-18e91eb74405882-20241017T173226640__low_aspen | c89da75b-748d-447e-841d-1b2382d66a94 | ess-dive-18e91eb74405882-20241017T173226640 | low_aspen | 38.9261964 | -106.97144 | Geolocation reported or directly resolved in the source package harmonization. |
| Location0000003 | ess-dive-18e91eb74405882-20241017T173226640__middle_aspen | 29ee28ea-0f43-44a0-be3a-eeff39e22f1d | ess-dive-18e91eb74405882-20241017T173226640 | middle_aspen | 38.9283998 | -106.97812 | Geolocation reported or directly resolved in the source package harmonization. |
| Location0000004 | ess-dive-18e91eb74405882-20241017T173226640__middle_conifer | 71fc9bdc-641f-4799-8c88-ea1865b13367 | ess-dive-18e91eb74405882-20241017T173226640 | middle_conifer | 38.9274479 | -106.97852 | Geolocation reported or directly resolved in the source package harmonization. |
| Location0000005 | ess-dive-38e901ec3d7bd24-20230504T211548257225__BM | 14c81ef7-d65d-4d4b-bb95-05e642b685a4 | ess-dive-38e901ec3d7bd24-20230504T211548257225 | BM | 38.98715 | -107.003863 | Geolocation reported or directly resolved in the source package harmonization. |

---

## Table: sys_oterm

**Table Description:** Ontology terms from the BERVO and UO sources used by this database.

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| sys_oterm_id | string | No | Ontology term CURIE. |
| parent_sys_oterm_id | string | Yes | Parent ontology term CURIE. |
| sys_oterm_ontology | string | No | Ontology namespace for the term. |
| sys_oterm_name | string | Yes | Ontology term name. |
| sys_oterm_synonyms | string | Yes | JSON array of ontology term synonyms. |
| sys_oterm_definition | string | Yes | Ontology term definition. |
| sys_oterm_links | string | Yes | JSON array of ontology xrefs or links. |
| sys_oterm_properties | string | Yes | JSON object containing additional ontology properties. |

**Total Rows:** 2918

### Sample Data (5 rows)

| sys_oterm_id | parent_sys_oterm_id | sys_oterm_ontology | sys_oterm_name | sys_oterm_synonyms | sys_oterm_definition | sys_oterm_links | sys_oterm_properties |
|---|---|---|---|---|---|---|---|
| BERVO:0000000 | NULL | BERVO | Variable | [] | An observed or calculated property of a system. In BERVO, variables generally correspond to anything subject to change in an experiment or direct observation of an environment or other natural phenomenon. | [] | {"comment": ["Definition Curated"], "property_value": ["BERVO:Attribute http://www.w3.org/2002/07/NA", "BERVO:Context http://www.w3.org/2002/07/NA", "BERVO:has_unit \"NA\" xsd:string", "BERVO:measured_in http://www.w3.org/2002/07/NA", "BERVO:measurement_of http://www.w3.org/2002/07/NA", "BERVO:Qualifier http://www.w3.org/2002/07/NA"]} |
| BERVO:0000001 | BERVO:9000000 | BERVO | Ecosystem net radiation | ["Eco_NetRad_col"] | EcoSIM output: The balance between incoming solar shortwave radiation and atmospheric longwave radiation versus reflected shortwave radiation and outgoing longwave radiation from terrestrial surfaces and vegetation. This quantity is fundamental for calculating the energy budget of ecosystems and drives evapotranspiration, photosynthesis, and soil temperature dynamics in Earth system models. | [] | {"comment": ["Definition source - Claude Sonnet 4 through GitHub Copilot in VSCode (Sep 25 2025)"], "property_value": ["BERVO:Attribute BERVO:8000531", "BERVO:Context BERVO:8000043", "BERVO:has_unit \"MJ d-2 h-1\" xsd:string", "BERVO:has_value_type BERVO:8000244", "BERVO:measured_in BERVO:8000021", "BERVO:measured_in BERVO:8000131", "BERVO:measurement_of BERVO:8000132", "BERVO:Qualifier BERVO:8000262"]} |
| BERVO:0000002 | BERVO:0001854 | BERVO | Ecosystem latent heat flux | ["Eco_Heat_Latent_col"] | EcoSIM output: The energy transfer associated with water vapor movement from terrestrial surfaces to the atmosphere through evapotranspiration processes. This flux represents a major component of the surface energy balance and is critical for understanding water cycle dynamics and climate feedbacks in Earth system models. | [] | {"comment": ["Definition source - Claude Sonnet 4 through GitHub Copilot in VSCode (Sep 25 2025)"], "property_value": ["BERVO:Attribute BERVO:8000273", "BERVO:Context BERVO:8000043", "BERVO:has_unit \"MJ d-2 h-1\" xsd:string", "BERVO:has_value_type BERVO:8000244", "BERVO:measured_in BERVO:8000131", "BERVO:measurement_of BERVO:8000092", "BERVO:Qualifier http://www.w3.org/2002/07/NA"]} |
| BERVO:0000003 | BERVO:0001854 | BERVO | Ecosystem sensible heat flux | ["Eco_Heat_Sens_col"] | EcoSIM output: The direct transfer of thermal energy between the atmosphere and land surface entities including ground surface and vegetation through conduction and convection. This flux component controls air temperature dynamics and atmospheric boundary layer development in environmental modeling studies. | [] | {"comment": ["Definition source - Claude Sonnet 4 through GitHub Copilot in VSCode (Sep 25 2025)"], "property_value": ["BERVO:Attribute BERVO:8000273", "BERVO:Context BERVO:8000043", "BERVO:has_unit \"MJ d-2 h-1\" xsd:string", "BERVO:has_value_type BERVO:8000244", "BERVO:measured_in BERVO:8000062", "BERVO:measured_in BERVO:8000131", "BERVO:measurement_of BERVO:8000092", "BERVO:Qualifier http://www.w3.org/2002/07/NA"]} |
| BERVO:0000004 | BERVO:0001854 | BERVO | Ecosystem storage heat flux | ["Eco_Heat_GrndSurf_col"] | EcoSIM output: The residual energy flux absorbed by the ground calculated by subtracting latent and sensible heat fluxes from net radiation. This flux drives soil temperature changes and affects subsurface thermal dynamics, root zone processes, and permafrost behavior in Earth system models. | [] | {"comment": ["Definition source - Claude Sonnet 4 through GitHub Copilot in VSCode (Sep 25 2025)"], "property_value": ["BERVO:Attribute BERVO:8000273", "BERVO:Context BERVO:8000043", "BERVO:Context BERVO:8000062", "BERVO:has_unit \"MJ d-2 h-1\" xsd:string", "BERVO:has_value_type BERVO:8000244", "BERVO:measured_in BERVO:8000062", "BERVO:measurement_of BERVO:8000092", "BERVO:Qualifier http://www.w3.org/2002/07/NA"]} |

---

## Table: sys_typedef

**Table Description:** Column definitions for static data tables in this database.

### Schema

| Column Name | Data Type | Nullable | Comment |
|-------------|-----------|----------|----------|
| type_name | string | No | Static data type name. |
| field_name | string | No | Source field name. |
| berdl_column_name | string | No | BERDL column name. |
| scalar_type | string | Yes | Logical scalar type. |
| is_required | boolean | Yes | Whether the field is required. |
| is_pk | boolean | Yes | Whether the field is a primary key. |
| is_upk | boolean | Yes | Whether the field is a unique public key. |
| fk | string | Yes | Referenced static data type or table. |
| constraint | string | Yes | Additional field constraint. |
| comment | string | Yes | Human-readable field comment. |
| units_sys_oterm_id | string | Yes | Unit ontology term CURIE. |
| units_sys_oterm_name | string | Yes | Unit ontology term name. |
| type_sys_oterm_id | string | Yes | Field type ontology term CURIE. |
| type_sys_oterm_name | string | Yes | Field type ontology term name. |

**Total Rows:** 25

### Sample Data (5 rows)

| type_name | field_name | berdl_column_name | scalar_type | is_required | is_pk | is_upk | fk | constraint | comment | units_sys_oterm_id | units_sys_oterm_name | type_sys_oterm_id | type_sys_oterm_name |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Dataset | id | sdt_dataset_id | text | true | true | false | NULL | NULL | Unique identifier for the dataset. | NULL | NULL | BERVO:8000528 | Identifier |
| Dataset | name | sdt_dataset_name | text | true | false | true | NULL | NULL | Unique dataset name using the ESS-DIVE package identifier. | NULL | NULL | BERVO:8000528 | Identifier |
| Dataset | doi_link | doi_link | text | false | false | false | NULL | NULL | DOI link for the archived ESS-DIVE dataset. | NULL | NULL | BERVO:8000391 | Link |
| Dataset | is_imported | is_imported | boolean | true | false | false | NULL | NULL | Whether the dataset is included in the BERDL observation import. | NULL | NULL | BERVO:8000358 | Presence |
| Dataset | import_decision_comment | import_decision_comment | text | false | false | false | NULL | NULL | Dataset-level inclusion or exclusion rationale. | NULL | NULL | BERVO:8000305 | Comment |

---

