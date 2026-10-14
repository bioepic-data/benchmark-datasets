"""Harmonize the hand-written packages of Group 4: coordinates are converted from UTM or a local X/Y grid.

The soil pH functions (ph_<id>) were copied from notebooks/harmonize_ph and the carbon functions (c_<id>) from
notebooks/harmonize_carbon, unchanged apart from the assemble() signature. PACKAGES combines them into one function
per package that returns {variable key: harmonized table}.

Packages:
    doi:10.5440/1109232                [pH+carbon] Roy Chowdhury et al., Barrow BGC soil cores 2012-2013  (UTM 4N)
    doi:10.5440/1860505                [pH+carbon] Dafflon et al., Teller soil properties 2019            (UTM 3N)
    doi:10.15485/2588765               [pH+carbon] Lilly-Dickey Woods ForestGEO plot soils 2014           (plot grid -> UTM 16N)
    doi:10.25581/ornlsfa.024/1837084   [pH+carbon] NIST forest-edge transect soils        (grid X/Y, affine fit)
    doi:10.15485/3030222               [carbon]
    doi:10.5440/1358456                [carbon]

Attributes:
    PACKAGES: (DOI, package function, variables) per package; the package function combines the pH and carbon
        functions (extract.combine).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, cast

import numpy as np
import pandas as pd  # noqa: F401

from ..common import *  # noqa: F401,F403
from ..common import _text  # noqa: F401
from ..extract import Col, combine, from_columns, from_long, make_base, merge_tables  # noqa: F401
from ..datatypes import Tables


# ====================================================================================================
# Soil pH (from notebooks/harmonize_ph/group4_projected_coords.py)
# ====================================================================================================


def _latlon(e: Iterable[Any], n: Iterable[Any], zone: int, ndigits: int) -> tuple[list[float], list[float]]:
    """Convert UTM easting / northing to latitude / longitude (WGS84, northern hemisphere).

    Args:
        e: Eastings (m).
        n: Northings (m).
        zone: UTM zone.
        ndigits: Decimal places kept.

    Returns:
        Latitudes and longitudes.

    Examples:
        >>> lat, lon = _latlon([500000], [4649776], 18, 3)
        >>> lat, lon
        ([42.0], [-75.0])
    """
    ll = [utm_to_latlon(float(a), float(b), zone) for a, b in zip(e, n)]
    return [round(a, ndigits) for a, _ in ll], [round(b, ndigits) for _, b in ll]


def ph_1109232() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.5440/1109232.

    Package: Soil Physicochemical Characteristics from Ice Wedge Polygons, Utqiagvik (Barrow), Alaska, Ver. 1.

    Source files: BGC_Soil_Core_Descriptions_2012-2013_Physicochemical_Properties_v3.csv.

    Location: BGC_Soil_Core_Descriptions_2012-2013_Physicochemical_Properties_v3.csv (core UTM Zone 4N, NAD83,
    converted to decimal degrees).

    Methods: pH_KCl.

    Notes:
        - Metadata block on top; column names on row 9, units on row 10.
        - Values match Roy Chowdhury et al. 2015 Table 1.
        - Added in v3 from Zheng et al. 2018.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_1109232())  # doctest: +SKIP
        45
    """
    doi = "doi:10.5440/1109232"
    src = "BGC_Soil_Core_Descriptions_2012-2013_Physicochemical_Properties_v3.csv"
    raw = pd.read_csv(raw_path(doi, src), encoding="latin1", dtype=str, header=None)
    # Metadata block on top; column names on row 9, units on row 10.
    d = raw.iloc[10:]
    d.columns = [str(c).strip() for c in raw.iloc[8]]
    d = d.dropna(how="all").apply(lambda s: s.str.strip())
    d["ph"] = pd.to_numeric(d["pH_of_soil_layer"], errors="coerce")
    d = d[d["ph"] > -9000].copy()
    lat, lon = _latlon(d["Easting_UTM"], d["Northing_UTM"], 4, 5)

    confirmed = {"NGADG0005", "NGADG0009", "NGADG0017"}  # values match Roy Chowdhury et al. 2015 Table 1
    zheng = {"NGADG0001", "NGADG0003"}  # added in v3 from Zheng et al. 2018

    def method(core: str) -> str:
        if core in zheng:
            return "1 M KCl, 1:2 soil slurry (cores added in v3 from Zheng et al. 2018, Biogeosciences 15:6621)"
        if core in confirmed:
            return "2 M KCl, 1:5 w:v (user guide: water and 2 M KCl 1:5; values match Roy Chowdhury et al. 2015 Table 1 pHKCl)"
        return ("2 M KCl, 1:5 w:v, inferred (user guide lists water and 2 M KCl 1:5 without saying which is reported; "
                "same column as confirmed KCl cores)")

    dropped = ("doi:10.5440/1440029 (incubation day-0 pH, same Barrow 2012 cores) was ignored: it covers 8 of these 13 "
               "cores (NGADG0001, 0003, 0005, 0009, 0017, 0043, 0048, 0073) with the same KCl pH, identical where depth "
               "intervals match or close to the mean of these 10-cm intervals over its wider layers; exceptions: "
               "NGADG0073 permafrost 55-82 cm 7.06 there vs 5.92 here, NGADG0043 mineral 30-50 cm 4.54 there vs "
               "4.89/4.98 here")
    notes = []
    for r in d.itertuples():
        n = (f"lat/long source: {doi}:{src} (core UTM Zone 4N, NAD83, converted to decimal degrees); "
             f"pH method: {method(r.Core_ID)}")
        if r.Microtopography == "unknown":
            n += "; Area and Microtopography recorded as unknown"
        if r.Soil_horizon.lower() == "ice":
            n += "; horizon recorded as ice (ice-rich permafrost layer with measurable soil)"
        notes.append(f"{n}; {dropped}")
    keys = ["Core_ID", "Polygonal_type", "Microtopography", "Soil_horizon"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": d["upper_depth_of_soil_layer"].map(fmt_num) + "-" + d["lower_depth_of_soil_layer"].map(fmt_num),
        "date": d["Date_sampled"], "pH": d["ph"], "ph_method": "pH_KCl", "latitude": lat, "longitude": lon, "notes": notes,
    })
    return assemble(out, "pH", raw=True)


def ph_1860505() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.5440/1860505.

    Package: Soil physical and thermal properties from soil samples at multiple locations at Teller Road Site,
    Seward Peninsula, Alaska, 2019.

    Source files: Data_August2019_Teller_Archive_Final.csv.

    Location: Data_August2019_Teller_Archive_Final.csv (sample Easting/Northing, UTM Zone 3N per
    Dafflon_etal_SoilProp_20220613.pdf; datum not stated, WGS84 assumed; converted to decimal degrees).

    Methods: pH_H2O.

    Notes:
        - Single depth = centre of a ~5 cm horizontal cylinder; report centre +/- 2.5 cm, floored at 0.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_1860505())  # doctest: +SKIP
        107
    """
    doi = "doi:10.5440/1860505"
    src = "Data_August2019_Teller_Archive_Final.csv"
    guide = "Dafflon_etal_SoilProp_20220613.pdf"
    raw = pd.read_csv(raw_path(doi, src), encoding="latin1", dtype=str, header=None, keep_default_na=False)
    d = raw.iloc[2:]  # row 1 = names, row 2 = units
    d.columns = [str(c).strip() for c in raw.iloc[0]]
    d = d.apply(lambda s: s.str.strip())
    d = d[d["Soil_sample_ID_#1"] != ""]
    d["ph"] = pd.to_numeric(d["pH"], errors="coerce")
    d = d[d["ph"].notna() & (d["ph"] > -9000)].copy()
    lat, lon = _latlon(d["Easting"], d["Northing"], 3, 6)
    # Single depth = centre of a ~5 cm horizontal cylinder; report centre +/- 2.5 cm, floored at 0.
    depth = [f"{fmt_num(max(float(z) - 2.5, 0))}-{fmt_num(float(z) + 2.5)}" for z in d["Soil_sample_depth"]]
    keys = ["Soil_sample_ID_#1", "Location_#"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": depth, "date": d["Sampling_date"], "pH": d["ph"], "ph_method": "pH_H2O", "latitude": lat, "longitude": lon,
        "notes": [(f"lat/long source: {doi}:{src} (sample Easting/Northing, UTM Zone 3N per {guide}; datum not stated, "
                   "WGS84 assumed; converted to decimal degrees); pH method: 1:2 soil:water by volume, dried (65 C) and "
                   "<2 mm sieved soil, University of Arkansas Agricultural Diagnostic Laboratory (SERA-6 methods), per "
                   "package methods; depth converted to an approximate interval: source gives a single depth below ground "
                   f"surface ({z} cm) for a horizontal cylinder (~95-153 cm3, ~5 cm diameter) pushed into the "
                   "pit/auger-hole wall; interval assumes the reported depth is the cylinder centre, +/-2.5 cm (floored "
                   f"at 0); sample IDs {a}/{b}")
                  for z, a, b in zip(d["Soil_sample_depth"], d["Soil_sample_ID_#2"], d["Soil_sample_ID_#3"])],
    })
    return assemble(out, "pH", raw=True)


def ph_2588765() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/2588765.

    Package: Soil biogeochemical properties and metrics of tree-mycorrhizal dominance for a 25-Ha forest in South
    Central Indiana, USA.

    Source files: ldw_dat_raw.csv.

    Location: ldw_dat_raw.csv (per-point UTM16Nx/UTM16Ny, UTM zone 16N converted to decimal degrees, datum not
    stated).

    Methods: pH_CaCl2.

    Notes:
        - UTM values are written with thousands separators ("567,235.00").

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_2588765())  # doctest: +SKIP
        243
    """
    doi = "doi:10.15485/2588765"
    src = "ldw_dat_raw.csv"
    r = read_csv(doi, src, encoding="utf-8-sig")
    r = r[~is_missing(r["pH_CaCl"])].copy()
    # UTM values are written with thousands separators ("567,235.00").
    lat, lon = _latlon(r["UTM16Nx"].str.replace(",", ""), r["UTM16Ny"].str.replace(",", ""), 16, 6)
    g = lambda v: "%g" % float(v)
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": r["ID"] + ":" + r["X"].map(g) + ":" + r["Y"].map(g), "id_type": "ID:X:Y",
        "depth": "0-5", "date": "2014", "pH": r["pH_CaCl"], "ph_method": "pH_CaCl2", "latitude": lat, "longitude": lon,
        "notes": ("lat/long source: doi:10.15485/2588765:ldw_dat_raw.csv (per-point UTM16Nx/UTM16Ny, UTM zone 16N "
                  "converted to decimal degrees, datum not stated); pH_CaCl2: 5 g air-dried soil in 40 mL 0.01 M CaCl2 "
                  "(1:8), shaken 30 min, benchtop meter; 0-5 cm, three 5-cm cores per 0.25x0.25 m subplot after litter "
                  "removal, composited; date: sample coordinates recorded summer 2014 per methods, exact sampling date "
                  "not given (package temporal coverage 2012-05 to 2014-09); Lilly-Dickey Woods ForestGEO plot, Indiana; "
                  "X/Y = m from southern/western plot boundary; pH_BaCl2 column (pH in barium chloride solution) not "
                  "included"),
    })
    return assemble(out, "pH", raw=True)


def ph_1837084() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.25581/ornlsfa.024/1837084.

    Package: NIST: Soil Respiration, Moisture, Temperature, Chemistry; and Fine Root Measurements from a Transect
    Through a Forest Edge, Gaithersburg, Maryland, 2017-2021.

    Source files: NIST_Soil.csv, NIST_Respiration.csv.

    Location: estimated from soil-core grid position X/Y (NIST_Soil.csv) using an affine fit of X/Y to
    Latitude/Longitude of 70 respiration collars in NIST_Respiration.csv (same site grid; median fit residual ~5 m).

    Methods: pH_H2O.

    Notes:
        - Respiration collars have both grid X/Y and Latitude/Longitude: fit lat/lon = a + b*X + c*Y.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_1837084())  # doctest: +SKIP
        324
    """
    doi = "doi:10.25581/ornlsfa.024/1837084"
    src = "NIST_Soil.csv"
    # Respiration collars have both grid X/Y and Latitude/Longitude: fit lat/lon = a + b*X + c*Y.
    r = read_csv(doi, "NIST_Respiration.csv", encoding="latin1")
    c = r[~is_missing(r["Latitude"])].drop_duplicates("Collar_ID")
    A = np.c_[np.ones(len(c)), c["X"].astype(float), c["Y"].astype(float)]
    blat = np.linalg.lstsq(A, c["Latitude"].astype(float), rcond=None)[0]
    blon = np.linalg.lstsq(A, c["Longitude"].astype(float), rcond=None)[0]
    d = read_csv(doi, src, encoding="latin1")
    d = d[~is_missing(d["Soil_pH_water"])].copy()
    x, y = d["X"].astype(float), d["Y"].astype(float)
    keys = ["Sample_ID", "Transect_letter", "Landscape_name", "Lab_replicate"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": d["Soil_depth_upper"] + "-" + d["Soil_depth_lower"], "date": d["Date"], "pH": d["Soil_pH_water"],
        "ph_method": "pH_H2O",
        "latitude": (blat[0] + blat[1] * x + blat[2] * y).round(6),
        "longitude": (blon[0] + blon[1] * x + blon[2] * y).round(6),
        "notes": [("lat/long source: estimated from soil-core grid position X/Y (NIST_Soil.csv) using an affine fit of X/Y "
                   f"to Latitude/Longitude of {len(c)} respiration collars in {doi}:NIST_Respiration.csv (same site grid; "
                   "median fit residual ~5 m)"
                   + ("; meadow/canopy positions (Y<0) extrapolated beyond the collar grid" if yy < 0 else "")
                   + "; pH_H2O: 1 part soil to 2 parts deionized water, shaken, pH of supernatant with probe; "
                   "Lab_replicate = analytical replicate (2 per core section); NIST FOREST forest-edge transect, "
                   f"landscape position {ln} (Y = {yy:g} m from forest edge), transect {t}")
                  for yy, ln, t in zip(y, d["Landscape_name"], d["Transect_letter"])],
    })
    return assemble(out, "pH", raw=True)


# ====================================================================================================
# Soil carbon (from notebooks/harmonize_carbon/group4_projected_coords.py)
# ====================================================================================================



def c_1109232() -> pd.DataFrame:
    """Harmonize total carbon of doi:10.5440/1109232.

    Package: Soil Physicochemical Characteristics from Ice Wedge Polygons, Utqiagvik (Barrow), Alaska, Ver. 1.

    Source files: BGC_Soil_Core_Descriptions_2012-2013_Physicochemical_Properties_v3.csv.

    Location: BGC_Soil_Core_Descriptions_2012-2013_Physicochemical_Properties_v3.csv (core UTM Zone 4N, NAD83,
    converted to decimal degrees).

    Methods: unknown.

    Notes:
        - Metadata block on top; column names on row 9, units on row 10.

    Returns:
        The total carbon table in the harmonized layout (common.assemble).

    Examples:
        >>> len(c_1109232())  # doctest: +SKIP
        32
    """
    doi = "doi:10.5440/1109232"
    src = "BGC_Soil_Core_Descriptions_2012-2013_Physicochemical_Properties_v3.csv"
    raw = pd.read_csv(raw_path(doi, src), encoding="latin1", dtype=str, header=None)
    # Metadata block on top; column names on row 9, units on row 10.
    d = raw.iloc[10:]
    d.columns = [str(c).strip() for c in raw.iloc[8]]
    d = d.dropna(how="all").apply(lambda s: s.str.strip())
    d["tc"] = pd.to_numeric(d["percent_total carbon_of_soil_layer"], errors="coerce")
    d = d[d["tc"] > -9000].copy()
    lat, lon = _latlon(d["Easting_UTM"], d["Northing_UTM"], 4, 5)
    notes = []
    for r in d.itertuples():
        n = (f"lat/long source: {doi}:{src} (core UTM Zone 4N, NAD83, converted to decimal degrees); "
             "percent_total carbon_of_soil_layer (%); instrument not stated in the data file")
        if r.Microtopography == "unknown":
            n += "; Area and Microtopography recorded as unknown"
        if r.Soil_horizon.lower() == "ice":
            n += "; horizon recorded as ice (ice-rich permafrost layer with measurable soil)"
        notes.append(n)
    keys = ["Core_ID", "Polygonal_type", "Microtopography", "Soil_horizon"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": d["upper_depth_of_soil_layer"].map(fmt_num) + "-" + d["lower_depth_of_soil_layer"].map(fmt_num),
        "date": d["Date_sampled"], "TC": d["tc"], "tc_method": UNKNOWN, "latitude": lat, "longitude": lon,
        "notes": notes,
    })
    return assemble(out, "TC")


def c_1860505() -> Tables:
    """Harmonize total carbon, loss on ignition of doi:10.5440/1860505.

    Package: Soil physical and thermal properties from soil samples at multiple locations at Teller Road Site,
    Seward Peninsula, Alaska, 2019.

    Source files: Data_August2019_Teller_Archive_Final.csv.

    Location: Data_August2019_Teller_Archive_Final.csv (sample Easting/Northing, UTM Zone 3N per
    Dafflon_etal_SoilProp_20220613.pdf; datum not stated, WGS84 assumed; converted to decimal degrees);
    Data_August2019_Teller_Archive_Final.csv (sample Easting/Northing, UTM Zone 3N, converted).

    Methods: TC dry_combustion; LOI loss_on_ignition.

    Notes:
        - Single depth = centre of a ~5 cm horizontal cylinder; report centre +/- 2.5 cm, floored at 0 (as for soil pH).

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), LOI (loss on ignition).

    Examples:
        >>> {k: len(t) for k, t in c_1860505().items()}  # doctest: +SKIP
        {'TC': 123, 'LOI': 115}
    """
    doi = "doi:10.5440/1860505"
    src = "Data_August2019_Teller_Archive_Final.csv"
    guide = "Dafflon_etal_SoilProp_20220613.pdf"
    raw = pd.read_csv(raw_path(doi, src), encoding="latin1", dtype=str, header=None, keep_default_na=False)
    d = raw.iloc[2:]  # row 1 = names, row 2 = units
    d.columns = [str(c).strip() for c in raw.iloc[0]]
    d = d.apply(lambda s: s.str.strip())
    d = d[d["Soil_sample_ID_#1"] != ""]
    d["tc"] = pd.to_numeric(d["C"], errors="coerce")
    d = d[d["tc"].notna() & (d["tc"] > -9000)].copy()
    lat, lon = _latlon(d["Easting"], d["Northing"], 3, 6)
    # Single depth = centre of a ~5 cm horizontal cylinder; report centre +/- 2.5 cm, floored at 0 (as for soil pH).
    depth = [f"{fmt_num(max(float(z) - 2.5, 0))}-{fmt_num(float(z) + 2.5)}" for z in d["Soil_sample_depth"]]
    keys = ["Soil_sample_ID_#1", "Location_#"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": depth, "date": d["Sampling_date"], "TC": d["tc"], "tc_method": DRY_COMBUSTION,
        "latitude": lat, "longitude": lon,
        "notes": [(f"lat/long source: {doi}:{src} (sample Easting/Northing, UTM Zone 3N per {guide}; datum not stated, "
                   "WGS84 assumed; converted to decimal degrees); C (g/100g dry) by combustion, Elementar varioMax CN "
                   "cube, University of Arkansas Agricultural Diagnostic Laboratory (package methods); depth converted "
                   f"to an approximate interval: source gives a single depth ({z} cm) for a horizontal ~5 cm cylinder "
                   "pushed into the pit wall, taken as centre +/-2.5 cm (floored at 0)")
                  for z in d["Soil_sample_depth"]],
    })
    base = out.drop(columns=["TC", "tc_method", "notes"])
    loi = emit(base, "LOI", d["LOI"], LOI_METHOD,
               [(f"lat/long source: {doi}:{src} (sample Easting/Northing, UTM Zone 3N, converted); LOI (g/100 g dry), "
                 "University of Arkansas Agricultural Diagnostic Laboratory, SERA-6 methods (package methods); depth "
                 f"approximated from the single sample depth ({z} cm) as for TC") for z in d["Soil_sample_depth"]])
    return {"TC": assemble(out, "TC"), "LOI": loi}


def c_2588765() -> pd.DataFrame:
    """Harmonize total carbon of doi:10.15485/2588765.

    Package: Soil biogeochemical properties and metrics of tree-mycorrhizal dominance for a 25-Ha forest in South
    Central Indiana, USA.

    Source files: CN_data.csv.

    Location: CN_data.csv plot grid gx/gy (m) converted to UTM 16N with the offsets in ldw_dat_raw.csv (UTM16Nx =
    567225 + X, UTM16Ny = 4343000 + Y; gx/gy match its X/Y), datum not stated.

    Methods: dry_combustion.

    Notes:
        - Plot grid -> UTM 16N: in ldw_dat_raw.csv UTM16Nx = 567225 + X and UTM16Ny = 4343000 + Y for every point.
          CN_data gx/gy coincide with ldw_dat_raw X/Y (85 of 104 points; the rest are '.5' averaged pairs), so gx is the
          east offset and gy the north offset despite the data dictionary wording.

    Returns:
        The total carbon table in the harmonized layout (common.assemble).

    Examples:
        >>> len(c_2588765())  # doctest: +SKIP
        104
    """
    doi = "doi:10.15485/2588765"
    src = "CN_data.csv"
    d = read_csv(doi, src)
    d = d[~is_missing(d["pC"])].copy()
    # Plot grid -> UTM 16N: in ldw_dat_raw.csv UTM16Nx = 567225 + X and UTM16Ny = 4343000 + Y for every point.
    # CN_data gx/gy coincide with ldw_dat_raw X/Y (85 of 104 points; the rest are '.5' averaged pairs), so
    # gx is the east offset and gy the north offset despite the data dictionary wording.
    lat, lon = _latlon(567225 + num(d["gx"]), 4343000 + num(d["gy"]), 16, 6)
    g = lambda v: "%g" % float(v)
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["ID"] + ":" + d["gx"].map(g) + ":" + d["gy"].map(g),
        "id_type": "ID:gx:gy", "depth": "0-5", "date": "2014", "TC": d["pC"], "tc_method": DRY_COMBUSTION,
        "latitude": lat, "longitude": lon,
        "notes": [("lat/long source: doi:10.15485/2588765:CN_data.csv plot grid gx/gy (m) converted to UTM 16N with the "
                   "offsets in doi:10.15485/2588765:ldw_dat_raw.csv (UTM16Nx = 567225 + X, UTM16Ny = 4343000 + Y; gx/gy "
                   "match its X/Y), datum not stated; pC = soil carbon (% by mass) from Costech elemental analyzer, "
                   "air-dried ground soil (package methods); 0-5 cm composite of three cores per subplot; date: summer "
                   "2014 per methods, exact date not given; Lilly-Dickey Woods ForestGEO plot, Indiana"
                   + ("; ID ending in .5: two samples within 10 m averaged (data dictionary)" if i.endswith(".5") else ""))
                  for i in d["ID"]],
    })
    return assemble(out, "TC")


def c_1837084() -> Tables:
    """Harmonize total carbon, dissolved organic carbon of doi:10.25581/ornlsfa.024/1837084.

    Package: NIST: Soil Respiration, Moisture, Temperature, Chemistry; and Fine Root Measurements from a Transect
    Through a Forest Edge, Gaithersburg, Maryland, 2017-2021.

    Source files: NIST_Soil.csv, NIST_Respiration.csv.

    Location: estimated from soil-core grid position X/Y (NIST_Soil.csv) using an affine fit of X/Y to
    Latitude/Longitude of 70 respiration collars in NIST_Respiration.csv (same site grid; median fit residual ~5 m);
    estimated from soil-core grid X/Y with an affine fit to the respiration-collar coordinates in
    NIST_Respiration.csv (as for TC).

    Methods: TC dry_combustion; DOC salt_extraction.

    Notes:
        - Respiration collars have both grid X/Y and Latitude/Longitude: fit lat/lon = a + b*X + c*Y (as for soil pH).

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), DOC (dissolved organic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_1837084().items()}  # doctest: +SKIP
        {'TC': 108, 'DOC': 162}
    """
    doi = "doi:10.25581/ornlsfa.024/1837084"
    src = "NIST_Soil.csv"
    # Respiration collars have both grid X/Y and Latitude/Longitude: fit lat/lon = a + b*X + c*Y (as for soil pH).
    r = read_csv(doi, "NIST_Respiration.csv", encoding="latin1")
    c = r[~is_missing(r["Latitude"])].drop_duplicates("Collar_ID")
    A = np.c_[np.ones(len(c)), c["X"].astype(float), c["Y"].astype(float)]
    blat = np.linalg.lstsq(A, c["Latitude"].astype(float), rcond=None)[0]
    blon = np.linalg.lstsq(A, c["Longitude"].astype(float), rcond=None)[0]
    d = read_csv(doi, src, encoding="latin1")
    full = d.copy()
    d = d[~is_missing(d["Percent_C"])].copy()
    x, y = d["X"].astype(float), d["Y"].astype(float)
    keys = ["Sample_ID", "Transect_letter", "Landscape_name", "Lab_replicate"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": d["Soil_depth_upper"] + "-" + d["Soil_depth_lower"], "date": d["Date"], "TC": d["Percent_C"],
        "tc_method": DRY_COMBUSTION,
        "latitude": (blat[0] + blat[1] * x + blat[2] * y).round(6),
        "longitude": (blon[0] + blon[1] * x + blon[2] * y).round(6),
        "notes": [("lat/long source: estimated from soil-core grid position X/Y (NIST_Soil.csv) using an affine fit of X/Y "
                   f"to Latitude/Longitude of {len(c)} respiration collars in {doi}:NIST_Respiration.csv (same site grid; "
                   "median fit residual ~5 m)"
                   + ("; meadow/canopy positions (Y<0) extrapolated beyond the collar grid" if yy < 0 else "")
                   + "; total C of 2 mm sieved, air-dried, ground soil by Leco Tru-Spec CN combustion analyzer (package "
                   "methods); Lab_replicate = analytical replicate; NIST FOREST forest-edge transect, landscape position "
                   f"{ln} (Y = {yy:g} m from forest edge), transect {t}")
                  for yy, ln, t in zip(y, d["Landscape_name"], d["Transect_letter"])],
    })
    e = full[~is_missing(full["DOC"])].copy()
    ex, ey = e["X"].astype(float), e["Y"].astype(float)
    doc = pd.DataFrame({
        "doi": doi, "source_file": src, "id": e[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": e["Soil_depth_upper"] + "-" + e["Soil_depth_lower"], "date": e["Date"], "value": e["DOC"],
        "method": SALT_EXTRACTION, "DOC_unit": "mg C kg-1 dry soil", "DOC_medium": "0.5 M K2SO4 extract",
        "latitude": (blat[0] + blat[1] * ex + blat[2] * ey).round(6),
        "longitude": (blon[0] + blon[1] * ex + blon[2] * ey).round(6),
        "notes": ("lat/long source: estimated from soil-core grid X/Y with an affine fit to the respiration-collar "
                  f"coordinates in {doi}:NIST_Respiration.csv (as for TC); DOC = dissolved extractable organic C, ug C g-1 "
                  "soil (= mg C kg-1), data dictionary; unfumigated K2SO4 extract analysed on a Shimadzu TOC-L (package "
                  "methods); NIST FOREST forest-edge transect"),
    })
    return {"TC": assemble(out, "TC"), "DOC": assemble(doc, "DOC")}


# ----------------------------------------------------------------------------------------------------
# Packages added for the other carbon variables
# ----------------------------------------------------------------------------------------------------

def c_3030222() -> dict:
    """Harmonize soil organic carbon of doi:10.15485/3030222.

    Package: Soil carbon stocks from soil organic carbon at the Teller 47, Teller 27, and Kougarok 86 field sites,
    Seward Peninsula, Alaska, 2021 – 2023.

    Source files: SoilCarbon_TL47TL27KR.csv.

    Location: SoilCarbon_TL47TL27KR.csv (X/Y taken as UTM zone 3N, datum not stated, converted).

    Methods: SOC acid_treated_combustion.

    Notes:
        - One source row holds "X<tab>Y" in the X cell; split it.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): SOC (soil organic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_3030222().items()}  # doctest: +SKIP
        {'SOC': 203}
    """
    doi = "doi:10.15485/3030222"
    src = "SoilCarbon_TL47TL27KR.csv"
    d = read_csv(doi, src)
    d = d[~is_missing(d["percentC"])].copy()
    # One source row holds "X<tab>Y" in the X cell; split it.
    bad = d["X"].str.contains("\t")
    d.loc[bad, "Y"] = d.loc[bad, "X"].str.split("\t").str[1]
    d.loc[bad, "X"] = d.loc[bad, "X"].str.split("\t").str[0]
    lat, lon = _latlon(d["X"], d["Y"], 3, 6)
    rows = []
    for r, la, lo in zip(d.to_dict("records"), lat, lon):
        top, bot = float(r["Top_cm"]), float(r["Bottom_cm"])
        depth = f"{fmt_num(min(top, bot))}-{fmt_num(max(top, bot))}"
        rows.append(dict(
            doi=doi, source_file=src, id=f"{r['FieldLocation']}:{r['SampleName']}", id_type="FieldLocation:SampleName",
            depth=depth, date=r["SampleDate"], value=r["percentC"], method=ACID_COMBUSTION, latitude=la, longitude=lo,
            notes=(f"lat/long source: {doi}:{src} (X/Y taken as UTM zone 3N, datum not stated, converted); percentC = "
                   "percent soil organic carbon (data dictionary): carbonate removed by acid fumigation, then Eurovector "
                   f"elemental analyzer-IRMS (package methods); stdev_percentC {r['stdev_percentC']}; sampling month only"
                   + ("; source top/bottom reversed, written shallow-deep" if top > bot else ""))))
    return {"SOC": assemble(pd.DataFrame(rows), "SOC")}


def c_1358456() -> dict:
    """Harmonize soil organic matter of doi:10.5440/1358456.

    Package: Physical, Chemical, and Hydrologic Characteristics of Active Layer and Permafrost Soils of Arctic
    Polygonal Tundra, Barrow, Alaska, 2013-2016.

    Source files: core_physical_chem_data_20180321.csv.

    Location: core_physical_chem_data_20180321.csv (core Northing/Easting, taken as UTM Zone 4N like the other
    Barrow core data, converted).

    Methods: SOM unknown.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): SOM (soil organic matter).

    Examples:
        >>> {k: len(t) for k, t in c_1358456().items()}  # doctest: +SKIP
        {'SOM': 82}
    """
    doi = "doi:10.5440/1358456"
    src = "core_physical_chem_data_20180321.csv"
    raw = pd.read_csv(raw_path(doi, src), encoding="latin1", dtype=str, header=None, keep_default_na=False)
    d = raw.iloc[7:]
    d.columns = [c.strip() for c in raw.iloc[5]]
    d = d[(d["Core_Sample_ID"] != "") & ~is_missing(d["Organic_Matter_Content"])]
    lat, lon = _latlon(d["Easting"], d["Northing"], 4, 6)
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Core_Sample_ID"] + ":" + d["Mid_Depth_Core_Section"],
        "id_type": "Core_Sample_ID:Mid_Depth_Core_Section", "depth": d["Mid_Depth_Core_Section"], "date": "2013/2016",
        "value": d["Organic_Matter_Content"], "method": UNKNOWN, "latitude": lat, "longitude": lon,
        "notes": [(f"lat/long source: {doi}:{src} (core Northing/Easting, taken as UTM Zone 4N like the other Barrow core "
                   "data, converted); Organic_Matter_Content (wt%), from the organic and mineral masses of the core "
                   "section (method not detailed); depth is the mid-depth (cm) of the core section; "
                   f"{g}, {p}; date from package temporal coverage (2013-2016)")
                  for g, p in zip(d["Geomorph_Feature"], d["Polygon_feature"])],
    })
    return {"SOM": assemble(out, "SOM")}


# ====================================================================================================
# Packages
# ====================================================================================================

PACKAGES = [
    ("doi:10.5440/1109232", combine(("pH", ph_1109232), ("TC", c_1109232)), ('pH', 'TC')),
    ("doi:10.5440/1860505", combine(("pH", ph_1860505), ("TC", c_1860505)), ('pH', 'TC', 'LOI')),
    ("doi:10.15485/2588765", combine(("pH", ph_2588765), ("TC", c_2588765)), ('pH', 'TC')),
    ("doi:10.25581/ornlsfa.024/1837084", combine(("pH", ph_1837084), ("TC", c_1837084)), ('pH', 'TC', 'DOC')),
    ("doi:10.15485/3030222", combine(("TC", c_3030222)), ('SOC',)),
    ("doi:10.5440/1358456", combine(("TC", c_1358456)), ('SOM',)),
]
