#!/usr/bin/env python3
"""Build BERDL-ready import files for WFSFA harmonized soil moisture data."""

from __future__ import annotations

import csv
import json
import re
from collections import OrderedDict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parent
SOURCE_METADATA_DIR = REPO_ROOT / "data/processed/ess-dive_wfsfa_soil_datasets"
DOWNLOADED_SOURCE_DIR = ROOT / "downloaded_data/ess-dive_wfsfa_soil_datasets"
HARMONIZED_DIR = DOWNLOADED_SOURCE_DIR / "harmonized_soil_moisture_data"
OUT_DIR = ROOT / "data/berdl_import/watershed_sfa_soil_moisture"
DDT_NDARRAY_ID = "watershed_sfa_soil_moisture_observation"
OBO_SOURCES = [
    ("BERVO", Path("/h/jmc/data/bioepic/chess/ontologies/bervo_github/bervo.obo")),
    ("UO", Path("/h/jmc/data/bioepic/chess/ontologies/uo/uo.obo")),
]


TERMS = {
    "BERVO:0001743": ("BERVO", "Volumetric water content"),
    "BERVO:0001750": ("BERVO", "Soil micropore matric water potential"),
    "BERVO:0001810": ("BERVO", "Gravimetric water content"),
    "BERVO:8000069": ("BERVO", "Depth"),
    "BERVO:8000237": ("BERVO", "Count"),
    "BERVO:8000238": ("BERVO", "Time"),
    "BERVO:8000240": ("BERVO", "DateTime"),
    "BERVO:8000300": ("BERVO", "Time series"),
    "BERVO:8000303": ("BERVO", "Method"),
    "BERVO:8000305": ("BERVO", "Comment"),
    "BERVO:8000350": ("BERVO", "Size"),
    "BERVO:8000358": ("BERVO", "Presence"),
    "BERVO:8000391": ("BERVO", "Link"),
    "BERVO:8000394": ("BERVO", "Location"),
    "BERVO:8000395": ("BERVO", "Latitude"),
    "BERVO:8000396": ("BERVO", "Longitude"),
    "BERVO:8000528": ("BERVO", "Identifier"),
    "UO:0000008": ("UO", "meter"),
    "UO:0000031": ("UO", "minute"),
    "UO:0000110": ("UO", "pascal"),
    "UO:0000185": ("UO", "degree"),
    "UO:0000189": ("UO", "count unit"),
    "UO:0000190": ("UO", "ratio unit"),
    "UO:0000233": ("UO", "byte"),
}


def clean(value) -> str:
    if value is None:
        return ""
    value = str(value).strip()
    if value in {"", "NA", "NaN", "nan", "None", "NULL", "null"}:
        return ""
    return value


def float_string(value, multiplier: float = 1.0) -> str:
    value = clean(value)
    if not value:
        return ""
    return f"{float(value) * multiplier:.15g}"


def bool_string(value) -> str:
    value = clean(value).lower()
    if value in {"true", "t", "1", "yes"}:
        return "true"
    if value in {"false", "f", "0", "no"}:
        return "false"
    return ""


def dataset_id_from_file(path: Path) -> str:
    return path.name.removesuffix("_harmonized.csv")


def safe_name(*parts: str) -> str:
    raw = "__".join(clean(p) for p in parts if clean(p))
    return re.sub(r"[^A-Za-z0-9_.:-]+", "_", raw)


def read_harmonized_manifest() -> dict[str, str]:
    out: dict[str, str] = {}
    manifest = SOURCE_METADATA_DIR / "ess-dive_harmonized_soil_urls.csv"
    with manifest.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            filename = clean(row.get("filename"))
            url = clean(row.get("url"))
            if filename.endswith("_harmonized.csv"):
                out[filename.removesuffix("_harmonized.csv")] = url
            elif filename == "location_data_harmonized_with_uuid.csv":
                out[filename] = url
    return out


def row_count(path: Path) -> int:
    with path.open("rb") as fh:
        return max(sum(block.count(b"\n") for block in iter(lambda: fh.read(1 << 20), b"")) - 1, 0)


def load_mapping() -> list[dict]:
    with (SOURCE_METADATA_DIR / "sm_data_harmonization_mapping.json").open(encoding="utf-8") as fh:
        return json.load(fh)


def load_location_rows() -> list[dict]:
    path = DOWNLOADED_SOURCE_DIR / "location_data_harmonized_with_uuid.csv"
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def observed_location_pairs() -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for path in sorted(HARMONIZED_DIR.glob("*_harmonized.csv")):
        dataset_name = dataset_id_from_file(path)
        with path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                site_id = clean(row.get("site_id"))
                if site_id:
                    pairs.add((dataset_name, site_id))
    return pairs


def depth_method(entry: dict) -> str:
    hm = entry.get("harmonization_mappings")
    if not isinstance(hm, dict):
        return ""
    depth = hm.get("depth")
    if not isinstance(depth, dict):
        return ""
    parts = []
    for _, spec in sorted(depth.items()):
        transformation = clean(spec.get("transformation"))
        unit_conversion = clean(spec.get("unit_conversion"))
        if transformation and unit_conversion:
            parts.append(f"{transformation} {unit_conversion}")
        elif transformation:
            parts.append(transformation)
        elif unit_conversion:
            parts.append(unit_conversion)
    return " ".join(parts)


def location_method(qc_flag: str) -> str:
    qc_flag = clean(qc_flag)
    if not qc_flag:
        return "Geolocation reported or directly resolved in the source package harmonization."
    if qc_flag == "g1":
        return "Geolocation not reported in the source package; retrieved from the Varadharajan et al. location registration data."
    if qc_flag == "g2":
        return "Geolocation not reported in the source package and not otherwise available."
    return f"Geolocation resolution flag from harmonization workflow: {qc_flag}."


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: clean(row.get(k, "")) for k in fieldnames})


def normalize_oterm_id(value: str) -> str:
    value = clean(value)
    value = re.sub(r"\bbervo:BERVO_", "BERVO:", value)
    value = re.sub(r"\bBERVO_", "BERVO:", value)
    return value


def obo_quoted_value(value: str) -> str:
    match = re.match(r'^[^"]*"((?:[^"\\]|\\.)*)"', value)
    if not match:
        return clean(value)
    return match.group(1).replace(r"\"", '"')


def parse_obo_terms(path: Path, ontology_name: str) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Ontology source not found: {path}")

    rows = []
    current: dict | None = None
    in_term = False

    def flush() -> None:
        nonlocal current
        if not current or not current.get("sys_oterm_id"):
            current = None
            return
        rows.append({
            "sys_oterm_id": current["sys_oterm_id"],
            "parent_sys_oterm_id": current.get("parent_sys_oterm_id", ""),
            "sys_oterm_ontology": current.get("sys_oterm_ontology", ontology_name),
            "sys_oterm_name": current.get("sys_oterm_name", ""),
            "sys_oterm_synonyms": json.dumps(current.get("synonyms", []), sort_keys=True),
            "sys_oterm_definition": current.get("sys_oterm_definition", ""),
            "sys_oterm_links": json.dumps(current.get("links", []), sort_keys=True),
            "sys_oterm_properties": json.dumps(current.get("properties", {}), sort_keys=True) if current.get("properties") else "",
        })
        current = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line == "[Term]":
            flush()
            current = {
                "sys_oterm_ontology": ontology_name,
                "synonyms": [],
                "links": [],
                "properties": {},
            }
            in_term = True
            continue
        if line.startswith("[") and line.endswith("]"):
            flush()
            in_term = False
            continue
        if not in_term or current is None or not line or line.startswith("!"):
            continue

        key, sep, value = line.partition(": ")
        if not sep:
            continue
        if key == "id":
            term_id = normalize_oterm_id(value)
            current["sys_oterm_id"] = term_id
            current["sys_oterm_ontology"] = term_id.partition(":")[0] or ontology_name
        elif key == "name":
            current["sys_oterm_name"] = clean(value)
        elif key == "def":
            current["sys_oterm_definition"] = obo_quoted_value(value)
        elif key == "synonym":
            current["synonyms"].append(obo_quoted_value(value))
        elif key == "xref":
            current["links"].append(normalize_oterm_id(value))
        elif key == "is_a" and not current.get("parent_sys_oterm_id"):
            parent = value.split("!", 1)[0].strip()
            current["parent_sys_oterm_id"] = normalize_oterm_id(parent)
        elif key in {"property_value", "is_obsolete", "comment", "alt_id"}:
            properties = current["properties"]
            properties.setdefault(key, []).append(normalize_oterm_id(value))
    flush()
    return rows


def build_sdt_dataset(mapping: list[dict], manifest: dict[str, str]) -> list[dict]:
    csv_paths = {dataset_id_from_file(p): p for p in sorted(HARMONIZED_DIR.glob("*_harmonized.csv"))}
    rows = []
    for i, entry in enumerate(mapping, start=1):
        dataset_name = clean(entry.get("dataset_identifier"))
        if not dataset_name:
            continue
        is_imported = dataset_name in csv_paths
        doi = clean(entry.get("doi"))
        doi_link = f"https://doi.org/{doi.removeprefix('doi:')}" if doi else ""
        harmonized_file_name = f"{dataset_name}_harmonized.csv" if is_imported else ""
        hm = entry.get("harmonization_mappings")
        if is_imported:
            decision = "Included in BERDL import because a harmonized soil moisture CSV is available and parsed successfully."
        elif isinstance(hm, str):
            decision = hm
        elif isinstance(hm, dict):
            decision = "Not included in this BERDL import because no harmonized CSV was present in the local import set."
        else:
            decision = "Not included in this BERDL import."
        rows.append({
            "sdt_dataset_id": f"Dataset{i:07d}",
            "sdt_dataset_name": dataset_name,
            "doi_link": doi_link,
            "is_imported": "true" if is_imported else "false",
            "import_decision_comment": decision,
            "depth_resolution_method": depth_method(entry),
            "harmonized_file_name": harmonized_file_name,
            "harmonized_file_download_link": manifest.get(dataset_name, ""),
            "harmonized_file_size_byte": str(csv_paths[dataset_name].stat().st_size) if is_imported else "",
            "harmonized_file_row_count": str(row_count(csv_paths[dataset_name])) if is_imported else "",
            "harmonization_mapping_json": json.dumps(entry, sort_keys=True, separators=(",", ":")),
        })
    return rows


def build_locations(
    location_rows: list[dict],
    observed_pairs: set[tuple[str, str]],
) -> tuple[list[dict], list[dict], dict[tuple[str, str], str]]:
    harmonized: OrderedDict[str, dict] = OrderedDict()
    source_rows = []
    location_lookup: dict[tuple[str, str], str] = {}
    site_index: dict[str, list[dict]] = {}
    for row in location_rows:
        site_id = clean(row.get("site_id"))
        if site_id:
            site_index.setdefault(site_id, []).append(row)
    for i, row in enumerate(location_rows, start=1):
        dataset_name = clean(row.get("source_dataset_id"))
        site_id = clean(row.get("site_id"))
        uuid = clean(row.get("harmonized_location_uuid"))
        if not dataset_name or not site_id:
            continue
        h_name = uuid or safe_name("harmonized_location", dataset_name, site_id)
        if h_name not in harmonized:
            harmonized[h_name] = {
                "sdt_harmonized_location_id": f"HarmonizedLocation{len(harmonized) + 1:07d}",
                "sdt_harmonized_location_name": h_name,
                "latitude_degree": float_string(row.get("latitude_harmonized")),
                "longitude_degree": float_string(row.get("longitude_harmonized")),
                "records_in_harmonized_location_count_unit": clean(row.get("n_records_in_uuid")),
                "datasets_in_harmonized_location_count_unit": clean(row.get("n_datasets_in_uuid")),
            }
        loc_name = safe_name(dataset_name, site_id)
        location_lookup[(dataset_name, site_id)] = loc_name
        source_rows.append({
            "sdt_location_id": f"Location{i:07d}",
            "sdt_location_name": loc_name,
            "sdt_harmonized_location_name": h_name,
            "sdt_dataset_name": dataset_name,
            "site_identifier": site_id,
            "latitude_degree": float_string(row.get("latitude")),
            "longitude_degree": float_string(row.get("longitude")),
            "geolocation_resolution_method": location_method(row.get("qc_flag")),
        })
    next_index = len(source_rows) + 1
    for dataset_name, site_id in sorted(observed_pairs):
        if (dataset_name, site_id) in location_lookup:
            continue
        site_matches = site_index.get(site_id, [])
        matched_uuid = {clean(r.get("harmonized_location_uuid")) for r in site_matches if clean(r.get("harmonized_location_uuid"))}
        if len(matched_uuid) == 1:
            match = site_matches[0]
            h_name = next(iter(matched_uuid))
            latitude = float_string(match.get("latitude_harmonized"))
            longitude = float_string(match.get("longitude_harmonized"))
            method = (
                "Source dataset/site pair was absent from location_data_harmonized_with_uuid.csv; "
                "geolocation was resolved by matching site_identifier to an existing harmonized location UUID."
            )
        else:
            h_name = safe_name("missing_harmonized_location", dataset_name, site_id)
            latitude = ""
            longitude = ""
            method = "Location record was present in the harmonized observation CSV but absent from location_data_harmonized_with_uuid.csv."
            if h_name not in harmonized:
                harmonized[h_name] = {
                    "sdt_harmonized_location_id": f"HarmonizedLocation{len(harmonized) + 1:07d}",
                    "sdt_harmonized_location_name": h_name,
                    "latitude_degree": "",
                    "longitude_degree": "",
                    "records_in_harmonized_location_count_unit": "1",
                    "datasets_in_harmonized_location_count_unit": "1",
                }
        loc_name = safe_name(dataset_name, site_id)
        location_lookup[(dataset_name, site_id)] = loc_name
        source_rows.append({
            "sdt_location_id": f"Location{next_index:07d}",
            "sdt_location_name": loc_name,
            "sdt_harmonized_location_name": h_name,
            "sdt_dataset_name": dataset_name,
            "site_identifier": site_id,
            "latitude_degree": latitude,
            "longitude_degree": longitude,
            "geolocation_resolution_method": method,
        })
        next_index += 1
    return list(harmonized.values()), source_rows, location_lookup


def write_observation(location_lookup: dict[tuple[str, str], str]) -> int:
    out_path = OUT_DIR / "ddt_soil_moisture_observation.csv"
    fieldnames = [
        "sdt_dataset_name",
        "sdt_location_name",
        "datetime_utc",
        "depth_below_soil_surface_meter",
        "replicate_series_count_unit",
        "is_time_series",
        "time_interval_minute",
        "volumetric_water_content_ratio_unit",
        "gravimetric_water_content_ratio_unit",
        "soil_micropore_matric_water_potential_pascal",
    ]
    total = 0
    with out_path.open("w", newline="", encoding="utf-8") as out_fh:
        writer = csv.DictWriter(out_fh, fieldnames=fieldnames)
        writer.writeheader()
        for path in sorted(HARMONIZED_DIR.glob("*_harmonized.csv")):
            dataset_name = dataset_id_from_file(path)
            with path.open(newline="", encoding="utf-8") as in_fh:
                reader = csv.DictReader(in_fh)
                for row in reader:
                    site_id = clean(row.get("site_id"))
                    writer.writerow({
                        "sdt_dataset_name": dataset_name,
                        "sdt_location_name": location_lookup.get((dataset_name, site_id), safe_name(dataset_name, site_id)),
                        "datetime_utc": clean(row.get("datetime_UTC")),
                        "depth_below_soil_surface_meter": float_string(row.get("depth_m")),
                        "replicate_series_count_unit": clean(row.get("replicate")),
                        "is_time_series": bool_string(row.get("is_timeseries")),
                        "time_interval_minute": float_string(row.get("interval_min")),
                        "volumetric_water_content_ratio_unit": float_string(row.get("volumetric_water_content_m3_m3")),
                        "gravimetric_water_content_ratio_unit": float_string(row.get("gravimetric_water_content_gH2O_gs")),
                        "soil_micropore_matric_water_potential_pascal": float_string(row.get("water_potential_kPa"), 1000.0),
                    })
                    total += 1
    return total


def typedef_row(type_name, field_name, column, scalar_type, required, pk, upk, fk, comment, type_id, unit_id=""):
    type_name_text = TERMS[type_id][1] if type_id else ""
    unit_name = TERMS[unit_id][1] if unit_id else ""
    return {
        "type_name": type_name,
        "field_name": field_name,
        "berdl_column_name": column,
        "scalar_type": scalar_type,
        "is_required": str(required).lower(),
        "is_pk": str(pk).lower(),
        "is_upk": str(upk).lower(),
        "fk": fk,
        "constraint": "",
        "comment": comment,
        "units_sys_oterm_id": unit_id,
        "units_sys_oterm_name": unit_name,
        "type_sys_oterm_id": type_id,
        "type_sys_oterm_name": type_name_text,
    }


def build_sys_typedef() -> list[dict]:
    rows = []
    rows += [
        typedef_row("Dataset", "id", "sdt_dataset_id", "text", True, True, False, "", "Unique identifier for the dataset.", "BERVO:8000528"),
        typedef_row("Dataset", "name", "sdt_dataset_name", "text", True, False, True, "", "Unique dataset name using the ESS-DIVE package identifier.", "BERVO:8000528"),
        typedef_row("Dataset", "doi_link", "doi_link", "text", False, False, False, "", "DOI link for the archived ESS-DIVE dataset.", "BERVO:8000391"),
        typedef_row("Dataset", "is_imported", "is_imported", "boolean", True, False, False, "", "Whether the dataset is included in the BERDL observation import.", "BERVO:8000358"),
        typedef_row("Dataset", "import_decision_comment", "import_decision_comment", "text", False, False, False, "", "Dataset-level inclusion or exclusion rationale.", "BERVO:8000305"),
        typedef_row("Dataset", "depth_resolution_method", "depth_resolution_method", "text", False, False, False, "", "Dataset-level method used to resolve depth values.", "BERVO:8000303"),
        typedef_row("Dataset", "harmonized_file_name", "harmonized_file_name", "text", False, False, False, "", "Harmonized CSV filename.", "BERVO:8000528"),
        typedef_row("Dataset", "harmonized_file_download_link", "harmonized_file_download_link", "text", False, False, False, "", "Download URL for the harmonized CSV file.", "BERVO:8000391"),
        typedef_row("Dataset", "harmonized_file_size_byte", "harmonized_file_size_byte", "integer", False, False, False, "", "Size of the harmonized CSV file in bytes.", "BERVO:8000350", "UO:0000233"),
        typedef_row("Dataset", "harmonized_file_row_count", "harmonized_file_row_count", "integer", False, False, False, "", "Number of observation rows in the harmonized CSV file.", "BERVO:8000237", "UO:0000189"),
        typedef_row("Dataset", "harmonization_mapping_json", "harmonization_mapping_json", "text", False, False, False, "", "Raw harmonization mapping JSON for the source dataset.", "BERVO:8000305"),
    ]
    rows += [
        typedef_row("Harmonized_Location", "id", "sdt_harmonized_location_id", "text", True, True, False, "", "Unique identifier for the harmonized location.", "BERVO:8000528"),
        typedef_row("Harmonized_Location", "name", "sdt_harmonized_location_name", "text", True, False, True, "", "Unique harmonized location name.", "BERVO:8000528"),
        typedef_row("Harmonized_Location", "latitude", "latitude_degree", "float", False, False, False, "", "Harmonized latitude in decimal degrees.", "BERVO:8000395", "UO:0000185"),
        typedef_row("Harmonized_Location", "longitude", "longitude_degree", "float", False, False, False, "", "Harmonized longitude in decimal degrees.", "BERVO:8000396", "UO:0000185"),
        typedef_row("Harmonized_Location", "records_in_harmonized_location", "records_in_harmonized_location_count_unit", "integer", False, False, False, "", "Number of source location records in this harmonized location.", "BERVO:8000237", "UO:0000189"),
        typedef_row("Harmonized_Location", "datasets_in_harmonized_location", "datasets_in_harmonized_location_count_unit", "integer", False, False, False, "", "Number of source datasets represented in this harmonized location.", "BERVO:8000237", "UO:0000189"),
    ]
    rows += [
        typedef_row("Location", "id", "sdt_location_id", "text", True, True, False, "", "Unique identifier for the dataset-specific source location.", "BERVO:8000528"),
        typedef_row("Location", "name", "sdt_location_name", "text", True, False, True, "", "Unique source location name used by observation rows.", "BERVO:8000528"),
        typedef_row("Location", "harmonized_location", "sdt_harmonized_location_name", "text", True, False, False, "Harmonized_Location", "Harmonized location reference.", "BERVO:8000528"),
        typedef_row("Location", "dataset", "sdt_dataset_name", "text", True, False, False, "Dataset", "Source dataset reference.", "BERVO:8000528"),
        typedef_row("Location", "site_identifier", "site_identifier", "text", True, False, False, "", "Source site identifier from the harmonized location file.", "BERVO:8000528"),
        typedef_row("Location", "latitude", "latitude_degree", "float", False, False, False, "", "Source location latitude in decimal degrees.", "BERVO:8000395", "UO:0000185"),
        typedef_row("Location", "longitude", "longitude_degree", "float", False, False, False, "", "Source location longitude in decimal degrees.", "BERVO:8000396", "UO:0000185"),
        typedef_row("Location", "geolocation_resolution_method", "geolocation_resolution_method", "text", False, False, False, "", "Method used to resolve source geolocation.", "BERVO:8000303"),
    ]
    return rows


def build_ddt_ndarray() -> list[dict]:
    metadata = {
        "source": "WFSFA harmonized soil moisture data",
        "description": "Combined observation table for 14 harmonized ESS-DIVE soil moisture packages.",
    }
    return [{
        "ddt_ndarray_id": DDT_NDARRAY_ID,
        "ddt_ndarray_name": "watershed_sfa_soil_moisture_observation",
        "ddt_ndarray_description": "Combined WFSFA harmonized soil moisture observation table.",
        "ddt_ndarray_type_sys_oterm_id": "BERVO:9000032",
        "ddt_ndarray_type_sys_oterm_name": "Soil and water variable",
        "ddt_ndarray_shape": "",
        "ddt_ndarray_dimension_names": "dataset,location,time",
        "ddt_ndarray_dimension_types_sys_oterm_id": "BERVO:8000528,BERVO:8000394,BERVO:8000240",
        "ddt_ndarray_dimension_types_sys_oterm_name": "Identifier,Location,DateTime",
        "ddt_ndarray_dimension_variable_names": "sdt_dataset_name,sdt_location_name,datetime_utc,depth_below_soil_surface_meter,replicate_series_count_unit",
        "ddt_ndarray_dimension_variable_types_sys_oterm_id": "BERVO:8000528,BERVO:8000528,BERVO:8000240,BERVO:8000069,BERVO:8000237",
        "ddt_ndarray_dimension_variable_types_sys_oterm_name": "Identifier,Identifier,DateTime,Depth,Count",
        "ddt_ndarray_variable_names": "is_time_series,time_interval_minute,volumetric_water_content_ratio_unit,gravimetric_water_content_ratio_unit,soil_micropore_matric_water_potential_pascal",
        "ddt_ndarray_variable_types_sys_oterm_id": "BERVO:8000300,BERVO:8000238,BERVO:0001743,BERVO:0001810,BERVO:0001750",
        "ddt_ndarray_variable_types_sys_oterm_name": "Time series,Time,Volumetric water content,Gravimetric water content,Soil micropore matric water potential",
        "ddt_ndarray_metadata": json.dumps(metadata, sort_keys=True),
        "superceded_by_ddt_ndarray_id": "",
    }]


def ddt_row(column, data_type, scalar, fk, comment, unit_id, dim_num, dim_id, var_num, var_id, original):
    return {
        "ddt_ndarray_id": DDT_NDARRAY_ID,
        "berdl_column_name": column,
        "berdl_column_data_type": data_type,
        "scalar_type": scalar,
        "foreign_key": fk,
        "comment": comment,
        "unit_sys_oterm_id": unit_id,
        "unit_sys_oterm_name": TERMS[unit_id][1] if unit_id else "",
        "dimension_number": str(dim_num) if dim_num else "",
        "dimension_oterm_id": dim_id,
        "dimension_oterm_name": TERMS[dim_id][1] if dim_id else "",
        "variable_number": str(var_num) if var_num else "",
        "variable_oterm_id": var_id,
        "variable_oterm_name": TERMS[var_id][1] if var_id else "",
        "original_csv_string": original,
    }


def build_sys_ddt_typedef() -> list[dict]:
    return [
        ddt_row("sdt_dataset_name", "string", "object_ref", "sdt_dataset.sdt_dataset_name", "Source ESS-DIVE dataset package.", "", 1, "BERVO:8000528", 1, "BERVO:8000528", "dataset from harmonized CSV filename"),
        ddt_row("sdt_location_name", "string", "object_ref", "sdt_location.sdt_location_name", "Dataset-specific source location.", "", 2, "BERVO:8000394", 2, "BERVO:8000528", "site_id plus source dataset"),
        ddt_row("datetime_utc", "string", "string", "", "Observation timestamp in UTC.", "", 3, "BERVO:8000240", 3, "BERVO:8000240", "datetime_UTC"),
        ddt_row("depth_below_soil_surface_meter", "double", "numeric", "", "Depth below soil surface.", "UO:0000008", 4, "BERVO:8000069", 4, "BERVO:8000069", "depth_m"),
        ddt_row("replicate_series_count_unit", "integer", "numeric", "", "Replicate index or count for repeated sensors/measurements.", "UO:0000189", 5, "BERVO:8000237", 5, "BERVO:8000237", "replicate"),
        ddt_row("is_time_series", "boolean", "boolean", "", "Whether the record is part of a regular time series.", "", 0, "", 1, "BERVO:8000300", "is_timeseries"),
        ddt_row("time_interval_minute", "double", "numeric", "", "Sampling interval for regular time series data.", "UO:0000031", 0, "", 2, "BERVO:8000238", "interval_min"),
        ddt_row("volumetric_water_content_ratio_unit", "double", "numeric", "", "Volumetric water content.", "UO:0000190", 0, "", 3, "BERVO:0001743", "volumetric_water_content_m3_m3"),
        ddt_row("gravimetric_water_content_ratio_unit", "double", "numeric", "", "Gravimetric water content.", "UO:0000190", 0, "", 4, "BERVO:0001810", "gravimetric_water_content_gH2O_gs"),
        ddt_row("soil_micropore_matric_water_potential_pascal", "double", "numeric", "", "Soil water potential converted from kilopascals to pascals.", "UO:0000110", 0, "", 5, "BERVO:0001750", "water_potential_kPa; multiply by 1000 to convert kPa to Pa"),
    ]


def build_sys_oterm() -> list[dict]:
    by_id = OrderedDict()
    for ontology_name, path in OBO_SOURCES:
        for row in parse_obo_terms(path, ontology_name):
            by_id.setdefault(row["sys_oterm_id"], row)
    return [by_id[term_id] for term_id in sorted(by_id)]


def write_schema_sql() -> None:
    schema = """
CREATE TABLE sdt_dataset (
  sdt_dataset_id STRING,
  sdt_dataset_name STRING,
  doi_link STRING,
  is_imported BOOLEAN,
  import_decision_comment STRING,
  depth_resolution_method STRING,
  harmonized_file_name STRING,
  harmonized_file_download_link STRING,
  harmonized_file_size_byte BIGINT,
  harmonized_file_row_count BIGINT,
  harmonization_mapping_json STRING
);

CREATE TABLE sdt_harmonized_location (
  sdt_harmonized_location_id STRING,
  sdt_harmonized_location_name STRING,
  latitude_degree DOUBLE,
  longitude_degree DOUBLE,
  records_in_harmonized_location_count_unit BIGINT,
  datasets_in_harmonized_location_count_unit BIGINT
);

CREATE TABLE sdt_location (
  sdt_location_id STRING,
  sdt_location_name STRING,
  sdt_harmonized_location_name STRING,
  sdt_dataset_name STRING,
  site_identifier STRING,
  latitude_degree DOUBLE,
  longitude_degree DOUBLE,
  geolocation_resolution_method STRING
);

CREATE TABLE ddt_soil_moisture_observation (
  sdt_dataset_name STRING,
  sdt_location_name STRING,
  datetime_utc STRING,
  depth_below_soil_surface_meter DOUBLE,
  replicate_series_count_unit BIGINT,
  is_time_series BOOLEAN,
  time_interval_minute DOUBLE,
  volumetric_water_content_ratio_unit DOUBLE,
  gravimetric_water_content_ratio_unit DOUBLE,
  soil_micropore_matric_water_potential_pascal DOUBLE
);

CREATE TABLE ddt_ndarray (
  ddt_ndarray_id STRING,
  ddt_ndarray_name STRING,
  ddt_ndarray_description STRING,
  ddt_ndarray_type_sys_oterm_id STRING,
  ddt_ndarray_type_sys_oterm_name STRING,
  ddt_ndarray_shape STRING,
  ddt_ndarray_dimension_names STRING,
  ddt_ndarray_dimension_types_sys_oterm_id STRING,
  ddt_ndarray_dimension_types_sys_oterm_name STRING,
  ddt_ndarray_dimension_variable_names STRING,
  ddt_ndarray_dimension_variable_types_sys_oterm_id STRING,
  ddt_ndarray_dimension_variable_types_sys_oterm_name STRING,
  ddt_ndarray_variable_names STRING,
  ddt_ndarray_variable_types_sys_oterm_id STRING,
  ddt_ndarray_variable_types_sys_oterm_name STRING,
  ddt_ndarray_metadata STRING,
  superceded_by_ddt_ndarray_id STRING
);

CREATE TABLE sys_typedef (
  type_name STRING,
  field_name STRING,
  berdl_column_name STRING,
  scalar_type STRING,
  is_required BOOLEAN,
  is_pk BOOLEAN,
  is_upk BOOLEAN,
  fk STRING,
  "constraint" STRING,
  comment STRING,
  units_sys_oterm_id STRING,
  units_sys_oterm_name STRING,
  type_sys_oterm_id STRING,
  type_sys_oterm_name STRING
);

CREATE TABLE sys_ddt_typedef (
  ddt_ndarray_id STRING,
  berdl_column_name STRING,
  berdl_column_data_type STRING,
  scalar_type STRING,
  foreign_key STRING,
  comment STRING,
  unit_sys_oterm_id STRING,
  unit_sys_oterm_name STRING,
  dimension_number BIGINT,
  dimension_oterm_id STRING,
  dimension_oterm_name STRING,
  variable_number BIGINT,
  variable_oterm_id STRING,
  variable_oterm_name STRING,
  original_csv_string STRING
);

CREATE TABLE sys_oterm (
  sys_oterm_id STRING,
  parent_sys_oterm_id STRING,
  sys_oterm_ontology STRING,
  sys_oterm_name STRING,
  sys_oterm_synonyms STRING,
  sys_oterm_definition STRING,
  sys_oterm_links STRING,
  sys_oterm_properties STRING
);
"""
    (OUT_DIR / "schema.sql").write_text(schema.strip() + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mapping = load_mapping()
    manifest = read_harmonized_manifest()
    location_rows = load_location_rows()
    sdt_dataset = build_sdt_dataset(mapping, manifest)
    sdt_hloc, sdt_location, location_lookup = build_locations(location_rows, observed_location_pairs())
    observation_count = write_observation(location_lookup)

    write_csv(OUT_DIR / "sdt_dataset.csv", [
        "sdt_dataset_id", "sdt_dataset_name", "doi_link", "is_imported",
        "import_decision_comment", "depth_resolution_method", "harmonized_file_name",
        "harmonized_file_download_link", "harmonized_file_size_byte",
        "harmonized_file_row_count", "harmonization_mapping_json",
    ], sdt_dataset)
    write_csv(OUT_DIR / "sdt_harmonized_location.csv", [
        "sdt_harmonized_location_id", "sdt_harmonized_location_name",
        "latitude_degree", "longitude_degree",
        "records_in_harmonized_location_count_unit",
        "datasets_in_harmonized_location_count_unit",
    ], sdt_hloc)
    write_csv(OUT_DIR / "sdt_location.csv", [
        "sdt_location_id", "sdt_location_name", "sdt_harmonized_location_name",
        "sdt_dataset_name", "site_identifier", "latitude_degree",
        "longitude_degree", "geolocation_resolution_method",
    ], sdt_location)
    write_csv(OUT_DIR / "ddt_ndarray.csv", list(build_ddt_ndarray()[0].keys()), build_ddt_ndarray())
    write_csv(OUT_DIR / "sys_typedef.csv", list(build_sys_typedef()[0].keys()), build_sys_typedef())
    write_csv(OUT_DIR / "sys_ddt_typedef.csv", list(build_sys_ddt_typedef()[0].keys()), build_sys_ddt_typedef())
    write_csv(OUT_DIR / "sys_oterm.csv", list(build_sys_oterm()[0].keys()), build_sys_oterm())
    write_schema_sql()

    summary = {
        "obo_sources": [str(path) for _, path in OBO_SOURCES],
        "sdt_dataset": len(sdt_dataset),
        "sdt_harmonized_location": len(sdt_hloc),
        "sdt_location": len(sdt_location),
        "ddt_soil_moisture_observation": observation_count,
        "ddt_ndarray": 1,
        "sys_typedef": len(build_sys_typedef()),
        "sys_ddt_typedef": len(build_sys_ddt_typedef()),
        "sys_oterm": len(build_sys_oterm()),
    }
    (OUT_DIR / "build_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Wrote import package to {OUT_DIR}")


if __name__ == "__main__":
    main()
