"""Harmonize the hand-written packages of Group 1: coordinates come from the data file itself (per-sample latitude/longitude columns).

The soil pH functions (ph_<id>) were copied from notebooks/harmonize_ph and the carbon functions (c_<id>) from
notebooks/harmonize_carbon, unchanged apart from the assemble() signature. PACKAGES combines them into one function
per package that returns {variable key: harmonized table}.

Packages:
    doi:10.15485/1725884               [pH+carbon] Rowland et al., East River floodplain fine sediment 2014-2017
    doi:10.5440/1854940                [carbon] NGEE Arctic / ABoVE SAR soil samples, Seward Peninsula 2017 and 2019
    doi:10.15485/3367449               [pH+carbon] Sorensen et al., NEON AOP 2018 East River topsoils
    doi:10.25581/ORNLSFA.020/1638590   [carbon] EBIS soils at Oak Ridge and four AmeriFlux sites 2001-2011
    doi:10.5440/1342956                [carbon] Kholodov et al., Teller MM27 soil pits 2016
    doi:10.5440/1417652                [carbon] Kholodov et al., Council MM71 soil pits 2016
    doi:10.15485/2438343               [carbon] Kougarok Fire Complex organic layer, burned and unburned sites 2022
    doi:10.15485/1630815               [carbon] Missouri and Florida wetland soils 2015-2016 (DMS coordinates in the table header)
    doi:10.25581/ORNLSFA.031/2274949   [pH+carbon] Buell et al., multi-site microbial biomass methods
    doi:10.5440/1164833                [carbon]
    doi:10.5440/1226245                [carbon]
    doi:10.15485/2566016               [carbon]
    doi:10.15485/2587411               [carbon]
    doi:10.15485/1894515               [carbon]
    doi:10.15485/2455027               [carbon]
    doi:10.15485/2407117               [carbon]
    doi:10.15485/1577267               [pH] Sorensen et al., East River Pumphouse soils 2016-2017
    doi:10.5440/1785119                [pH] NGEE Arctic shrub seedling experiment soils 2018
    doi:10.15485/2572883               [pH] Tasoff et al., East River vegetation-type soils 2016
    doi:10.5440/1185213                [pH] Iversen et al., Barrow active layer incubations 2012

Attributes:
    PACKAGES: (DOI, package function, variables) per package; the package function combines the pH and carbon
        functions (extract.combine).
"""

from __future__ import annotations

from collections.abc import Iterable
import re
from typing import Any, cast

import pandas as pd  # noqa: F401

from ..common import *  # noqa: F401,F403
from ..common import _text  # noqa: F401
from ..extract import Col, combine, from_columns, from_long, make_base, merge_tables  # noqa: F401
from ..datatypes import Tables


# ====================================================================================================
# Soil pH (from notebooks/harmonize_ph/group1_infile_coords.py)
# ====================================================================================================


def ph_1577267() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/1577267.

    Package: Soil Nitrogen, Water Content, Microbial Biomass, and Archaeal, Bacterial and Fungal Communities from
    the East River Watershed, Colorado collected in 2016-2017.

    Source files: 2017_East_River_Pumphouse_Soil_Water_Content_and_pH__1_.csv.

    Methods: pH_H2O.

    Notes:
        - Excel turned "5-15 cm" into "15-May" in some rows; "15 cm +" is the open-ended bottom layer.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_1577267())  # doctest: +SKIP
        321
    """
    doi = "doi:10.15485/1577267"
    src = "2017_East_River_Pumphouse_Soil_Water_Content_and_pH__1_.csv"
    d = strip_bom(read_csv(doi, src, encoding="latin1"))
    d = d[~is_missing(d["Latitude"]) & ~is_missing(d["Longitude"]) & ~is_missing(d["Soil pH"])].copy()
    # Excel turned "5-15 cm" into "15-May" in some rows; "15 cm +" is the open-ended bottom layer.
    depth_map = {"0-5 cm": "0-5", "5-15 cm": "5-15", "15-May": "5-15", "15 cm +": "15+"}
    keys = ["Location", "Field_Site", "Block", "Plot", "Replicate", "Topographic_Position"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src,
        "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": d["Depth_Increment"].map(depth_map),
        "date": pd.to_datetime(d["Date_Collected"], format="%m/%d/%Y").dt.strftime("%Y-%m-%d"),
        "pH": d["Soil pH"], "ph_method": "pH_H2O",
        "latitude": d["Latitude"], "longitude": d["Longitude"], "IGSN": d["IGSN"].str.strip(),
        "Lab_ID_LBNL": d["Lab_ID_LBNL"], "notes": "",
    })
    return assemble(out, "pH", extra=["Lab_ID_LBNL"], raw=True)


def ph_1725884() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/1725884.

    Package: Bulk density, grain size, carbon, and nitrogen content of floodplain fine sediment along the East
    River, Colorado collected from 2014 to 2017.

    Source files: EastRiver_2014_SoilPits_H20ExtractedCarbon.csv.

    Location: EastRiver_2014_SoilPits_H20ExtractedCarbon.csv (per-pit DGPS, 1.5 m horizontal precision).

    Methods: pH_H2O.

    Notes:
        - Both pits are labelled TTFP1 in the source; the second pit is the block with different coordinates, and the
          methods list pits TTFP1 and TTFP2, so relabel it.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_1725884())  # doctest: +SKIP
        21
    """
    doi = "doi:10.15485/1725884"
    src = "EastRiver_2014_SoilPits_H20ExtractedCarbon.csv"
    d = strip_bom(read_csv(doi, src))
    # Both pits are labelled TTFP1 in the source; the second pit is the block with different
    # coordinates, and the methods list pits TTFP1 and TTFP2, so relabel it.
    first_pit = (d["Latitude"] == d["Latitude"].iloc[0]) & (d["Longitude"] == d["Longitude"].iloc[0])
    sample = d["Sample ID"].where(first_pit, d["Sample ID"].str.replace("TTFP1", "TTFP2", regex=False))
    base = ("lat/long source: doi:10.15485/1725884:EastRiver_2014_SoilPits_H20ExtractedCarbon.csv "
            "(per-pit DGPS, 1.5 m horizontal precision); pH_H2O: 1:1 soil:DI water (30 g moisture-corrected "
            "soil to 30 mL total), shaken ~20 h, centrifuged 15,000 RCF 15 min, pH measured on 0.2 um-filtered "
            "extract; floodplain soil pit sampled 2014-10-27")
    relabel = ("; Sample ID relabeled from TTFP1 to TTFP2: source file labels both pits TTFP1, but these rows "
               "have distinct coordinates and methods list pits TTFP1 and TTFP2")
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": sample, "id_type": "Sample ID",
        "depth": [depth_range(a, b) for a, b in zip(d["Interval top depth (cm BGS)"], d["Interval bottom depth (cm BGS)"])],
        "date": pd.to_datetime(d["Sample Date"], format="%m/%d/%y").dt.strftime("%Y-%m-%d"),
        "pH": d["pH"], "ph_method": "pH_H2O", "latitude": d["Latitude"], "longitude": d["Longitude"],
        "notes": [base if f else base + relabel for f in first_pit],
    })
    return assemble(out, "pH", raw=True)


def ph_1785119() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.5440/1785119.

    Package: Shrub Seedling Experiment: Environmental Conditions, Vegetation Composition, and Seedling Recruitment,
    Seward Peninsula, Alaska, 2018-2019.

    Source files: NGEE_shrub_seedling_experiment_soil_chemistry_20210523.csv.

    Location: NGEE_shrub_seedling_experiment_soil_chemistry_20210523.csv (plot location).

    Methods: pH_H2O.

    Notes:
        - pH was only measured on the 2018 0-10 cm cores.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_1785119())  # doctest: +SKIP
        20
    """
    doi = "doi:10.5440/1785119"
    src = "NGEE_shrub_seedling_experiment_soil_chemistry_20210523.csv"
    d = strip_bom(read_csv(doi, src))
    d = d[~is_missing(d["pH"])].copy()  # pH was only measured on the 2018 0-10 cm cores
    site_text = {
        "CN-MM71": "Council MM71 (thermokarst-disturbed and intact tussock tundra)",
        "KG-MM86": "Quartz Creek burn area (2015 Mingvk Lake fire), Kougarok MM86",
        "KG-MM80": "Quartz Creek unburned, Kougarok MM80",
    }
    base = ("lat/long source: doi:10.5440/1785119:NGEE_shrub_seedling_experiment_soil_chemistry_20210523.csv "
            "(plot location); pH method: DI water, 7:1 water:soil by weight (1:7 soil:water), oven-dried (60 C) "
            "ground soil, per package methods; 0-10 cm core from organic horizon surface, collected adjacent to "
            "plot (not subject to scraping treatment); ")
    keys = ["locale", "site", "plot-ID"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": "0-" + d["sample-depth"], "date": d["collection-date"], "pH": d["pH"], "ph_method": "pH_H2O",
        "latitude": d["latitude"], "longitude": d["longitude"],
        "notes": base + d["site"].map(site_text),
    })
    return assemble(out, "pH", raw=True)


def ph_2572883() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/2572883.

    Package: Montane Conifer, Aspen, Meadow, and Sagebrush Metagenome Resolved Genomes and Traits in East River
    Watershed, Colorado, USA.

    Source files: EastRiver_Vegtype_sample_metadata.csv.

    Location: EastRiver_Vegtype_sample_metadata.csv (per-sample Latitude/Longitude).

    Methods: unknown.

    Notes:
        - One row lists Min_Depth 5 > Max_Depth 4.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_2572883())  # doctest: +SKIP
        66
    """
    doi = "doi:10.15485/2572883"
    src = "EastRiver_Vegtype_sample_metadata.csv"
    d = strip_bom(read_csv(doi, src))
    layer = {"1": "shallower", "2": "deeper"}
    depth, extra = [], []
    for top, bot, lay in zip(d["Min_Depth"], d["Max_Depth"], d["depth"]):
        core = f"{layer[lay]} subsample (depth={lay}) of a 0-20 cm core"
        if top == "NA" or bot == "NA":
            depth.append("")
            extra.append(f"depth not reported in source (Min_Depth/Max_Depth NA); {core}")
        elif float(top) > float(bot):  # one row lists Min_Depth 5 > Max_Depth 4
            depth.append(f"{bot}-{top}")
            extra.append(f"source lists Min_Depth {top} > Max_Depth {bot}; written as {bot}-{top}; {core}")
        else:
            depth.append(f"{top}-{bot}")
            extra.append(f"depth from Min_Depth-Max_Depth (cm); {core}")
    keys = ["sample", "Location", "Replicate", "Vegtype", "depth"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": depth, "date": d["DateTime"].str[:10], "pH": d["pH"], "ph_method": "unknown",
        "latitude": d["Latitude"], "longitude": d["Longitude"], "IGSN": d["IGSN"],
        "notes": [("lat/long source: doi:10.15485/2572883:EastRiver_Vegtype_sample_metadata.csv (per-sample "
                   "Latitude/Longitude); pH method not reported (data dictionary: 'pH of associated sample'); "
                   f"{e}; vegetation {v}; sampled Aug 2016 (Gs0118068 metagenome samples)")
                  for e, v in zip(extra, d["Vegtype"])],
    })
    return assemble(out, "pH", raw=True)


def ph_3367449() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/3367449.

    Package: Soil physical and chemical measurements for topsoils collected during NEON campaign in East River, CO
    (06/14/2018-06/28/2018)

    Source files: 2018_NEON_soil_physical_chemical_measurements.csv, samples.csv.

    Location: 2018_NEON_soil_physical_chemical_measurements.csv (per-sample Latitude/Longitude).

    Methods: pH_H2O.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_3367449())  # doctest: +SKIP
        407
    """
    doi = "doi:10.15485/3367449"
    src = "2018_NEON_soil_physical_chemical_measurements.csv"
    d = strip_bom(read_csv(doi, src))
    s = strip_bom(read_csv(doi, "samples.csv"))[["IGSN", "Collection date"]]
    d = d.merge(s, on="IGSN", how="left")  # collection date lives in samples.csv
    d = d[~is_missing(d["Soil_pH"]) & ~is_missing(d["Latitude"]) & ~is_missing(d["Longitude"])]
    note = ("lat/long source: doi:10.15485/3367449:2018_NEON_soil_physical_chemical_measurements.csv "
            "(per-sample Latitude/Longitude); pH_H2O: 1:1 with DI water, by mass (package methods; data dictionary "
            "says 1:1 w/vol slurry), USGS Soils and Sediment Lab, Denver; depth 2.5-7.5 cm per package methods "
            "('Surface samples (2.5 - 7.5 cm)'; AMS core with two stacked 2 in inserts), but samples.csv describes "
            "'Soil samples, 0-10 cm' (depth in core max 0.1 m) and doi:10.15485/2587101 reports 0-0.05 m for the "
            "same samples; date from doi:10.15485/3367449:samples.csv 'Collection date' matched by IGSN; NEON AOP "
            "2018 East River ground campaign; site ")
    ignored = ("; doi:10.15485/2587101 (NEON 2018 metagenome samples) was ignored: it covers a subset of these "
               "samples (215 shared), though with different pH values (only 27 of the 215 match; median absolute "
               "difference 0.44 pH units; extreme cases: 353-ER18 3.74 here vs 6.40 in 2587101, 110-ER18 7.45 vs "
               "5.18, 399-ER18 7.29 vs 5.38, 127-ER18 5.15 vs 6.69)")
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["SampleSiteCode"] + ":" + d["Sampling_Area"],
        "id_type": "SampleSiteCode:Sampling_Area", "depth": "2.5-7.5", "date": d["Collection date"].str[:10],
        "pH": d["Soil_pH"], "ph_method": "pH_H2O", "latitude": d["Latitude"], "longitude": d["Longitude"],
        "IGSN": d["IGSN"], "notes": note + d["Site_Name"] + ignored,
    })
    return assemble(out, "pH", raw=True)


def ph_2274949() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.25581/ORNLSFA.031/2274949.

    Package: Interrelationships among methods of estimating microbial biomass across multiple soil orders and
    biomes: Supporting data.

    Source files: TESSFA_SMB_proxy.csv.

    Location: TESSFA_SMB_proxy.csv (Latitude/Longitude, 'approximate site' coordinates per data dictionary).

    Methods: pH_H2O.

    Notes:
        - Marcell S1 Bog peat samples have pH -9999.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_2274949())  # doctest: +SKIP
        31
    """
    doi = "doi:10.25581/ORNLSFA.031/2274949"
    src = "TESSFA_SMB_proxy.csv"
    d = strip_bom(read_csv(doi, src))
    d = d[~is_missing(d["pH"])]  # Marcell S1 Bog peat samples have pH -9999
    keys = ["Site_Id", "Site_location", "Soil_horizon"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": d["Soil_horizon"], "date": "2012/2013", "pH": d["pH"], "ph_method": "pH_H2O",
        "latitude": d["Latitude"].astype(float).round(6), "longitude": d["Longitude"].astype(float).round(6),
        "notes": [("lat/long source: doi:10.25581/ORNLSFA.031/2274949:TESSFA_SMB_proxy.csv (Latitude/Longitude, "
                   "'approximate site' coordinates per data dictionary); pH_H2O: 1 part soil to 2 parts Milli-Q water, "
                   f"shaken, pH of supernatant; depth given only as soil horizon '{h}' (no cm depths reported); soil "
                   f"order {o}; date: samples processed 2012-2013 per package description, collection dates not "
                   "reported; multi-site microbial biomass method comparison (one composite sample per site and horizon)")
                  for h, o in zip(d["Soil_horizon"], d["Soil_order"])],
    })
    return assemble(out, "pH", raw=True)


def ph_1185213() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.5440/1185213.

    Package: Active Layer Soil Carbon and Nutrient Mineralization, Barrow, Alaska, 2012.

    Source files: Schadel_et_al_2015_NGEE_Arctic_Barrow_Soil_Incubations_2012.csv,
    Treat_et_al_2015_NGEE_Arctic_Barrow_Soil_Incubations_2012.csv.

    Location: Schadel_et_al_2015_NGEE_Arctic_Barrow_Soil_Incubations_2012.csv (per-plot Latitude/Longitude, NGEE
    Vegetation Plot); Treat_et_al_2015_NGEE_Arctic_Barrow_Soil_Incubations_2012.csv (per-plot Latitude/Longitude,
    NGEE Vegetation Plot).

    Methods: pH_H2O.

    Notes:
        - pH is repeated on every incubation row (3 temperatures x 5 days): keep one row per soil layer.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_1185213())  # doctest: +SKIP
        57
    """
    r: Any  # one source row (itertuples / to_dict record): cell types are not known statically
    doi = "doi:10.5440/1185213"
    files = {  # file name -> header rows to skip before the column names (a units row follows the names)
        "Schadel_et_al_2015_NGEE_Arctic_Barrow_Soil_Incubations_2012.csv": 8,
        "Treat_et_al_2015_NGEE_Arctic_Barrow_Soil_Incubations_2012.csv": 9,
    }
    hz = {"O": "organic", "Mi": "mineral", "M": "mineral", "DO": "deep organic (near permafrost boundary)", "": "not recorded"}
    meth = ("pH_H2O: field-moist soil in distilled water, 1:4 (organic) or 1:2 (mineral) soil:water slurry "
            "(user guide), Beckman 350 meter; initial pH before 28-day incubation")
    rows = []
    for src, skip in files.items():
        d = strip_bom(read_csv(doi, src, skiprows=skip)).iloc[1:]
        lead = f"lat/long source: doi:10.5440/1185213:{src} (per-plot Latitude/Longitude, NGEE Vegetation Plot); {meth}; "
        if src.startswith("Schadel"):
            # pH is repeated on every incubation row (3 temperatures x 5 days): keep one row per soil layer
            d = d.drop_duplicates(["Plot_ID", "Soil_Horizon", "Upper_depth_of_soil_layer",
                                   "Lower_depth_of_soil_layer", "pH_of_soil_layer"])
            for r in d.itertuples():
                rows.append(dict(
                    doi=doi, source_file=src, id=f"{r.Plot_ID}:{r.Microtopography}:{r.Soil_Horizon}",
                    id_type="Plot_ID:Microtopography:Soil_Horizon",
                    depth=depth_range(r.Upper_depth_of_soil_layer, r.Lower_depth_of_soil_layer),
                    date=r.Date_sampled, pH=r.pH_of_soil_layer, ph_method="pH_H2O",
                    latitude=r.Latitude, longitude=r.Longitude,
                    notes=lead + f"soil horizon {r.Soil_Horizon} ({hz[r.Soil_Horizon]}), 5-cm increments combined into "
                                 f"horizon and re-sampled for pH; {r.Polygon_type}, microtopography {r.Microtopography}; "
                                 "Barrow Environmental Observatory Intensive Site 1"))
        else:
            d = d.drop_duplicates(["Plot_ID", "Soil_Horizon", "Soil_depth_increment", "Upper_depth_of_soil_layer",
                                   "Lower_depth_of_soil_layer", "pH_of_soil_layer"])
            d = d[~is_missing(d["pH_of_soil_layer"])]  # also drops the template's blank rows
            for r in d.itertuples():
                rows.append(dict(
                    doi=doi, source_file=src, id=f"{r.Plot_ID}:{r.Microtopography}:{r.Soil_depth_increment}",
                    id_type="Plot_ID:Microtopography:Soil_depth_increment",
                    depth=depth_range(round(float(r.Upper_depth_of_soil_layer) * 100, 1),
                                      round(float(r.Lower_depth_of_soil_layer) * 100, 1)),  # metres -> cm
                    date=r.Date_Sampled, pH=r.pH_of_soil_layer, ph_method="pH_H2O",
                    latitude=r.Latitude, longitude=r.Longitude,
                    notes=lead + f"5-cm depth increment (source depths in m, converted to cm), horizon "
                                 f"{r.Soil_Horizon or 'not recorded'} ({hz[r.Soil_Horizon]}); {r.Polygon_type}, "
                                 f"microtopography {r.Microtopography}; Barrow Environmental Observatory Intensive Site 1"))
    return assemble(pd.DataFrame(rows), "pH", raw=True)


# ====================================================================================================
# Soil carbon (from notebooks/harmonize_carbon/group1_infile_coords.py)
# ====================================================================================================


def c_1725884() -> Tables:
    """Harmonize carbon variables of doi:10.15485/1725884.

    Package: Bulk density, grain size, carbon, and nitrogen content of floodplain fine sediment along the East
    River, Colorado collected from 2014 to 2017.

    Source files: EastRiverFloodplainSoilCarbonandNitrogen.csv, EastRiver_2014_SoilPits_SolidCarbon.csv,
    EastRiver_2014_SoilPits_H20ExtractedCarbon.csv, EastRiverFloodplainOrganicMatter.csv.

    Location: EastRiverFloodplainSoilCarbonandNitrogen.csv (per-sample DGPS, 1.5 m horizontal precision);
    EastRiver_2014_SoilPits_SolidCarbon.csv (per-pit DGPS, 1.5 m horizontal precision);
    EastRiver_2014_SoilPits_H20ExtractedCarbon.csv (per-pit DGPS); EastRiverFloodplainOrganicMatter.csv (per-sample
    DGPS).

    Methods: TC dry_combustion; SOC TC_minus_TIC; SIC acidification; WEOC water_extraction; SOM loss_on_ignition.

    Notes:
        - Both pits are labelled TTFP1 in the source; the block with different coordinates is pit TTFP2 (same relabeling
          as the harmonized soil pH file for this package).
        - Water extracts (1:1 soil:water) of the 2014 pits -> WEOC in mg C per kg dry soil.
        - Organic matter by loss on ignition (550 C) of the whole sample.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), SOC (soil organic carbon), SIC
        (soil inorganic carbon), WEOC (water-extractable organic carbon), SOM (soil organic matter).

    Examples:
        >>> {k: len(t) for k, t in c_1725884().items()}  # doctest: +SKIP
        {'TC': 113, 'SOC': 113, 'SIC': 113, 'WEOC': 18, 'SOM': 48}
    """
    r: Any  # one source row (itertuples / to_dict record): cell types are not known statically
    doi = "doi:10.15485/1725884"
    method = ("TC by Shimadzu TOC-VCPH with solid sample module SSM-5000A (combustion at 900 C in O2, "
              "Co/Pt catalytic post-combustion), per package methods")
    ic_method = ("IC by the SSM-5000A IC furnace (phosphoric acid, CO2 purged at 200 C), per package methods")
    rows, soc, sic = [], [], []

    src = "EastRiverFloodplainSoilCarbonandNitrogen.csv"
    d = strip_bom(read_csv(doi, src))
    d = d[~is_missing(d["TC (%) Average"])]
    for r in d.to_dict("records"):
        reps = "two replicates averaged" if not is_missing(pd.Series([r["TC (%) Data-2"]])).iloc[0] else "single analysis"
        loc = "oxbow/abandoned channel" if ("OB" in r["Field ID"] or "AC" in r["Field ID"]) else "floodplain"
        base = dict(doi=doi, source_file=src, id=r["Field ID"], id_type="Field ID",
                    depth=depth_range(r["Interval top depth (cm BGS)"], r["Interval bottom depth (cm BGS)"]),
                    date=pd.to_datetime(r["Date Sampled"], format="%m/%d/%y").strftime("%Y-%m-%d"),
                    latitude=r["Latitude"], longitude=r["Longitude"])
        where = (f"lat/long source: doi:10.15485/1725884:{src} (per-sample DGPS, 1.5 m horizontal precision)")
        site = (f"East River {loc} fine sediment, {r['Distance downstream (m)']} m downstream, "
                f"{r['Distance from River Bank (m)']} m from bank")
        rows.append(dict(base, TC=r["TC (%) Average"], tc_method=DRY_COMBUSTION,
                         notes=f"{where}; {method}; TC (%) Average ({reps}); {site}"))
        soc.append(dict(base, value=r["OC (%) (TC-IC)"], method=TC_MINUS_TIC,
                        notes=f"{where}; OC (%) (TC-IC) = TC (%) minus IC (%) ({method}; {ic_method}); {site}"))
        sic.append(dict(base, value=r["IC (%) Average"], method=ACIDIFICATION,
                        notes=f"{where}; IC (%) Average; {ic_method}; {site}"))

    src = "EastRiver_2014_SoilPits_SolidCarbon.csv"
    d = strip_bom(read_csv(doi, src))
    # Both pits are labelled TTFP1 in the source; the block with different coordinates is pit TTFP2
    # (same relabeling as the harmonized soil pH file for this package).
    first = (d["Latitude"] == d["Latitude"].iloc[0]) & (d["Longitude"] == d["Longitude"].iloc[0])
    relabel = ("; Sample ID relabeled from TTFP1 to TTFP2: source file labels both pits TTFP1, but these rows have "
               "distinct coordinates and methods list pits TTFP1 and TTFP2")
    for r, f in zip(d.to_dict("records"), first):
        sid = r["Sample ID"] if f else r["Sample ID"].replace("TTFP1", "TTFP2")
        base = dict(doi=doi, source_file=src, id=sid, id_type="Sample ID",
                    depth=depth_range(r["Interval top depth (cm BGS)"], r["Interval bottom depth (cm BGS)"]),
                    date=pd.to_datetime(r["Sample Date"], format="%m/%d/%y").strftime("%Y-%m-%d"),
                    latitude=r["Latitude"], longitude=r["Longitude"])
        where = f"lat/long source: doi:10.15485/1725884:{src} (per-pit DGPS, 1.5 m horizontal precision)"
        tail = "floodplain soil pit sampled 2014-10-27" + ("" if f else relabel)
        rows.append(dict(base, TC=r["TC (%)"], tc_method=DRY_COMBUSTION, notes=f"{where}; {method}; {tail}"))
        soc.append(dict(base, value=r["TOC (%)"], method=TC_MINUS_TIC,
                        notes=f"{where}; TOC (%) = TC minus TIC ({method}; {ic_method}); {tail}"))
        sic.append(dict(base, value=r["TIC (%)"], method=ACIDIFICATION, notes=f"{where}; TIC (%); {ic_method}; {tail}"))

    # Water extracts (1:1 soil:water) of the 2014 pits -> WEOC in mg C per kg dry soil.
    src = "EastRiver_2014_SoilPits_H20ExtractedCarbon.csv"
    d = strip_bom(read_csv(doi, src))
    first = (d["Latitude"] == d["Latitude"].iloc[0]) & (d["Longitude"] == d["Longitude"].iloc[0])
    weoc = []
    for r, f in zip(d.to_dict("records"), first):
        conc = num(pd.Series([r["Total DOC (mM)"]])).iloc[0] * MMOL_C  # mg C per L of extract (dilution corrected)
        weoc.append(dict(
            doi=doi, source_file=src, id=r["Sample ID"] if f else r["Sample ID"].replace("TTFP1", "TTFP2"),
            id_type="Sample ID",
            depth=depth_range(r["Interval top depth (cm BGS)"], r["Interval bottom depth (cm BGS)"]),
            date=pd.to_datetime(r["Sample Date"], format="%m/%d/%y").strftime("%Y-%m-%d"),
            latitude=r["Latitude"], longitude=r["Longitude"], value=fmt_tc(conc), method=WATER_EXTRACTION,
            notes=(f"lat/long source: doi:10.15485/1725884:{src} (per-pit DGPS); DI-water extract, 1:1 soil:solution "
                   "(30 g moisture-corrected soil to 30 mL total water), shaken ~20 h, centrifuged, 0.2 um filtered; "
                   f"WEOC = Total DOC (mM) {r['Total DOC (mM)']} x 12.011 mg C/mmol = mg C/L of extract, equal to mg C/kg "
                   "dry soil at 1 L/kg; floodplain soil pit sampled 2014-10-27" + ("" if f else relabel))))

    # Organic matter by loss on ignition (550 C) of the whole sample.
    src = "EastRiverFloodplainOrganicMatter.csv"
    t = read_csv(doi, src, header=None)
    hdr = t.iloc[0].tolist()
    d = t.iloc[2:]
    c = {k: hdr.index(k) for k in ["Sample_ID", "Latitude", "Longitude", "Interval top depth (cm BGS)",
                                     "Interval bottom depth (cm BGS)", "Date Sampled", "Organic Matter Percentage"]}
    d = d[~is_missing(d[c["Organic Matter Percentage"]]) & ~is_missing(d[c["Sample_ID"]])]
    som = []
    for r in d.itertuples(index=False):
        top, bot = r[c["Interval top depth (cm BGS)"]], r[c["Interval bottom depth (cm BGS)"]]
        som.append(dict(
            doi=doi, source_file=src, id=r[c["Sample_ID"]], id_type="Sample_ID",
            depth="" if is_missing(pd.Series([top, bot])).any() else (fmt_num(top) if top == bot else depth_range(top, bot)),
            date=pd.to_datetime(r[c["Date Sampled"]], format="%m/%d/%y").strftime("%Y-%m-%d"),
            latitude=r[c["Latitude"]], longitude=r[c["Longitude"]], value=r[c["Organic Matter Percentage"]],
            method=LOI_METHOD,
            notes=(f"lat/long source: doi:10.15485/1725884:{src} (per-sample DGPS); Organic Matter Percentage (total "
                   "sample) by loss on ignition: oven-dried 105 C, combusted in a muffle furnace at 550 C for at least "
                   "12 h (package methods)" + ("; depth is a single sample depth (top = bottom in source)"
                                                if top == bot else "") + "; East River abandoned channel / floodplain")))
    return {"TC": assemble(pd.DataFrame(rows), "TC"), "SOC": assemble(pd.DataFrame(soc), "SOC"),
            "SIC": assemble(pd.DataFrame(sic), "SIC"), "WEOC": assemble(pd.DataFrame(weoc), "WEOC"),
            "SOM": assemble(pd.DataFrame(som), "SOM")}


def c_1854940() -> Tables:
    """Harmonize total carbon, soil organic carbon of doi:10.5440/1854940.

    Package: Soil moisture, physical and chemical properties coincident with airborne SAR data collections for 2017
    and 2019, Seward Peninsula, Alaska.

    Source files: soil_samples_seward_2017.csv, soil_samples_seward_2019.csv.

    Location: soil_samples_seward_2017.csv (per-sample Latitude/Longitude); soil_samples_seward_2019.csv (per-sample
    Latitude/Longitude).

    Methods: TC dry_combustion; SOC acid_treated_combustion.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), SOC (soil organic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_1854940().items()}  # doctest: +SKIP
        {'TC': 67, 'SOC': 51}
    """
    doi = "doi:10.5440/1854940"
    method = ("TC by Eurovector elemental analyzer coupled to Isoprime IRMS (~5 mg crushed sample), Los Alamos "
              "National Laboratory, per package methods")
    caveat = ("samples follow ABoVE SAR ground-truthing protocol: split by visible horizon (vegetation, duff or "
              "mineral layer) and may include surface vegetation (package methods)")
    rows, soc = [], []
    oc_method = ("organic C by Eurovector elemental analyzer-IRMS after 6 N HCl treatment at 50 C in silver capsules "
                 "(carbonate removed), per package methods")
    for year, tc, flag, area in [("2017", "Total_C", "C_flag", "Area"), ("2019", "Total_C_%", "C_Flag", "Area")]:
        src = f"soil_samples_seward_{year}.csv"
        d = strip_bom(read_csv(doi, src)).iloc[1:]  # second row holds units
        oc = "Organic_C_EA" if year == "2017" else "Organic_C_EA_%"
        for r in d[~is_missing(d[oc])].to_dict("records"):
            plot_ = "SAR_Plot" if "SAR_Plot" in d.columns else "SAR_plot"
            keys_ = ["Site", plot_, "SAR_Transect", "SAR_Flag", "Soil_Sample_ID"]
            lo_, hi_ = [c for c in d.columns if c.lower().startswith("soil_sample_depth_u")][0], \
                [c for c in d.columns if c.lower().startswith("soil_sample_depth_l")][0]
            depth_, dnote_ = checked_depth(r[lo_], r[hi_])
            fl = r[flag]
            soc.append(dict(
                doi=doi, source_file=src, id=":".join(r[k] or "NA" for k in keys_), id_type=":".join(keys_),
                depth=depth_, date=r["Date"], value=r[oc], method=ACID_COMBUSTION,
                latitude=r["Latitude"], longitude=r["Longitude"],
                notes=(f"lat/long source: doi:10.5440/1854940:{src} (per-sample Latitude/Longitude); {oc_method}; "
                       f"{caveat}; locale {r['Locale']}; C flag {fl or 'NA'}"
                       + (" (organic C exceeded total C; data dictionary says to use total C as organic C)" if fl == "V1" else "")
                       + dnote_)))
        d = d[~is_missing(d[tc])]
        plot = "SAR_Plot" if "SAR_Plot" in d.columns else "SAR_plot"
        lo = "Soil_Sample_Depth_upper" if year == "2017" else "soil_sample_depth_upper"
        hi = "Soil_Sample_Depth_lower" if year == "2017" else "soil_sample_depth_lower"
        keys = ["Site", plot, "SAR_Transect", "SAR_Flag", "Soil_Sample_ID"]
        for r in d.to_dict("records"):
            extra = f"; field note: {r['Notes']}" if r.get("Notes") else ""
            depth, dnote = checked_depth(r[lo], r[hi])
            rows.append(dict(
                doi=doi, source_file=src, id=":".join(r[k] or "NA" for k in keys), id_type=":".join(keys),
                depth=depth, date=r["Date"], TC=r[tc], tc_method=DRY_COMBUSTION,
                latitude=r["Latitude"], longitude=r["Longitude"],
                notes=(f"lat/long source: doi:10.5440/1854940:{src} (per-sample Latitude/Longitude); {method}; "
                       f"{caveat}; locale {r['Locale']}{dnote}{extra}")))
    return {"TC": assemble(pd.DataFrame(rows), "TC"), "SOC": assemble(pd.DataFrame(soc), "SOC")}


def c_3367449() -> Tables:
    """Harmonize carbon variables of doi:10.15485/3367449.

    Package: Soil physical and chemical measurements for topsoils collected during NEON campaign in East River, CO
    (06/14/2018-06/28/2018)

    Source files: 2018_NEON_soil_physical_chemical_measurements.csv, samples.csv.

    Location: 2018_NEON_soil_physical_chemical_measurements.csv (per-sample Latitude/Longitude).

    Methods: TC dry_combustion; SOC ramped_combustion; SIC ramped_combustion; DOC salt_extraction; LOI
    loss_on_ignition.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), SOC (soil organic carbon), SIC
        (soil inorganic carbon), DOC (dissolved organic carbon), LOI (loss on ignition).

    Examples:
        >>> {k: len(t) for k, t in c_3367449().items()}  # doctest: +SKIP
        {'TC': 416, 'SOC': 416, 'SIC': 416, 'DOC': 417, 'LOI': 414}
    """
    doi = "doi:10.15485/3367449"
    src = "2018_NEON_soil_physical_chemical_measurements.csv"
    d = strip_bom(read_csv(doi, src))
    s = strip_bom(read_csv(doi, "samples.csv"))[["IGSN", "Collection date"]]
    d = d.merge(s, on="IGSN", how="left")  # collection date lives in samples.csv
    note = ("lat/long source: doi:10.15485/3367449:2018_NEON_soil_physical_chemical_measurements.csv "
            "(per-sample Latitude/Longitude); TC by temperature-ramped combustion: Soil_TC = ROC + TOC400 + TIC "
            "(carbon evolved at 400 C under O2, residual organic C, and C evolved at 900 C under N2), per data "
            "dictionary; depth 2.5-7.5 cm per package methods ('Surface samples (2.5 - 7.5 cm)'), but samples.csv "
            "describes 'Soil samples, 0-10 cm' (same depth convention as the harmonized soil pH file); date from "
            "doi:10.15485/3367449:samples.csv 'Collection date' matched by IGSN; NEON AOP 2018 East River ground "
            "campaign; site ")
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["SampleSiteCode"] + ":" + d["Sampling_Area"],
        "id_type": "SampleSiteCode:Sampling_Area", "depth": "2.5-7.5", "date": d["Collection date"].str[:10],
        "TC": d["Soil_TC"], "tc_method": DRY_COMBUSTION, "latitude": d["Latitude"], "longitude": d["Longitude"],
        "IGSN": d["IGSN"], "notes": note + d["Site_Name"],
    })
    base = out.drop(columns=["TC", "tc_method", "notes"])
    loc = ("lat/long source: doi:10.15485/3367449:2018_NEON_soil_physical_chemical_measurements.csv (per-sample "
           "Latitude/Longitude); ")
    tail = ("; depth 2.5-7.5 cm per package methods; date from samples.csv 'Collection date' matched by IGSN; NEON AOP "
            "2018 East River ground campaign; site " + d["Site_Name"])
    return {
        "TC": assemble(out, "TC"),
        "SOC": emit(base, "SOC", d["Soil_TOC"], RAMPED_COMBUSTION,
                    loc + "Soil_TOC = ROC + TOC400 (temperature-ramped combustion: C evolved at 400 C under O2 plus "
                    "residual organic C), per data dictionary" + tail),
        "SIC": emit(base, "SIC", d["Soil_TIC"], RAMPED_COMBUSTION,
                    loc + "Soil_TIC = C evolved at 900 C under N2 (temperature-ramped combustion), per data dictionary"
                    + tail),
        "DOC": emit(base, "DOC", d["Soil_Total_Extractable_Organic_C"], SALT_EXTRACTION,
                    loc + "Soil_Total_Extractable_Organic_C: dissolved organic C in soil extracts, ug C/g oven-dry soil "
                    "(= mg C/kg), per data dictionary; extractant not named in the data dictionary" + tail,
                    DOC_unit="mg C kg-1 dry soil", DOC_medium="soil extract (extractant not stated)"),
        "LOI": emit(base, "LOI", d["Soil_OM_loss_on_ignition"], LOI_METHOD,
                    loc + "Soil_OM_loss_on_ignition (%), 'soil organic matter loss on ignition' per data dictionary; "
                    "ignition temperature not stated" + tail),
    }


def c_1638590() -> pd.DataFrame:
    """Harmonize total carbon of doi:10.25581/ORNLSFA.020/1638590.

    Package: Enriched Background Isotope Study (EBIS): Analysis of 14C-Enriched Carbon Cycle in Soils and Litter at
    Forested Oak Ridge and AmeriFlux Sites, 2001-2011.

    Source files: EB_TN_SoilLitter_Analyses_20240308.csv, EB_AMER_SoilLitter_Analyses_20240308.csv.

    Location: EB_TN_SoilLitter_Analyses_20240308.csv (site-level Lat/Long); EB_AMER_SoilLitter_Analyses_20240308.csv
    (site-level Lat/Long).

    Methods: unknown.

    Notes:
        - One AMER plot/layer/year has two analyses: the source's Order number keys the rows.

    Returns:
        The total carbon table in the harmonized layout (common.assemble).

    Examples:
        >>> len(c_1638590())  # doctest: +SKIP
        861
    """
    doi = "doi:10.25581/ORNLSFA.020/1638590"
    method = ("C (%) by elemental analyzer (EBIS radiocarbon program); instrument not given in the data file")
    rows = []
    src = "EB_TN_SoilLitter_Analyses_20240308.csv"
    d = read_csv(doi, src)
    d = d[~d["Soil_layer"].str.startswith("Oi") & ~is_missing(d["C"]) & (d["Year"] != "-9999")]
    for r in d.to_dict("records"):
        organic = r["Soil_layer"] == "OeOa"
        rows.append(dict(
            doi=doi, source_file=src, id=f"{r['Site']}:{r['Plot']}:{r['Treatment']}:{r['Soil_layer']}",
            id_type="Site:Plot:Treatment:Soil_layer", depth="O" if organic else r["Soil_layer"],
            date=r["Year"], TC=r["C"], tc_method=UNKNOWN, latitude=r["Lat"], longitude=r["Long"], Order=r["Order"],
            notes=(f"lat/long source: {doi}:{src} (site-level Lat/Long); {method}; Oak Ridge Reservation EBIS site "
                   f"{r['Site']}, {r['Soil_type']}; litter treatment {r['Treatment']} (14C-enriched vs ambient litter "
                   "label only); " + ("Oe+Oa organic horizon" if organic else "mineral soil layer")
                   + f"; sampling time in source: '{r['Date']}' (year {r['Year']}); Oi litter layers excluded")))
    src = "EB_AMER_SoilLitter_Analyses_20240308.csv"
    d = read_csv(doi, src)
    d = d[d["Soil_layer"].str.startswith("Soil") | (d["Soil_layer"] == "OeOa")]
    d = d[~is_missing(d["C"])]
    for r in d.to_dict("records"):
        organic = r["Soil_layer"] == "OeOa"
        depth = "O" if organic else "-".join(str(int(x)) for x in r["Soil_layer"].split()[1].split("-"))
        rows.append(dict(
            doi=doi, source_file=src, id=f"{r['Site']}:{r['Plot']}:{r['Plot_type']}:{r['Soil_layer']}",
            id_type="Site:Plot:Plot_type:Soil_layer", depth=depth, date=r["Year"], TC=r["C"], tc_method=UNKNOWN,
            latitude=r["Lat"], longitude=r["Long"], Order=r["Order"],
            notes=(f"lat/long source: {doi}:{src} (site-level Lat/Long); {method}; AmeriFlux EBIS site {r['Site']}, "
                   f"{r['Soi_type']}; " + ("Oe+Oa organic horizon" if organic else "mineral soil layer")
                   + f"; sampling time in source: '{r['Date']}' (year {r['Year']}); litter layers excluded")))
    # One AMER plot/layer/year has two analyses: the source's Order number keys the rows.
    return assemble(pd.DataFrame(rows), "TC", extra=["Order"])


def _kholodov(doi: str, src: str, site_text: str) -> pd.DataFrame:
    """Harmonize total carbon of a Kholodov et al. soil-pit table (NGEE Arctic, Seward Peninsula 2016).

    The two packages share one layout: title rows above the header, a units row under it, per-pit local coordinates
    and a single sample depth per row.

    Args:
        doi: The package DOI.
        src: The ESS-DIVE file name of the pit table.
        site_text: Site description for notes.

    Returns:
        The total carbon table in the harmonized layout (common.assemble).

    Examples:
        >>> len(_kholodov("doi:10.5440/1417652", "CN_MM71_Physical_and_Chem_Measurements_2016.csv", "Council"))  # doctest: +SKIP
        5
    """
    lines = _text(doi, src).split("\n")
    skip = next(i for i, l in enumerate(lines) if l.startswith("Region,"))  # title rows above the header
    d = read_csv(doi, src, skiprows=skip).iloc[1:]  # first row after the header holds units
    d = d[~is_missing(d["total_carbon"])]
    pit = "Sampling_site" if "Sampling_site" in d.columns else "Samping_site"
    method = {"SOIL 0.20": "soil calibration", "090219 PLNT-1": "plant calibration"}
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Site"] + ":" + d[pit] + ":" + d["sample_ID"],
        "id_type": f"Site:{pit}:sample_ID", "depth": d["sample_depth"], "date": d["Observation_date"],
        "TC": d["total_carbon"], "tc_method": UNKNOWN, "latitude": d["local_latitude"], "longitude": d["local_longitude"],
        "notes": [(f"lat/long source: {doi}:{src} (per-pit local_latitude/local_longitude); total_carbon (wt. %), "
                   f"analyzer run label 'TC Method' = '{m}' ({method.get(m, 'run label')}), instrument not stated; depth is "
                   f"a single sample depth (cm) as reported, not an interval; {l} layer; {site_text}")
                  for m, l in zip(d["TC Method"], d["model_layer_description"])],
    })
    return assemble(out, "TC")


def c_1342956() -> pd.DataFrame:
    """Harmonize total carbon of doi:10.5440/1342956.

    Package: Soil Physical, Chemical, and Thermal Characterization, Teller Road Site, Seward Peninsula, Alaska,
    2016.

    Source files: TL_MM27_Physical and Chem_Measurements_2016.csv.

    Location: TL_MM27_Physical and Chem_Measurements_2016.csv (per-pit local_latitude/local_longitude).

    Methods: unknown.

    Returns:
        The total carbon table in the harmonized layout (common.assemble).

    Examples:
        >>> len(c_1342956())  # doctest: +SKIP
        30
    """
    return _kholodov("doi:10.5440/1342956", "TL_MM27_Physical and Chem_Measurements_2016.csv",
                     "NGEE Arctic Teller MM27 soil pits, September 2016")


def c_1417652() -> pd.DataFrame:
    """Harmonize total carbon of doi:10.5440/1417652.

    Package: Soil Physical, Chemical, and Thermal Characterization, Council Road Site, Seward Peninsula, Alaska,
    2016.

    Source files: CN_MM71_Physical_and_Chem_Measurements_2016.csv.

    Location: CN_MM71_Physical_and_Chem_Measurements_2016.csv (per-pit local_latitude/local_longitude).

    Methods: unknown.

    Returns:
        The total carbon table in the harmonized layout (common.assemble).

    Examples:
        >>> len(c_1417652())  # doctest: +SKIP
        5
    """
    return _kholodov("doi:10.5440/1417652", "CN_MM71_Physical_and_Chem_Measurements_2016.csv",
                     "NGEE Arctic Council MM71 soil pits, September 2016")


def c_2438343() -> Tables:
    """Harmonize total carbon, soil organic carbon stock of doi:10.15485/2438343.

    Package: Organic layer thickness and carbon concentration in burned and unburned sites, Seward Peninsula, AK,
    2022.

    Source files: Organic_Layer_Tundra_NGEEArctic_data.csv.

    Location: Organic_Layer_Tundra_NGEEArctic_data.csv (per-sample Lat/Long);
    Organic_Layer_Tundra_NGEEArctic_data.csv (per-sample Lat/Long; source longitude is positive, sign corrected to
    west).

    Methods: TC dry_combustion; SOCstock concentration_x_bulk_density_x_thickness.

    Notes:
        - One source row ('Burned _4X_C') lists a positive (east) longitude; every other site is ~164.6 W.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), SOCstock (soil organic carbon
        stock).

    Examples:
        >>> {k: len(t) for k, t in c_2438343().items()}  # doctest: +SKIP
        {'TC': 34, 'SOCstock': 34}
    """
    doi = "doi:10.15485/2438343"
    src = "Organic_Layer_Tundra_NGEEArctic_data.csv"
    d = read_csv(doi, src).iloc[1:]  # first row holds units
    d = d[~is_missing(d["C"])]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Sample_Name"] + ":" + d["Rep"], "id_type": "Sample_Name:Rep",
        "depth": "O", "date": d["Sampling_Date"], "TC": [fmt_tc(v / 10) for v in num(d["C"])],
        # One source row ('Burned _4X_C') lists a positive (east) longitude; every other site is ~164.6 W.
        "tc_method": DRY_COMBUSTION, "latitude": d["Lat"],
        "longitude": [("-" + l.strip().lstrip("-")) for l in d["Long"].str.replace("\xa0", "", regex=False)],
        "notes": [(f"lat/long source: {doi}:{src} (per-sample Lat/Long"
                   + ("; source longitude is positive, sign corrected to west" if not l.strip().replace("\xa0", "").startswith("-") else "")
                   + f"); TC converted from C {c} g/kg to % (/10); "
                   "elemental C by dry combustion, Elementar UNICUBE, air-dried ground organic layer (package methods); "
                   f"whole organic layer (mean thickness {t} cm); fire history: {f}, burned {n} time(s) (wildfire, field "
                   "condition, not a treatment)")
                  for l, c, t, f, n in zip(d["Long"], d["C"], d["OL_Depth_M"], d["Fire_h"], d["Times_Burned"])],
    })
    base = out.drop(columns=["TC", "tc_method", "notes"])
    stock = emit(base, "SOCstock", [fmt_tc(v / 1000) for v in num(d["C_Stock"])], STOCK_CALC,
                 [(f"lat/long source: {doi}:{src} (per-sample Lat/Long); C_Stock {s_} converted from g C m-2 to kg C m-2 "
                   "(/1000; units row says g kg-1, but C x bulk density x thickness reproduces the values in g m-2); "
                   f"stock of the whole organic layer (depth 'O', mean thickness {t} cm), C by dry combustion (Elementar "
                   f"UNICUBE); fire history: {f}, burned {n} time(s)")
                  for s_, t, f, n in zip(d["C_Stock"], d["OL_Depth_M"], d["Fire_h"], d["Times_Burned"])])
    return {"TC": assemble(out, "TC"), "SOCstock": stock}


def c_1630815() -> Tables:
    """Harmonize carbon variables of doi:10.15485/1630815.

    Package: Trace Metal Content and Speciation, Water and Soil Chemistry, and Methane Production for a Wetland in
    Missouri (September 2015) and in Florida (January 2016)

    Source files: ExtendedDataTable2.csv.

    Location: ExtendedDataTable2.csv (table header, DMS WGS84 per location).

    Methods: TC dry_combustion; SOC TC_minus_TIC; SIC acidification.

    Notes:
        - "Missouri"/"Florida" rows: DMS coordinates of locations A, B, C in columns 1, 3, 5.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), SOC (soil organic carbon), SIC
        (soil inorganic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_1630815().items()}  # doctest: +SKIP
        {'TC': 6, 'SOC': 3, 'SIC': 3}
    """
    doi = "doi:10.15485/1630815"
    src = "ExtendedDataTable2.csv"
    t = read_csv(doi, src, header=None)
    coords = {}
    for i in (5, 6):  # "Missouri"/"Florida" rows: DMS coordinates of locations A, B, C in columns 1, 3, 5
        for loc, j in zip("ABC", (1, 3, 5)):
            lat, lon = re.findall(r"[^NS]+[NS]|[^EW]+[EW]", str(t.iat[i, j]).replace("\ufffd", "d"))[:2]
            coords[(t.iat[i, 0], loc)] = (round(dms_to_decimal(lat), 6), round(dms_to_decimal(lon), 6))
    row = t[t[0].str.startswith("Total Carbon")].iloc[0]
    rows: list[dict[str, Any]] = []
    other: dict[str, list[dict[str, Any]]] = {"SOC": [], "SIC": []}
    rowx = {"SOC": t[t[0].str.startswith("Total Organic Carbon")].iloc[0],
            "SIC": t[t[0].str.startswith("Total Inorganic Carbon")].iloc[0]}
    for site, cols, date in [("Missouri", (1, 2, 3), "2015-09"), ("Florida", (7, 8, 9), "2016-01")]:
        for loc, j in zip("ABC", cols):
            lat, lon = coords[(site, loc)]
            rows.append(dict(
                doi=doi, source_file=src, id=f"{site}:{loc}", id_type="Field Site:Location", depth="",
                date=date, TC=row[j], tc_method=DRY_COMBUSTION, latitude=lat, longitude=lon,
                notes=(f"lat/long source: {doi}:{src} (table header, DMS WGS84 per location); Total Carbon (wt.%) by "
                       "Shimadzu TOC-L with SSM-5000A solid sample combustion unit (package methods); one value per "
                       "sampling location; triplicate ~15 cm piston cores extruded in 5 cm increments, but the depth "
                       f"interval of the tabulated value is not stated (depth left blank); {site} wetland "
                       + ("(Marais Temps Clair Conservation Area)" if site == "Missouri" else
                          "(University of Central Florida Arboretum)"))))
            for var, lab, m in [("SOC", "Total Organic Carbon", TC_MINUS_TIC), ("SIC", "Total Inorganic Carbon", ACIDIFICATION)]:
                other[var].append(dict(
                    doi=doi, source_file=src, id=f"{site}:{loc}", id_type="Field Site:Location", depth="", date=date,
                    value=rowx[var][j], method=m, latitude=lat, longitude=lon,
                    notes=(f"lat/long source: {doi}:{src} (table header, DMS WGS84 per location); {lab} (wt.%) by "
                           "Shimadzu TOC-L with SSM-5000A solid sample unit (package methods; TOC as TC minus TIC); one "
                           f"value per sampling location, depth interval not stated; {site} wetland")))
    return {"TC": assemble(pd.DataFrame(rows), "TC"), "SOC": assemble(pd.DataFrame(other["SOC"]), "SOC"),
            "SIC": assemble(pd.DataFrame(other["SIC"]), "SIC")}


# ----------------------------------------------------------------------------------------------------
# Packages added for the other carbon variables
# ----------------------------------------------------------------------------------------------------

def c_2274949() -> dict:
    """Harmonize carbon variables of doi:10.25581/ORNLSFA.031/2274949.

    Package: Interrelationships among methods of estimating microbial biomass across multiple soil orders and
    biomes: Supporting data.

    Source files: TESSFA_SMB_proxy.csv.

    Location: TESSFA_SMB_proxy.csv (approximate site Latitude/Longitude per data dictionary).

    Methods: TC dry_combustion; SOC acid_treated_combustion; SIC TC_minus_TOC; DOC salt_extraction.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), SOC (soil organic carbon), SIC
        (soil inorganic carbon), DOC (dissolved organic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_2274949().items()}  # doctest: +SKIP
        {'TC': 31, 'SOC': 31, 'SIC': 31, 'DOC': 33}
    """
    doi = "doi:10.25581/ORNLSFA.031/2274949"
    src = "TESSFA_SMB_proxy.csv"
    d = strip_bom(read_csv(doi, src))
    keys = ["Site_Id", "Site_location", "Soil_horizon"]
    base = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": d["Soil_horizon"], "date": "2012/2013",
        "latitude": d["Latitude"].astype(float).round(6), "longitude": d["Longitude"].astype(float).round(6),
    })
    loc = (f"lat/long source: {doi}:{src} (approximate site Latitude/Longitude per data dictionary); ")
    tail = [(f"; depth given only as soil horizon '{h}'; soil order {o}; date: samples processed 2012-2013, collection "
             "dates not reported; one composite sample per site and horizon") for h, o in zip(d["Soil_horizon"], d["Soil_order"])]
    lec = "Leco combustion analyzer (data dictionary)"
    return {
        "TC": emit(base, "TC", d["Bulk_soil_C"], DRY_COMBUSTION, [loc + f"Bulk_soil_C: total C by {lec}" + t for t in tail]),
        "SOC": emit(base, "SOC", d["TOC"], ACID_COMBUSTION,
                    [loc + f"TOC: total C by {lec} after acid treatment" + t for t in tail]),
        "SIC": emit(base, "SIC", d["TIC"], TC_MINUS_TOC, [loc + "TIC = Bulk_soil_C - TOC (data dictionary)" + t for t in tail]),
        "DOC": emit(base, "DOC", d["DOC_mean"], SALT_EXTRACTION,
                    [loc + "DOC_mean: unfumigated K2SO4-extractable organic C, ug C g-1 dry soil (= mg C kg-1), mean of 3 "
                     "subsamples (data dictionary)" + t for t in tail],
                    DOC_unit="mg C kg-1 dry soil", DOC_medium="K2SO4 extract, unfumigated"),
    }


def c_1164833() -> dict:
    """Harmonize dissolved organic carbon of doi:10.5440/1164833.

    Package: Microtopographic and Depth Controls on Active Layer Chemistry in Arctic Polygonal Ground: Supporting
    Data.

    Source files: NGA011_Microtopographic_Supporting_Data.csv.

    Location: NGA011_Microtopographic_Supporting_Data.csv (per-sample Latitude/Longitude).

    Methods: DOC porewater.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): DOC (dissolved organic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_1164833().items()}  # doctest: +SKIP
        {'DOC': 25}
    """
    doi = "doi:10.5440/1164833"
    src = "NGA011_Microtopographic_Supporting_Data.csv"
    d = read_csv(doi, src).iloc[1:]  # first row holds units
    d = d[d["Method"].isin(["DP", "Wick", "Rhiz"]) & ~is_missing(d["DOC"])]  # porewater samplers; surface water excluded
    sampler = {"DP": "drive-point piezometer", "Wick": "wick sampler", "Rhiz": "rhizon sampler"}
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Sample_ID"], "id_type": "Sample_ID", "depth": d["Depth"],
        "date": pd.to_datetime(d["Date_sampled"], format="%m/%d/%Y").dt.strftime("%Y-%m-%d"), "value": d["DOC"],
        "method": POREWATER, "DOC_unit": "mg C L-1", "DOC_medium": [f"active-layer porewater ({sampler[m]})" for m in d["Method"]],
        "latitude": d["Latitude"], "longitude": d["Longitude"],
        "notes": [(f"lat/long source: {doi}:{src} (per-sample Latitude/Longitude); DOC (mg L-1) of active-layer porewater "
                   f"collected with a {sampler[m]}; depth is the sampling depth (cm) as reported; {p}, {l}; surface-water "
                   "samples excluded") for m, p, l in zip(d["Method"], d["Polygonal"], d["Location"])],
    })
    return {"DOC": assemble(out, "DOC")}


def c_1226245() -> dict:
    """Harmonize dissolved organic carbon of doi:10.5440/1226245.

    Package: Surface and Active Layer Pore Water Chemistry from Ice Wedge Polygons, Utqiagvik (Barrow), Alaska,
    2013-2014.

    Source files: BGC_BarrowWaterChemistry_2013_2014_v1.csv.

    Location: BGC_BarrowWaterChemistry_2013_2014_v1.csv (per-sample Latitude/Longitude).

    Methods: DOC porewater.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): DOC (dissolved organic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_1226245().items()}  # doctest: +SKIP
        {'DOC': 46}
    """
    doi = "doi:10.5440/1226245"
    src = "BGC_BarrowWaterChemistry_2013_2014_v1.csv"
    d = read_csv(doi, src, skiprows=8).iloc[1:]  # metadata block, header, units row
    pw = ~d["Collection_type"].isin(["surface water", "", "none"])
    d = d[pw & ~is_missing(d["Dissolved_organic_C"])]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Sample_ID"], "id_type": "Sample_ID", "depth": d["Sample_depth_max"],
        "date": d["Sampling_date"], "value": d["Dissolved_organic_C"], "method": POREWATER, "DOC_unit": "mg C L-1",
        "DOC_medium": "active-layer porewater (" + d["Collection_type"] + ")",
        "latitude": d["Latitude"], "longitude": d["Longitude"],
        "notes": [(f"lat/long source: {doi}:{src} (per-sample Latitude/Longitude); Dissolved_organic_C (mg L-1) of "
                   f"active-layer porewater ({c}); depth = Sample_depth_max (cm), '{z.strip()}' depth class; {p} polygon, "
                   f"{m}; surface-water samples excluded") for c, z, p, m in
                  zip(d["Collection_type"], d["Depth_designation"], d["Polygon_type"], d["Microtopography"])],
    })
    return {"DOC": assemble(out, "DOC")}


def c_2566016() -> dict:
    """Harmonize total carbon, loss on ignition of doi:10.15485/2566016.

    Package: Changuinola peat soil characteristics and gas emission raw data October 2019.

    Source files: Hedgpethetal_2025_rawdata.csv.

    Location: Hedgpethetal_2025_rawdata.csv (site Site_Lat/Site_Long).

    Methods: TC unknown; LOI loss_on_ignition.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), LOI (loss on ignition).

    Examples:
        >>> {k: len(t) for k, t in c_2566016().items()}  # doctest: +SKIP
        {'TC': 16, 'LOI': 16}
    """
    doi = "doi:10.15485/2566016"
    src = "Hedgpethetal_2025_rawdata.csv"
    d = read_csv(doi, src)
    base = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Site_Name"] + ":" + d["Depth"], "id_type": "Site_Name:Depth",
        "depth": [depth_range(float(z) - 5, float(z) + 5) for z in d["Depth"]], "date": "2019-10",
        "latitude": d["Site_Lat"], "longitude": d["Site_Long"],
    })
    tail = [(f"; depth {z} +/- 5 cm per package methods; Changuinola peat deposit, Panama, {s} site; sampled October 2019")
            for z, s in zip(d["Depth"], d["Site_Name"])]
    loc = f"lat/long source: {doi}:{src} (site Site_Lat/Site_Long); "
    loi = num(d["Bulk_Peat_LOI"])
    return {
        "TC": emit(base, "TC", d["Bulk_Peat_%C"], UNKNOWN, [loc + "Bulk_Peat_%C of bulk peat, instrument not stated" + t for t in tail]),
        "LOI": emit(base, "LOI", d["Bulk_Peat_LOI"], LOI_METHOD,
                    [loc + "Bulk_Peat_LOI (%), ignition temperature not stated" + (" (value above 100% in source)" if v > 100 else "")
                     + t for v, t in zip(loi, tail)]),
    }


def c_2587411() -> dict:
    """Harmonize soil organic matter of doi:10.15485/2587411.

    Package: Soil Texture and Organic Matter from Teller Field Site and Barrow Environmental Observatory, Alaska,
    2024.

    Source files: NGA574_data.csv.

    Location: NGA574_data.csv (per-core Latitude/Longitude).

    Methods: SOM loss_on_ignition.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): SOM (soil organic matter).

    Examples:
        >>> {k: len(t) for k, t in c_2587411().items()}  # doctest: +SKIP
        {'SOM': 52}
    """
    doi = "doi:10.15485/2587411"
    src = "NGA574_data.csv"
    d = read_csv(doi, src)
    d = d[~is_missing(d["Perc_Organic_Matter"])]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Site"] + ":" + d["Core_ID"] + ":" + d["Field_ID"],
        "id_type": "Site:Core_ID:Field_ID", "depth": [depth_range(a, b) for a, b in zip(d["Depth_start"], d["Depth_end"])],
        "date": d["Date_collected"], "value": d["Perc_Organic_Matter"], "method": LOI_METHOD,
        "latitude": d["Latitude"], "longitude": d["Longitude"],
        "notes": (f"lat/long source: {doi}:{src} (per-core Latitude/Longitude); Perc_Organic_Matter by loss on ignition, "
                  "Desert Research Institute Soil Characterization and Quaternary Pedology Laboratory (package methods); "
                  "NGEE Arctic Teller 27 / Barrow Environmental Observatory, August 2024"),
    })
    return {"SOM": assemble(out, "SOM")}


def c_1894515() -> dict:
    """Harmonize carbon variables of doi:10.15485/1894515.

    Package: Soil organic matter, tree communities, and fungal communities across mycorrhizal gradients in the
    Eastern United States.

    Source files: Soil_Data_Final.csv.

    Location: Soil_Data_Final.csv (per-plot GPS_North/GPS_West, west longitude written as negative).

    Methods: TC unknown; POMC density_fractionation; MAOMC density_fractionation.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), POMC (particulate organic
        matter carbon), MAOMC (mineral-associated organic matter carbon).

    Examples:
        >>> {k: len(t) for k, t in c_1894515().items()}  # doctest: +SKIP
        {'TC': 38, 'POMC': 38, 'MAOMC': 38}
    """
    doi = "doi:10.15485/1894515"
    src = "Soil_Data_Final.csv"
    d = read_csv(doi, src)
    base = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["State"] + ":" + d["Site"], "id_type": "State:Site", "depth": "0-10",
        "date": "2017", "latitude": d["GPS_North"], "longitude": [f"-{v.lstrip('-')}" for v in d["GPS_West"]],
    })
    loc = f"lat/long source: {doi}:{src} (per-plot GPS_North/GPS_West, west longitude written as negative); "
    tail = ("; top 10 cm of mineral soil after removing the O horizon (package methods); density fractionation in "
            "1.7 g cm-3 sodium polytungstate; sampled 2017 (no day given)")
    return {
        "TC": emit(base, "TC", d["perC"], UNKNOWN, loc + "perC = %C of bulk soil, instrument not stated" + tail),
        "POMC": emit(base, "POMC", [fmt_tc(v * 1000) for v in num(d["gC.LF.gsoil"])], DENSITY_FRACTIONATION,
                     loc + "gC.LF.gsoil (g C in free + occluded light fraction per g soil) x1000 = g C kg-1 soil" + tail),
        "MAOMC": emit(base, "MAOMC", [fmt_tc(v * 1000) for v in num(d["gC HF.gsoil"])], DENSITY_FRACTIONATION,
                      loc + "gC HF.gsoil (g C in heavy fraction per g soil) x1000 = g C kg-1 soil" + tail),
    }


def c_2455027() -> dict:
    """Harmonize water-extractable organic carbon of doi:10.15485/2455027.

    Package: Aqueous Organic Matter from Kougarok Fire Complex, Alaska, 2023.

    Source files: Organic_Layer_Tundra_Chemistry_NGEEArctic_data.csv.

    Location: Organic_Layer_Tundra_Chemistry_NGEEArctic_data.csv (per-sample Lat/Long).

    Methods: WEOC water_extraction.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): WEOC (water-extractable organic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_2455027().items()}  # doctest: +SKIP
        {'WEOC': 18}
    """
    doi = "doi:10.15485/2455027"
    src = "Organic_Layer_Tundra_Chemistry_NGEEArctic_data.csv"
    d = strip_bom(read_csv(doi, src)).iloc[1:]  # first row holds units
    d = d[~is_missing(d["DOC"])]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Sample_Name"] + ":" + d["Rep"], "id_type": "Sample_Name:Rep",
        "depth": "O", "date": "2023-06/2023-07", "value": [fmt_tc(v * 1000) for v in num(d["DOC"])],
        "method": WATER_EXTRACTION, "latitude": d["Lat"], "longitude": d["Long"],
        "notes": [(f"lat/long source: {doi}:{src} (per-sample Lat/Long); DOC {c} mg C g-1 organic layer leached in water "
                   f"x1000 = mg C kg-1 (water leachate of {m} g organic layer held at {t} C; TOC_leachate {l} mg L-1); "
                   f"whole organic layer; fire history {f}; date from package temporal coverage")
                  for c, m, t, l, f in zip(d["DOC"], d["OL_Inc_Mass"], d["Store_Inc_Temp"], d["TOC_leachate"], d["Fire_h"])],
    })
    return {"WEOC": assemble(out, "WEOC")}


def c_2407117() -> dict:
    """Harmonize soil organic carbon stock of doi:10.15485/2407117.

    Package: Soil carbon, nitrogen, and ice content data (2014-2018) at Happy Valley and Sagwon Hills in Northern
    Alaska, United States.

    Source files: stocks_by_core.csv.

    Location: stocks_by_core.csv (per-core latitude_dd/longitude_dd).

    Methods: SOCstock concentration_x_bulk_density_x_thickness.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): SOCstock (soil organic carbon stock).

    Examples:
        >>> {k: len(t) for k, t in c_2407117().items()}  # doctest: +SKIP
        {'SOCstock': 227}
    """
    doi = "doi:10.15485/2407117"
    src = "stocks_by_core.csv"
    d = read_csv(doi, src)
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["location"] + ":" + d["hillslope_position"] + ":" + d["id"],
        "id_type": "location:hillslope_position:id", "depth": "0-" + d["depth_cm"], "date": "2014-07/2018-07",
        "value": d["c_stocks_kgC_m-2"], "method": STOCK_CALC, "latitude": d["latitude_dd"], "longitude": d["longitude_dd"],
        "notes": [(f"lat/long source: {doi}:{src} (per-core latitude_dd/longitude_dd); c_stocks_kgC_m-2 = cumulative C stock "
                   f"from the surface to {z} cm; soil pit or trench cores, {h} position, {sg}; date from package temporal "
                   "coverage (2014-2018, per-core date not given)") for z, h, sg in
                  zip(d["depth_cm"], d["hillslope_position"], d["subgroup"])],
    })
    return {"SOCstock": assemble(out, "SOCstock")}


# ====================================================================================================
# Packages
# ====================================================================================================

PACKAGES = [
    ("doi:10.15485/1725884", combine(("pH", ph_1725884), ("TC", c_1725884)), ('pH', 'TC', 'SOC', 'SOM', 'SIC', 'WEOC')),
    ("doi:10.5440/1854940", combine(("TC", c_1854940)), ('TC', 'SOC')),
    ("doi:10.15485/3367449", combine(("pH", ph_3367449), ("TC", c_3367449)), ('pH', 'TC', 'DOC', 'SOC', 'SIC', 'LOI')),
    ("doi:10.25581/ORNLSFA.020/1638590", combine(("TC", c_1638590)), ('TC',)),
    ("doi:10.5440/1342956", combine(("TC", c_1342956)), ('TC',)),
    ("doi:10.5440/1417652", combine(("TC", c_1417652)), ('TC',)),
    ("doi:10.15485/2438343", combine(("TC", c_2438343)), ('TC', 'SOCstock')),
    ("doi:10.15485/1630815", combine(("TC", c_1630815)), ('TC', 'SOC', 'SIC')),
    ("doi:10.25581/ORNLSFA.031/2274949", combine(("pH", ph_2274949), ("TC", c_2274949)), ('pH', 'TC', 'DOC', 'SOC', 'SIC')),
    ("doi:10.5440/1164833", combine(("TC", c_1164833)), ('DOC',)),
    ("doi:10.5440/1226245", combine(("TC", c_1226245)), ('DOC',)),
    ("doi:10.15485/2566016", combine(("TC", c_2566016)), ('TC', 'LOI')),
    ("doi:10.15485/2587411", combine(("TC", c_2587411)), ('SOM',)),
    ("doi:10.15485/1894515", combine(("TC", c_1894515)), ('TC', 'POMC', 'MAOMC')),
    ("doi:10.15485/2455027", combine(("TC", c_2455027)), ('WEOC',)),
    ("doi:10.15485/2407117", combine(("TC", c_2407117)), ('SOCstock',)),
    ("doi:10.15485/1577267", combine(("pH", ph_1577267)), ('pH',)),
    ("doi:10.5440/1785119", combine(("pH", ph_1785119)), ('pH',)),
    ("doi:10.15485/2572883", combine(("pH", ph_2572883)), ('pH',)),
    ("doi:10.5440/1185213", combine(("pH", ph_1185213)), ('pH',)),
]
