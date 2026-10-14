"""Harmonize the hand-written packages of Group 3: coordinates are joined from another table, KML file or package by a site / plot / core key.

The soil pH functions (ph_<id>) were copied from notebooks/harmonize_ph and the carbon functions (c_<id>) from
notebooks/harmonize_carbon, unchanged apart from the assemble() signature. PACKAGES combines them into one function
per package that returns {variable key: harmonized table}.

Packages:
    doi:10.15485/1874586               [pH+carbon] Chacon et al., PARCHED Panama 2020  (plot KML from doi:10.15485/3377028)
    doi:10.15485/1959350               [pH+carbon] Johnson et al., Wood Buffalo burn experiment 2019 (control cores; site table)
    doi:10.15485/2438579               [pH+carbon] Wood Buffalo burn experiment 2022 (control cores; site table)
    doi:10.15485/2283432               [pH+carbon] Martinez et al., Campinas Ferralsols 2017 (site_info.csv)
    doi:10.15485/2283436               [pH+carbon] Finstad et al., oil palm / forest profiles 2011 (profile locations)
    doi:10.15485/1631979               [carbon] East River meander-bound floodplains G, L, Z 2015-2016 (sampling-site table)
    doi:10.15485/1839189               [carbon] East River Meander Z and Y floodplain sediments 2017 (locations_meta data.csv)
    doi:10.15485/2350837               [carbon] Kougarok Fire Complex soil C and N 2022 (field observation table)
    doi:10.21952/WTR/1506944           [carbon] Kenwell et al., East River floodplain soils 2014-2015 (Coordinates sheet)
    doi:10.5440/1464956                [carbon] Ladd et al., Barrow LCP/HCP organic horizons 2014 (area points from doi:10.5440/1618325)
    doi:10.15485/1910300               [carbon]
    doi:10.21952/WTR/1572186           [carbon]
    doi:10.5440/1440029                [carbon]
    doi:10.5440/1841590                [pH+carbon] NGEE Arctic soil acid-base titration (titration-file coordinates)
    doi:10.5440/1346200                [pH+carbon] Salmon et al., Kougarok soil cores 2016  (plot waypoints from doi:10.5440/1346196)
    doi:10.15485/1602783               [carbon]
    doi:10.15485/1962817               [pH] Northeastern US tree species plots (sitelats.csv)
    doi:10.15485/1994876               [pH] Anderson et al., East River Meander C sediments 2017 (sample_metadata.xlsx)
    doi:10.15485/3025240               [pH] Marmolejo-Cossio et al., East River moraine pits (Table_1)

Attributes:
    PACKAGES: (DOI, package function, variables) per package; the package function combines the pH and carbon
        functions (extract.combine).
"""

from __future__ import annotations

from collections.abc import Iterable
import io
import re
from typing import Any, cast

import pandas as pd  # noqa: F401

from ..common import *  # noqa: F401,F403
from ..common import _text  # noqa: F401
from ..extract import Col, combine, from_columns, from_long, make_base, merge_tables  # noqa: F401
from ..datatypes import Tables


# ====================================================================================================
# Soil pH (from notebooks/harmonize_ph/group3_joined_coords.py)
# ====================================================================================================


def _read_cr_csv(doi: str, name: str, **kw: Any) -> pd.DataFrame:
    """Read a CSV file that may use old Mac line endings (CR only), every cell as text.

    Args:
        doi: The package DOI.
        name: The ESS-DIVE file name.
        **kw: Passed to pandas.read_csv (dtype=str and keep_default_na=False by default).

    Returns:
        The table.
    """
    text = raw_path(doi, name).read_bytes().decode("utf-8-sig", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
    kw.setdefault("dtype", str)
    kw.setdefault("keep_default_na", False)
    return pd.read_csv(io.StringIO(text), **kw)


def ph_1874586() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/1874586.

    Package: 16S and ITS Amplicon Sequencing Fastq files and metadata from PARCHED Panama Tropical Forest soils,
    2019-2020.

    Source files: Field_PARCHED_Metadata_2020.csv, PARCHED_field_sites.kml.

    Location: doi:10.15485/3377028:PARCHED_field_sites.kml, placemark ...; package metadata (Gigante site point).

    Methods: pH_H2O.

    Notes:
        - Plot placemarks "Site Name (CODE) PLOT" in the KML shipped with doi:10.15485/3377028.
        - The KML has no 7C placemark; its "7E" label sits among the controls (odd plots are controls).
        - GIG 8E: no placemark; Gigante site point from the package metadata.
        - depth_cat is used because the source "depth" column says 10 for every row.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_1874586())  # doctest: +SKIP
        50
    """
    r: Any  # one source row (itertuples / to_dict record): cell types are not known statically
    doi = "doi:10.15485/1874586"
    src = "Field_PARCHED_Metadata_2020.csv"
    d = strip_bom(read_csv(doi, src))
    d = d[~is_missing(d["pH"])]
    # Plot placemarks "Site Name (CODE) PLOT" in the KML shipped with doi:10.15485/3377028.
    kml = raw_path("doi:10.15485/3377028", "PARCHED_field_sites.kml").read_text()
    marks = {}
    for pm in re.findall(r"<Placemark.*?</Placemark>", kml, re.S):
        name = must_match(r"<name>(.*?)</name>", pm).group(1)
        lon, lat = must_match(r"<coordinates>\s*([-\d.]+),([-\d.]+)", pm).groups()
        code, plot = must_match(r"\((\w+)\)\s+(\w+)$", name).groups()
        marks[(code, plot)] = (name, float(lat), float(lon))
    method = ("pH_H2O: 8.0 +/- 1.0 g soil in 40 mL DI water (~1:5), settled ~30 min, pH of slurry measured (Mettler "
              "Toledo SevenCompact S220); composite of six 2.54 cm cores per plot and depth pooled into two composites "
              "(where both replicates i and ii are listed, they share one pH value)")
    rows = []
    for r in d.itertuples(index=False):
        site, plot, trt, cat = r.Site, r.plot, r.Treatment, r.depth_cat
        if (site, plot) in marks:
            name, lat, lon = marks[(site, plot)]
            loc = f"lat/long source: doi:10.15485/3377028:PARCHED_field_sites.kml, placemark '{name}'"
        elif site == "GIG" and plot == "7C":
            # The KML has no 7C placemark; its "7E" label sits among the controls (odd plots are controls).
            name, lat, lon = marks[("GIG", "7E")]
            loc = (f"lat/long source: doi:10.15485/3377028:PARCHED_field_sites.kml, placemark '{name}'; KML label 7E "
                   "assumed to be plot 7C (odd plots are controls; no 7C placemark exists)")
        else:  # GIG 8E: no placemark; Gigante site point from the package metadata
            lat, lon = 9.09919, -79.854
            loc = ("lat/long source: doi:10.15485/1874586 package metadata (Gigante site point); no GIG 8E placemark in "
                   "doi:10.15485/3377028:PARCHED_field_sites.kml; Gigante site point from doi:10.15485/1874586 package "
                   "metadata used")
        # depth_cat is used because the source "depth" column says 10 for every row.
        if cat == "twenty":
            depth = "10-20"
            dnote = ("depth 10-20 from depth_cat 'twenty' in source; source depth column says 10 for all rows and no 0-10 "
                     "rows exist for GIG exclusion plots in 2020, so depth may be mislabeled")
        else:
            depth = "0-10"
            dnote = "depth 0-10 from depth_cat 'ten' in source (source depth column reports 10)"
        note = f"{loc}; {method}; {dnote}" + ("; throughfall exclusion (drought) plot" if trt == "exclusion" else "")
        rows.append(dict(doi=doi, source_file=src, id=f"{r.sample_id}:{r.rainfall_grad}:{site}:{plot}:{r.replicate}:{trt}",
                         id_type="sample_id:rainfall_grad:Site:plot:replicate:Treatment", depth=depth, date="2020-01",
                         pH=r.pH, ph_method="pH_H2O", latitude=lat, longitude=lon, notes=note))
    return assemble(pd.DataFrame(rows), "pH", raw=True)


def ph_1346200() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.5440/1346200.

    Package: NGEE Arctic Plant Traits: Soil Cores, Kougarok Road Mile Marker 64, Seward Peninsula, Alaska, 2016.

    Source files: NGEEArctic_Kougarok2016_SoilCoreData_v1.csv,
    NGEE_Arctic_Kougarok_2016_GPSwaypoints_Ecotypes_v1.csv.

    Location: doi:10.5440/1346196:NGEE_Arctic_Kougarok_2016_GPSwaypoints_Ecotypes_v1.csv (vegetation plot ...).

    Methods: pH_H2O.

    Notes:
        - Vegetation plot coordinates from doi:10.5440/1346196 (column ID = PlotID).
        - Soil file writes "TTWBT-1" where the waypoint file has "TT-WBT-1".

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_1346200())  # doctest: +SKIP
        63
    """
    doi = "doi:10.5440/1346200"
    src = "NGEEArctic_Kougarok2016_SoilCoreData_v1.csv"
    d = read_csv(doi, src, skiprows=6, encoding="latin1")
    d = d[~is_missing(d["pH"])]
    # Vegetation plot coordinates from doi:10.5440/1346196 (column ID = PlotID).
    w = read_csv("doi:10.5440/1346196", "NGEE_Arctic_Kougarok_2016_GPSwaypoints_Ecotypes_v1.csv", skiprows=6, encoding="latin1")
    pts = {r.ID: (r.latitude, r.longitude) for r in w.itertuples()}
    # Soil file writes "TTWBT-1" where the waypoint file has "TT-WBT-1".
    wp = {p: p if p in pts else p.replace("TTWBT", "TT-WBT") for p in d["PlotID"].unique()}
    match = {p: f"; soil file PlotID '{p}' matched to '{q}', differs only by hyphen" if p != q else "" for p, q in wp.items()}
    ratio = {"organic": "~1:10", "mineral": "~1:5"}
    keys = ["PlotID", "CoreRep", "Horizon_TextureBased"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": [depth_range(a, b) for a, b in zip(d["DepthTop_cm"], d["DepthBottom_cm"])],
        "date": "2016-07-25/2016-07-27", "pH": d["pH"], "ph_method": "pH_H2O",
        "latitude": d["PlotID"].map(lambda p: pts[wp[p]][0]), "longitude": d["PlotID"].map(lambda p: pts[wp[p]][1]),
        "notes": [(f"lat/long source: doi:10.5440/1346196:NGEE_Arctic_Kougarok_2016_GPSwaypoints_Ecotypes_v1.csv "
                   f"(vegetation plot '{wp[p]}'{match[p]}); pH in {ratio[h]} wet soil:DI water (w:w), {h} horizon, fresh root-free soil, "
                   f"read after 5 min (user guide PDF); {e}; sampled 25-27 July 2016 (no per-core date)")
                  for p, h, e in zip(d["PlotID"], d["Horizon_TextureBased"], d["Ecotype"])],
    })
    return assemble(out, "pH", raw=True)


def ph_1959350() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/1959350.

    Package: Impact of burning on soil properties and respiration; Wood Buffalo National Park, Canada; June 2019.

    Source files: all_sample_metadata.csv, sampling_site_characteristics.csv.

    Location: sampling_site_characteristics.csv (site-level; all cores at a site share one point).

    Methods: pH_CaCl2.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_1959350())  # doctest: +SKIP
        150
    """
    doi = "doi:10.15485/1959350"
    src = "all_sample_metadata.csv"
    d = strip_bom(read_csv(doi, src))
    d = d[(d["burn.trtmt"] == "control") & ~is_missing(d["pH"])].copy()  # unburned control cores only
    site = strip_bom(read_csv(doi, "sampling_site_characteristics.csv")).drop_duplicates("Site")
    pts = dict(zip(site["Site"], zip(site["Latitude,N,18,8"], site["Longitude,N,18,8"])))
    n_rows = d.groupby("core.id.hor")["Full.id"].transform("size")
    notes = []
    for hor, ch, n, sp in zip(d["horizon"], d["core.id.hor"], n_rows, d["Leading.Species"]):
        if hor == "O":
            ratio = "0.1 M CaCl2, 1:5 soil:solution, supernatant pH (per Johnson et al. 2023 SI; ESS-DIVE methods list 1:1 for organic, likely swapped)"
        else:
            ratio = "0.1 M CaCl2, 1:1 soil:solution, supernatant pH (per Johnson et al. 2023 SI; ESS-DIVE methods list 1:5 for mineral, likely swapped)"
        notes.append("lat/long source: doi:10.15485/1959350:sampling_site_characteristics.csv (site-level; all cores at a "
                     f"site share one point); {ratio}; unburned control core from lab burn experiment; {sp.replace('_', ' ')}; "
                     f"pH measured once per core-horizon ({ch}) and repeated across its {n} incubation/DNA rows; sampled "
                     "June 2019 (no exact day in source)")
    keys = ["Full.id", "incub.trtmt", "site", "horizon", "burn.trtmt", "core"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": d["horizon"], "date": "2019-06", "pH": d["pH"], "ph_method": "pH_CaCl2",
        "latitude": d["site"].map(lambda s: pts[s][0]), "longitude": d["site"].map(lambda s: pts[s][1]), "notes": notes,
    })
    return assemble(out, "pH", raw=True)


def ph_2438579() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/2438579.

    Package: Impact of fire on chemical properties and respiration of boreal forest soils.

    Source files: metadata.csv, site_location_and_texture.csv.

    Location: site_location_and_texture.csv (site-level point).

    Methods: pH_CaCl2.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_2438579())  # doctest: +SKIP
        18
    """
    doi = "doi:10.15485/2438579"
    src = "metadata.csv"
    m = read_csv(doi, src)
    s = read_csv(doi, "site_location_and_texture.csv")
    loc = s.drop_duplicates("site").set_index("site")[["location.Y", "location.X"]]
    c = m[(m["burn.trtmt.duration.seconds"] == "0") & ~is_missing(m["pH"])].copy()  # unburned controls only
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": c["sample.id"] + ":" + c["site"] + ":" + c["horizon"] + ":control",
        "id_type": "sample.id:site:horizon:burn.trtmt", "depth": c["horizon"], "date": "2022-06",
        "pH": c["pH"], "ph_method": "pH_CaCl2",
        "latitude": c["site"].map(loc["location.Y"]), "longitude": c["site"].map(loc["location.X"]),
        "notes": [("lat/long source: doi:10.15485/2438579:site_location_and_texture.csv (site-level point); "
                   f"0.1 M CaCl2, {'1:1' if h == 'O' else '1:5'} soil:solution for {'organic' if h == 'O' else 'mineral'} "
                   "horizon per ESS-DIVE methods (note: Johnson et al. 2023 SI for sister package doi:10.15485/1959350 gives "
                   "the opposite ratios); unburned control core (burn duration 0 s) from lab burn experiment, pH measured "
                   f"on O and M subsamples after 48 h at 65% field capacity; {v.replace('_', ' ')}; field collection date not "
                   "given, 2022-06 from package temporal coverage start (2022-06-15); burned cores (30 s, 120 s) excluded")
                  for h, v in zip(c["horizon"], c["vegetation"])],
    })
    return assemble(out.sort_values("id").reset_index(drop=True), "pH", raw=True)


def ph_1962817() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/1962817.

    Package: Mycorrhiza better predict soil fungal community composition and function than aboveground traits in
    temperate forest ecosystems.

    Source files: pH_full.csv, sitelats.csv.

    Location: sitelats.csv (site ...; site-level point, no plot coordinates).

    Methods: pH_H2O.

    Notes:
        - pH-file Location codes vs sitelats.csv site codes (matched by site name in the package metadata).
        - Trailing spaces in Sample and Horizon values.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_1962817())  # doctest: +SKIP
        48
    """
    doi = "doi:10.15485/1962817"
    src = "pH_full.csv"
    d = strip_bom(read_csv(doi, src))
    lat = strip_bom(read_csv(doi, "sitelats.csv")).set_index("site")
    # pH-file Location codes vs sitelats.csv site codes (matched by site name in the package metadata).
    site = {
        "AB": ("AB", "site 'AB', Abies Brook, Norwich VT"),
        "CB": ("CV", "site 'CV', matched to pH-file Location 'CB' via site name Clement Brook in package metadata"),
        "HBR": ("HB", "site 'HB', matched to pH-file Location 'HBR' via site name Hubbard Brook in package metadata"),
        "LP": ("LP", "site 'LP', Long Pond"),
        "RR": ("RM", "site 'RM', matched to pH-file Location 'RR' via site name Roaring Ridge in package metadata"),
    }
    d = d.apply(lambda c: c.str.strip())  # trailing spaces in Sample and Horizon values
    notes = []
    for loc, hz, sp, myc, rep, odep, name in zip(d["Location"], d["Horizon"], d["Species"], d["Mycorrhizal type"],
                                                 d["Replicate"], d["O.horizon.depth"], d["Sample"]):
        if hz == "Mineral":
            hnote = "mineral horizon = top 10 cm of B horizon (below E horizon if present), not measured from the ground surface"
        else:
            hnote = f"organic horizon = Oe+Oa (Oi removed), O horizon thickness {odep} cm"
        notes.append(f"lat/long source: doi:10.15485/1962817:sitelats.csv ({site[loc][1]}; site-level point, no plot "
                     "coordinates); pH method: 1:1 soil:water, dried soil, Mettler Toledo S220, per package methods; "
                     f"{hnote}; under {sp} ({myc}), plot replicate {rep}; sampled snow-free season 2017-2019 (no "
                     f"per-sample date); source sample name '{name}'")
    keys = ["Sample", "Location", "Species", "Horizon", "Replicate"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": d["Horizon"].map({"Mineral": "M", "Organic": "O"}), "date": "2017/2019", "pH": d["pH"],
        "ph_method": "pH_H2O", "latitude": d["Location"].map(lambda l: lat.loc[site[l][0], "Lat"]),
        "longitude": d["Location"].map(lambda l: lat.loc[site[l][0], "Long"]), "notes": notes,
    })
    return assemble(out, "pH", raw=True)


def ph_2283432() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/2283432.

    Package: Organic carbon feedbacks to soil structure in Profundihumic and Haplic Ferralsols in Campinas, Sao
    Paulo, Brazil.

    Source files: Martinez_2023_porosity_roots_chemistry.xlsx, Martinez_2023_site_info.csv.

    Location: Martinez_2023_site_info.csv (site point for Profundihumic Ferralsols (PF); profiles PF1-3 share it,
    individual pit coordinates not given); Martinez_2023_site_info.csv (site point for Haplic Ferralsols (HF);
    profiles HF1-3 share it, individual pit coordinates not given).

    Methods: pH_H2O, pH_KCl.

    Notes:
        - Profile name is written on its first row only.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_2283432())  # doctest: +SKIP
        48
    """
    doi = "doi:10.15485/2283432"
    src = "Martinez_2023_porosity_roots_chemistry.xlsx"
    b = read_excel(doi, src, sheet_name="Bulk_morph_chem", header=None).iloc[3:27]
    b = b[[0, 1, 2, 24, 25]].copy()
    b.columns = ["profile", "depth", "hor", "ph_water", "ph_kcl"]
    b["profile"] = b["profile"].replace("", None).ffill()  # profile name is written on its first row only
    si = _read_cr_csv(doi, "Martinez_2023_site_info.csv", header=1).iloc[1:]
    pts = {r["Site Name"][:2]: (r["Latitude"], r["Longitude"]) for _, r in si.iterrows()}
    soil = {"PF": "Profundihumic Ferralsols (PF)", "HF": "Haplic Ferralsols (HF)"}
    meth = {"pH_H2O": 'water, 1:1 (column "Soil pH 1:1")',
            "pH_KCl": '1 M KCl, soil:solution ratio not stated (column "Soil pH", method column "KCL 1M")'}
    frames = []
    for col, method in [("ph_water", "pH_H2O"), ("ph_kcl", "pH_KCl")]:  # stacked: water first, then KCl
        x = b[~is_missing(b[col])]
        cls = x["profile"].str[:2]
        frames.append(pd.DataFrame({
            "doi": doi, "source_file": src, "id": x["profile"] + ":" + x["hor"], "id_type": "Soil profile:Hor",
            "depth": x["depth"], "date": "2017-08-20", "pH": x[col], "ph_method": method,
            "latitude": cls.map(lambda c: pts[c][0]), "longitude": cls.map(lambda c: pts[c][1]),
            "notes": [(f"lat/long source: doi:10.15485/2283432:Martinez_2023_site_info.csv (site point for {soil[c]}; "
                       f"profiles {c}1-3 share it, individual pit coordinates not given); pH method: {meth[method]}, "
                       f"air-dried <2 mm soil, sheet Bulk_morph_chem; soil pit sampled by depth increment (horizon {h}); "
                       "profile name filled down from its first row in source; sampling date from package temporal coverage")
                      for c, h in zip(cls, x["hor"])],
        }))
    return assemble(pd.concat(frames), "pH", raw=True)


def ph_2283436() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/2283436.

    Package: Soil Carbon Dynamics Following Land Use Changes and Conversion to Oil Palm Plantations in Tropical
    Lowlands Inferred From Radiocarbon.

    Source files: Finstad_2020_TS1_Soil_Data.csv, Finstad_2020_Soil_Profile_Sampling_Locations.csv.

    Location: Finstad_2020_Soil_Profile_Sampling_Locations.csv (profile ..., WGS84 per Finstad_2020_Sites.csv).

    Methods: pH_H2O.

    Notes:
        - Soil-data plots "Mvombo 1/2" are profiles Mvombo/Palm1 and Palm2.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_2283436())  # doctest: +SKIP
        76
    """
    doi = "doi:10.15485/2283436"
    src = "Finstad_2020_TS1_Soil_Data.csv"
    d = _read_cr_csv(doi, src, skiprows=2)
    d.columns = [re.sub(r"\s+", " ", c).strip() for c in d.columns]
    d = d[~is_missing(d["pH"]) & (d["pH"] != "-") & (d["Country"] != "")]
    loc = _read_cr_csv(doi, "Finstad_2020_Soil_Profile_Sampling_Locations.csv").iloc[2:]
    pts = {(r.site_name, r.pro_name): (r.pro_lat, r.pro_long) for r in loc.itertuples()}
    profile_of = {"Natural forest": "Natural", "Oil palm": "Palm", "Pasture": "Pasture", "Secondary": "Secondary"}
    rows = []
    for r in d.itertuples(index=False):
        country, plot, lu, depth, ph = r[0], r[1], r[2], r[3], r[17]
        extra = ""
        if plot.startswith("Mvombo "):  # soil-data plots "Mvombo 1/2" are profiles Mvombo/Palm1 and Palm2
            site, prof = "Mvombo", "Palm" + plot.split()[-1]
            extra = f"; soil-data plot '{plot}' matched to profile Mvombo/{prof}"
        else:
            site, prof = plot, profile_of[lu]
        lat, lon = pts[(site, prof)]
        rows.append(dict(
            doi=doi, source_file=src, id=f"{country}:{plot}:{lu}", id_type="Country:Plot Name:Land Use", depth=depth,
            date="2011", pH=ph, ph_method="pH_H2O", latitude=lat, longitude=lon,
            notes=(f"lat/long source: doi:10.15485/2283436:Finstad_2020_Soil_Profile_Sampling_Locations.csv (profile "
                   f"'{site}' / '{prof}', WGS84 per Finstad_2020_Sites.csv){extra}; pH method: water, 1:4 soil:water, "
                   "air-dried <2 mm soil, per package methods (Finstad et al. 2020 GBC); land use: "
                   f"{lu}{'' if lu == 'Natural forest' else ' (managed/converted from natural forest)'}; sampled 2011 (package temporal coverage, no per-sample date)")))
    return assemble(pd.DataFrame(rows), "pH", raw=True)


def ph_1994876() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/1994876.

    Package: 2017 Meander C sediment characterization from the East River, Colorado.

    Source files: MCB2017_density_and_bulk_fractions.csv, sample_metadata.xlsx.

    Location: sample_metadata.xlsx (position ...; one point per transect position, triplicates share it).

    Methods: unknown.

    Notes:
        - Single reported depths (30 / 70 cm) mapped to the sampled intervals, per doi:10.15485/1860454.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_1994876())  # doctest: +SKIP
        18
    """
    doi = "doi:10.15485/1994876"
    src = "MCB2017_density_and_bulk_fractions.csv"
    d = strip_bom(read_csv(doi, src))
    d = d[~is_missing(d["ph"])]
    meta = read_excel(doi, "sample_metadata.xlsx").set_index("SFA designations")
    # Single reported depths (30 / 70 cm) mapped to the sampled intervals, per doi:10.15485/1860454.
    dmap = {
        "30": ("15-30", "mapped to 15-30 cm as the 15 cm core increment (5 cm diameter slide-hammer corer) with bottom at 30 cm"),
        "70": ("50-90", "mapped to 50-90 cm as the bucket-auger interval (8.3 cm diameter, below coarse alluvium) with "
                        "midpoint at 70 cm"),
    }
    notes = [(f"lat/long source: doi:10.15485/1994876:sample_metadata.xlsx (position {l}, {meta.loc[l, 'Position']}; one "
              "point per transect position, triplicates share it); pH method not described in package (methods text "
              "omits pH; Anderson et al. 2023 ACS Earth Space Chem 7:1623 not accessible to confirm); air-dried, <2 mm "
              "sieved floodplain sediment (Meander C, East River), not a developed soil profile; depth range inferred, not "
              f"confirmed: source reports a single depth ({dc} cm, 'shallow'/'deep'; Anderson et al. 2023 SI also gives "
              f"only 30/70 cm); {dmap[dc][1]}, per related package doi:10.15485/1860454:S_XANES_bulk soil and "
              "sediment.csv (sample labels MCB3_15-30cm_2017, MCB3_50-90cm_2017) and package methods (June 2017 Meander "
              "C cores collected in ~15 cm increments by 5 cm corer, then 8.3 cm bucket auger below coarse alluvium); Fox "
              "et al. list only position MCB3, same sampling scheme assumed for MCB1/MCB2; sampled June 2017")
             for l, dc in zip(d["location"], d["depth_cm"])]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["ID"] + ":" + d["location"], "id_type": "ID:location",
        "depth": d["depth_cm"].map(lambda v: dmap[v][0]), "date": "2017-06", "pH": d["ph"], "ph_method": "unknown",
        "latitude": d["location"].map(meta["Latitude"]), "longitude": d["location"].map(meta["Longitude"]), "notes": notes,
    })
    return assemble(out, "pH", raw=True)


def ph_1841590() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.5440/1841590.

    Package: Soil pH Buffering Capacity, Geochemical Characterization, and Soil Water Retention for Arctic Soils of
    Seward Peninsula and Utqiagvik, Alaska, 2013-2019.

    Source files: 2201_BGC_Soil_Characterization.csv, 2201_BGC_Soil_Acid_Base_Titration_Data.csv.

    Location: 2201_BGC_Soil_Acid_Base_Titration_Data.csv (per-soil coordinates).

    Methods: pH_H2O.

    Notes:
        - NGADG0062 longitude typo in the titration file.

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> len(ph_1841590())  # doctest: +SKIP
        21
    """
    doi = "doi:10.5440/1841590"
    src = "2201_BGC_Soil_Characterization.csv"
    d = strip_bom(read_csv(doi, src))
    t = strip_bom(read_csv(doi, "2201_BGC_Soil_Acid_Base_Titration_Data.csv")).drop_duplicates("Soil_Number")
    pts = t.set_index("Soil_Number")[["Latitude", "Longitude"]]
    lead = "lat/long source: doi:10.5440/1841590:2201_BGC_Soil_Acid_Base_Titration_Data.csv (per-soil coordinates)"
    meth = ("pH method: Initial_pH in water 1:5 (w:v) slurry, per package methods and data dictionary; titration-curve pH "
            "values excluded")
    tail = "sampling date not reported (package temporal coverage 2013-2019)"
    rows = []
    for r in d.itertuples(index=False):
        num, core, locale, site, area, layer, up, low, ph = r[0], r[1], r[3], r[4], r[5], r[7], r[8], r[9], r[11]
        lat, lon = pts.loc[num, "Latitude"], pts.loc[num, "Longitude"]
        loc_note = lead
        if lon == "-162.600043":  # NGADG0062 longitude typo in the titration file
            lon = "-156.600043"
            loc_note += ("; longitude corrected from -162.600043 to -156.600043 (source value places the Barrow site "
                         "~230 km west in the Chukchi Sea)")
        if up == "-9999" and low == "-9999":
            depth = "NA"
        elif low == "-9999":
            depth = f"{up}-NA"
        else:
            depth = f"{up}-{low}"
        if num == "1":
            mid = ("composite soil: titration file lists cores NGADG0013/NGADG0014/NGADG0015 (Intensive Site 1/Intensive "
                   "Site 2/Intensive Site 3), characterization file lists NGADG0013 at Intensive Site 3")
        elif core.strip() == "NGADG0073":
            mid = ("site given as Intensive Site 3 here but Intensive Site 1 in titration file and core catalogue "
                   "doi:10.5440/1109232 (coordinates match Site 1)")
        elif low == "-9999":
            mid = "lower depth not reported (only upper depth given)"
        else:
            mid = ""
        note = "; ".join(x for x in [loc_note, meth, mid, tail] if x)
        rows.append(dict(doi=doi, source_file=src, id=f"{num}:{core.strip()}:{locale}:{site}:{area}:{layer}",
                         id_type="Soil_Number:Core_ID:Locale:Site:Area:Soil_Layer", depth=depth, date="2013/2019",
                         pH=ph, ph_method="pH_H2O", latitude=lat, longitude=lon, notes=note))
    return assemble(pd.DataFrame(rows), "pH", raw=True)


def ph_3025240() -> pd.DataFrame:
    """Harmonize soil pH of doi:10.15485/3025240.

    Package: Meteoric 10Be Flux Calibration Data for the East River Watershed, Colorado, USA.

    Source files: csv.zip/Table_S3.csv, Table_S3.csv, Table_1.csv.

    Location: csv.zip/Table_1.csv (pit).

    Notes:
        - Join on the pit ID (site names differ slightly between the two tables).

    Returns:
        The soil pH table in the harmonized layout (common.assemble).

    Examples:
        >>> t = ph_3025240()  # doctest: +SKIP
    """
    doi = "doi:10.15485/3025240"
    src = "csv.zip/Table_S3.csv"
    s3 = read_csv(doi, "Table_S3.csv")
    t1 = read_csv(doi, "Table_1.csv")
    # Join on the pit ID (site names differ slightly between the two tables).
    t1["pit"] = t1["field_id"].str.lower().str.replace(r"\(\d+\)", "", regex=True)
    s3["pit"] = s3["sample_id"].str.lower().str.extract(r"^(er_[a-z0-9]+_pit_1)")[0]
    m = s3.merge(t1[["pit", "field_id", "latitude_deg", "longitude_deg"]], on="pit", how="left")
    date_note = ("sampling date not reported in package or paper (Marmolejo-Cossio et al. 2026, Geochronology 8:547); "
                 "likely 2020 (inferred, not set in date column): Gothic pit ER_GM_Pit_1 was also sampled for Quirk et al. "
                 "2024 (Quaternary Res. 119:86; doi:10.15485/2316162, temporal coverage from 2020-01, boulder samples on "
                 "these moraines coded ERIV20...), other pits assumed same field campaign")
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": m["site"] + ":" + m["sample_id"], "id_type": "site:sample_id",
        "depth": m["depth_interval_cm"], "date": "", "pH": m["average_ph"], "ph_method": "pH_H2O",
        "latitude": m["latitude_deg"], "longitude": m["longitude_deg"],
        "notes": [(f"lat/long source: doi:10.15485/3025240:csv.zip/Table_1.csv (pit {f}); pH_H2O: ~5 g powdered <2 mm "
                   "soil in 12 mL ultrapure water (~1:2.4), stirred, left overnight, pH probe (Marmolejo-Cossio et al., "
                   f"EGUsphere-2025-4254); mean of duplicate readings ({a}, {b}; 1 SD {sd}); depth intervals are "
                   f"composites of 5-10 cm field increments; {date_note}")
                  for f, a, b, sd in zip(m["field_id"], m["ph_1"], m["ph_2"], m["one_sigma_sd"])],
    })
    return assemble(out, "pH", raw=True)


# ====================================================================================================
# Soil carbon (from notebooks/harmonize_carbon/group3_joined_coords.py)
# ====================================================================================================


def c_1874586() -> pd.DataFrame:
    """Harmonize total carbon of doi:10.15485/1874586.

    Package: 16S and ITS Amplicon Sequencing Fastq files and metadata from PARCHED Panama Tropical Forest soils,
    2019-2020.

    Source files: Field_PARCHED_Metadata_2020.csv, PARCHED_field_sites.kml.

    Location: doi:10.15485/3377028:PARCHED_field_sites.kml, placemark ...; package metadata (Gigante site point).

    Methods: dry_combustion.

    Notes:
        - Plot placemarks "Site Name (CODE) PLOT" in the KML shipped with doi:10.15485/3377028 (as for soil pH).
        - GIG 8E: no placemark; Gigante site point from the package metadata.

    Returns:
        The total carbon table in the harmonized layout (common.assemble).

    Examples:
        >>> len(c_1874586())  # doctest: +SKIP
        50
    """
    doi = "doi:10.15485/1874586"
    src = "Field_PARCHED_Metadata_2020.csv"
    d = strip_bom(read_csv(doi, src))
    d = d[~is_missing(d["Total Carbon"])].rename(columns={"Total Carbon": "TC"})
    # Plot placemarks "Site Name (CODE) PLOT" in the KML shipped with doi:10.15485/3377028 (as for soil pH).
    marks = {}
    for name, (lat, lon) in kml_points("doi:10.15485/3377028", "PARCHED_field_sites.kml").items():
        m = re.search(r"\((\w+)\)\s+(\w+)$", name)
        if m:
            marks[m.groups()] = (name, lat, lon)
    method = ("TC by Costech ECS 4010 elemental analyzer (package methods call it 'total organic carbon'; no acid "
              "pretreatment described, and the column is 'Total Carbon'; acidic tropical forest soils); composite of six "
              "2.54 cm cores per plot and depth")
    rows = []
    for r in d.itertuples(index=False):
        site, plot, trt, cat = r.Site, r.plot, r.Treatment, r.depth_cat
        if (site, plot) in marks:
            name, lat, lon = marks[(site, plot)]
            loc = f"lat/long source: doi:10.15485/3377028:PARCHED_field_sites.kml, placemark '{name}'"
        elif site == "GIG" and plot == "7C":
            name, lat, lon = marks[("GIG", "7E")]
            loc = (f"lat/long source: doi:10.15485/3377028:PARCHED_field_sites.kml, placemark '{name}'; KML label 7E "
                   "assumed to be plot 7C (odd plots are controls; no 7C placemark exists)")
        else:  # GIG 8E: no placemark; Gigante site point from the package metadata
            lat, lon = 9.09919, -79.854
            loc = ("lat/long source: doi:10.15485/1874586 package metadata (Gigante site point); no GIG 8E placemark in "
                   "doi:10.15485/3377028:PARCHED_field_sites.kml")
        if cat == "twenty":
            depth = "10-20"
            dnote = ("depth 10-20 from depth_cat 'twenty' in source; source depth column says 10 for all rows and no 0-10 "
                     "rows exist for GIG exclusion plots in 2020, so depth may be mislabeled")
        else:
            depth = "0-10"
            dnote = "depth 0-10 from depth_cat 'ten' in source (source depth column reports 10)"
        note = f"{loc}; {method}; {dnote}" + ("; throughfall exclusion (drought) plot" if trt == "exclusion" else "")
        rows.append(dict(doi=doi, source_file=src, id=f"{r.sample_id}:{r.rainfall_grad}:{site}:{plot}:{r.replicate}:{trt}",
                         id_type="sample_id:rainfall_grad:Site:plot:replicate:Treatment", depth=depth, date="2020-01",
                         TC=r.TC,
                         tc_method=DRY_COMBUSTION, latitude=lat, longitude=lon, notes=note))
    return assemble(pd.DataFrame(rows), "TC")


def c_1959350() -> pd.DataFrame:
    """Harmonize total carbon of doi:10.15485/1959350.

    Package: Impact of burning on soil properties and respiration; Wood Buffalo National Park, Canada; June 2019.

    Source files: all_sample_metadata.csv, sampling_site_characteristics.csv.

    Location: sampling_site_characteristics.csv (site-level; all cores at a site share one point).

    Methods: dry_combustion.

    Notes:
        - TC is measured once per core-horizon and repeated on its incubation rows.

    Returns:
        The total carbon table in the harmonized layout (common.assemble).

    Examples:
        >>> len(c_1959350())  # doctest: +SKIP
        30
    """
    doi = "doi:10.15485/1959350"
    src = "all_sample_metadata.csv"
    d = strip_bom(read_csv(doi, src))
    d = d[(d["burn.trtmt"] == "control") & ~is_missing(d["percent.total.C"])].copy()  # unburned control cores only
    n_rows = d.groupby("core.id.hor")["Full.id"].transform("size")
    d["n_rows"] = n_rows
    d = d.drop_duplicates("core.id.hor")  # TC is measured once per core-horizon and repeated on its incubation rows
    site = strip_bom(read_csv(doi, "sampling_site_characteristics.csv")).drop_duplicates("Site")
    pts = dict(zip(site["Site"], zip(site["Latitude,N,18,8"], site["Longitude,N,18,8"])))
    keys = ["core.id.hor", "site", "horizon", "burn.trtmt", "core"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": d["horizon"], "date": "2019-06", "TC": d["percent.total.C"], "tc_method": DRY_COMBUSTION,
        "latitude": d["site"].map(lambda s: pts[s][0]), "longitude": d["site"].map(lambda s: pts[s][1]),
        "notes": [("lat/long source: doi:10.15485/1959350:sampling_site_characteristics.csv (site-level; all cores at a "
                   "site share one point); total C by combustion at 900 C, Flash EA 1112 CN analyzer, oven-dried "
                   "(105 C) ball-milled soil (package methods); unburned control core from lab burn experiment; "
                   f"{sp.replace('_', ' ')}; TC measured once per core-horizon and repeated on its {n} incubation/DNA "
                   "rows in source, kept once here (the soil pH file keeps one row per incubation/DNA row); sampled "
                   "June 2019 (no exact day in source)") for sp, n in zip(d["Leading.Species"], d["n_rows"])],
    })
    return assemble(out, "TC")


def c_2438579() -> pd.DataFrame:
    """Harmonize total carbon of doi:10.15485/2438579.

    Package: Impact of fire on chemical properties and respiration of boreal forest soils.

    Source files: metadata.csv, site_location_and_texture.csv.

    Location: site_location_and_texture.csv (site-level point).

    Methods: dry_combustion.

    Returns:
        The total carbon table in the harmonized layout (common.assemble).

    Examples:
        >>> len(c_2438579())  # doctest: +SKIP
        18
    """
    doi = "doi:10.15485/2438579"
    src = "metadata.csv"
    m = read_csv(doi, src)
    s = read_csv(doi, "site_location_and_texture.csv")
    loc = s.drop_duplicates("site").set_index("site")[["location.Y", "location.X"]]
    c = m[(m["burn.trtmt.duration.seconds"] == "0") & ~is_missing(m["C.percent"])].copy()  # unburned controls only
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": c["sample.id"] + ":" + c["site"] + ":" + c["horizon"] + ":control",
        "id_type": "sample.id:site:horizon:burn.trtmt", "depth": c["horizon"], "date": "2022-06",
        "TC": c["C.percent"], "tc_method": DRY_COMBUSTION,
        "latitude": c["site"].map(loc["location.Y"]), "longitude": c["site"].map(loc["location.X"]),
        "notes": [("lat/long source: doi:10.15485/2438579:site_location_and_texture.csv (site-level point); total C by "
                   "combustion at 900 C, Flash EA 1112 CN analyzer, oven-dried (105 C) ball-milled soil (package "
                   "methods); unburned control core (burn duration 0 s) from lab burn experiment, sampled 48 h after "
                   f"treatment; {'organic' if h == 'O' else 'mineral'} horizon; {v.replace('_', ' ')}; field collection "
                   "date not given, 2022-06 from package temporal coverage start; burned cores (30 s, 120 s) excluded")
                  for h, v in zip(c["horizon"], c["vegetation"])],
    })
    return assemble(out.sort_values("id").reset_index(drop=True), "TC")


def c_2283432() -> Tables:
    """Harmonize total carbon, soil organic carbon stock of doi:10.15485/2283432.

    Package: Organic carbon feedbacks to soil structure in Profundihumic and Haplic Ferralsols in Campinas, Sao
    Paulo, Brazil.

    Source files: Martinez_2023_porosity_roots_chemistry.xlsx, Martinez_2023_site_info.csv.

    Location: Martinez_2023_site_info.csv (site ...).

    Methods: TC dry_combustion; SOCstock concentration_x_bulk_density_x_thickness.

    Notes:
        - Profile name is written on its first row only.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), SOCstock (soil organic carbon
        stock).

    Examples:
        >>> {k: len(t) for k, t in c_2283432().items()}  # doctest: +SKIP
        {'TC': 24, 'SOCstock': 26}
    """
    doi = "doi:10.15485/2283432"
    src = "Martinez_2023_porosity_roots_chemistry.xlsx"
    b = read_excel(doi, src, sheet_name="Bulk_morph_chem", header=None).iloc[3:27]
    b = b[[0, 1, 2, 38, 39]].copy()
    b.columns = ["profile", "depth", "hor", "tc", "stock"]
    b["profile"] = b["profile"].replace("", None).ffill()  # profile name is written on its first row only
    b = b[~is_missing(b["tc"])]
    si = read_csv(doi, "Martinez_2023_site_info.csv", header=1).iloc[1:]
    pts = {r["Site Name"][:2]: (r["Latitude"], r["Longitude"]) for _, r in si.iterrows()}
    soil = {"PF": "Profundihumic Ferralsols (PF)", "HF": "Haplic Ferralsols (HF)"}
    cls = b["profile"].str[:2]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": b["profile"] + ":" + b["hor"], "id_type": "Soil profile:Hor",
        "depth": b["depth"], "date": "2017-08-20", "TC": b["tc"], "tc_method": DRY_COMBUSTION,
        "latitude": cls.map(lambda c: pts[c][0]), "longitude": cls.map(lambda c: pts[c][1]),
        "notes": [(f"lat/long source: doi:10.15485/2283432:Martinez_2023_site_info.csv (site point for {soil[c]}; "
                   f"profiles {c}1-3 share it, individual pit coordinates not given); total C by LECO elemental analyzer "
                   "(package methods), sheet Bulk_morph_chem column 'Total Carbon' (%); soil pit sampled by depth "
                   f"increment (horizon {h}); profile name filled down from its first row in source; sampling date from "
                   "package temporal coverage") for c, h in zip(cls, b["hor"])],
    })
    base = out.drop(columns=["TC", "tc_method", "notes"])
    layer = emit(base, "SOCstock", [fmt_tc(v * 10) for v in num(b["stock"])], STOCK_CALC,
                 [(f"lat/long source: doi:10.15485/2283432:Martinez_2023_site_info.csv (site point for {soil[c]}); "
                   f"Bulk Layer Reported Soil Organic Carbon Stock {v} g cm-2 x10 = kg C m-2 for this layer; sheet "
                   "Bulk_morph_chem; sampling date from package temporal coverage") for c, v in zip(cls, b["stock"])])
    prof = pd.DataFrame({
        "doi": doi, "source_file": "Martinez_2023_site_info.csv", "id": si["Site Name"], "id_type": "Site Name",
        "depth": "0-" + si["Reported Profile Soil Organic Carbon Stock Depth"].map(fmt_num), "date": "2017-08-20",
        "value": [fmt_tc(v * 10) for v in num(si["Reported Profile Soil Organic Carbon Stock"])], "method": STOCK_CALC,
        "latitude": si["Latitude"], "longitude": si["Longitude"],
        "notes": [(f"lat/long source: doi:10.15485/2283432:Martinez_2023_site_info.csv (site point); Reported Profile Soil "
                   f"Organic Carbon Stock {v} g cm-2 x10 = kg C m-2 to the reported depth (profile total; the layer stocks "
                   "of the same profiles are listed separately)") for v in si["Reported Profile Soil Organic Carbon Stock"]],
    })
    return {"TC": assemble(out, "TC"), "SOCstock": pd.concat([layer, assemble(prof, "SOCstock")], ignore_index=True)}


def c_2283436() -> Tables:
    """Harmonize total carbon, soil organic carbon stock of doi:10.15485/2283436.

    Package: Soil Carbon Dynamics Following Land Use Changes and Conversion to Oil Palm Plantations in Tropical
    Lowlands Inferred From Radiocarbon.

    Source files: Finstad_2020_TS1_Soil_Data.csv, Finstad_2020_Soil_Profile_Sampling_Locations.csv.

    Location: Finstad_2020_Soil_Profile_Sampling_Locations.csv (profile ...).

    Methods: TC dry_combustion; SOCstock concentration_x_bulk_density_x_thickness.

    Notes:
        - Soil-data plots "Mvombo 1/2" are profiles Mvombo/Palm1 and Palm2.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), SOCstock (soil organic carbon
        stock).

    Examples:
        >>> {k: len(t) for k, t in c_2283436().items()}  # doctest: +SKIP
        {'TC': 120, 'SOCstock': 150}
    """
    r: Any  # one source row (itertuples / to_dict record): cell types are not known statically
    doi = "doi:10.15485/2283436"
    src = "Finstad_2020_TS1_Soil_Data.csv"
    d = read_csv(doi, src, skiprows=2)
    d.columns = [re.sub(r"\s+", " ", c).strip() for c in d.columns]
    d = d[~is_missing(d["C (%)"]) & (d["Country"] != "")]
    loc = read_csv(doi, "Finstad_2020_Soil_Profile_Sampling_Locations.csv").iloc[2:]
    pts = {(r.site_name, r.pro_name): (r.pro_lat, r.pro_long) for r in loc.itertuples()}
    profile_of = {"Natural forest": "Natural", "Oil palm": "Palm", "Pasture": "Pasture", "Secondary": "Secondary"}
    rows, stock = [], []
    for r in d.to_dict("records"):
        country, plot, lu = r["Country"], r["Plot Name"], r["Land Use"]
        extra = ""
        if plot.startswith("Mvombo "):  # soil-data plots "Mvombo 1/2" are profiles Mvombo/Palm1 and Palm2
            site, prof = "Mvombo", "Palm" + plot.split()[-1]
            extra = f"; soil-data plot '{plot}' matched to profile Mvombo/{prof}"
        else:
            site, prof = plot, profile_of[lu]
        lat, lon = pts[(site, prof)]
        rows.append(dict(
            doi=doi, source_file=src, id=f"{country}:{plot}:{lu}", id_type="Country:Plot Name:Land Use",
            depth=r["Depth (cm)"], date="2011", TC=r["C (%)"], tc_method=DRY_COMBUSTION, latitude=lat, longitude=lon,
            notes=(f"lat/long source: doi:10.15485/2283436:Finstad_2020_Soil_Profile_Sampling_Locations.csv (profile "
                   f"'{site}' / '{prof}', WGS84 per Finstad_2020_Sites.csv){extra}; C (%) by Vario EL CN analyzer, "
                   "combustion at 900 C of air-dried <2 mm ground soil (package methods call it total organic carbon; no "
                   "acid pretreatment described; acidic tropical soils); land use: "
                   f"{lu}{'' if lu == 'Natural forest' else ' (managed/converted from natural forest)'}; sampled 2011 "
                   "(package temporal coverage, no per-sample date)")))
        stock.append(dict({k: v for k, v in rows[-1].items() if k not in ("TC", "tc_method", "notes")},
                          value=r["C stock (kg C m-2)"], method=STOCK_CALC,
                          notes=(f"lat/long source: doi:10.15485/2283436:Finstad_2020_Soil_Profile_Sampling_Locations.csv "
                                 f"(profile '{site}' / '{prof}'){extra}; C stock (kg C m-2) of this depth layer from C (%) "
                                 f"and bulk density (package methods); land use: {lu}; sampled 2011")))
    for r in loc.itertuples():
        stock.append(dict(
            doi=doi, source_file="Finstad_2020_Soil_Profile_Sampling_Locations.csv", id=f"{r.site_name}:{r.pro_name}",
            id_type="site_name:pro_name", depth=f"0-{fmt_num(r.pro_soc_depth)}", date="2011",
            value=fmt_tc(float(r.pro_soc) / 10), method=STOCK_CALC, latitude=r.pro_lat, longitude=r.pro_long,
            notes=(f"lat/long source: doi:10.15485/2283436:Finstad_2020_Soil_Profile_Sampling_Locations.csv (profile point); "
                   f"pro_soc {r.pro_soc} converted to kg C m-2 as Mg C ha-1 / 10: the units row says g cm-2, but the values "
                   "match the sum of the layer stocks only when read as Mg C ha-1; profile total to the reported depth; "
                   "sampled 2011")))
    return {"TC": assemble(pd.DataFrame(rows), "TC"), "SOCstock": assemble(pd.DataFrame(stock), "SOCstock")}


def c_1631979() -> Tables:
    """Harmonize carbon variables of doi:10.15485/1631979.

    Package: Genome-resolved metagenomics and metatranscriptomics of microbial communities in three meander-bound
    floodplain soils along the East River, Colorado.

    Source files: FloodplainSamplingSites_PMatheus_BanfieldLab__1_.xlsx,
    ERMG_ERML_ERMZ_Solid_TOC_TIC_TN_Sep2015_data.xlsx, ERML_Solid_TOC_TIC_TN_2016_data.xlsx.

    Location: FloodplainSamplingSites_PMatheus_BanfieldLab__1_.xlsx (sheet ...).

    Methods: TC dry_combustion; SOC TC_minus_TIC; SIC unknown.

    Notes:
        - One sheet per sampling year; 2016 resampled several 2015 positions under the same Sample ID.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), SOC (soil organic carbon), SIC
        (soil inorganic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_1631979().items()}  # doctest: +SKIP
        {'TC': 127, 'SOC': 127, 'SIC': 127}
    """
    doi = "doi:10.15485/1631979"
    sites_file = "FloodplainSamplingSites_PMatheus_BanfieldLab__1_.xlsx"
    # One sheet per sampling year; 2016 resampled several 2015 positions under the same Sample ID.
    sites = {y: pd.read_excel(raw_path(doi, sites_file), sheet_name=y)
             .rename(columns={"Depth (top cm)": "Depth (top; cm)", "Depth (bottom cm)": "Depth (bottom; cm)"})
             .assign(year=y).set_index("Sample ID") for y in ("2015", "2016")}

    def site_id(sample: str) -> str:
        """TC-file sample names -> sampling-site table IDs (ERMG_T1-19m -> ERMGT119, ERML_T2-31A -> ERMLT231A')."""
        m = re.match(r"^(ERM[GLZ])[_-]T(\d)-(\d+)m$", sample)  # ERMG_T1-0m or ERML-T1-0m
        if m:
            return f"{m.group(1)}T{m.group(2)}{int(m.group(3)):02d}"
        m = re.match(r"^ERML_T(\d)-(\d+)([AB]?)(?:-(\d))?$", sample)
        if m:
            sid = f"ERMLT{m.group(1)}{m.group(2)}{m.group(3)}" + (f"_{m.group(4)}" if m.group(4) else "")
            return sid if sid in sites["2016"].index else sid + "'"
        ib = {"ERML_IB25": "ERMLIBT25", "ERML_IBT27": "ERMLIBT27", "ERML_TIB45": "ERMLIBT45", "ERML_IBT47": "ERMLIBT47"}
        return ib[sample]

    method = ("TC by combustion on dried solids (TC = TOC + TIC; package description), average of replicate analyses "
              "('TC, %' Average column)")
    rows: list[dict[str, Any]] = []
    soc: list[dict[str, Any]] = []
    sic: list[dict[str, Any]] = []
    files: list[tuple[str, list[str | int], str]] = [
        ("ERMG_ERML_ERMZ_Solid_TOC_TIC_TN_Sep2015_data.xlsx", ["ERMG", "ERML", "ERMZ"], "2015"),
        ("ERML_Solid_TOC_TIC_TN_2016_data.xlsx", [0], "2016")]
    for src, sheets, year in files:
        for sh in sheets:
            x = pd.read_excel(raw_path(doi, src), sheet_name=sh, header=None)
            hdr = x.iloc[3].astype(str).tolist()
            avg = hdr.index("Average")  # first Average column belongs to TC
            ic_avg = hdr.index("Average", avg + 1)  # second Average column belongs to IC
            oc_col = hdr.index("OC=TC-IC")
            idcol = 1
            for _, r in x.iloc[4:].iterrows():
                sample, tc = r[idcol], r[avg]
                if not isinstance(sample, str) or pd.isna(tc):
                    continue
                ic, oc = r[ic_avg], r[oc_col]
                sid = site_id(sample.strip())
                s_ = sites[year].loc[sid]
                if pd.isna(s_["Depth (top; cm)"]) or pd.isna(s_["Depth (bottom; cm)"]):
                    depth, dnote = "", "; depth not given in the sampling-site table"
                else:
                    depth, dnote = checked_depth(s_["Depth (top; cm)"], s_["Depth (bottom; cm)"])
                rows.append(dict(
                    doi=doi, source_file=src, id=f"{sample.strip()}:{sid}", id_type="Sample ID (TC file):Sample ID (site table)",
                    depth=depth, date="2015-09" if s_["year"] == "2015" else "2016", TC=fmt_tc(tc), tc_method=DRY_COMBUSTION,
                    latitude=s_["Latitude"], longitude=s_["Longitude"],
                    notes=(f"lat/long source: {doi}:{sites_file} (sheet {s_['year']}, per-sample Latitude/Longitude, matched "
                           f"by sample name {sample.strip()} -> {sid}); {method}; depth from the sampling-site table; "
                           f"{s_['Site description']}"
                           + ("; date: 2015 samples collected 2015-09-10/16 (package temporal coverage)" if s_["year"] == "2015"
                              else "; date: 2016 sampling, month not given") + dnote)))
                where = (f"lat/long source: {doi}:{sites_file} (sheet {s_['year']}, matched by sample name "
                         f"{sample.strip()} -> {sid}); ")
                tail = f"; depth from the sampling-site table; {s_['Site description']}" + dnote
                base = {k: v for k, v in rows[-1].items() if k not in ("TC", "tc_method", "notes")}
                soc.append(dict(base, value=fmt_tc(oc) if not pd.isna(oc) else "", method=TC_MINUS_TIC,
                                notes=where + "OC = TC - IC (column 'OC=TC-IC'), TC by combustion and IC as averages of "
                                "replicate analyses" + tail))
                sic.append(dict(base, value=fmt_tc(ic) if not pd.isna(ic) else "", method=UNKNOWN,
                                notes=where + "IC (%) average of replicate analyses ('IC, %' Average column); IC method "
                                "not described in the package" + tail))
    return {"TC": assemble(pd.DataFrame(rows), "TC"), "SOC": assemble(pd.DataFrame(soc), "SOC"),
            "SIC": assemble(pd.DataFrame(sic), "SIC")}


def c_1839189() -> Tables:
    """Harmonize carbon variables of doi:10.15485/1839189.

    Package: Geochemistry of East River, Colorado floodplain sediments from Meander Z and Meander Y collected in
    2017.

    Source files: particle size_TIC_TOC_moisture content.csv, locations_meta data.csv.

    Location: locations_meta data.csv (per-core Latitude/Longitude, matched by Location ID).

    Methods: TC dry_combustion; SOC TC_minus_TIC; SIC acidification.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), SOC (soil organic carbon), SIC
        (soil inorganic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_1839189().items()}  # doctest: +SKIP
        {'TC': 24, 'SOC': 24, 'SIC': 24}
    """
    doi = "doi:10.15485/1839189"
    src = "particle size_TIC_TOC_moisture content.csv"
    d = read_csv(doi, src)
    d = d[~is_missing(d["TC_wt %"])]
    loc = read_csv(doi, "locations_meta data.csv").set_index("Location ID")

    def sampled(location: str) -> str:
        return str(pd.to_datetime(cast(str, loc.loc[location, "sample date"]), format="%m/%d/%Y").strftime("%Y-%m-%d"))

    approx = d["depth_cm bgs"].str.startswith("~")
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Location ID"] + ":" + d["sample ID"], "id_type": "Location ID:sample ID",
        "depth": d["depth_cm bgs"].str.lstrip("~"),
        "date": d["Location ID"].map(sampled),
        "TC": d["TC_wt %"], "tc_method": DRY_COMBUSTION,
        "latitude": d["Location ID"].map(loc["Latitude"]), "longitude": d["Location ID"].map(loc["Longitude"]),
        "notes": [(f"lat/long source: {doi}:locations_meta data.csv (per-core Latitude/Longitude, matched by Location ID); "
                   "TC by Shimadzu TOC-V with solids module, catalytically aided combustion at 900 C, air-dried milled "
                   "sediment (package methods); East River floodplain sediment core, Meander Z/Y"
                   + ("; depth given as approximate ('~') in source" if a else "")) for a in approx],
    })
    base = out.drop(columns=["TC", "tc_method", "notes"])
    where = f"lat/long source: {doi}:locations_meta data.csv (per-core Latitude/Longitude, matched by Location ID); "
    tail = "; East River floodplain sediment core, Meander Z/Y"
    return {"TC": assemble(out, "TC"),
            "SOC": emit(base, "SOC", d["TOC_wt %"], TC_MINUS_TIC,
                        where + "TOC_wt % = TC - TIC (Shimadzu TOC-V with solids module; package methods)" + tail),
            "SIC": emit(base, "SIC", d["TIC_wt %"], ACIDIFICATION,
                        where + "TIC_wt % by Shimadzu TOC-V solids module, thermally aided acid oxidation (package "
                        "methods)" + tail)}


def c_2350837() -> pd.DataFrame:
    """Harmonize total carbon of doi:10.15485/2350837.

    Package: Soil Carbon and Nitrogen Elemental Analysis and Middle Infrared Spectroscopy from the Kougarok Fire
    Complex, Seward Peninsula, Alaska, 2022.

    Source files: Kougarok_Fire_Complex_Carbon_Nitrogen_Analysis.csv, Kougarok_Fire_Complex_Field_Observations.csv.

    Location: Kougarok_Fire_Complex_Field_Observations.csv (site ...; matched by Soil_Sample_ID prefix, '-' read as
    '_').

    Methods: dry_combustion.

    Returns:
        The total carbon table in the harmonized layout (common.assemble).

    Examples:
        >>> len(c_2350837())  # doctest: +SKIP
        60
    """
    doi = "doi:10.15485/2350837"
    src = "Kougarok_Fire_Complex_Carbon_Nitrogen_Analysis.csv"
    d = read_csv(doi, src).drop_duplicates("Soil_Sample_ID")  # A/B replicate rows share avg_Per_C
    obs = read_csv(doi, "Kougarok_Fire_Complex_Field_Observations.csv").drop_duplicates("Site").set_index("Site")
    d["site"] = d["Soil_Sample_ID"].str.rsplit("-", n=1).str[0].str.replace("-", "_")
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Soil_Sample_ID"], "id_type": "Soil_Sample_ID", "depth": d["Depth"],
        "date": d["site"].map(obs["Date"]), "TC": d["avg_Per_C"], "tc_method": DRY_COMBUSTION,
        "latitude": d["site"].map(obs["Latitude"]), "longitude": d["site"].map(obs["Longitude"]),
        "notes": [(f"lat/long source: {doi}:Kougarok_Fire_Complex_Field_Observations.csv (site {s}; matched by Soil_Sample_ID "
                   "prefix, '-' read as '_'); total C by Thermo Flash 2000 elemental analyzer, duplicate analyses "
                   "averaged (avg_Per_C); depth is the sample depth label (cm) as reported, not an interval; date from the "
                   f"field observation table; {b.lower()} site, burned {n} time(s) (wildfire history, not a treatment)")
                  for s, b, n in zip(d["site"], d["site"].map(obs["Burned_Unburned"]),
                                     d["site"].map(obs["Number_of_times_burned"]))],
    })
    return assemble(out, "TC")


def c_1506944() -> Tables:
    """Harmonize carbon variables of doi:10.21952/WTR/1506944.

    Package: Using geochemical indicators to distinguish high biogeochemical activity in floodplain soils and
    sediments, Science of the Total Environment: Dataset.

    Source files: Kenwell Data Package.xlsx.

    Location: Kenwell Data Package.xlsx (sheet Coordinates, point ...).

    Methods: TC dry_combustion; SOC unknown; SIC unknown.

    Notes:
        - No coordinates for this sample (Db, Dd, Yule)

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), SOC (soil organic carbon), SIC
        (soil inorganic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_1506944().items()}  # doctest: +SKIP
        {'TC': 64, 'SOC': 41, 'SIC': 41}
    """
    r: Any  # one source row (itertuples / to_dict record): cell types are not known statically
    doi = "doi:10.21952/WTR/1506944"
    src = "Kenwell Data Package.xlsx"
    t = pd.read_excel(raw_path(doi, src), sheet_name="TOC", header=None).iloc[4:, 1:5]
    t.columns = ["sample", "oc", "ic", "tc"]
    soc, sic = [], []
    t = t[t["sample"].notna() & ~t["sample"].astype(str).str.contains("Average|Minimum|Maximum|n.a.")]
    c = pd.read_excel(raw_path(doi, src), sheet_name="Coordinates", header=None).iloc[4:, 1:4]
    pts = {str(k).strip(): (a, b) for k, a, b in c.itertuples(index=False) if pd.notna(a)}
    alias = {"OdT": "OdT/OdB", "OdB": "OdT/OdB", "OxM": "Ox Mancos", "OxU": "Ox Up"}

    def point(s: str) -> str | None:
        if s in alias:
            return alias[s]
        for k in sorted(pts, key=len, reverse=True):  # longest coordinate ID that prefixes the sample name
            if s.startswith(k):
                return k
        return None

    rows = []
    for r in t.itertuples(index=False):
        s = str(r.sample).strip()
        k = point(s)
        if k is None:
            continue  # no coordinates for this sample (Db, Dd, Yule)
        lat, lon = pts[k]
        rows.append(dict(
            doi=doi, source_file=src, id=s, id_type="Sample ID", depth="", date="2014-06/2015-06", TC=fmt_tc(r.tc),
            tc_method=DRY_COMBUSTION, latitude=lat, longitude=lon,
            notes=(f"lat/long source: {doi}:{src} (sheet Coordinates, point '{k}'"
                   + (f", matched to sample '{s}' by name prefix" if k != s else "") + "); % Total Carbon (sheet TOC) = "
                   "% organic + % inorganic C, UIC CM 5014 coulometer on duplicate samples (package methods); East River "
                   "floodplain soil/sediment, hand-augered; sampling depth not reported (suffixes such as T/B in sample "
                   "names are not explained); date from package temporal coverage; Rifle borehole samples have no "
                   "coordinates in the package and are not included")))
        base = {k: v for k, v in rows[-1].items() if k not in ("TC", "tc_method", "notes")}
        where = f"lat/long source: {doi}:{src} (sheet Coordinates, point '{k}'); "
        tail = ("; UIC CM 5014 coulometer on duplicate samples (package methods); sampling depth not reported; date from "
                "package temporal coverage")
        soc.append(dict(base, value=fmt_tc(r.oc) if str(r.oc) != "n.a." else "", method=UNKNOWN,
                        notes=where + "% Organic Carbon (sheet TOC)" + tail))
        sic.append(dict(base, value=fmt_tc(r.ic) if str(r.ic) != "n.a." else "", method=UNKNOWN,
                        notes=where + "% Inorganic Carbon (sheet TOC)" + tail))
    return {"TC": assemble(pd.DataFrame(rows), "TC"), "SOC": assemble(pd.DataFrame(soc), "SOC"),
            "SIC": assemble(pd.DataFrame(sic), "SIC")}


def c_1464956() -> pd.DataFrame:
    """Harmonize total carbon of doi:10.5440/1464956.

    Package: Soil Organic Horizon Exometabolomics Extracts and Soil Characteristics with Depth, Utqiagvik (Barrow),
    Alaska, 2014.

    Source files: LCP_HCP_Organic_Horizon_Soil_Characteristics_2014_20181210.csv.

    Location: doi:10.5440/1618325:NGEE_User_Guidance_Document_template_BEO_SoilFe_20200515.pdf (general location of
    BEO Intensive Site 1 Area A; this package has no coordinates);
    doi:10.5440/1618325:NGEE_User_Guidance_Document_template_BEO_SoilFe_20200515.pdf (general location of BEO
    Intensive Site 1 Area B; this package has no coordinates).

    Methods: unknown.

    Notes:
        - Barrow Environmental Observatory Intensive Site 1 areas A (low-centered) and B (high-centered): general points
          from the user guide of doi:10.5440/1618325 (same BEO Site 1 areas; this package gives no coordinates).

    Returns:
        The total carbon table in the harmonized layout (common.assemble).

    Examples:
        >>> len(c_1464956())  # doctest: +SKIP
        12
    """
    doi = "doi:10.5440/1464956"
    src = "LCP_HCP_Organic_Horizon_Soil_Characteristics_2014_20181210.csv"
    d = read_csv(doi, src, skiprows=8).iloc[1:]  # metadata block, then header, then units row
    d = d[~is_missing(d["Carbon_total"])]
    # Barrow Environmental Observatory Intensive Site 1 areas A (low-centered) and B (high-centered): general points
    # from the user guide of doi:10.5440/1618325 (same BEO Site 1 areas; this package gives no coordinates).
    area = {"A": (71.2815, -156.61012), "B": (71.27933, -156.60475)}
    keys = ["Site", "Area", "Polygon_type", "Species", "Core ID", "Increment_ID"]
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": [depth_range(a, b) for a, b in zip(d["upper_depth_of_soil_layer"], d["lower_depth_of_soil_layer"])],
        "date": d["Date_sampled"], "TC": d["Carbon_total"], "tc_method": UNKNOWN,
        "latitude": d["Area"].map(lambda a: area[a][0]), "longitude": d["Area"].map(lambda a: area[a][1]),
        "notes": [(f"lat/long source: doi:10.5440/1618325:NGEE_User_Guidance_Document_template_BEO_SoilFe_20200515.pdf "
                   f"(general location of BEO Intensive Site 1 Area {a}; this package has no coordinates); Carbon_total (%), "
                   "instrument not stated; source also lists Carbon_inorganic (~34-43%) larger than Carbon_total_organic "
                   f"(~2-13%), which looks like swapped labels; organic horizon {i.lower()} increment; {p}, {sp}")
                  for a, i, p, sp in zip(d["Area"], d["Increment_ID"], d["Polygon_type"], d["Species"])],
    })
    return assemble(out, "TC")


# ----------------------------------------------------------------------------------------------------
# Packages added for the other carbon variables
# ----------------------------------------------------------------------------------------------------

def c_1910300() -> dict:
    """Harmonize soil organic carbon of doi:10.15485/1910300.

    Package: Bulk density, grain size, carbon content and isotopes, and nitrogen content of floodplain sediment
    along the Koyukuk River, Alaska collected in Summer 2018.

    Source files: Koyukuk_River_Floodplain_Soil_Geochemistry.csv, Koyukuk_River_Floodplain_Sample_Sites.csv.

    Location: Koyukuk_River_Floodplain_Sample_Sites.csv (site ...).

    Methods: SOC unknown.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): SOC (soil organic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_1910300().items()}  # doctest: +SKIP
        {'SOC': 34}
    """
    doi = "doi:10.15485/1910300"
    src = "Koyukuk_River_Floodplain_Soil_Geochemistry.csv"
    d = read_csv(doi, src, encoding="latin1")
    d["toc"] = d["TOC (dry wt%)"].str.split("±").str[0].str.strip()
    d = d[~is_missing(d["toc"])]
    sites = read_csv(doi, "Koyukuk_River_Floodplain_Sample_Sites.csv", encoding="latin1").set_index("Sample site")
    lat, lon = sites.columns[1], sites.columns[2]  # after set_index: Landform, Latitude, Longitude, ...
    out = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d["Sample Name"], "id_type": "Sample Name",
        "depth": d["Depth (cm)"].replace("-", ""), "date": "2018-06-27/2018-07-09", "value": d["toc"], "method": UNKNOWN,
        "latitude": d["Sample Site"].map(sites[lat]), "longitude": d["Sample Site"].map(sites[lon]),
        "notes": [(f"lat/long source: {doi}:Koyukuk_River_Floodplain_Sample_Sites.csv (site '{s}'); TOC (dry wt%) "
                   f"{t} (value before '±' kept); depth is a single sample depth (cm) as reported"
                   + ("" if z != "-" else " (no depth given, e.g. bank peat)") + f"; stratigraphic unit {u}; Koyukuk River "
                   "floodplain, sampled summer 2018 (package temporal coverage)")
                  for s, t, z, u in zip(d["Sample Site"], d["TOC (dry wt%)"], d["Depth (cm)"], d["Stratigraphic Unit"])],
    })
    return {"SOC": assemble(out, "SOC")}


def c_1572186() -> Tables:
    """Harmonize soil organic carbon, soil inorganic carbon of doi:10.21952/WTR/1572186.

    Package: Geochemical characterization of floodplain sediments from Meander C and O in the East River Watershed,
    CO, USA.

    Source files: summary_of_sediment_data_Fox_et_al_2019.xlsx.

    Location: summary_of_sediment_data_Fox_et_al_2019.xlsx (sheet 'meta data', GPS for ...).

    Methods: SOC TC_minus_TIC, unknown; SIC acidification.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): SOC (soil organic carbon), SIC (soil inorganic
        carbon).

    Examples:
        >>> {k: len(t) for k, t in c_1572186().items()}  # doctest: +SKIP
        {'SOC': 62, 'SIC': 44}
    """
    doi = "doi:10.21952/WTR/1572186"
    src = "summary_of_sediment_data_Fox_et_al_2019.xlsx"
    x = pd.read_excel(raw_path(doi, src), sheet_name="data summary", header=None).iloc[3:]
    x = x[x[1].astype(str).str.match(r"^M[OC]")]
    meta = pd.read_excel(raw_path(doi, src), sheet_name="meta data", header=None).iloc[2:]
    pts = {str(r[0]).strip(): (r[3], r[4], r[2]) for r in meta.itertuples(index=False) if pd.notna(r[3])}
    rows: dict[str, list[dict[str, Any]]] = {"SOC": [], "SIC": []}
    for r in x.itertuples(index=False):
        loc, name, depth = r[0], r[1], r[2]
        lat, lon, desc = pts[loc]
        base = dict(doi=doi, source_file=src, id=f"{loc}:{name}", id_type="Location:Sample Name", depth=depth,
                    date="2016", latitude=lat, longitude=lon)
        where = f"lat/long source: {doi}:{src} (sheet 'meta data', GPS for {loc}: {desc}); "
        tail = "; East River Meander C / oxbow floodplain sediment core (Fox et al. 2019); sampling year from the study"
        if pd.notna(r[13]):
            rows["SOC"].append(dict(base, value=fmt_tc(r[13]), method=TC_MINUS_TIC,
                                    notes=where + "TOC (%) by Shimadzu solid TOC analyzer (TC - TIC), sheet 'data summary'" + tail))
        if pd.notna(r[6]):
            rows["SOC"].append(dict(base, value=fmt_tc(r[6]), method=UNKNOWN,
                                    notes=where + "TOC (%) by elemental analyzer ('C and N by EA' block); a second "
                                    "measurement of the same sample" + tail))
        if pd.notna(r[15]):
            rows["SIC"].append(dict(base, value=fmt_tc(r[15]), method=ACIDIFICATION,
                                    notes=where + "TIC (%) by Shimadzu solid TOC analyzer, sheet 'data summary'"
                                    + ("; slightly negative value (below detection) kept as reported" if r[15] < 0 else "")
                                    + tail))
    return {v: assemble(pd.DataFrame(rs), v) for v, rs in rows.items()}


def c_1440029() -> dict:
    """Harmonize soil organic carbon of doi:10.5440/1440029.

    Package: Synthesis of Soil Geochemical Characteristics and Organic Carbon Degradation from Arctic Polygon
    Tundra, Utqiagvik (Barrow), Alaska.

    Source files: BGC_Soil_Core_Descriptions_2012-2013_Physicochemical_Properties_v3.csv,
    10.5440_1440029_NGADG*.csv.

    Location: doi:10.5440/1109232:BGC_Soil_Core_Descriptions_2012-2013_Physicochemical_Properties_v3.csv (core ...,
    UTM Zone 4N NAD83 converted; this synthesis package has no coordinates).

    Methods: SOC unknown.

    Notes:
        - Core locations and dates from the core catalogue doi:10.5440/1109232 (UTM 4N, NAD83).

    Returns:
        {variable: table} in the harmonized layout (common.assemble): SOC (soil organic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_1440029().items()}  # doctest: +SKIP
        {'SOC': 17}
    """
    import glob
    from ..common import PACKAGE_DATA, utm_to_latlon
    doi = "doi:10.5440/1440029"
    # Core locations and dates from the core catalogue doi:10.5440/1109232 (UTM 4N, NAD83).
    cdoi, csrc = "doi:10.5440/1109232", "BGC_Soil_Core_Descriptions_2012-2013_Physicochemical_Properties_v3.csv"
    raw = pd.read_csv(raw_path(cdoi, csrc), encoding="latin1", dtype=str, header=None)
    cat = raw.iloc[10:]
    cat.columns = [str(c).strip() for c in raw.iloc[8]]
    cat = cat.dropna(how="all").drop_duplicates("Core_ID").set_index("Core_ID")
    rows = []
    for path in sorted(glob.glob(str(PACKAGE_DATA / "10.5440_1440029_NGADG*.csv"))):
        src = path.split("10.5440_1440029_")[1]
        d = read_csv(doi, src, skiprows=8).iloc[1:]  # metadata block, header, units row
        d = d[~is_missing(d["SOC"])].drop_duplicates(["Core_ID", "Soil_layer", "Upper_depth_of_soil_layer",
                                                      "Lower_depth_of_soil_layer", "SOC"])
        for r in d.to_dict("records"):
            c = r["Core_ID"].strip()
            if c not in cat.index:
                continue
            lat, lon = utm_to_latlon(float(cat.loc[c, "Easting_UTM"]), float(cat.loc[c, "Northing_UTM"]), 4)
            rows.append(dict(
                doi=doi, source_file=src, id=f"{c}:{r['Soil_layer']}", id_type="Core_ID:Soil_layer",
                depth=depth_range(r["Upper_depth_of_soil_layer"], r["Lower_depth_of_soil_layer"]),
                date=cat.loc[c, "Date_sampled"], value=r["SOC"], method=UNKNOWN, latitude=round(lat, 5),
                longitude=round(lon, 5),
                notes=(f"lat/long source: {cdoi}:{csrc} (core {c}, UTM Zone 4N NAD83 converted; this synthesis package has "
                       "no coordinates); date from the same core catalogue; SOC (%) of the core layer, method not stated; "
                       f"repeated on every incubation row of {src} in source, kept once per layer; {r['Polygon Type']} "
                       f"polygon, {r['Microtopography']}")))
    return {"SOC": assemble(pd.DataFrame(rows), "SOC")}


def c_1841590() -> dict:
    """Harmonize soil organic carbon of doi:10.5440/1841590.

    Package: Soil pH Buffering Capacity, Geochemical Characterization, and Soil Water Retention for Arctic Soils of
    Seward Peninsula and Utqiagvik, Alaska, 2013-2019.

    Source files: 2201_BGC_Soil_Characterization.csv, 2201_BGC_Soil_Acid_Base_Titration_Data.csv.

    Location: 2201_BGC_Soil_Acid_Base_Titration_Data.csv (per-soil coordinates).

    Methods: SOC unknown.

    Notes:
        - NGADG0062 longitude typo in the titration file (as for pH)

    Returns:
        {variable: table} in the harmonized layout (common.assemble): SOC (soil organic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_1841590().items()}  # doctest: +SKIP
        {'SOC': 21}
    """
    doi = "doi:10.5440/1841590"
    src = "2201_BGC_Soil_Characterization.csv"
    d = strip_bom(read_csv(doi, src))
    t = strip_bom(read_csv(doi, "2201_BGC_Soil_Acid_Base_Titration_Data.csv")).drop_duplicates("Soil_Number")
    pts = t.set_index("Soil_Number")[["Latitude", "Longitude"]]
    rows = []
    for r in d.to_dict("records"):
        n, core = r["Soil_Number"], r["Core_ID"].strip()
        lat, lon = pts.loc[n, "Latitude"], pts.loc[n, "Longitude"]
        fix = ""
        if lon == "-162.600043":  # NGADG0062 longitude typo in the titration file (as for pH)
            lon, fix = "-156.600043", "; longitude corrected from -162.600043 to -156.600043"
        up, low = r["upper_depth_of_soil_layer"], r["lower_depth_of_soil_layer"]
        depth = "NA" if up == "-9999" and low == "-9999" else (f"{up}-NA" if low == "-9999" else f"{up}-{low}")
        rows.append(dict(
            doi=doi, source_file=src, id=f"{n}:{core}:{r['Locale']}:{r['Site']}:{r['Area']}:{r['Soil_Layer']}",
            id_type="Soil_Number:Core_ID:Locale:Site:Area:Soil_Layer", depth=depth, date="2013/2019",
            value=r["SOC_percent"], method=UNKNOWN, latitude=lat, longitude=lon,
            notes=(f"lat/long source: {doi}:2201_BGC_Soil_Acid_Base_Titration_Data.csv (per-soil coordinates){fix}; "
                   "SOC_percent, method not stated in the data dictionary; sampling date not reported (package temporal "
                   "coverage 2013-2019)")))
    return {"SOC": assemble(pd.DataFrame(rows), "SOC")}


def c_1346200() -> dict:
    """Harmonize total carbon, dissolved organic carbon of doi:10.5440/1346200.

    Package: NGEE Arctic Plant Traits: Soil Cores, Kougarok Road Mile Marker 64, Seward Peninsula, Alaska, 2016.

    Source files: NGEEArctic_Kougarok2016_SoilCoreData_v1.csv,
    NGEE_Arctic_Kougarok_2016_GPSwaypoints_Ecotypes_v1.csv.

    Location: doi:10.5440/1346196:NGEE_Arctic_Kougarok_2016_GPSwaypoints_Ecotypes_v1.csv (vegetation plot ...).

    Methods: TC unknown; DOC unknown.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): TC (total carbon), DOC (dissolved organic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_1346200().items()}  # doctest: +SKIP
        {'TC': 63, 'DOC': 63}
    """
    doi = "doi:10.5440/1346200"
    src = "NGEEArctic_Kougarok2016_SoilCoreData_v1.csv"
    d = read_csv(doi, src, skiprows=6, encoding="latin1")
    w = read_csv("doi:10.5440/1346196", "NGEE_Arctic_Kougarok_2016_GPSwaypoints_Ecotypes_v1.csv", skiprows=6, encoding="latin1")
    pts = {r.ID: (r.latitude, r.longitude) for r in w.itertuples()}
    wp = {p: p if p in pts else p.replace("TTWBT", "TT-WBT") for p in d["PlotID"].unique()}
    keys = ["PlotID", "CoreRep", "Horizon_TextureBased"]
    base = pd.DataFrame({
        "doi": doi, "source_file": src, "id": d[keys].agg(":".join, axis=1), "id_type": ":".join(keys),
        "depth": [depth_range(a, b) for a, b in zip(d["DepthTop_cm"], d["DepthBottom_cm"])],
        "date": "2016-07-25/2016-07-27",
        "latitude": d["PlotID"].map(lambda p: pts[wp[p]][0]), "longitude": d["PlotID"].map(lambda p: pts[wp[p]][1]),
    })
    locs = [(f"lat/long source: doi:10.5440/1346196:NGEE_Arctic_Kougarok_2016_GPSwaypoints_Ecotypes_v1.csv (vegetation "
             f"plot '{wp[p]}'); ") for p in d["PlotID"]]
    tail = [f"; {h} horizon; {e}; sampled 25-27 July 2016 (as for pH)" for h, e in zip(d["Horizon_TextureBased"], d["Ecotype"])]
    return {
        "TC": emit(base, "TC", d["BulkSoilC_percent"], UNKNOWN,
                   [l + "BulkSoilC_percent (bulk soil C, %), instrument not stated in the data file" + t for l, t in zip(locs, tail)]),
        "DOC": emit(base, "DOC", [fmt_tc(v * 1000) for v in num(d["DOC_mgCpergdrysoil"])], UNKNOWN,
                    [l + "DOC_mgCpergdrysoil x1000 = mg C kg-1 dry soil; extractant not stated in the data file" + t
                     for l, t in zip(locs, tail)],
                    DOC_unit="mg C kg-1 dry soil", DOC_medium="soil extract (extractant not stated)"),
    }


def c_1602783() -> dict:
    """Harmonize dissolved organic carbon of doi:10.15485/1602783.

    Package: Marine Corps Base Camp Lejeune CW-5 Marsh Carbon, Nutrient and Atmospheric Gas exchanges with overlying
    water.

    Source files: CW5_Marsh_Carbon_Nutrient_AtmGas_Exchange.xlsx.

    Location: CW5_Marsh_Carbon_Nutrient_AtmGas_Exchange.xlsx (sheet 'Location', point for ...).

    Methods: DOC porewater.

    Returns:
        {variable: table} in the harmonized layout (common.assemble): DOC (dissolved organic carbon).

    Examples:
        >>> {k: len(t) for k, t in c_1602783().items()}  # doctest: +SKIP
        {'DOC': 71}
    """
    doi = "doi:10.15485/1602783"
    src = "CW5_Marsh_Carbon_Nutrient_AtmGas_Exchange.xlsx"
    x = pd.read_excel(raw_path(doi, src), sheet_name="DCERP seasonal plot data", header=None).iloc[3:]
    loc = pd.read_excel(raw_path(doi, src), sheet_name="Location", header=None).iloc[2:]
    pts = {str(r[1]).strip(): (r[2], r[3]) for r in loc.itertuples(index=False)}
    site = {("Freeman", "Edge"): "Freeman's Creek (Edge)", ("Freeman", "Interior"): "Freeman's Creek (Interior)"}
    rows = []
    for r in x.itertuples(index=False):
        plot, marsh, where, trt, season = r[1], r[2], r[3], r[4], r[5]
        if trt != "Control" or pd.isna(plot):
            continue
        key = site.get((str(marsh).strip(), str(where).strip()), "Trap's Bay Creek")
        lat, lon = pts[key]
        for depth, col in (("5", 8), ("15", 9)):
            if pd.isna(r[col]):
                continue
            rows.append(dict(
                doi=doi, source_file=src, id=f"{plot}:{marsh}:{where}:{season}", id_type="Plot:Marsh:Location:Season",
                depth=depth, date=str(season).split()[-1], value=fmt_tc(float(r[col]) * MMOL_C), method=POREWATER,
                DOC_unit="mg C L-1", DOC_medium="marsh porewater", latitude=lat, longitude=lon,
                notes=(f"lat/long source: {doi}:{src} (sheet 'Location', point for {key}); DOC {r[col]} mM x 12.011 = mg C "
                       f"L-1 of porewater at {depth} cm; season '{season}' (year only in date); control plot (fertilized "
                       "plots excluded); Camp Lejeune CW-5 marsh, sheet 'DCERP seasonal plot data'")))
    return {"DOC": assemble(pd.DataFrame(rows), "DOC")}


# ====================================================================================================
# Packages
# ====================================================================================================

PACKAGES = [
    ("doi:10.15485/1874586", combine(("pH", ph_1874586), ("TC", c_1874586)), ('pH', 'TC')),
    ("doi:10.15485/1959350", combine(("pH", ph_1959350), ("TC", c_1959350)), ('pH', 'TC')),
    ("doi:10.15485/2438579", combine(("pH", ph_2438579), ("TC", c_2438579)), ('pH', 'TC')),
    ("doi:10.15485/2283432", combine(("pH", ph_2283432), ("TC", c_2283432)), ('pH', 'TC', 'SOCstock')),
    ("doi:10.15485/2283436", combine(("pH", ph_2283436), ("TC", c_2283436)), ('pH', 'TC', 'SOCstock')),
    ("doi:10.15485/1631979", combine(("TC", c_1631979)), ('TC', 'SOC', 'SIC')),
    ("doi:10.15485/1839189", combine(("TC", c_1839189)), ('TC', 'SOC', 'SIC')),
    ("doi:10.15485/2350837", combine(("TC", c_2350837)), ('TC',)),
    ("doi:10.21952/WTR/1506944", combine(("TC", c_1506944)), ('TC', 'SOC', 'SIC')),
    ("doi:10.5440/1464956", combine(("TC", c_1464956)), ('TC',)),
    ("doi:10.15485/1910300", combine(("TC", c_1910300)), ('SOC',)),
    ("doi:10.21952/WTR/1572186", combine(("TC", c_1572186)), ('SOC', 'SIC')),
    ("doi:10.5440/1440029", combine(("TC", c_1440029)), ('SOC',)),
    ("doi:10.5440/1841590", combine(("pH", ph_1841590), ("TC", c_1841590)), ('pH', 'SOC')),
    ("doi:10.5440/1346200", combine(("pH", ph_1346200), ("TC", c_1346200)), ('pH', 'TC', 'DOC')),
    ("doi:10.15485/1602783", combine(("TC", c_1602783)), ('DOC',)),
    ("doi:10.15485/1962817", combine(("pH", ph_1962817)), ('pH',)),
    ("doi:10.15485/1994876", combine(("pH", ph_1994876)), ('pH',)),
    ("doi:10.15485/3025240", combine(("pH", ph_3025240)), ('pH',)),
]
