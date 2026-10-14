"""Harmonize the hand-written packages of Group 2: coordinates come from package metadata (spatialCoverage), methods text, a user guide or a data description.

The soil pH functions (ph_<id>) were copied from notebooks/harmonize_ph and the carbon functions (c_<id>) from
notebooks/harmonize_carbon, unchanged apart from the assemble() signature. PACKAGES combines them into one function
per package that returns {variable key: harmonized table}.

Packages:
    doi:10.15485/1454273               [pH+carbon] SUMO, Los Alamos 2016
    doi:10.15485/1835182               [pH+carbon] Craig et al., six eastern US temperate forests 2017
    doi:10.15485/1898051               [pH+carbon] McFarlane et al., four temperate forest soils 2007
    doi:10.15485/2480291               [pH+carbon] Blodgett whole-soil warming: initial pits 2013 and control cores 2014-2018
    doi:10.15485/2564914               [pH+carbon] Blodgett whole-soil warming, STXM bulk chemistry 2021
    doi:10.15485/2583150               [pH+carbon] COMPASS-FME synoptic site characterization 2021-2022
    doi:10.15485/3024076               [pH+carbon] Mayes et al., Knoxville urban parks 2024-2025
    doi:10.25581/ornlsfa.034/2530530   [pH+carbon] MOFLUX quarterly soil cores 2017-2023
    doi:10.5440/1618325                [pH+carbon] Herndon et al., Barrow soil Fe 2015
    doi:10.15485/1866269               [carbon] Blodgett whole-soil warming, June 2018 cores (control plots)
    doi:10.15485/1797785               [carbon] Blodgett whole-soil warming, April 2018 O horizons (control plots)
    doi:10.15485/1892050               [carbon] EBIS bulk soils, Walker Branch and TVA, Oak Ridge 2001-2004
    doi:10.15485/1773008               [carbon] Argonne marsh and Tims Branch riparian wetland soils 2018-2019
    doi:10.15485/1908426               [carbon] Argonne marsh and Tims Branch riparian wetland soils 2020
    doi:10.3334/CDIAC/SPRUCE.005       [carbon] SPRUCE S1-Bog peat cores 2012
    doi:10.15485/2570819               [carbon] Council MM71 soil cores 2023
    doi:10.15485/1631972               [carbon]
    doi:10.15485/3003878               [carbon]
    doi:10.15485/2350835               [pH+carbon] Rowley et al., Point Reyes grassland cores
    doi:10.15485/2405147               [pH+carbon] Rowley et al., Point Reyes hillslope cores (cores 6-7 carry their own coordinates)
    doi:10.15485/1618870               [pH+carbon] Sihi et al., El Verde catena, Luquillo, Puerto Rico 2017-2018
    doi:10.15485/1830417               [carbon]
    doi:10.15485/3030227               [pH+carbon] EXCHANGE-D tea bag experiment 2025 (Time1 only)
    doi:10.15485/2407118               [carbon]
    doi:10.15485/2530252               [carbon]
    doi:10.15485/3024414               [carbon]
    doi:10.5440/1875838                [pH+carbon] NGEE Arctic Teller column experiment cores 2018
    doi:10.15485/1659374               [pH] Fitch et al., ectomycorrhizal gradient, Vermont 2019
    doi:10.15485/1810163               [pH] Zosso et al., Blodgett whole-soil warming 2018
    doi:10.15485/2587853               [pH] Wilson & Megonigal, coastal forest-to-wetland transects 2022

Attributes:
    PACKAGES: (DOI, package function, variables) per package; the package function combines the pH and carbon
        functions (extract.combine).
    BLODGETT: (latitude, longitude) of Blodgett Forest Research Station, doi:10.15485/2480291 spatialCoverage.
    WETLAND_SITES: Site -> (latitude, longitude, description) of the Argonne marsh and Tims Branch riparian sites
        (doi:10.15485/1773008 and 1908426 spatialCoverage).
    COMPASS_ZONES: (site, zone) -> (latitude, longitude) of the COMPASS-FME zone (plot) points, from the
        doi:10.15485/2583150 spatialCoverage descriptions.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
import re
from typing import Any, cast

import pandas as pd  # noqa: F401

from ..common import *  # noqa: F401,F403
from ..common import _text  # noqa: F401
from ..extract import Col, combine, from_columns, from_long, make_base, merge_tables  # noqa: F401
from ..datatypes import Tables


# ====================================================================================================
# Soil pH (from notebooks/harmonize_ph/group2_metadata_coords.py)
# ====================================================================================================


def ph_1454273() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/1454273.

    Package: SUMO Nitrogen Labeling Experiment and Soil Biogeochemistry.

    Source files: Soil biogeochemistry_2016.xlsx.

    Methods: pH_H2O.

    Notes:
        - Site point (SUMO, Frijoles Mesa) from the package spatialCoverage. All 68 rows are kept, including one 20-40
          cm sample without a pH value, as in the committed file.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_1454273())  # doctest: +SKIP
        68
    """
    doi = "doi:10.15485/1454273"
    src = "Soil biogeochemistry_2016.xlsx"
    d = read_excel(doi, src, sheet_name="Raw data")
    # Site point (SUMO, Frijoles Mesa) from the package spatialCoverage. All 68 rows are kept,
    # including one 20-40 cm sample without a pH value, as in the committed file.
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Tree_ID"], "id_type": "tree", "depth": d["depth"],
        "date": d["Date"].str[:10], "pH": d["pH"], "ph_method": "pH_H2O",
        "latitude": 35.8184, "longitude": -106.3061, "notes": "",
    })
    return assemble(out, "pH", raw=True)


def ph_1618870() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/1618870.

    Package: Soil chemistry data across a catena in the Luquillo Experimental Forest, Puerto Rico.

    Source files: SoilData_ElVERDE_PR.csv.

    Location: package metadata (spatialCoverage; single El Verde point shared by ridge, slope and valley positions).

    Methods: pH_CaCl2, pH_H2O.

    Notes:
        - "BNovember1,2017" is a typo for "November1,2017" in the source.
        - Two methods stacked as separate rows.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_1618870())  # doctest: +SKIP
        119
    """
    doi = "doi:10.15485/1618870"
    src = "SoilData_ElVERDE_PR.csv"
    d = strip_bom(read_csv(doi, src))
    d["source_row"] = (d.index + 2).astype(str)  # row number in the file (header is row 1)
    # "BNovember1,2017" is a typo for "November1,2017" in the source.
    d["date"] = pd.to_datetime(d["Sampling_Date"].str.lstrip("B"), format="%B%d,%Y").dt.strftime("%Y-%m-%d")
    keys = ["Soil Site", "Topographic_locations", "Field_replicate", "Lab_replicate"]
    d["id"] = d[keys].apply(lambda r: ":".join(v.strip() for v in r), axis=1)
    lead = ("lat/long source: doi:10.15485/1618870 package metadata (spatialCoverage; single El Verde point shared "
            "by ridge, slope and valley positions); ")
    tail = ("; 0-10 cm; sampled quarterly Apr 2017-May 2018; lab replicates (a, b) kept as separate rows; "
            "source_row = row in SoilData_ElVERDE_PR.csv")
    methods = {"pH_H2O": "pH_H2O: deionized water", "pH_CaCl2": "pH_CaCl2: 0.005 M CaCl2"}
    frames = []
    for col in ["pH_H2O", "pH_CaCl2"]:  # two methods stacked as separate rows
        x = d[~is_missing(d[col])]
        frames.append(pd.DataFrame({
            "doi": doi, "source_file": src, "id": x["id"], "id_type": ":".join(keys), "depth": "0-10",
            "date": x["date"], "pH": x[col], "ph_method": col, "latitude": 18.32134, "longitude": -65.81948,
            "source_row": x["source_row"],
            "notes": lead + methods[col] + ", 1:2 soil:solution, glass electrode (Thomas 1996)" + tail,
        }))
    return assemble(pd.concat(frames), "pH", extra=["source_row"], raw=True)


def ph_1659374() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/1659374.

    Package: Soil microbial function and fungal community data along an ectomycorrhizal basal area gradient,
    Vermont, May 2019.

    Source files: SCxTS_CUE.csv.

    Location: package metadata (spatialCoverage: Norwich, VT 43.72, -72.35 and Hanover, NH 43.72, -72.16).

    Methods: pH_H2O.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_1659374())  # doctest: +SKIP
        20
    """
    doi = "doi:10.15485/1659374"
    src = "SCxTS_CUE.csv"
    d = strip_bom(read_csv(doi, src)).sort_values(["Sample", "Layer"])
    note = ("lat/long source: doi:10.15485/1659374 package metadata (spatialCoverage: Norwich, VT 43.72, -72.35 and "
            "Hanover, NH 43.72, -72.16); There are two sites but no information on linking data to the exact site. "
            "Mid-point is taken; pH_H2O: 1:1 soil:deionized water, benchtop pH meter (Mettler Toledo), measured on "
            "frozen organic horizon and mineral soil (mineral sieved <2 mm); date = package temporal coverage start "
            "(title: May 2019)")
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Sample"] + ":" + d["Layer"], "id_type": "Sample:Layer",
        "depth": d["Layer"].map({"Mineral": "M", "Organic": "O"}), "date": "2019-05-22", "pH": d["pH"],
        "ph_method": "pH_H2O", "latitude": 43.72, "longitude": (-72.35 + -72.16) / 2, "notes": note,
    })
    return assemble(out, "pH", raw=True)


def ph_1810163() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/1810163.

    Package: Blodgett Forest CA Warming Experiment phospholipid fatty acid and branched glycerol dialkyl glycerol
    tetraethers data 2018 from: "Whole-soil warming decreases abundance and modifies the community structure of
    microorganisms in the subsoil but not in surface soil".

    Source files: 20210719_Data_soil_2021_14.csv.

    Location: Zosso et al. 2021 (site-level coordinates; no plot-level coordinates).

    Methods: pH_CaCl2.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_1810163())  # doctest: +SKIP
        48
    """
    doi = "doi:10.15485/1810163"
    src = "20210719_Data_soil_2021_14.csv"
    d = strip_bom(read_csv(doi, src))
    d = d[~is_missing(d["pH"])]
    lead = ("lat/long source: Zosso et al. 2021 (site-level coordinates; no plot-level coordinates); pH in 0.01 M "
            "CaCl2 (soil:solution ratio not reported); sampling date reported only as April 2018; ")
    combined = ("; combined sample (Lab-IDs NO51 and NO52) covering 0-20 cm, overlapping the 0-8 cm sample NO50; "
                "pH reported to 3 decimals, likely an average of the two")
    notes = [lead + f"plot {p} ({t}, block {b})" + (combined if lab.endswith("NO51_52") else "")
             for p, t, b, lab in zip(d["Plot"], d["Treatment"], d["Block"], d["Lab-ID"])]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Lab-ID"], "id_type": "Lab-ID", "depth": d["Sampling Depth"],
        "date": "2018-04", "pH": d["pH"], "ph_method": "pH_CaCl2", "latitude": 38.91194, "longitude": -120.66111,
        "notes": notes,
    })
    return assemble(out, "pH", raw=True)


def ph_1835182() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/1835182.

    Package: Data for “Fast-decaying plant litter enhances soil carbon in temperate forests, but not through
    microbial physiological traits”.

    Source files: field_data.csv.

    Location: Data_description.pdf (site-level table, ...; nine plots within ~1 km2, plot coordinates not given).

    Methods: pH_CaCl2.

    Notes:
        - Site table in the package's Data_description.pdf (Spatial Coverage); SRC is the source's code for SERC.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_1835182())  # doctest: +SKIP
        54
    """
    doi = "doi:10.15485/1835182"
    src = "field_data.csv"
    d = strip_bom(read_csv(doi, src))
    # Site table in the package's Data_description.pdf (Spatial Coverage); SRC is the source's code for SERC.
    sites = {
        "HF": (42.53, -72.18, "Harvard Forest, MA"),
        "LDW": (39.23, -86.22, "Lilly-Dickey Woods, IN"),
        "SCBI": (38.90, -78.15, "Smithsonian Conservation Biology Institute, VA"),
        "SRC": (38.88, -76.57, "Smithsonian Environmental Research Center (SERC), MD"),
        "TRC": (38.52, -90.55, "Tyson Research Center, MO"),
        "WLF": (45.55, -88.80, "Wabikon Lake Forest, WI"),
    }

    def note(site: str, myco: str) -> str:
        s = sites[site][2]
        n = (f"lat/long source: doi:10.15485/1835182:Data_description.pdf (site-level table, {s}; nine plots within "
             "~1 km2, plot coordinates not given); 0.01 M CaCl2, 8:1 mL solution:g soil, benchtop pH meter; composite "
             "of four 5-cm-diameter cores per 20x20 m plot (inner 10x10 m), 0-5 cm including any thin O horizon")
        if site == "HF":
            n += " (thick O horizon >5 cm removed before coring at HF)"
        n += f"; sampled July 2017 (no day given); plot mycorrhizal dominance {myco}"
        if site == "SRC":
            n += "; site code SRC in source = SERC"
        if site == "LDW":
            n += ("; LDW plots are a subset of the Lilly-Dickey Woods ForestGEO plot also sampled 2012-2014 in "
                  "doi:10.15485/2588765 (different sampling, not duplicates)")
        return n

    keys = ["Site", "Plot", "Myco"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": "0-5", "date": "2017-07", "pH": d["pH"], "ph_method": "pH_CaCl2",
        "latitude": d["Site"].map(lambda s: sites[s][0]), "longitude": d["Site"].map(lambda s: sites[s][1]),
        "notes": [note(s, m) for s, m in zip(d["Site"], d["Myco"])],
    })
    return assemble(out, "pH", raw=True)


def ph_1898051() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/1898051.

    Package: Organic carbon content and turnover time in relation to pedogenic iron and aluminum in four temperate
    forest soils sampled in 2007.

    Source files: SoilChemistrySiteCharac_RCP_20140307_EXP.csv.

    Location: package metadata (site-level coordinates, longitude sign corrected to west; package lists positive
    longitudes).

    Methods: pH_H2O.

    Notes:
        - Site points from the package spatialCoverage; the package lists positive longitudes, corrected to west.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_1898051())  # doctest: +SKIP
        40
    """
    doi = "doi:10.15485/1898051"
    src = "SoilChemistrySiteCharac_RCP_20140307_EXP.csv"
    d = strip_bom(read_csv(doi, src))
    # Site points from the package spatialCoverage; the package lists positive longitudes, corrected to west.
    sites = {
        "BEF": (44.0647, -71.288, "Bartlett Experimental Forest, NH"),
        "HAF": (42.5377, -72.1715, "Harvard Forest, MA"),
        "MOZ": (38.7441, -92.2, "Missouri Ozarks Baskett Wilderness, MO"),
        "UMBS": (45.5598, -84.7138, "University of Michigan Biological Station, MI"),
    }
    note = ("lat/long source: package metadata (site-level coordinates, longitude sign corrected to west; package lists "
            "positive longitudes); {}; pH method inferred as water 1:1 (McFarlane et al. 2013 measured both water and "
            "0.01 M CaCl2 at 1:1; package column unlabeled, values match reported water pH); sampled Nov-Dec 2007; no "
            "plot ID in source; 5 plots per site and depth are not individually identified")
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Site"], "id_type": "Site",
        "depth": d["Depth"].str.replace(" cm", "", regex=False), "date": "2007-11/2007-12", "pH": d["pH"],
        "ph_method": "pH_H2O", "latitude": d["Site"].map(lambda s: sites[s][0]),
        "longitude": d["Site"].map(lambda s: sites[s][1]), "notes": d["Site"].map(lambda s: note.format(sites[s][2])),
    })
    return assemble(out, "pH", raw=True)


def ph_2350835() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/2350835.

    Package: Association between soil organic carbon and calcium in acidic grassland soils from Point Reyes National
    Seashore, CA.

    Source files: Bulk_Data.csv.

    Location: package metadata (spatial coverage 'Core ...'; the data file has no coordinates).

    Methods: pH_KCl.

    Notes:
        - Core points from the package spatialCoverage ("Core 1", "Core 2", "Core 3").

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_2350835())  # doctest: +SKIP
        24
    """
    doi = "doi:10.15485/2350835"
    src = "Bulk_Data.csv"
    d = strip_bom(read_csv(doi, src)).iloc[1:]  # second line holds units
    d = d[~is_missing(d["Soil pH"])]
    # Core points from the package spatialCoverage ("Core 1", "Core 2", "Core 3").
    cores = {"1": (37.970136, -122.732161), "2": (37.989346, -122.748204), "3": (38.062778, -122.814722)}
    core = d["Sample"].str.extract(r"Core (\d+)")[0]
    note = ("lat/long source: doi:10.15485/2350835 package metadata (spatial coverage 'Core {}'; the data file has no "
            "coordinates); pH method: 1 M KCl, 1:2.5 soil:solution, dried (40 C) <2 mm soil, glass combination "
            "electrode, per package methods (Rowley et al. 2023 Biogeochemistry 165:91); acidic grassland soil core, "
            "Point Reyes National Seashore, CA; sampling date not given in package (temporal coverage 2020-11 to "
            "2022-11; Rowley et al. 2023 full text not accessible)")
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Sample"], "id_type": "Sample", "depth": d["Depth"],
        "date": "2020-11/2022-11", "pH": d["Soil pH"], "ph_method": "pH_KCl",
        "latitude": core.map(lambda c: cores[c][0]), "longitude": core.map(lambda c: cores[c][1]),
        "notes": core.map(note.format),
    })
    return assemble(out, "pH", raw=True)


def ph_2405147() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/2405147.

    Package: The importance of accounting for landscape position when investigating grasslands: A multidisciplinary
    characterisation of a Californian coastal grassland.

    Source files: SoilCores.xlsx.

    Location: package metadata (Point Reyes Experimental Field Site point; no per-core coordinates for the five
    hillslope cores); SoilCores.xlsx (second table, core coordinates 37°58′13.6″ N, 122°43′55.7″ W converted to
    decimal degrees); SoilCores.xlsx (second table, core coordinates 37°58′12.9″ N, 122°43′56″ W converted to
    decimal degrees).

    Methods: pH_KCl.

    Notes:
        - Table 1 (rows 2-48): hillslope cores 1-5; site point from the package metadata.
        - Table 2 (rows 50-79, no header): cores 6-8 with their own DMS coordinates (column A), sample name (C),
          mid-depth (I) and pH (J). Core 8 duplicates doi:10.15485/2350835 Core 1 and is excluded.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_2405147())  # doctest: +SKIP
        68
    """
    doi = "doi:10.15485/2405147"
    src = "SoilCores.xlsx"
    x = read_excel(doi, src, sheet_name="Soil Cores", header=None)
    rows = []
    # Table 1 (rows 2-48): hillslope cores 1-5; site point from the package metadata.
    t1 = x.iloc[1:48]
    t1 = t1[t1[0] != ""]
    for r in t1.itertuples(index=False):
        core, zone, depth, ph = r[0], r[1], r[3], r[6]
        rows.append(dict(
            doi=doi, source_file=src, id=f"Core {core}:Zone {zone}", id_type="New core:Zone", depth=depth,
            date="2020-10/2020-12", pH=ph, ph_method="pH_KCl", latitude=37.9711, longitude=-122.7301,
            notes=("lat/long source: doi:10.15485/2405147 package metadata (Point Reyes Experimental Field Site point; "
                   "no per-core coordinates for the five hillslope cores); pH method: 1 M KCl, 1:2.5, dried (40 C) soil, "
                   "glass combination electrode, per package methods (Rowley et al. 2024 Earth's Future "
                   "12:e2023EF004208; water pH measured but not reported); "
                   f"hillslope core {core} in landscape zone {zone}; sampled October-December 2020")))
    # Table 2 (rows 50-79, no header): cores 6-8 with their own DMS coordinates (column A), sample name (C),
    # mid-depth (I) and pH (J). Core 8 duplicates doi:10.15485/2350835 Core 1 and is excluded.
    t2 = x.iloc[49:]
    t2 = t2[t2[2].str.match(r"Core [67]\.")]
    for core, g in t2.groupby(t2[2].str.extract(r"Core (\d+)\.")[0], sort=True):
        coord = str(g.iloc[0, 0])
        lat_txt, lon_txt = coord.split(",")
        lat, lon = round(dms_to_decimal(lat_txt), 6), round(dms_to_decimal(lon_txt), 6)
        top = 0.0
        for r in g.itertuples(index=False):
            mid = float(r[8])
            bottom = 2 * mid - top  # contiguous layers rebuilt from mid-depths
            rows.append(dict(
                doi=doi, source_file=src, id=r[2], id_type="Sample", depth=depth_range(top, bottom),
                date="2020-11/2022-11", pH=r[9], ph_method="pH_KCl", latitude=lat, longitude=lon,
                notes=(f"lat/long source: doi:10.15485/2405147:SoilCores.xlsx (second table, core coordinates {coord} "
                       "converted to decimal degrees); pH method: 1 M KCl, 1:2.5, per package methods; depth interval "
                       f"reconstructed from source mid-depths ({fmt_num(mid)} cm) assuming contiguous layers from 0 cm "
                       "(method reproduces doi:10.15485/2350835 Core 1 ranges within 0.5 cm); second-table core 8 "
                       "excluded as duplicate of doi:10.15485/2350835 Core 1; sampling date not given for cores 6-7 "
                       "(range of related package doi:10.15485/2350835 used)")))
            top = bottom
    return assemble(pd.DataFrame(rows), "pH", raw=True)


def ph_2480291() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/2480291.

    Package: Experimental Soil Warming Impacts Soil Moisture and Plant Water Stress and Thereby Ecosystem Carbon
    Dynamics (Blodgett, CA)

    Source files: Blodgett_Initial_Characterization_20200410.xlsx.

    Location: package metadata (spatialCoverage; single Blodgett Forest Research Station point, site-level; no pit
    coordinates).

    Notes:
        - Date from sample names "131030_Pit ..." (YYMMDD) in sheet "C and N stocks".

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_2480291())  # doctest: +SKIP
        33
    """
    doi = "doi:10.15485/2480291"
    src = "Blodgett_Initial_Characterization_20200410.xlsx"
    x = pd.read_excel(raw_path(doi, src), sheet_name="pH", header=2).dropna(subset=["Pit"])
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": x["Pit"].map(fmt_num), "id_type": "Pit",
        "depth": [depth_range(a, b) for a, b in zip(x["Top Depth"], x["Bottom Depth"])],
        # Date from sample names "131030_Pit ..." (YYMMDD) in sheet "C and N stocks".
        "date": "2013-10-30", "pH": x["pH average"].round(3), "ph_method": "",
        "latitude": 38.91044, "longitude": -120.66236,
        "notes": [("lat/long source: doi:10.15485/2480291 package metadata (spatialCoverage; single Blodgett Forest "
                   "Research Station point, site-level; no pit coordinates); sheet 'pH'; pH = 'pH average' of two "
                   f"readings ({fmt_num(a)}, {fmt_num(b)}); pH method not reported in package: circumstantially likely "
                   "water pH, since values (5.2-7.2) run ~0.5-1 unit higher than 0.01 M CaCl2 pH at the same site "
                   "(3.7-6.1; doi:10.15485/1810163, 2018), but not confirmed; date inferred from sample names "
                   "'131030_Pit ...' in sheet 'C and N stocks' (YYMMDD), not stated in package; initial site "
                   "characterization pit") for a, b in zip(x["pH rep 1"], x["pH rep 2"])],
    })
    return assemble(out, "pH", raw=True)


def ph_2564914() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/2564914.

    Package: Calcium is associated with specific soil organic carbon decomposition products at Blodgett Forest
    Research Center, Georgetown, California as analysed with scanning transmission X-ray microscopy carbon near-edge
    X-ray absorption fine structure spectroscopy.

    Source files: Bulk_Soil_Chemistry.csv.

    Location: package description ('The samples were collected from here: 38.912013, -120.661469'; site-level;
    package spatialCoverage lists a different point, 38.8862914, -120.6477055).

    Methods: pH_CaCl2.

    Notes:
        - Treatment is written on the first row only.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_2564914())  # doctest: +SKIP
        25
    """
    doi = "doi:10.15485/2564914"
    src = "Bulk_Soil_Chemistry.csv"
    x = read_csv(doi, src, header=None, skiprows=2).iloc[:, [0, 1, 2, 6]]
    x.columns = ["Treatment", "Profile", "Depth", "pH"]
    x["Treatment"] = x["Treatment"].replace("", None).ffill()  # treatment is written on the first row only
    x = x[~x["Treatment"].str.startswith("Heated") & ~is_missing(x["pH"])]  # heated plots excluded
    note = ("lat/long source: doi:10.15485/2564914 package description ('The samples were collected from here: "
            "38.912013, -120.661469'; site-level; package spatialCoverage lists a different point, 38.8862914, "
            "-120.6477055); 0.01 M CaCl2 at a 2:1 ratio (as stated in package methods), Hamilton Polilyte Lab "
            "electrode, University of Zurich; bulk characterisation on a separate core adjacent to the STXM soil core; "
            "cores sampled May 2021 (no day given); control plot (heated +4 C whole-soil warming plots, profiles "
            "Heated:1-3, excluded); profile {p} presumably = paired plot {p} (methods: control cores 1-3, warmed cores "
            "4-6 from paired plots 1-3)")
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": "Control:" + x["Profile"], "id_type": "Treatment:Profile",
        "depth": x["Depth"], "date": "2021-05", "pH": x["pH"], "ph_method": "pH_CaCl2",
        "latitude": 38.912013, "longitude": -120.661469, "notes": x["Profile"].map(lambda p: note.format(p=p)),
    })
    return assemble(out, "pH", raw=True)


def ph_2583150() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/2583150.

    Package: COMPASS-FME Synoptic Site Characterization.

    Source files: chemistry_combined_all_horizons.csv.

    Location: package metadata (spatialCoverage description, ... plot, zone-level; 8-9 samples per zone spread over
    200-1000 m2 share one point).

    Methods: pH_H2O.

    Notes:
        - Zone (plot) coordinates written in the package spatialCoverage site descriptions.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_2583150())  # doctest: +SKIP
        239
    """
    doi = "doi:10.15485/2583150"
    src = "chemistry_combined_all_horizons.csv"
    a = read_csv(doi, src)
    d = a[(a["name"].str.lower() == "ph") & ~is_missing(a["value"])].copy()
    # Zone (plot) coordinates written in the package spatialCoverage site descriptions.
    zones = {
        ("CRC", "upland"): (41.6153, -83.2297), ("CRC", "transition"): (41.6219, -83.2381), ("CRC", "wetland"): (41.6219, -83.2389),
        ("PTR", "upland"): (41.5015, -83.0461), ("PTR", "transition"): (41.5020, -83.0456), ("PTR", "wetland"): (41.5016, -83.0444),
        ("OWC", "upland"): (41.3763, -82.5070), ("OWC", "transition"): (41.3758, -82.5063), ("OWC", "wte"): (41.3760, -82.5071),
        ("OWC", "wetland"): (41.3761, -82.5078),
        ("GCW", "upland"): (38.8741, -76.5522), ("GCW", "transition"): (38.8745, -76.5515), ("GCW", "wetland"): (38.8750, -76.5500),
        ("MSM", "upland"): (38.4315, -76.2267), ("MSM", "transition"): (38.4310, -76.2277), ("MSM", "wetland"): (38.4308, -76.2286),
        ("GWI", "upland"): (37.2192, -76.4087), ("GWI", "transition"): (37.2194, -76.4092), ("GWI", "wetland"): (37.2189, -76.4101),
    }
    names = {"CRC": "Crane Creek", "PTR": "Portage River", "OWC": "Old Woman Creek", "GCW": "GCReW",
             "MSM": "Moneystump Marsh", "GWI": "Goodwin Islands"}
    zcode = {"upland": "UP", "transition": "TR", "wetland": "W", "wte": "WTE"}
    month = {"Dec2021": "2021-12", "May22": "2022-05", "Aug22": "2022-08"}
    d["m"] = d["sample_label"].str.extract(r"COMPASS_(\w+?)_")[0]
    notes = []
    for s, t, h, m, tn in zip(d["site"], d["transect"], d["horizon"], d["m"], d["tree_number"]):
        hz = f"{h} horizon (organic), " if h == "O" else f"{h} horizon (mineral), "
        hz += "surface sample, top 5-10 cm" if h in ("O", "A") else "subsurface B horizon, depth not reported"
        notes.append(f"lat/long source: doi:10.15485/2583150 package metadata (spatialCoverage description, {names[s]} "
                     f"{zcode[t]} plot, zone-level; 8-9 samples per zone spread over 200-1000 m2 share one point); "
                     "pH_H2O: freeze-dried soil shaken with MilliQ water 1:10 w:v for 30 min, Milwaukee MW802 PRO probe; "
                     f"{hz}; sampled {month[m]} (month from sample_label; methods give Erie Dec 2021, MSM/GWI May 2022, "
                     f"GCW Sep 2022); COMPASS-FME synoptic site {s}, {t} zone, sampling point (tree_number) {tn}")
    keys = ["sample_label", "site", "transect", "tree_number", "horizon"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": d["horizon"].map({"O": "O", "A": "M", "B": "M"}), "date": d["m"].map(month), "pH": d["value"],
        "ph_method": "pH_H2O",
        "latitude": [zones[(s, t)][0] for s, t in zip(d["site"], d["transect"])],
        "longitude": [zones[(s, t)][1] for s, t in zip(d["site"], d["transect"])], "notes": notes,
    })
    return assemble(out, "pH", raw=True)


def ph_2587853() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/2587853.

    Package: Data for Wilson and Megonigal (2025), "Nitrate reduction across soils transitioning from coastal forest
    to wetland are hotspots for denitrification"

    Source files: NExpt_ESSDIVE_Datafile.csv.

    Location: package metadata (spatialCoverage description, ... plot, zone-level; replicate cores share one point).

    Methods: pH_H2O.

    Notes:
        - Zone coordinates from the package spatialCoverage descriptions (WC = wetland "W" plot).

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_2587853())  # doctest: +SKIP
        36
    """
    doi = "doi:10.15485/2587853"
    src = "NExpt_ESSDIVE_Datafile.csv"
    d = strip_bom(read_csv(doi, src))
    # Zone coordinates from the package spatialCoverage descriptions (WC = wetland "W" plot).
    zones = {
        ("GCW", "UP"): (38.8741, -76.5522), ("GCW", "TR"): (38.8745, -76.5515), ("GCW", "WC"): (38.8750, -76.5500),
        ("MSM", "UP"): (38.4315, -76.2267), ("MSM", "TR"): (38.4310, -76.2277), ("MSM", "WC"): (38.4308, -76.2286),
        ("GWI", "UP"): (37.2192, -76.4087), ("GWI", "TR"): (37.2194, -76.4092), ("GWI", "WC"): (37.2189, -76.4101),
        ("SWH", "UP"): (37.5708, -76.8954), ("SWH", "TR"): (37.56883, -76.8964), ("SWH", "WC"): (37.56659, -76.8970),
    }
    names = {"GCW": "GCReW", "MSM": "Moneystump Swamp", "GWI": "Goodwin Island", "SWH": "Sweet Hall Marsh"}
    zp = {"UP": "UP", "TR": "TR", "WC": "W"}
    zl = {"UP": "upland", "TR": "transition", "WC": "wetland center"}
    notes = [(f"lat/long source: doi:10.15485/2587853 package metadata (spatialCoverage description, {names[s]} {zp[z]} "
              "plot, zone-level; replicate cores share one point); pH_H2O: soil slurry 1:5 soil:water (data dictionary); "
              "whole core homogenized, core depth not reported; sampled September 2022 (no day given); "
              f"zone {z} ({zl[z]}) of a coastal forest-to-wetland transect"
              + ("; Sample_ID 'SHW_TR_A' as in source (typo for SWH)" if sid == "SHW_TR_A" else ""))
             for s, z, sid in zip(d["Site"], d["Zone"], d["Sample_ID"])]
    keys = ["Sample_ID", "Site", "Zone", "Replicate"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys), "depth": "",
        "date": "2022-09", "pH": d["pH"], "ph_method": "pH_H2O",
        "latitude": [zones[(s, z)][0] for s, z in zip(d["Site"], d["Zone"])],
        "longitude": [zones[(s, z)][1] for s, z in zip(d["Site"], d["Zone"])], "notes": notes,
    })
    return assemble(out, "pH", raw=True)


def ph_3024076() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/3024076.

    Package: Soil Characterizations of Five Urban Sites in Knoxville, Tennessee. 2024-2025.

    Source files: Soil_pH.csv.

    Location: package metadata (spatialCoverage point for ..., site-level; cores taken within 3 m of the site's soil
    monitoring station).

    Methods: pH_H2O.

    Notes:
        - One ID has a trailing space ("CE2 ")

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_3024076())  # doctest: +SKIP
        230
    """
    doi = "doi:10.15485/3024076"
    src = "Soil_pH.csv"
    d = strip_bom(read_csv(doi, src))
    d["Soil ID"] = d["Soil ID"].str.strip()  # one ID has a trailing space ("CE2 ")
    # Park points from the package spatialCoverage.
    parks = {"SEEED": (35.971, -83.903, "SEEED"), "Victor Ashe": (35.9825, -83.996, "Victor Ashe Park (VAP)"),
             "West Hills": (35.9316, -84.044, "West Hills Park (WHP)"),
             "Cumberland Estates": (35.983, -84.007, "Cumberland Estates Park (CEP)"),
             "West View": (35.9665, -83.961, "West View Park (WVP)")}
    keys = ["Location", "Soil ID", "Replicate #"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": "0-15", "date": d["Sample Date"].str.replace("_", "-"), "pH": d["pH"], "ph_method": "pH_H2O",
        "latitude": d["Location"].map(lambda s: parks[s][0]), "longitude": d["Location"].map(lambda s: parks[s][1]),
        "notes": [(f"lat/long source: doi:10.15485/3024076 package metadata (spatialCoverage point for {parks[s][2]}, "
                   "site-level; cores taken within 3 m of the site's soil monitoring station); pH_H2O: 1 part soil "
                   "(dried at 60-70 C) to 4 parts MQ water, shaken, centrifuged 3,500 rcf 10 min, pH of supernatant with "
                   "probe; 0-15 cm, 2-inch hammer corer; urban park soil, Knoxville TN; Replicate # = analytical "
                   "replicate of the same core (2-3 per core per methods)") for s in d["Location"]],
    })
    return assemble(out, "pH", raw=True)


def _ecd_kits() -> dict:
    """Read the EXCHANGE-D kit coordinates of doi:10.15485/3030227.

    The 34 "Kxxx, <site>" spatialCoverage entries were saved once to reference/10.15485_3030227_kit_coordinates.csv with
    ``curl -s https://api.ess-dive.lbl.gov/packages/doi:10.15485/3030227`` and are kept in the repo, so the function
    runs offline.

    Returns:
        {kit id: (latitude, longitude, description)}.

    Examples:
        >>> len(_ecd_kits())  # doctest: +SKIP
        34
    """
    ref = pd.read_csv(Path(__file__).parent.parent / "reference" / "10.15485_3030227_kit_coordinates.csv", dtype=str)
    return {r.kit_id: (float(r.latitude), float(r.longitude), r.description) for r in cast("Iterable[Any]", ref.itertuples())}


def ph_3030227() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/3030227.

    Package: EXCHANGE Campaign Degradation (ECD): Understanding Decomposition Dynamics Across Mid-Atlantic and Great
    Lakes Coastal Ecosystems.

    Source files: ecd_soil_ph_conductivity_L2.csv.

    Location: package metadata (spatialCoverage ..., USA', kit/site-level; upland, transition and wetland share one
    point).

    Methods: unknown.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_3030227())  # doctest: +SKIP
        95
    """
    doi = "doi:10.15485/3030227"
    src = "ecd_soil_ph_conductivity_L2.csv"
    d = strip_bom(read_csv(doi, src))
    d = d[(d["timepoint"] == "Time1") & ~is_missing(d["ph"])]  # Time2 (tea bag retrieval) excluded
    kits = _ecd_kits()
    keys = ["kit_id", "transect_location", "timepoint"]
    notes = [(f"lat/long source: doi:10.15485/3030227 package metadata (spatialCoverage '{kits[k][2]}', kit/site-level; "
              "upland, transition and wetland share one point); pH method not reported (data dictionary: 'Soil pH'); "
              "surface soil grab sample, depth not reported; Time1 = soil grab sampled at tea bag deployment, summer "
              "2025 (exact date not given); experimental design: EXCHANGE-D tea bag decomposition experiment, soil "
              "sampled at deployment (Time1) and again at retrieval ~77-107 days later (Time2, fall 2025); Time2 samples "
              "ignored (only the Time1 baseline kept; Time2 pH differed by median 0.54 units, upland ~0.75 lower); "
              f"{t} position on coastal upland-transition-wetland transect; EXCHANGE-D (ECD) community sampling")
             for k, t in zip(d["kit_id"], d["transect_location"])]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys), "depth": "",
        "date": "2025", "pH": d["ph"], "ph_method": "unknown",
        "latitude": d["kit_id"].map(lambda k: kits[k][0]), "longitude": d["kit_id"].map(lambda k: kits[k][1]),
        "IGSN": d["igsn"], "notes": notes,
    })
    return assemble(out, "pH", raw=True)


def ph_2530530() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.25581/ornlsfa.034/2530530.

    Package: Quarterly Soil Core and Root Analyses from the Missouri Ozarks AmeriFlux (MOFLUX) Site, Ashland,
    Missouri, 2017-2023.

    Source files: MOFLUX_quarterly_soil_cores_2017_2023.csv.

    Location: package metadata (spatialCoverage MOFLUX site point; cores taken near plot 1 of the southeast
    transect, near the automated soil respiration chambers; no per-core coordinates; IGSN records checked: same site
    point).

    Methods: pH_H2O.

    Notes:
        - Three analytical replicates per core are consecutive rows without a replicate column.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_2530530())  # doctest: +SKIP
        471
    """
    doi = "doi:10.25581/ornlsfa.034/2530530"
    src = "MOFLUX_quarterly_soil_cores_2017_2023.csv"
    d = strip_bom(read_csv(doi, src))
    # Three analytical replicates per core are consecutive rows without a replicate column.
    d["rep"] = (d.groupby("Sample_Name").cumcount() + 1).astype(str)
    d = d[~is_missing(d["pH"])]
    note = ("lat/long source: doi:10.25581/ornlsfa.034/2530530 package metadata (spatialCoverage MOFLUX site point; cores "
            "taken near plot 1 of the southeast transect, near the automated soil respiration chambers; no per-core "
            "coordinates; IGSN records checked: same site point); pH_H2O: soil dried at 60-70 C, 1 part soil to 4 parts "
            "MQ water, supernatant measured with pH probe; 0-15 cm, 2-inch hammer corer, 8 cores per sampling date; "
            "three analytical replicates per core listed as consecutive rows without a replicate column (replicate "
            "number assigned by row order); Missouri Ozarks AmeriFlux (US-MOz), Baskett forest, quarterly sampling "
            "2017-2023")
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Sample_Name"] + ":" + d["rep"],
        "id_type": "Sample_Name:analytical_replicate (row order within Sample_Name)", "depth": "0-15",
        "date": d["Sample_Date"], "pH": d["pH"], "ph_method": "pH_H2O", "latitude": 38.7441, "longitude": -92.2,
        "IGSN": d["IGSN"], "notes": note,
    })
    return assemble(out, "pH", raw=True)


def ph_1618325() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.5440/1618325.

    Package: Iron and Phosphorus Geochemistry in High-Centered and Low-Centered Polygon Soils from the Barrow
    Environmental Observatory, Utqiagvik, Alaska, 2015.

    Source files: Herndon_BEO_SoilFe_TableS1_20200513.csv.

    Location: NGEE_User_Guidance_Document_template_BEO_SoilFe_20200515.pdf (general location for Area A,
    low-centered polygon; exact core locations not recorded);
    NGEE_User_Guidance_Document_template_BEO_SoilFe_20200515.pdf (general location for Area B, high-centered
    polygon; exact core locations not recorded).

    Methods: pH_KCl.

    Notes:
        - General locations per polygon from the package user guide (exact core locations not recorded).

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_1618325())  # doctest: +SKIP
        27
    """
    doi = "doi:10.5440/1618325"
    src = "Herndon_BEO_SoilFe_TableS1_20200513.csv"
    d = strip_bom(read_csv(doi, src)).iloc[1:]  # second line holds units
    d = d[~is_missing(d["Soil_pH"])]
    # General locations per polygon from the package user guide (exact core locations not recorded).
    poly = {"Low-centered": ("Area A, low-centered polygon", 71.2815, -156.61012),
            "High-centered": ("Area B, high-centered polygon", 71.27933, -156.60475)}
    keys = ["Sample_Name", "Polygon", "Feature", "Horizon"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": [depth_range(a, b) for a, b in zip(d["Upper_depth_cm"], d["Lower_depth_cm"])], "date": "2015-10",
        "pH": d["Soil_pH"], "ph_method": "pH_KCl",
        "latitude": d["Polygon"].map(lambda p: poly[p][1]), "longitude": d["Polygon"].map(lambda p: poly[p][2]),
        "IGSN": d["Sample_IGSN"],
        "notes": [("lat/long source: doi:10.5440/1618325:NGEE_User_Guidance_Document_template_BEO_SoilFe_20200515.pdf "
                   f"(general location for {poly[p][0]}; exact core locations not recorded); pH method: 1 M KCl, 1:5 "
                   "(1.0 g dry soil : 5 mL N2-degassed 1 M KCl, anaerobic chamber), per user guide; bulk "
                   f"{h.lower()} horizon of core {c}; sampled early October 2015 (package temporal coverage 2015-10-15)")
                  for p, h, c in zip(d["Polygon"], d["Horizon"], d["Core_IGSN"])],
    })
    return assemble(out, "pH", raw=True)


def ph_1875838() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.5440/1875838.

    Package: Arctic Soil Column Saturation & Drainage Experiment for Biogeochemical Redox Dynamics; Council, Alaska
    2020-2022.

    Source files: NGA287_Core_Characterization.csv.

    Location: package methods text (Field Site Description and Sampling; point for thermokarst channel cores
    NGADG0184/NGADG0185; the data file has no coordinates); package methods text (Field Site Description and
    Sampling; point for upland cores NGADG0189/NGADG0183, collected within 1 m of each other; the data file has no
    coordinates).

    Methods: pH_KCl.

    Notes:
        - Points written in the package methods text (Field Site Description and Sampling).
        - Increment midpoints -> 10 cm increments.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_1875838())  # doctest: +SKIP
        27
    """
    doi = "doi:10.5440/1875838"
    src = "NGA287_Core_Characterization.csv"
    d = strip_bom(read_csv(doi, src)).iloc[1:]  # second line holds units
    d = d[~is_missing(d["pH_KCl"])]
    # Points written in the package methods text (Field Site Description and Sampling).
    pts = {
        "Thermokarst": (64.860044, -163.697718, "point for thermokarst channel cores NGADG0184/NGADG0185"),
        "Upland": (64.859833, -163.698213, "point for upland cores NGADG0189/NGADG0183, collected within 1 m of each other"),
    }
    mid = d["Depth"].astype(float)
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["core"] + ":" + d["soil_Type"], "id_type": "core:soil_Type",
        "depth": [depth_range(m - 5, m + 5) for m in mid],  # increment midpoints -> 10 cm increments
        "date": "2018-07", "pH": d["pH_KCl"], "ph_method": "pH_KCl",
        "latitude": d["soil_Type"].map(lambda t: pts[t][0]), "longitude": d["soil_Type"].map(lambda t: pts[t][1]),
        "notes": [(f"lat/long source: doi:10.5440/1875838 package methods text (Field Site Description and Sampling; "
                   f"{pts[t][2]}; the data file has no coordinates); pH method: 1 M KCl, 1:5 (mass:volume), air-dried "
                   f"soil, triplicate mean (sd {sd}), per package methods; initial field-core characterization before the "
                   "column experiment (pre/post-experiment soil pH and column porewater pH excluded); depth converted "
                   f"from increment midpoint ({fmt_num(m)} cm) to its 10 cm increment; cores collected July 2018")
                  for t, sd, m in zip(d["soil_Type"], d["pH_KCl_stddev"], mid)],
    })
    return assemble(out, "pH", raw=True)


# ====================================================================================================
# Soil carbon (from notebooks/harmonize_carbon/group2_metadata_coords.py)
# ====================================================================================================

BLODGETT = (38.91044, -120.66236)  # doi:10.15485/2480291 spatialCoverage (Blodgett Forest Research Station)


def c_1454273() -> Tables:
    """Harmonize carbon variables of doi:10.15485/1454273.

    Package: SUMO Nitrogen Labeling Experiment and Soil Biogeochemistry.

    Source files: Soil biogeochemistry_2016.xlsx.

    Location: package metadata (spatialCoverage SUMO site point, State Road 4, Los Alamos NM; site-level, no
    per-tree coordinates; the harmonized soil pH file for this package uses 35.8184); package metadata
    (spatialCoverage SUMO site point, site-level).

    Methods: TC unknown; SOC TC_minus_TIC; SIC unknown.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), SOC (soil organic carbon), SIC
        (soil inorganic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_1454273().items()}  # doctest: +SKIP
        {'TC': 67, 'SOC': 67, 'SIC': 67}
    """
    doi = "doi:10.15485/1454273"
    src = "Soil biogeochemistry_2016.xlsx"
    d = read_excel(doi, src, sheet_name="Raw data")
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Tree_ID"], "id_type": "tree", "depth": d["depth"],
        "date": d["Date"].str[:10], "TC": d["TotalC"], "tc_method": UNKNOWN,
        "latitude": 35.8181, "longitude": -106.3061,
        "notes": ("lat/long source: doi:10.15485/1454273 package metadata (spatialCoverage SUMO site point, State Road 4, "
                  "Los Alamos NM; site-level, no per-tree coordinates; the harmonized soil pH file for this package uses "
                  "35.8184); TotalC in % (sheet 'Metadata': 'Total carbon content'); file also reports IC and OC; "
                  "instrument not given in the data file, methods referenced to Grossiord et al. 2018 (Plant Cell "
                  "Environ.); soil under individual trees of the SUMO survival-mortality experiment (Tree_ID)"),
    })
    base = out.drop(columns=["TC", "tc_method", "notes"])
    loc = ("lat/long source: doi:10.15485/1454273 package metadata (spatialCoverage SUMO site point, site-level); ")
    tail = "; methods referenced to Grossiord et al. 2018; soil under individual trees of the SUMO experiment (Tree_ID)"
    return {"TC": assemble(out, "TC"),
            "SOC": emit(base, "SOC", d["OC"], TC_MINUS_TIC,
                        loc + "OC (%), 'Total organic carbon content' (sheet 'Metadata'); equals TotalC minus IC in the "
                        "source" + tail),
            "SIC": emit(base, "SIC", d["IC"], UNKNOWN,
                        loc + "IC (%), 'Total inorganic carbon content' (sheet 'Metadata'); method not stated" + tail)}


def c_1835182() -> Tables:
    """Harmonize carbon variables of doi:10.15485/1835182.

    Package: Data for “Fast-decaying plant litter enhances soil carbon in temperate forests, but not through
    microbial physiological traits”.

    Source files: field_data.csv.

    Location: Data_description.pdf (site-level table, ...).

    Methods: TC unknown; DOC salt_extraction; MAOMC size_fractionation.

    Notes:
        - Site table in the package's Data_description.pdf (Spatial Coverage); SRC is the source's code for SERC.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), DOC (dissolved organic carbon),
        MAOMC (mineral-associated organic matter carbon).

    Examples:
        >>> {k: len(t) for k, t in c_1835182().items()}  # doctest: +SKIP
        {'TC': 54, 'DOC': 54, 'MAOMC': 54}
    """
    doi = "doi:10.15485/1835182"
    src = "field_data.csv"
    d = strip_bom(read_csv(doi, src))
    # Site table in the package's Data_description.pdf (Spatial Coverage); SRC is the source's code for SERC.
    sites = {
        "HF": (42.53, -72.18, "Harvard Forest, MA"),
        "LDW": (39.23, -86.22, "Lilly-Dickey Woods, IN"),
        "SCBI": (38.90, -78.15, "Smithsonian Conservation Biology Institute, VA"),
        "SRC": (38.88, -76.57, "Smithsonian Environmental Research Center (SERC), MD"),
        "TRC": (38.52, -90.55, "Tyson Research Center, MO"),
        "WLF": (45.55, -88.80, "Wabikon Lake Forest, WI"),
    }

    def note(site: str, myco: str, raw: str) -> str:
        n = (f"lat/long source: doi:10.15485/1835182:Data_description.pdf (site-level table, {sites[site][2]}; nine "
             "plots within ~1 km2, plot coordinates not given); TC converted from source column C x 100: the data "
             "description gives C in 'mg C g soil-1', but values (0.018-0.26) only make sense as g C g soil-1 "
             f"(source value {raw}); 'total soil C concentration' per Data_description.pdf, instrument not given; "
             "composite of four 5-cm cores per 20x20 m plot, 0-5 cm including any thin O horizon")
        if site == "HF":
            n += " (thick O horizon >5 cm removed before coring at HF)"
        n += f"; sampled summer 2017 (no day given); plot mycorrhizal dominance {myco}"
        if site == "SRC":
            n += "; site code SRC in source = SERC"
        return n

    keys = ["Site", "Plot", "Myco"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": "0-5", "date": "2017-07", "TC": [fmt_tc(v * 100) for v in num(d["C"])], "tc_method": UNKNOWN,
        "latitude": d["Site"].map(lambda s: sites[s][0]), "longitude": d["Site"].map(lambda s: sites[s][1]),
        "notes": [note(s, m, c) for s, m, c in zip(d["Site"], d["Myco"], d["C"])],
    })
    base = out.drop(columns=["TC", "tc_method", "notes"])
    locs = [f"lat/long source: doi:10.15485/1835182:Data_description.pdf (site-level table, {sites[s][2]})" for s in d["Site"]]
    tail = "; 0-5 cm plot composite (four cores), sampled summer 2017"
    return {"TC": assemble(out, "TC"),
            "DOC": emit(base, "DOC", d["DOC"], SALT_EXTRACTION,
                        [f"{l}; DOC = organic C extractable with 0.5 M K2SO4, ug C g-1 soil (= mg C kg-1), Data_description.pdf"
                         f"{tail}" for l in locs],
                        DOC_unit="mg C kg-1 dry soil", DOC_medium="0.5 M K2SO4 extract"),
            "MAOMC": emit(base, "MAOMC", [fmt_tc(v * 1000) for v in num(d["MAOMC"])], SIZE_FRACTIONATION,
                          [f"{l}; MAOMC = mineral-associated organic matter C (<53 um fraction); converted x1000 to g C kg-1 "
                           f"soil: the data description gives 'mg MAOM C g soil-1', but like column C the values (source "
                           f"{m}) only make sense as g/g{tail}" for l, m in zip(locs, d["MAOMC"])])}


def c_1898051() -> pd.DataFrame:
    """Harmonize total carbon of doi:10.15485/1898051.

    Package: Organic carbon content and turnover time in relation to pedogenic iron and aluminum in four temperate
    forest soils sampled in 2007.

    Source files: SoilChemistrySiteCharac_RCP_20140307_EXP.csv.

    Location: package metadata (site-level coordinates, longitude sign corrected to west; package lists positive
    longitudes).

    Methods: unknown.

    Returns:
        The total carbon table in the harmonized layout (common.assemble).

    Examples:
        >>> len(c_1898051())  # doctest: +SKIP
        40
    """
    doi = "doi:10.15485/1898051"
    src = "SoilChemistrySiteCharac_RCP_20140307_EXP.csv"
    d = strip_bom(read_csv(doi, src))
    d["source_row"] = (d.index + 2).astype(str)  # file line number (header = line 1)
    sites = {
        "BEF": (44.0647, -71.288, "Bartlett Experimental Forest, NH"),
        "HAF": (42.5377, -72.1715, "Harvard Forest, MA"),
        "MOZ": (38.7441, -92.2, "Missouri Ozarks Baskett Wilderness, MO"),
        "UMBS": (45.5598, -84.7138, "University of Michigan Biological Station, MI"),
    }
    note = ("lat/long source: package metadata (site-level coordinates, longitude sign corrected to west; package lists "
            "positive longitudes); {}; TC = source column '%C' (package title calls it organic carbon content; acidic, "
            "carbonate-free forest soils, so %C measured by combustion equals total C); instrument not given in "
            "package; sampled Nov-Dec 2007; no plot ID in source; 5 plots per site and depth are not individually "
            "identified")
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Site"], "id_type": "Site",
        "depth": d["Depth"].str.replace(" cm", "", regex=False), "date": "2007-11/2007-12", "TC": d["%C"],
        "tc_method": UNKNOWN, "latitude": d["Site"].map(lambda s: sites[s][0]),
        "longitude": d["Site"].map(lambda s: sites[s][1]), "source_row": d["source_row"],
        "notes": d["Site"].map(lambda s: note.format(sites[s][2])),
    })
    return assemble(out, "TC", extra=["source_row"])


def c_2480291() -> Tables:
    """Harmonize total carbon, dissolved organic carbon of doi:10.15485/2480291.

    Package: Experimental Soil Warming Impacts Soil Moisture and Plant Water Stress and Thereby Ecosystem Carbon
    Dynamics (Blodgett, CA)

    Source files: Blodgett_Initial_Characterization_20200410.xlsx, TrtCoreData_CN_MB.csv.

    Location: package metadata (spatialCoverage; single Blodgett Forest Research Station point, site-level; no pit
    or plot coordinates).

    Methods: TC dry_combustion; DOC salt_extraction.

    Notes:
        - Several control cores per plot, depth and date share Plot:Treatment (UID mostly blank): source_row keys them.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), DOC (dissolved organic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_2480291().items()}  # doctest: +SKIP
        {'TC': 146, 'DOC': 60}
    """
    r: Any  # one source row (itertuples / to_dict record): cell types are not known statically
    doi = "doi:10.15485/2480291"
    loc = ("lat/long source: doi:10.15485/2480291 package metadata (spatialCoverage; single Blodgett Forest Research "
           "Station point, site-level; no pit or plot coordinates)")
    rows = []

    src = "Blodgett_Initial_Characterization_20200410.xlsx"
    x = pd.read_excel(raw_path(doi, src), sheet_name="C and N stocks").dropna(subset=["Pit"])
    for i, r in zip(x.index, x.itertuples()):
        top, bot = must_match(r"(\d+)-(\d+)\.raw$", r.Name).groups()
        rows.append(dict(
            doi=doi, source_file=src, id=f"{fmt_num(r.Pit)}", id_type="Pit", depth=depth_range(top, bot),
            date="2013-10-30", TC=fmt_tc(r.C), tc_method=DRY_COMBUSTION, latitude=BLODGETT[0], longitude=BLODGETT[1],
            source_row=f"C and N stocks:{i + 2}",
            notes=(f"{loc}; sheet 'C and N stocks', column C (%), elemental analyzer run '{r.Name}'; depth from sample "
                   "name; date from sample names '131030_Pit ...' (YYMMDD); initial site characterization pit "
                   "(before warming treatment)")))

    src = "TrtCoreData_CN_MB.csv"
    d = strip_bom(read_csv(doi, src))
    d["source_row"] = (d.index + 2).astype(str)
    e = d[(d["Treatment"] == "Control") & (d["Depth"] != "Litter") & ~is_missing(d["Extractable_NPOC.mg.gdrysoil"])]
    doc = pd.DataFrame({
        "doi": doi, "source_file": src, "id": e["Plot"] + ":" + e["Treatment"] + ":" + e["UID"].replace("", "NA"),
        "id_type": "Plot:Treatment:UID", "depth": e["Depth"].replace("20-Oct", "10-20"),
        "date": pd.to_datetime(e["Date"], format="%Y%m%d").dt.strftime("%Y-%m-%d"),
        "value": [fmt_tc(v * 1000) for v in num(e["Extractable_NPOC.mg.gdrysoil"])], "method": SALT_EXTRACTION,
        "DOC_unit": "mg C kg-1 dry soil", "DOC_medium": "soil extract, unfumigated (extractant not named)",
        "latitude": BLODGETT[0], "longitude": BLODGETT[1], "source_row": e["source_row"],
        "notes": (f"{loc}; Extractable_NPOC (mg C g-1 dry soil) x1000 = mg C kg-1; unfumigated extract of the "
                  "chloroform-fumigation microbial biomass method; extractant not named in the file; control plot of the "
                  "whole-soil warming experiment (heated plots and litter rows excluded)"),
    })
    d = d[(d["Treatment"] == "Control") & (d["Depth"] != "Litter") & ~is_missing(d["%C"])]
    for r in d.to_dict("records"):
        depth = "10-20" if r["Depth"] == "20-Oct" else r["Depth"]  # Excel turned "10-20" into "20-Oct"
        flag = f"; source flag: '{r['Possible sample issues?']}'" if r["Possible sample issues?"] else ""
        rows.append(dict(
            doi=doi, source_file=src, id=f"{r['Plot']}:{r['Treatment']}:{r['UID'] or 'NA'}", id_type="Plot:Treatment:UID",
            depth=depth, date=pd.to_datetime(r["Date"], format="%Y%m%d").strftime("%Y-%m-%d"), TC=r["%C"],
            tc_method=DRY_COMBUSTION, latitude=BLODGETT[0], longitude=BLODGETT[1], source_row=r["source_row"],
            notes=(f"{loc}; %C by elemental analyzer-IRMS ({r['Instrument']}); control plot of the whole-soil warming "
                   "experiment (heated plots and litter rows excluded)"
                   + ("; depth 10-20 written as '20-Oct' in source (Excel date conversion)" if r["Depth"] == "20-Oct" else "")
                   + flag)))
    # Several control cores per plot, depth and date share Plot:Treatment (UID mostly blank): source_row keys them.
    return {"TC": assemble(pd.DataFrame(rows), "TC", extra=["source_row"]),
            "DOC": assemble(doc, "DOC", extra=["source_row"])}


def c_2564914() -> pd.DataFrame:
    """Harmonize total carbon of doi:10.15485/2564914.

    Package: Calcium is associated with specific soil organic carbon decomposition products at Blodgett Forest
    Research Center, Georgetown, California as analysed with scanning transmission X-ray microscopy carbon near-edge
    X-ray absorption fine structure spectroscopy.

    Source files: Bulk_Soil_Chemistry.csv.

    Location: package description ('The samples were collected from here: 38.912013, -120.661469'; site-level;
    package spatialCoverage lists a different point, 38.8862914, -120.6477055).

    Methods: dry_combustion.

    Notes:
        - Treatment is written on the first row only.

    Returns:
        The total carbon table in the harmonized layout (common.assemble).

    Examples:
        >>> len(c_2564914())  # doctest: +SKIP
        29
    """
    doi = "doi:10.15485/2564914"
    src = "Bulk_Soil_Chemistry.csv"
    x = read_csv(doi, src, header=None, skiprows=2).iloc[:, [0, 1, 2, 3]]
    x.columns = ["Treatment", "Profile", "Depth", "C"]
    x["Treatment"] = x["Treatment"].replace("", None).ffill()  # treatment is written on the first row only
    x = x[~x["Treatment"].str.startswith("Heated") & ~is_missing(x["C"])]  # heated plots excluded
    note = ("lat/long source: doi:10.15485/2564914 package description ('The samples were collected from here: "
            "38.912013, -120.661469'; site-level; package spatialCoverage lists a different point, 38.8862914, "
            "-120.6477055); total C by Vario Micro Cube elemental analyser + Isoprime 100 IRMS, UC Davis Stable "
            "Isotope Facility (package methods); C (%) reported to one decimal; bulk characterisation on a separate "
            "core adjacent to the STXM soil core; cores sampled May 2021 (no day given); control plot (heated +4 C "
            "plots excluded); profile {p} presumably = paired plot {p}")
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": "Control:" + x["Profile"], "id_type": "Treatment:Profile",
        "depth": x["Depth"], "date": "2021-05", "TC": x["C"], "tc_method": DRY_COMBUSTION,
        "latitude": 38.912013, "longitude": -120.661469, "notes": x["Profile"].map(lambda p: note.format(p=p)),
    })
    return assemble(out, "TC")


def _compass(name: str) -> pd.DataFrame:
    """Harmonize one chemistry variable of the COMPASS-FME synoptic sites (doi:10.15485/2583150).

    Rows of chemistry_combined_all_horizons.csv with the given `name` are placed at the zone (plot) point of their site
    and transect, taken from the package spatialCoverage descriptions; O and A horizons are surface samples (depth 'O'
    and 'M'), B horizons subsurface with no depth reported; the month comes from sample_label.

    Args:
        name: The analyte in the source's name column: 'TC_perc' (total carbon) or 'npoc_ug_g' (water-extractable
            organic carbon, ug C g-1 = mg C kg-1).

    Returns:
        The harmonized table (TC column; the caller relabels it for WEOC).

    Examples:
        >>> len(_compass("TC_perc"))  # doctest: +SKIP
        236
    """
    doi = "doi:10.15485/2583150"
    src = "chemistry_combined_all_horizons.csv"
    a = read_csv(doi, src)
    d = a[(a["name"] == name) & ~is_missing(a["value"])].copy()
    # Zone (plot) coordinates written in the package spatialCoverage site descriptions (as in the soil pH file).
    zones = {
        ("CRC", "upland"): (41.6153, -83.2297), ("CRC", "transition"): (41.6219, -83.2381), ("CRC", "wetland"): (41.6219, -83.2389),
        ("PTR", "upland"): (41.5015, -83.0461), ("PTR", "transition"): (41.5020, -83.0456), ("PTR", "wetland"): (41.5016, -83.0444),
        ("OWC", "upland"): (41.3763, -82.5070), ("OWC", "transition"): (41.3758, -82.5063), ("OWC", "wte"): (41.3760, -82.5071),
        ("OWC", "wetland"): (41.3761, -82.5078),
        ("GCW", "upland"): (38.8741, -76.5522), ("GCW", "transition"): (38.8745, -76.5515), ("GCW", "wetland"): (38.8750, -76.5500),
        ("MSM", "upland"): (38.4315, -76.2267), ("MSM", "transition"): (38.4310, -76.2277), ("MSM", "wetland"): (38.4308, -76.2286),
        ("GWI", "upland"): (37.2192, -76.4087), ("GWI", "transition"): (37.2194, -76.4092), ("GWI", "wetland"): (37.2189, -76.4101),
    }
    names = {"CRC": "Crane Creek", "PTR": "Portage River", "OWC": "Old Woman Creek", "GCW": "GCReW",
             "MSM": "Moneystump Marsh", "GWI": "Goodwin Islands"}
    zcode = {"upland": "UP", "transition": "TR", "wetland": "W", "wte": "WTE"}
    month = {"Dec2021": "2021-12", "May22": "2022-05", "Aug22": "2022-08"}
    d["m"] = d["sample_label"].str.extract(r"COMPASS_(\w+?)_")[0]
    notes = []
    for s, t, h, m, tn in zip(d["site"], d["transect"], d["horizon"], d["m"], d["tree_number"]):
        hz = f"{h} horizon (organic), " if h == "O" else f"{h} horizon (mineral), "
        hz += "surface sample, top 5-10 cm" if h in ("O", "A") else "subsurface B horizon, depth not reported"
        notes.append(f"lat/long source: doi:10.15485/2583150 package metadata (spatialCoverage description, {names[s]} "
                     f"{zcode[t]} plot, zone-level; 8-9 samples per zone spread over 200-1000 m2 share one point); "
                     + ("TC_perc: total C by catalytic combustion, Elementar VarioMax Cube, freeze-dried samples (package "
                        "methods); " if name == "TC_perc" else
                        "npoc_ug_g: water-extractable organic C measured as NPOC (Shimadzu TOC-L), ug C g-1 dry soil "
                        "(= mg C kg-1), per data dictionary and package methods; ")
                     + f"{hz}; sampled {month[m]} (month from sample_label); COMPASS-FME synoptic site {s}, "
                     f"{t} zone, sampling point (tree_number) {tn}")
    keys = ["sample_label", "site", "transect", "tree_number", "horizon"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": d["horizon"].map({"O": "O", "A": "M", "B": "M"}), "date": d["m"].map(month), "TC": d["value"],
        "tc_method": DRY_COMBUSTION,
        "latitude": [zones[(s, t)][0] for s, t in zip(d["site"], d["transect"])],
        "longitude": [zones[(s, t)][1] for s, t in zip(d["site"], d["transect"])], "notes": notes,
    })
    return assemble(out, "TC")


def c_2583150() -> Tables:
    """Harmonize total carbon, water-extractable organic carbon of doi:10.15485/2583150.

    Package: COMPASS-FME Synoptic Site Characterization.

    Location: doi:10.15485/2583150 package metadata (spatialCoverage description, ... plot, zone-level; 8-9 samples
    per zone spread over 200-1000 m2 share one point).

    Methods: TC dry_combustion; WEOC water_extraction.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), WEOC (water-extractable organic
        carbon).

    Examples:
        >>> {k: len(t) for k, t in c_2583150().items()}  # doctest: +SKIP
        {'TC': 236, 'WEOC': 239}
    """
    tc = _compass("TC_perc")
    tcv = variable("TC")  # _compass returns an assembled TC table (long-key column names)
    w = _compass("npoc_ug_g").rename(columns={tcv.value_column: "value", tcv.method_column: "method"})
    w["method"] = WATER_EXTRACTION
    return {"TC": tc, "WEOC": assemble(w, "WEOC")}


def c_3024076() -> Tables:
    """Harmonize total carbon, dissolved organic carbon of doi:10.15485/3024076.

    Package: Soil Characterizations of Five Urban Sites in Knoxville, Tennessee. 2024-2025.

    Source files: Soil_Carbon_and_Nitrogen.csv, Soil_Dissolved_Organic_Carbon_and_Nitrogen.csv.

    Location: package metadata (spatialCoverage point for ...).

    Methods: TC dry_combustion; DOC salt_extraction.

    Notes:
        - Sample IDs repeat within a date (repeat analyses)

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), DOC (dissolved organic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_3024076().items()}  # doctest: +SKIP
        {'TC': 281, 'DOC': 230}
    """
    doi = "doi:10.15485/3024076"
    src = "Soil_Carbon_and_Nitrogen.csv"
    d = strip_bom(read_csv(doi, src))
    d["Sample ID"] = d["Sample ID"].str.strip()
    d["source_row"] = (d.index + 2).astype(str)  # Sample IDs repeat within a date (repeat analyses)
    parks = {"SEEED": (35.971, -83.903, "SEEED"), "Victor Ashe": (35.9825, -83.996, "Victor Ashe Park (VAP)"),
             "West Hills": (35.9316, -84.044, "West Hills Park (WHP)"),
             "Cumberland Estates": (35.983, -84.007, "Cumberland Estates Park (CEP)"),
             "West View": (35.9665, -83.961, "West View Park (WVP)")}
    keys = ["Location", "Sample ID"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": "0-15", "date": d["Sample Date"].str.replace("_", "-"), "TC": d["%Carbon"], "tc_method": DRY_COMBUSTION,
        "latitude": d["Location"].map(lambda s: parks[s][0]), "longitude": d["Location"].map(lambda s: parks[s][1]),
        "notes": [(f"lat/long source: doi:10.15485/3024076 package metadata (spatialCoverage point for {parks[s][2]}, "
                   "site-level; cores taken within 3 m of the site's soil monitoring station); total C of ground soil "
                   "by Elementar UNICUBE Trace combustion analyzer (package methods); 0-15 cm, 2-inch hammer corer; "
                   "urban park soil, Knoxville TN") for s in d["Location"]],
        "source_row": d["source_row"],
    })
    src2 = "Soil_Dissolved_Organic_Carbon_and_Nitrogen.csv"
    e = strip_bom(read_csv(doi, src2))
    e["source_row"] = (e.index + 2).astype(str)
    col = "Dissolved Organic Carbon Unfumigated (mg-C/g-soil)"
    e = e[~is_missing(e[col])]
    doc = pd.DataFrame({
        "doi": doi, "source_file": src2, "id": e["Location"] + ":" + e["Soil ID"].str.strip(), "id_type": "Location:Soil ID",
        "depth": "0-15", "date": e["Sample date"], "value": [fmt_tc(v * 1000) for v in num(e[col])],
        "method": SALT_EXTRACTION, "DOC_unit": "mg C kg-1 dry soil", "DOC_medium": "soil extract, unfumigated",
        "latitude": e["Location"].map(lambda s: parks[s][0]), "longitude": e["Location"].map(lambda s: parks[s][1]),
        "source_row": e["source_row"],
        "notes": [(f"lat/long source: doi:10.15485/3024076 package metadata (spatialCoverage point for {parks[s][2]}); "
                   "Dissolved Organic Carbon Unfumigated (mg C g-1 soil) x1000 = mg C kg-1; unfumigated extract of the "
                   "chloroform-fumigation method, NPOC by Elementar Vario TOC Cube (package methods); 0-15 cm core; urban "
                   "park soil, Knoxville TN") for s in e["Location"]],
    })
    return {"TC": assemble(out, "TC", extra=["source_row"]), "DOC": assemble(doc, "DOC", extra=["source_row"])}


def c_2530530() -> Tables:
    """Harmonize total carbon, dissolved organic carbon of doi:10.25581/ornlsfa.034/2530530.

    Package: Quarterly Soil Core and Root Analyses from the Missouri Ozarks AmeriFlux (MOFLUX) Site, Ashland,
    Missouri, 2017-2023.

    Source files: MOFLUX_quarterly_soil_cores_2017_2023.csv.

    Location: package metadata (spatialCoverage MOFLUX site point; cores taken near plot 1 of the southeast
    transect; no per-core coordinates); package metadata (spatialCoverage MOFLUX site point).

    Methods: TC dry_combustion; DOC salt_extraction.

    Notes:
        - Three analytical replicates per core are consecutive rows without a replicate column (as for pH).

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), DOC (dissolved organic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_2530530().items()}  # doctest: +SKIP
        {'TC': 471, 'DOC': 443}
    """
    doi = "doi:10.25581/ornlsfa.034/2530530"
    src = "MOFLUX_quarterly_soil_cores_2017_2023.csv"
    d = strip_bom(read_csv(doi, src))
    # Three analytical replicates per core are consecutive rows without a replicate column (as for pH).
    d["rep"] = (d.groupby("Sample_Name").cumcount() + 1).astype(str)
    note = ("lat/long source: doi:10.25581/ornlsfa.034/2530530 package metadata (spatialCoverage MOFLUX site point; cores "
            "taken near plot 1 of the southeast transect; no per-core coordinates); total C of ground soil by Leco "
            "Tru-Spec CN or Elementar UNICUBE Trace combustion analyzer (package methods; which instrument per date not "
            "given); 0-15 cm, 2-inch hammer corer, 8 cores per sampling date; three rows per core without a replicate "
            "column (number assigned by row order); Missouri Ozarks AmeriFlux (US-MOz)")
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Sample_Name"] + ":" + d["rep"],
        "id_type": "Sample_Name:analytical_replicate (row order within Sample_Name)", "depth": "0-15",
        "date": d["Sample_Date"], "TC": d["Total_C"], "tc_method": DRY_COMBUSTION, "latitude": 38.7441,
        "longitude": -92.2, "IGSN": d["IGSN"], "notes": note,
    })
    base = out.drop(columns=["TC", "tc_method", "notes"])
    doc = emit(base, "DOC", [fmt_tc(v * 1000) for v in num(d["DOC_unfumigated"])], SALT_EXTRACTION,
               ("lat/long source: doi:10.25581/ornlsfa.034/2530530 package metadata (spatialCoverage MOFLUX site point); "
                "DOC_unfumigated (mg C g-1 dry soil) x1000 = mg C kg-1; unfumigated extract (7.5 g fresh soil, 35 mL) of "
                "the chloroform-fumigation method, NPOC by Shimadzu TOC-L (2017-2022) or Elementar Vario TOC Cube (2023), "
                "package methods; extractant not named in the data dictionary; 0-15 cm core; three rows per core numbered "
                "by row order"),
               DOC_unit="mg C kg-1 dry soil", DOC_medium="soil extract, unfumigated")
    return {"TC": assemble(out, "TC"), "DOC": doc}


def c_1618325() -> Tables:
    """Harmonize total carbon, loss on ignition of doi:10.5440/1618325.

    Package: Iron and Phosphorus Geochemistry in High-Centered and Low-Centered Polygon Soils from the Barrow
    Environmental Observatory, Utqiagvik, Alaska, 2015.

    Source files: Herndon_BEO_SoilFe_TableS1_20200513.csv.

    Location: NGEE_User_Guidance_Document_template_BEO_SoilFe_20200515.pdf (general location for Area A,
    low-centered polygon; exact core locations not recorded);
    NGEE_User_Guidance_Document_template_BEO_SoilFe_20200515.pdf (general location for Area B, high-centered
    polygon; exact core locations not recorded); user guide (general location for Area A, low-centered polygon);
    user guide (general location for Area B, high-centered polygon).

    Methods: TC unknown; LOI loss_on_ignition.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), LOI (loss on ignition).

    Examples:
        >>> {k: len(t) for k, t in c_1618325().items()}  # doctest: +SKIP
        {'TC': 27, 'LOI': 27}
    """
    doi = "doi:10.5440/1618325"
    src = "Herndon_BEO_SoilFe_TableS1_20200513.csv"
    d = strip_bom(read_csv(doi, src)).iloc[1:]  # second line holds units
    d = d[~is_missing(d["Carbon"]) & ~is_missing(d["Sample_Name"])]
    poly = {"Low-centered": ("Area A, low-centered polygon", 71.2815, -156.61012),
            "High-centered": ("Area B, high-centered polygon", 71.27933, -156.60475)}
    keys = ["Sample_Name", "Polygon", "Feature", "Horizon"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": [depth_range(a, b) for a, b in zip(d["Upper_depth_cm"], d["Lower_depth_cm"])], "date": "2015-10",
        "TC": d["Carbon"], "tc_method": UNKNOWN,
        "latitude": d["Polygon"].map(lambda p: poly[p][1]), "longitude": d["Polygon"].map(lambda p: poly[p][2]),
        "IGSN": d["Sample_IGSN"],
        "notes": [("lat/long source: doi:10.5440/1618325:NGEE_User_Guidance_Document_template_BEO_SoilFe_20200515.pdf "
                   f"(general location for {poly[p][0]}; exact core locations not recorded); Carbon in weight % (units "
                   "row), bulk horizon C concentration; instrument not stated in package metadata; bulk "
                   f"{h.lower()} horizon of core {c}; sampled early October 2015")
                  for p, h, c in zip(d["Polygon"], d["Horizon"], d["Core_IGSN"])],
    })
    base = out.drop(columns=["TC", "tc_method", "notes"])
    loi = emit(base, "LOI", d["LOI"], LOI_METHOD,
               [(f"lat/long source: doi:10.5440/1618325 user guide (general location for {poly[p][0]}); LOI in weight % "
                 f"(units row); ignition temperature not stated in the data file; bulk {h.lower()} horizon; sampled early "
                 "October 2015") for p, h in zip(d["Polygon"], d["Horizon"])])
    return {"TC": assemble(out, "TC"), "LOI": loi}


def c_1866269() -> pd.DataFrame:
    """Harmonize total carbon of doi:10.15485/1866269.

    Package: Chemistry data from soils and soil incubation experiments from the whole-soil warming experiment at
    Blodgett Forest, CA, 2018, from: “Metabolic capabilities mute positive response to direct and indirect impacts
    of warming throughout the soil profile”.

    Source files: soilChemistry.csv.

    Location: package metadata (centre of the spatialCoverage box 38.91213-38.912527 N, 120.660948-120.661758 W;
    plot-level coordinates not given).

    Methods: dry_combustion.

    Returns:
        The total carbon table in the harmonized layout (common.assemble).

    Examples:
        >>> len(c_1866269())  # doctest: +SKIP
        15
    """
    doi = "doi:10.15485/1866269"
    src = "soilChemistry.csv"
    d = read_csv(doi, src).iloc[1:]  # first row holds units
    d = d[(d["fieldTreatment"] == "Control") & ~is_missing(d["totalC"])]
    fix = {"00-10": "0-10", "30-Oct": "10-30"}  # Excel turned "10-30" into "30-Oct"
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["sampleID"] + ":" + d["plot"] + ":" + d["fieldTreatment"],
        "id_type": "sampleID:plot:fieldTreatment", "depth": d["soilDepth"].map(lambda v: fix.get(v, v)),
        "date": "2018-06-04", "TC": d["totalC"], "tc_method": DRY_COMBUSTION,
        "latitude": 38.912329, "longitude": -120.661353, "IGSN": d["IGSN"],
        "notes": [("lat/long source: doi:10.15485/1866269 package metadata (centre of the spatialCoverage box "
                   "38.91213-38.912527 N, 120.660948-120.661758 W; plot-level coordinates not given); total C by "
                   "Costech ECS 4010 CHNSO analyzer, direct combustion, oven-dry ground soil (package methods); one 5-cm "
                   "AMS core per plot, June 2018 (date from sampleID 'BWE20180604...'); control plot (heated plots excluded)"
                   + ("; depth 10-30 written as '30-Oct' in source (Excel date conversion)" if v == "30-Oct" else ""))
                  for v in d["soilDepth"]],
    })
    return assemble(out, "TC")


def c_1797785() -> pd.DataFrame:
    """Harmonize total carbon of doi:10.15485/1797785.

    Package: Data from : "Warming promotes loss of subsoil carbon through accelerated degradation of plant-derived
    organic matter". Blodgett warming experiment.

    Source files: Blodgett_warming_Data.csv.

    Location: package metadata (spatialCoverage Blodgett point; no plot coordinates).

    Methods: dry_combustion.

    Notes:
        - Mineral soil rows repeat values already harmonized from doi:10.15485/2480291 (2018 UZH analyses); only the O
          horizons are new. Oi (fresh litter) and warmed plots are excluded.

    Returns:
        The total carbon table in the harmonized layout (common.assemble).

    Examples:
        >>> len(c_1797785())  # doctest: +SKIP
        4
    """
    doi = "doi:10.15485/1797785"
    src = "Blodgett_warming_Data.csv"
    d = read_csv(doi, src)
    # Mineral soil rows repeat values already harmonized from doi:10.15485/2480291 (2018 UZH analyses);
    # only the O horizons are new. Oi (fresh litter) and warmed plots are excluded.
    d = d[(d["Type of Material"] == "Organic horizon") & (d["Treatment"] == "Control")
          & d["Sampling Depth (cm)"].isin(["Oe", "Oa"]) & ~is_missing(d["C_percent"])]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Lab-ID"] + ":" + d["Plot"] + ":" + d["Sampling Depth (cm)"],
        "id_type": "Lab-ID:Plot:horizon", "depth": "O", "date": "2018-04", "TC": d["C_percent"],
        "tc_method": DRY_COMBUSTION, "latitude": 38.912, "longitude": -120.661,
        "notes": [("lat/long source: doi:10.15485/1797785 package metadata (spatialCoverage Blodgett point; no plot "
                   f"coordinates); C_percent of {h} horizon material by elemental analyzer (package methods, Zurich); "
                   "control plot, one core per plot, April 2018; Oi litter and warmed plots excluded; mineral soil rows "
                   "of this package are the same analyses as doi:10.15485/2480291 TrtCoreData_CN_MB.csv (2018-04-04) and "
                   "are taken from there") for h in d["Sampling Depth (cm)"]],
    })
    return assemble(out, "TC")


def c_1892050() -> pd.DataFrame:
    """Harmonize total carbon of doi:10.15485/1892050.

    Package: Soil and soil fraction radiocarbon, C and N from the Enriched Background Isotope Study, Oak Ridge
    National Laboratory, Tennessee, USA.

    Source files: RawData_CN_14C_compiled_cleaned.csv.

    Location: package metadata (spatialCoverage point for Walker Branch at Oak Ridge Reservation; site-level).

    Methods: dry_combustion.

    Returns:
        The total carbon table in the harmonized layout (common.assemble).

    Examples:
        >>> len(c_1892050())  # doctest: +SKIP
        40
    """
    doi = "doi:10.15485/1892050"
    src = "RawData_CN_14C_compiled_cleaned.csv"
    d = read_csv(doi, src, encoding="latin1")
    d = d[(d["Fraction"] == "BULK") & (d["Treatment"] == "CONTROL") & ~is_missing(d["C (%)"])]
    sites = {"WB": (35.960784, -84.275314, "Walker Branch"), "TVA": (35.910154, -84.375661, "TVA")}
    layer = {"7.5": "0-15", "22.5": "15-30", "45": "30-60", "75": "60-90"}
    keys = ["Sample", "Site", "Treatment", "plot", "Litter"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": d["AveDepthcm"].map(layer), "date": d["Year"], "TC": d["C (%)"], "tc_method": DRY_COMBUSTION,
        "latitude": d["Site"].map(lambda s: sites[s][0]), "longitude": d["Site"].map(lambda s: sites[s][1]),
        "notes": [(f"lat/long source: doi:10.15485/1892050 package metadata (spatialCoverage point for {sites[s][2]} at "
                   "Oak Ridge Reservation; site-level); C (%) of bulk soil by Costech elemental analyzer, combustion "
                   f"(package methods); depth from AveDepthcm {a} cm (EBIS layers 0-15/15-30/30-60/60-90); "
                   f"litter-manipulation CONTROL plot ({l.lower()} 14C litter label); density fractions and LITTER/ROOTS "
                   "manipulation plots excluded; sampling year only; overlaps partly with "
                   "doi:10.25581/ORNLSFA.020/1638590 (EBIS soils, same sites)")
                  for s, a, l in zip(d["Site"], d["AveDepthcm"], d["Litter"])],
    })
    return assemble(out, "TC")


WETLAND_SITES = {  # doi:10.15485/1773008 and doi:10.15485/1908426 spatialCoverage
    "Marsh 1": (41.70546944, -87.99862222, "Argonne National Laboratory marsh wetland site 401"),
    "Marsh 2": (41.70188333, -87.99435, "Argonne National Laboratory marsh wetland site 405"),
    "Riparian 1": (33.3376, -81.7183, "Tims Branch watershed, Savannah River National Laboratory, losing stream site"),
    "Riparian 2": (33.3359, -81.7189, "Tims Branch watershed, Savannah River National Laboratory, gaining stream site"),
}


def _wetland(doi: str, src: str, table: pd.DataFrame, col: int, date: str, depth_note: str) -> pd.DataFrame:
    """Harmonize total carbon of an Argonne marsh / Tims Branch riparian wetland table (doi:10.15485/1773008, 1908426).

    Rows are placed at the spatialCoverage point of their site (WETLAND_SITES); stream sediment rows (East Fork Poplar
    Creek) are skipped as not soil. Values are means of triplicate analyses, 0-5 cm.

    Args:
        doi: The package DOI.
        src: The ESS-DIVE file name of the table.
        table: The table, site name in the first column.
        col: Position of the total carbon column.
        date: Sampling date for every row.
        depth_note: Depth description for notes.

    Returns:
        The total carbon table in the harmonized layout (common.assemble).
    """
    rows = []
    for r in table.itertuples(index=False):
        site = str(r[0]).strip()
        if site not in WETLAND_SITES:  # stream sediment rows (East Fork Poplar Creek) are not soil
            continue
        lat, lon, desc = WETLAND_SITES[site]
        rows.append(dict(
            doi=doi, source_file=src, id=site, id_type="Sample", depth="0-5", date=date, TC=r[col],
            tc_method=DRY_COMBUSTION, latitude=lat, longitude=lon,
            notes=(f"lat/long source: {doi} package metadata (spatialCoverage point for {site}, {desc}); total C by "
                   "combustion, Elementar vario MACRO cube CHNS analyzer, dried soil (package methods); mean of "
                   f"triplicate analyses (error column in source); {depth_note}")))
    return assemble(pd.DataFrame(rows), "TC")


def c_1773008() -> pd.DataFrame:
    """Harmonize total carbon of doi:10.15485/1773008.

    Package: Soil and Water Chemistry and Trace Metal Extractability and Speciation in Wetland Soils from Illinois
    and South Carolina and Stream Sediments from Tennessee.

    Source files: Figure2_MajorElementConc.csv.

    Location: package metadata (spatialCoverage point for ...).

    Methods: dry_combustion.

    Returns:
        The total carbon table in the harmonized layout (common.assemble).

    Examples:
        >>> len(c_1773008())  # doctest: +SKIP
        4
    """
    doi = "doi:10.15485/1773008"
    src = "Figure2_MajorElementConc.csv"
    t = read_csv(doi, src, header=None, skiprows=4)  # title, blank, "surface layer", header
    return _wetland(doi, src, t, 1, "2018-10/2019-03",
                    "'surface layer' sample, taken as 0-5 cm (surface layer defined as 0-5 cm in companion package "
                    "doi:10.15485/1908426); date from package temporal coverage (marsh cores fall 2018, riparian "
                    "February 2019); stream sediment rows excluded")


def c_1908426() -> pd.DataFrame:
    """Harmonize total carbon of doi:10.15485/1908426.

    Package: Wetland Soil Characterization and Methane Production Impacted by Nickel Addition, Argonne and Tims
    Branch Wetlands, September and October 2020.

    Source files: Soil_CNSFe_Content.csv.

    Location: package metadata (spatialCoverage point for ...).

    Methods: dry_combustion.

    Returns:
        The total carbon table in the harmonized layout (common.assemble).

    Examples:
        >>> len(c_1908426())  # doctest: +SKIP
        4
    """
    doi = "doi:10.15485/1908426"
    src = "Soil_CNSFe_Content.csv"
    t = read_csv(doi, src, header=None, skiprows=3)  # title, blank, header
    return _wetland(doi, src, t, 3, "2020-09/2020-10",
                    "surface layer (0-5 cm) per package methods; date from package temporal coverage (September-October "
                    "2020)")


def c_spruce005() -> Tables:
    """Harmonize total carbon, loss on ignition of doi:10.3334/CDIAC/SPRUCE.005.

    Package: SPRUCE Peat Physical and Chemical Characteristics from Experimental Plot Cores, 2012.

    Source files: Peat_Characteristics_T0_20180425.csv.

    Location: package metadata (centre of the SPRUCE S1-Bog experiment site box; plot coordinates not given);
    package metadata (centre of the S1-Bog site box).

    Methods: TC unknown; LOI 100_minus_ash.

    Notes:
        - Core number: increments restart at 1 for each of the replicate cores per plot and topography.
        - Core numbers inferred from row order are not always unique: the source's Order number keys the rows.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), LOI (loss on ignition).

    Examples:
        >>> {k: len(t) for k, t in c_spruce005().items()}  # doctest: +SKIP
        {'TC': 567, 'LOI': 517}
    """
    doi = "doi:10.3334/CDIAC/SPRUCE.005"
    src = "Peat_Characteristics_T0_20180425.csv"
    d = read_csv(doi, src).iloc[1:]  # first row holds units
    # Core number: increments restart at 1 for each of the replicate cores per plot and topography.
    d["core"] = (d["Depth_increment"] == "1").groupby([d["Plot"], d["Topography"]]).cumsum().astype(str)
    top = num(d["Top_core_depth"])
    surface = top.groupby([d["Plot"], d["Topography"], d["core"]]).transform("max")
    d["dtop"], d["dbot"] = surface - top, surface - num(d["Bottom_core_depth"])
    d["surface"] = surface
    d = d[~is_missing(d["Carbon"])]
    topo = {"Hu": "hummock", "Ho": "hollow"}
    keys = ["Plot", "Topography", "core", "Depth_increment"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1),
        "id_type": "Plot:Topography:core (order in source):Depth_increment",
        "depth": [depth_range(a, b) for a, b in zip(d["dtop"], d["dbot"])], "date": d["Date_sampled"],
        "TC": d["Carbon"], "tc_method": UNKNOWN, "latitude": 47.50563, "longitude": -93.453275, "Order": d["Order"],
        "notes": [("lat/long source: doi:10.3334/CDIAC/SPRUCE.005 package metadata (centre of the SPRUCE S1-Bog "
                   "experiment site box; plot coordinates not given); Carbon (%) of peat, instrument not stated in the "
                   f"data file; {topo.get(t, t)} core; depth converted to cm below the core surface: source depths are "
                   f"relative to the hollow surface (positive above), source interval {a} to {b} cm, core surface at "
                   f"{s:g} cm; plot {p}, vegetation {v}; pre-treatment (before SPRUCE warming and CO2 treatments)")
                  for t, a, b, s, p, v in zip(d["Topography"], d["Top_core_depth"], d["Bottom_core_depth"],
                                              d["surface"], d["Plot"], d["Vegetation"])],
    })
    # Core numbers inferred from row order are not always unique: the source's Order number keys the rows.
    tc = assemble(out, "TC", extra=["Order"])
    a = read_csv(doi, src).iloc[1:]
    a["core"] = (a["Depth_increment"] == "1").groupby([a["Plot"], a["Topography"]]).cumsum().astype(str)
    top = num(a["Top_core_depth"])
    surface = top.groupby([a["Plot"], a["Topography"], a["core"]]).transform("max")
    a["dtop"], a["dbot"] = surface - top, surface - num(a["Bottom_core_depth"])
    a = a[~is_missing(a["Ash"])]
    loi = pd.DataFrame({
        "doi": doi, "source_file": src, "id": a[keys].agg(":".join, axis=1),
        "id_type": "Plot:Topography:core (order in source):Depth_increment",
        "depth": [depth_range(x, y) for x, y in zip(a["dtop"], a["dbot"])], "date": a["Date_sampled"],
        "value": [fmt_tc(100 - v) for v in num(a["Ash"])], "method": ASH_COMPLEMENT,
        "latitude": 47.50563, "longitude": -93.453275, "Order": a["Order"],
        "notes": [("lat/long source: doi:10.3334/CDIAC/SPRUCE.005 package metadata (centre of the S1-Bog site box); LOI = "
                   f"100 - Ash (%), source Ash {x}%; ignition temperature not stated in the data file; depth below the "
                   "core surface (source depths relative to the hollow surface); pre-treatment peat core") for x in a["Ash"]],
    })
    return {"TC": tc, "LOI": assemble(loi, "LOI", extra=["Order"])}


def c_2570819() -> Tables:
    """Harmonize total carbon, dissolved organic carbon of doi:10.15485/2570819.

    Package: Plant Characteristics, Porewater, Gas Flux, and Soil Biogeochemistry at Council Road Site Mile Marker
    71, Seward Peninsula, Alaska, 2023.

    Source files: SoilCores.csv, FieldPorewater.csv.

    Location: package metadata (single Council MM71 site point; plot coordinates not given); package metadata
    (single Council MM71 site point).

    Methods: TC dry_combustion; DOC porewater.

    Notes:
        - "0 to 10", once "0 to10"

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), DOC (dissolved organic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_2570819().items()}  # doctest: +SKIP
        {'TC': 85, 'DOC': 106}
    """
    doi = "doi:10.15485/2570819"
    src = "SoilCores.csv"
    d = read_csv(doi, src).iloc[1:]  # first row holds units
    d["source_row"] = (d.index + 2).astype(str)  # file line number (header = line 1)
    d = d[~is_missing(d["Soil_C"])]
    keys = ["Plot", "Subplot", "Location"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": d["Depth"].str.replace(r"\s*to\s*", "-", regex=True),  # "0 to 10", once "0 to10"
        "date": pd.to_datetime(d["Date"], format="%m/%d/%Y").dt.strftime("%Y-%m-%d"), "TC": d["Soil_C"],
        "tc_method": DRY_COMBUSTION, "latitude": 64.859722, "longitude": -163.699722, "source_row": d["source_row"],
        "notes": ("lat/long source: doi:10.15485/2570819 package metadata (single Council MM71 site point; plot "
                  "coordinates not given); Soil_C (%) by combustion, Elementar Unicube TRACE, soil dried at 70 C "
                  "(package methods); 10x10x10 cm soil blocks; column TC in this file is porewater total carbon (mM) "
                  "and is not used"),
    })
    rows = []
    for f, label in [("SoilCores.csv", "porewater of the soil-core blocks"), ("FieldPorewater.csv", "field porewater")]:
        e = read_csv(doi, f).iloc[1:]  # first row holds units
        e["source_row"] = (e.index + 2).astype(str)
        e = e[~is_missing(e["DOC"])]
        for r in e.to_dict("records"):
            rows.append(dict(
                doi=doi, source_file=f, id=f"{r['Plot']}:{r.get('Subplot', 'NA')}:{r['Location']}",
                id_type="Plot:Subplot:Location", depth=str(r["Depth"]).replace(" to ", "-").replace(" to", "-"),
                date=pd.to_datetime(r["Date"], format="%m/%d/%Y").strftime("%Y-%m-%d"),
                value=fmt_tc(float(r["DOC"]) * MMOL_C), method=POREWATER, DOC_unit="mg C L-1", DOC_medium=label,
                latitude=64.859722, longitude=-163.699722, source_row=f"{f}:{r['source_row']}",
                notes=(f"lat/long source: doi:10.15485/2570819 package metadata (single Council MM71 site point); DOC {r['DOC']} "
                       f"mM x 12.011 = mg C L-1 (data dictionary: 'Dissolved organic carbon; porewater'); {label}; "
                       "Shimadzu TOC analyzer (package methods)")))
    return {"TC": assemble(out, "TC", extra=["source_row"]),
            "DOC": assemble(pd.DataFrame(rows), "DOC", extra=["source_row"])}


# ----------------------------------------------------------------------------------------------------
# Packages added for the other carbon variables
# ----------------------------------------------------------------------------------------------------

COMPASS_ZONES = {  # zone (plot) points from the doi:10.15485/2583150 spatialCoverage descriptions (as for TC and pH)
    ("CRC", "UP"): (41.6153, -83.2297), ("CRC", "TR"): (41.6219, -83.2381), ("CRC", "W"): (41.6219, -83.2389),
    ("OWC", "UP"): (41.3763, -82.5070), ("OWC", "TR"): (41.3758, -82.5063), ("OWC", "W"): (41.3761, -82.5078),
    ("GCW", "UP"): (38.8741, -76.5522), ("GCW", "TR"): (38.8745, -76.5515), ("GCW", "W"): (38.8750, -76.5500),
    ("MSM", "UP"): (38.4315, -76.2267), ("MSM", "TR"): (38.4310, -76.2277), ("MSM", "W"): (38.4308, -76.2286),
}


def c_1631972() -> Tables:
    """Harmonize carbon variables of doi:10.15485/1631972.

    Package: Depth-resolved soil data from DOE-LM Riverton Wyoming site, April-September 2017.

    Source files: avgData.csv.

    Location: metadataFile.csv (Riverton installation pit 2, N 42.98864, W 108.40006; same point in package
    metadata).

    Methods: TC dry_combustion; SOC acid_treated_combustion; SIC TC_minus_TOC.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), SOC (soil organic carbon), SIC
        (soil inorganic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_1631972().items()}  # doctest: +SKIP
        {'TC': 83, 'SOC': 80, 'SIC': 80}
    """
    doi = "doi:10.15485/1631972"
    src = "avgData.csv"
    d = read_csv(doi, src)
    d["source_row"] = (d.index + 2).astype(str)
    base = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Loc_ID"] + ":" + d["Depth_int"], "id_type": "Loc_ID:Depth_int",
        "depth": d["Depth_int"], "date": pd.to_datetime(d["Date"], format="%m/%d/%y").dt.strftime("%Y-%m-%d"),
        "latitude": 42.98864, "longitude": -108.40006, "source_row": d["source_row"],
    })
    loc = ("lat/long source: doi:10.15485/1631972:metadataFile.csv (Riverton installation pit 2, N 42.98864, W 108.40006; "
           "same point in package metadata); ")
    tail = ("; DOE Legacy Management Riverton site (U/Mo/NO3 plume floodplain), installation pit 2 resampled on six "
            "dates in 2017")
    ea = "Carlo Erba NA1500 elemental analyzer on pulverized dry sediment (methodFile.csv)"
    k = ["source_row"]
    return {
        "TC": emit(base, "TC", d["Tot_C"], DRY_COMBUSTION, loc + f"Tot_C by {ea}" + tail, extra=k),
        "SOC": emit(base, "SOC", d["Tot_OrgC"], ACID_COMBUSTION,
                    loc + f"Tot_OrgC by {ea} after dropwise 1 M HCl until effervescence ceased (methodFile.csv)" + tail,
                    extra=k),
        "SIC": emit(base, "SIC", d["Tot_CO3-C"], TC_MINUS_TOC,
                    loc + "Tot_CO3-C = Tot_C - Tot_OrgC (metadataFile.csv: difference between Tot_C and Org_C)" + tail,
                    extra=k),
    }


def c_3003878() -> Tables:
    """Harmonize soil organic carbon of doi:10.15485/3003878.

    Package: Data for Stetten et al. (2025), "Biogeochemical controls on iron speciation and cycling across upland
    to shoreline gradients in freshwater and estuarine coastal soils (Lake Erie and Chesapeake Bay, United States)"

    Source files: solid_data.csv.

    Location: doi:10.15485/2583150 package metadata (COMPASS-FME ... zone point; this package lists site points
    only).

    Methods: SOC unknown.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): SOC (soil organic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_3003878().items()}  # doctest: +SKIP
        {'SOC': 81}
    """
    doi = "doi:10.15485/3003878"
    src = "solid_data.csv"
    d = read_csv(doi, src)
    d = d[~is_missing(d["TOC_pct"])]
    d["source_row"] = (d.index + 2).astype(str)
    zone = {"UP": "upland", "TR": "transition", "W": "wetland"}
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Site"] + ":" + d["Plot"] + ":" + d["Depth_cm"],
        "id_type": "Site:Plot:Depth_cm", "depth": d["Depth_cm"], "date": "2022-11/2023-03", "value": d["TOC_pct"],
        "method": UNKNOWN, "latitude": [COMPASS_ZONES[(a, b)][0] for a, b in zip(d["Site"], d["Plot"])],
        "longitude": [COMPASS_ZONES[(a, b)][1] for a, b in zip(d["Site"], d["Plot"])], "source_row": d["source_row"],
        "notes": [(f"lat/long source: doi:10.15485/2583150 package metadata (COMPASS-FME {s} {p} zone point; this package "
                   "lists site points only); TOC_pct = total organic C by dry combustion at 650 C on an elemental analyzer "
                   "(package methods); depth as reported (single depths are sample depths in cm); "
                   f"{zone[p]} zone; date from package temporal coverage") for s, p in zip(d["Site"], d["Plot"])],
    })
    return {"SOC": assemble(out, "SOC", extra=["source_row"])}


def c_2350835() -> Tables:
    """Harmonize soil organic carbon of doi:10.15485/2350835.

    Package: Association between soil organic carbon and calcium in acidic grassland soils from Point Reyes National
    Seashore, CA.

    Source files: Bulk_Data.csv.

    Location: package metadata (spatial coverage 'Core ...').

    Methods: SOC unknown.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): SOC (soil organic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_2350835().items()}  # doctest: +SKIP
        {'SOC': 24}
    """
    doi = "doi:10.15485/2350835"
    src = "Bulk_Data.csv"
    d = strip_bom(read_csv(doi, src)).iloc[1:]  # second line holds units
    d = d[~is_missing(d["SOC"])]
    cores = {"1": (37.970136, -122.732161), "2": (37.989346, -122.748204), "3": (38.062778, -122.814722)}
    core = d["Sample"].str.extract(r"Core (\d+)")[0]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Sample"], "id_type": "Sample", "depth": d["Depth"],
        "date": "2020-11/2022-11", "value": d["SOC"], "method": UNKNOWN,
        "latitude": core.map(lambda c: cores[c][0]), "longitude": core.map(lambda c: cores[c][1]),
        "notes": core.map(lambda c: (f"lat/long source: doi:10.15485/2350835 package metadata (spatial coverage 'Core {c}'); "
                                     "SOC (%), method not given in the data file (Rowley et al. 2023); acidic grassland soil "
                                     "core, Point Reyes National Seashore; date range from package temporal coverage")),
    })
    return {"SOC": assemble(out, "SOC")}


def c_2405147() -> Tables:
    """Harmonize soil organic carbon of doi:10.15485/2405147.

    Package: The importance of accounting for landscape position when investigating grasslands: A multidisciplinary
    characterisation of a Californian coastal grassland.

    Source files: SoilCores.xlsx.

    Location: package metadata (Point Reyes Experimental Field Site point; no per-core coordinates); SoilCores.xlsx
    (second table, core coordinates 37°58′13.6″ N, 122°43′55.7″ W converted); SoilCores.xlsx (second table, core
    coordinates 37°58′12.9″ N, 122°43′56″ W converted).

    Methods: SOC unknown.

    Notes:
        - Core 8 duplicates doi:10.15485/2350835 Core 1 (as for pH)

    Returns:
        {variable: table} in the harmonized layout (common.assemble): SOC (soil organic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_2405147().items()}  # doctest: +SKIP
        {'SOC': 68}
    """
    doi = "doi:10.15485/2405147"
    src = "SoilCores.xlsx"
    x = read_excel(doi, src, sheet_name="Soil Cores", header=None)
    rows = []
    t1 = x.iloc[1:48]
    t1 = t1[t1[0] != ""]
    for r in t1.itertuples(index=False):
        core, zone, depth, soc = r[0], r[1], r[3], r[7]
        rows.append(dict(
            doi=doi, source_file=src, id=f"Core {core}:Zone {zone}", id_type="New core:Zone", depth=depth,
            date="2020-10/2020-12", value=soc, method=UNKNOWN, latitude=37.9711, longitude=-122.7301,
            notes=("lat/long source: doi:10.15485/2405147 package metadata (Point Reyes Experimental Field Site point; "
                   "no per-core coordinates); SOC (%) from the first table of sheet 'Soil Cores', method not given in the "
                   f"data file (Rowley et al. 2024); hillslope core {core} in landscape zone {zone}; sampled "
                   "October-December 2020")))
    t2 = x.iloc[49:]
    t2 = t2[t2[2].str.match(r"Core [67]\.")]  # core 8 duplicates doi:10.15485/2350835 Core 1 (as for pH)
    for core, g in t2.groupby(t2[2].str.extract(r"Core (\d+)\.")[0], sort=True):
        coord = str(g.iloc[0, 0])
        lat_txt, lon_txt = coord.split(",")
        lat, lon = round(dms_to_decimal(lat_txt), 6), round(dms_to_decimal(lon_txt), 6)
        top = 0.0
        for r in g.itertuples(index=False):
            mid = float(r[8])
            bottom = 2 * mid - top
            rows.append(dict(
                doi=doi, source_file=src, id=r[2], id_type="Sample", depth=depth_range(top, bottom),
                date="2020-11/2022-11", value=r[10], method=UNKNOWN, latitude=lat, longitude=lon,
                notes=(f"lat/long source: doi:10.15485/2405147:SoilCores.xlsx (second table, core coordinates {coord} "
                       "converted); SOC (%) from the second table, method not given in the data file; depth interval "
                       f"reconstructed from mid-depths ({fmt_num(mid)} cm) assuming contiguous layers from 0 cm (as for pH); "
                       "core 8 excluded as duplicate of doi:10.15485/2350835 Core 1")))
            top = bottom
    return {"SOC": assemble(pd.DataFrame(rows), "SOC")}


def c_1618870() -> Tables:
    """Harmonize dissolved organic carbon of doi:10.15485/1618870.

    Package: Soil chemistry data across a catena in the Luquillo Experimental Forest, Puerto Rico.

    Source files: SoilData_ElVERDE_PR.csv.

    Location: package metadata (single El Verde point shared by ridge, slope and valley positions).

    Methods: DOC salt_extraction.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): DOC (dissolved organic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_1618870().items()}  # doctest: +SKIP
        {'DOC': 80}
    """
    doi = "doi:10.15485/1618870"
    src = "SoilData_ElVERDE_PR.csv"
    d = strip_bom(read_csv(doi, src))
    d["source_row"] = (d.index + 2).astype(str)
    d = d[~is_missing(d["DOC_mg_g"])]
    d["date"] = pd.to_datetime(d["Sampling_Date"].str.lstrip("B"), format="%B%d,%Y").dt.strftime("%Y-%m-%d")
    keys = ["Soil Site", "Topographic_locations", "Field_replicate", "Lab_replicate"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].apply(lambda r: ":".join(v.strip() for v in r), axis=1),
        "id_type": ":".join(keys), "depth": "0-10", "date": d["date"],
        "value": [fmt_tc(v * 1000) for v in num(d["DOC_mg_g"])], "method": SALT_EXTRACTION,
        "DOC_unit": "mg C kg-1 dry soil", "DOC_medium": "soil extract (extractant not stated)",
        "latitude": 18.32134, "longitude": -65.81948, "source_row": d["source_row"],
        "notes": ("lat/long source: doi:10.15485/1618870 package metadata (single El Verde point shared by ridge, slope and "
                  "valley positions); DOC_mg_g x1000 = mg C kg-1; extractant not stated in the data file; 0-10 cm; sampled "
                  "quarterly Apr 2017-May 2018; lab replicates kept as separate rows (as for pH)"),
    })
    return {"DOC": assemble(out, "DOC", extra=["source_row"])}


def c_1830417() -> Tables:
    """Harmonize dissolved organic carbon of doi:10.15485/1830417.

    Package: Kinetic and temperature sensitivity properties of soil exoenzymes through the soil profile down to
    one-meter depth at a temperate coniferous forest (Blodgett, CA)

    Source files: soilChemistry.csv.

    Location: package metadata (spatialCoverage Blodgett point).

    Methods: DOC salt_extraction.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): DOC (dissolved organic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_1830417().items()}  # doctest: +SKIP
        {'DOC': 27}
    """
    doi = "doi:10.15485/1830417"
    src = "soilChemistry.csv"
    d = read_csv(doi, src).iloc[1:]  # first row holds units
    d = d[~is_missing(d["DOC"])]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["sampleID"] + ":" + d["core"], "id_type": "sampleID:core",
        "depth": d["depth"].str.replace("00-10", "0-10"), "date": "2019-07-09", "value": d["DOC"],
        "method": SALT_EXTRACTION, "DOC_unit": "mg C kg-1 dry soil", "DOC_medium": "soil extract, unfumigated",
        "latitude": 38.912, "longitude": -120.66, "IGSN": d["IGSN"],
        "notes": ("lat/long source: doi:10.15485/1830417 package metadata (spatialCoverage Blodgett point); DOC (mg kg-1 dry "
                  "soil), unfumigated extract of the chloroform-fumigation microbial biomass method (package methods); "
                  "one of three 4.78 cm cores, 10 cm increments after removing the litter layer; date from sampleID "
                  "'BE20190709...'; Blodgett Forest mixed-conifer stand"),
    })
    return {"DOC": assemble(out, "DOC")}


def c_3030227() -> Tables:
    """Harmonize water-extractable organic carbon, soil organic matter of doi:10.15485/3030227.

    Package: EXCHANGE Campaign Degradation (ECD): Understanding Decomposition Dynamics Across Mid-Atlantic and Great
    Lakes Coastal Ecosystems.

    Source files: 10.15485_3030227_kit_coordinates.csv, ecd_soil_weom_L2.csv, ecd_soil_gwc_L2.csv.

    Location: package metadata (spatialCoverage ..., USA', kit-level; upland, transition and wetland share one
    point).

    Methods: WEOC water_extraction; SOM loss_on_ignition.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): WEOC (water-extractable organic carbon), SOM (soil
        organic matter).

    Examples:
        >>> {k: len(t) for k, t in c_3030227().items()}  # doctest: +SKIP
        {'WEOC': 102, 'SOM': 102}
    """
    from pathlib import Path
    doi = "doi:10.15485/3030227"
    ref = pd.read_csv(Path(__file__).parent.parent / "reference" / "10.15485_3030227_kit_coordinates.csv",
                      dtype=str)
    kits = {r.kit_id: (float(r.latitude), float(r.longitude), r.description) for r in cast("Iterable[Any]", ref.itertuples())}
    out = {}
    for var, src, col, method, what in [
            ("WEOC", "ecd_soil_weom_L2.csv", "weoc_ug_g", WATER_EXTRACTION,
             "weoc_ug_g: water-extractable organic C, ug C g-1 (= mg C kg-1) per data dictionary"),
            ("SOM", "ecd_soil_gwc_L2.csv", "som_percent", LOI_METHOD,
             "som_percent: soil organic matter (%) per data dictionary, by loss on ignition")]:
        d = read_csv(doi, src)
        d = d[(d["timepoint"] == "Time1") & ~is_missing(d[col])]
        keys = ["kit_id", "transect_location", "timepoint"]
        out[var] = assemble(pd.DataFrame({
            "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys), "depth": "",
            "date": "2025", "value": d[col], "method": method,
            "latitude": d["kit_id"].map(lambda k: kits[k][0]), "longitude": d["kit_id"].map(lambda k: kits[k][1]),
            "IGSN": d["igsn"],
            "notes": [(f"lat/long source: doi:10.15485/3030227 package metadata (spatialCoverage '{kits[k][2]}', kit-level; "
                       f"upland, transition and wetland share one point); {what}; surface soil grab, depth not reported; "
                       "Time1 (soil sampled at tea bag deployment, summer 2025) only, Time2 retrieval samples excluded (as "
                       f"for pH); {t} position on a coastal transect; EXCHANGE-D community sampling")
                      for k, t in zip(d["kit_id"], d["transect_location"])],
        }), var)
    return out


def c_2407118() -> Tables:
    """Harmonize soil organic matter of doi:10.15485/2407118.

    Package: Data for publication: "A fresh take: Seasonal changes in terrestrial freshwater inputs impact salt
    marsh hydrology and vegetation dynamics"

    Source files: Soil.csv.

    Location: package metadata (Elkhorn Slough NERR, Cowell Ranch site point; marsh positions not located
    separately).

    Methods: SOM unknown.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): SOM (soil organic matter).

    Examples:
        >>> {k: len(t) for k, t in c_2407118().items()}  # doctest: +SKIP
        {'SOM': 187}
    """
    doi = "doi:10.15485/2407118"
    src = "Soil.csv"
    d = strip_bom(read_csv(doi, src))
    d = d[~is_missing(d["Organic Matter (%)"])]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Sample ID"] + ":" + d["Nest"] + ":" + d["Location"],
        "id_type": "Sample ID:Nest:Location", "depth": d["Depth Range (cm)"],
        "date": pd.to_datetime(d["Date Collected"], format="%m/%d/%Y").dt.strftime("%Y-%m-%d"),
        "value": d["Organic Matter (%)"], "method": UNKNOWN, "latitude": 36.8517, "longitude": -121.7624,
        "notes": ("lat/long source: doi:10.15485/2407118 package metadata (Elkhorn Slough NERR, Cowell Ranch site point; "
                  "marsh positions not located separately); Organic Matter (%) of salt marsh sediment, method not stated in "
                  "the data file; 5 cm Russian peat borer cores sectioned by depth"),
    })
    return {"SOM": assemble(out, "SOM")}


def c_2530252() -> Tables:
    """Harmonize loss on ignition of doi:10.15485/2530252.

    Package: Soil Core Chemistry of Wetland, Old Woman Creek National Estuarine Research Reserve, Huron, OH,
    2023-10-24 to 2024-05-20.

    Source files: SoilChem_DataTable.csv, SoilChem_SampleMetadata.csv.

    Location: SoilChem_SampleMetadata.csv (decimalLatitude/decimalLongitude, one wetland point).

    Methods: LOI loss_on_ignition.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): LOI (loss on ignition).

    Examples:
        >>> {k: len(t) for k, t in c_2530252().items()}  # doctest: +SKIP
        {'LOI': 12}
    """
    doi = "doi:10.15485/2530252"
    src = "SoilChem_DataTable.csv"
    t = read_csv(doi, src, header=None)
    hdr = t.iloc[2].tolist()  # 'Column_Name' row
    start = t.index[t[0] == "#Start_Data"][0]
    d = t.iloc[start:].copy()
    d.columns = hdr
    d = d[~is_missing(d["LOI"])]
    m = read_csv(doi, "SoilChem_SampleMetadata.csv", skiprows=1).set_index("sampleName")

    def collected(sample: str) -> str:
        return str(pd.to_datetime(cast(str, m.loc[sample, "collectionDate"]), format="%m/%d/%Y").strftime("%Y-%m-%d"))

    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Sample_Name"], "id_type": "Sample_Name",
        "depth": [depth_range(a, b) for a, b in zip(d["Min_Depth_cm"], d["Max_Depth_cm"])],
        "date": d["Sample_Name"].map(collected),
        "value": d["LOI"], "method": LOI_METHOD,
        "latitude": d["Sample_Name"].map(m["decimalLatitude"]), "longitude": d["Sample_Name"].map(m["decimalLongitude"]),
        "notes": ("lat/long source: doi:10.15485/2530252:SoilChem_SampleMetadata.csv (decimalLatitude/decimalLongitude, one "
                  "wetland point); LOI (percent, as carbon per the units basis row), MethodID loss_ignition; depth converted "
                  "from inches in the source (Min/Max_Depth_cm); replicate halves of each core section kept as separate rows; "
                  "Old Woman Creek wetland soil core"),
    })
    return {"LOI": assemble(out, "LOI")}


def c_3024414() -> Tables:
    """Harmonize carbon variables of doi:10.15485/3024414.

    Package: Effects of 9.5 years warming on SOC concentration and composition in bulk soil and density fractions.

    Source files: Blodgett_9_5yr_soil_warming_Bulk_EA.csv, Blodgett_9_5yr_soil_warming_Density_fractionation.csv.

    Location: doi:10.15485/2480291 package metadata (Blodgett Forest Research Station point; this package gives only
    a ~8 km box).

    Methods: SOC unknown; POMC density_fractionation; MAOMC density_fractionation.

    Notes:
        - Every line is wrapped in quotes with doubled inner quotes; unwrap before parsing.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): SOC (soil organic carbon), POMC (particulate
        organic matter carbon), MAOMC (mineral-associated organic matter carbon).

    Examples:
        >>> {k: len(t) for k, t in c_3024414().items()}  # doctest: +SKIP
        {'SOC': 30, 'POMC': 9, 'MAOMC': 9}
    """
    import csv
    doi = "doi:10.15485/3024414"
    src = "Blodgett_9_5yr_soil_warming_Bulk_EA.csv"
    # Every line is wrapped in quotes with doubled inner quotes; unwrap before parsing.
    lines = [l.strip() for l in _text(doi, src, "latin1").strip().split("\n")]
    rows = [next(csv.reader([l[1:-1].replace('""', '"')])) for l in lines]
    d = pd.DataFrame(rows[1:], columns=rows[0])
    d = d[(d["Treatment"] == "Control") & ~is_missing(d["C"])]
    loc = ("lat/long source: doi:10.15485/2480291 package metadata (Blodgett Forest Research Station point; this package "
           "gives only a ~8 km box)")
    tail = "control plot of the whole-soil warming experiment (warmed plots excluded); sampled 2023-05-01 after 9.5 years"
    soc = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Block"] + ":" + d["Plot"] + ":" + d["ID"], "id_type": "Block:Plot:ID",
        "depth": [depth_range(float(m) - 5, float(m) + 5) for m in d["midpoint"]], "date": "2023-05-01",
        "value": d["C"], "method": UNKNOWN, "latitude": BLODGETT[0], "longitude": BLODGETT[1],
        "notes": (f"{loc}; C = soil organic carbon content (%) per data dictionary, elemental analysis (Bulk_EA); depth "
                  f"from the 10 cm interval around 'midpoint'; {tail}"),
    })
    src2 = "Blodgett_9_5yr_soil_warming_Density_fractionation.csv"
    f = read_csv(doi, src2)
    f = f[f["Treatment"] == "Control"]
    base = pd.DataFrame({
        "doi": doi, "source_file": src2, "id": f["Block"] + ":" + f["Plot"] + ":" + f["ID"], "id_type": "Block:Plot:ID",
        "depth": f["Depth"].str.replace(" cm", "", regex=False), "date": "2023-05-01",
        "latitude": BLODGETT[0], "longitude": BLODGETT[1],
    })
    return {
        "SOC": assemble(soc, "SOC"),
        "POMC": emit(base, "POMC", [fmt_tc(a + b) for a, b in zip(num(f["fLF_soil"]), num(f["oLF_soil"]))],
                     DENSITY_FRACTIONATION,
                     f"{loc}; POMC = fLF_soil + oLF_soil (mg OC per g fractionated soil = g C kg-1; free + occluded light "
                     f"fractions); {tail}"),
        "MAOMC": emit(base, "MAOMC", f["HF_soil"], DENSITY_FRACTIONATION,
                      f"{loc}; MAOMC = HF_soil (mg OC per g fractionated soil = g C kg-1; heavy fraction); {tail}"),
    }


def c_1875838() -> Tables:
    """Harmonize total carbon, dissolved organic carbon of doi:10.5440/1875838.

    Package: Arctic Soil Column Saturation & Drainage Experiment for Biogeochemical Redox Dynamics; Council, Alaska
    2020-2022.

    Source files: NGA287_Core_Characterization.csv.

    Location: package methods text (point for thermokarst channel cores NGADG0184/NGADG0185); package methods text
    (point for upland cores NGADG0189/NGADG0183).

    Methods: TC unknown; DOC salt_extraction.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), DOC (dissolved organic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_1875838().items()}  # doctest: +SKIP
        {'TC': 27, 'DOC': 13}
    """
    doi = "doi:10.5440/1875838"
    src = "NGA287_Core_Characterization.csv"
    d = strip_bom(read_csv(doi, src)).iloc[1:]  # second line holds units
    pts = {
        "Thermokarst": (64.860044, -163.697718, "point for thermokarst channel cores NGADG0184/NGADG0185"),
        "Upland": (64.859833, -163.698213, "point for upland cores NGADG0189/NGADG0183"),
    }
    mid = num(d["Depth"])
    base = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["core"] + ":" + d["soil_Type"] + ":" + d["Depth"],
        "id_type": "core:soil_Type:Depth", "depth": [depth_range(m - 5, m + 5) for m in mid], "date": "2018-07",
        "latitude": d["soil_Type"].map(lambda t: pts[t][0]), "longitude": d["soil_Type"].map(lambda t: pts[t][1]),
    })
    locs = [(f"lat/long source: doi:10.5440/1875838 package methods text ({pts[t][2]}); ") for t in d["soil_Type"]]
    tail = ("; initial field-core characterization before the column experiment; depth from increment midpoint to its "
            "10 cm increment (as for pH); cores collected July 2018")
    return {
        "TC": emit(base, "TC", d["Avg_C"], UNKNOWN,
                   [f"{l}Avg_C (%) of triplicate analyses (sd {s}), instrument not stated" + tail
                    for l, s in zip(locs, d["C_stddev"])]),
        "DOC": emit(base, "DOC", [fmt_tc(v * MMOL_C) for v in num(d["DOC_KCl_2M"])], SALT_EXTRACTION,
                    [f"{l}DOC_KCl_2M {v} umol C g-1 dry soil x 12.011 = mg C kg-1; 2 M KCl extract" + tail
                     for l, v in zip(locs, d["DOC_KCl_2M"])],
                    DOC_unit="mg C kg-1 dry soil", DOC_medium="2 M KCl extract"),
    }


# ====================================================================================================
# Packages
# ====================================================================================================

PACKAGES = [
    ("doi:10.15485/1454273", combine(("pH", ph_1454273), ("TC", c_1454273)), ('pH', 'TC', 'SOC', 'SIC')),
    ("doi:10.15485/1835182", combine(("pH", ph_1835182), ("TC", c_1835182)), ('pH', 'TC', 'DOC', 'MAOMC')),
    ("doi:10.15485/1898051", combine(("pH", ph_1898051), ("TC", c_1898051)), ('pH', 'TC')),
    ("doi:10.15485/2480291", combine(("pH", ph_2480291), ("TC", c_2480291)), ('pH', 'TC', 'DOC')),
    ("doi:10.15485/2564914", combine(("pH", ph_2564914), ("TC", c_2564914)), ('pH', 'TC')),
    ("doi:10.15485/2583150", combine(("pH", ph_2583150), ("TC", c_2583150)), ('pH', 'TC', 'WEOC')),
    ("doi:10.15485/3024076", combine(("pH", ph_3024076), ("TC", c_3024076)), ('pH', 'TC', 'DOC')),
    ("doi:10.25581/ornlsfa.034/2530530", combine(("pH", ph_2530530), ("TC", c_2530530)), ('pH', 'TC', 'DOC')),
    ("doi:10.5440/1618325", combine(("pH", ph_1618325), ("TC", c_1618325)), ('pH', 'TC', 'LOI')),
    ("doi:10.15485/1866269", combine(("TC", c_1866269)), ('TC',)),
    ("doi:10.15485/1797785", combine(("TC", c_1797785)), ('TC',)),
    ("doi:10.15485/1892050", combine(("TC", c_1892050)), ('TC',)),
    ("doi:10.15485/1773008", combine(("TC", c_1773008)), ('TC',)),
    ("doi:10.15485/1908426", combine(("TC", c_1908426)), ('TC',)),
    ("doi:10.3334/CDIAC/SPRUCE.005", combine(("TC", c_spruce005)), ('TC', 'LOI')),
    ("doi:10.15485/2570819", combine(("TC", c_2570819)), ('TC', 'DOC')),
    ("doi:10.15485/1631972", combine(("TC", c_1631972)), ('TC', 'SOC', 'SIC')),
    ("doi:10.15485/3003878", combine(("TC", c_3003878)), ('SOC',)),
    ("doi:10.15485/2350835", combine(("pH", ph_2350835), ("TC", c_2350835)), ('pH', 'SOC')),
    ("doi:10.15485/2405147", combine(("pH", ph_2405147), ("TC", c_2405147)), ('pH', 'SOC')),
    ("doi:10.15485/1618870", combine(("pH", ph_1618870), ("TC", c_1618870)), ('pH', 'DOC')),
    ("doi:10.15485/1830417", combine(("TC", c_1830417)), ('DOC',)),
    ("doi:10.15485/3030227", combine(("pH", ph_3030227), ("TC", c_3030227)), ('pH', 'SOM', 'WEOC')),
    ("doi:10.15485/2407118", combine(("TC", c_2407118)), ('SOM',)),
    ("doi:10.15485/2530252", combine(("TC", c_2530252)), ('LOI',)),
    ("doi:10.15485/3024414", combine(("TC", c_3024414)), ('SOC', 'POMC', 'MAOMC')),
    ("doi:10.5440/1875838", combine(("pH", ph_1875838), ("TC", c_1875838)), ('pH', 'TC', 'DOC')),
    ("doi:10.15485/1659374", combine(("pH", ph_1659374)), ('pH',)),
    ("doi:10.15485/1810163", combine(("pH", ph_1810163)), ('pH',)),
    ("doi:10.15485/2587853", combine(("pH", ph_2587853)), ('pH',)),
]
