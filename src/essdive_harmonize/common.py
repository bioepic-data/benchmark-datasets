"""Share paths, readers, formatting and writers among the soil variable harmonizers.

Package harmonizers read the raw ESS-DIVE files from data/source/package_data/ and return
{variable key: DataFrame} in the harmonized layout, one row per value, as for soil pH::

    doi, source_file, id, id_type, depth, date, <V>, <v>_method, [<V>_unit, other extra columns],
    latitude, longitude, IGSN, [key column], notes

This module holds the output paths and column layout of each variable (from variables.py), the readers for the raw
package files with their missing-value rules, number / depth / date formatting, coordinate helpers (UTM, degrees
minutes seconds, KML), `assemble` / `emit`, which put one variable's rows into the layout, the writers of
<doi_slug>_soil_<V>.csv / .xlsx and a verifier for rebuilt tables. The column-mapping helpers that most package
functions use (`from_columns`, `from_long`) are in extract.py.

Examples:
    >>> doi_slug("doi:10.15485/1725884")
    '10.15485_1725884'
    >>> depth_range(0, 5.0)
    '0-5'

Attributes:
    PACKAGE_DATA: Folder of the downloaded package files (data/source/package_data).
    OUT_ROOT: Output root of the harmonization (data/processed/harmonization).
    MATRIX: Candidate matrix of the earlier hit-matrix workflow (archived; read by triage.py).
    HITS_DIR: Folder of the earlier per-variable column-hit outputs.
    LEGACY_DIRS: Output folders of the earlier harmonize_ph / harmonize_carbon runs, by short key; read-only.
    UNKNOWN: Method value when the source does not say how a value was measured. The other upper-case strings
        (PH_H2O, DRY_COMBUSTION, SALT_EXTRACTION, ICP ...) are the method vocabulary of the method columns.
    MMOL_C: mg C per mmol C.
    MISSING: Text values treated as missing.
"""

from __future__ import annotations

import io
import math
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final

import pandas as pd
from openpyxl.utils import get_column_letter

from .datatypes import Field
from .variables import PROJECT_ROOT, VARIABLES, Variable, resolve

PACKAGE_DATA: Final[Path] = PROJECT_ROOT / "data" / "source" / "package_data"
OUT_ROOT: Final[Path] = PROJECT_ROOT / "data" / "processed" / "harmonization"
MATRIX: Final[Path] = PROJECT_ROOT / "data" / "intermediate" / "ess-dive_soil_selected_variables_column_hit_matrix.csv"
HITS_DIR: Final[Path] = PROJECT_ROOT / "data" / "intermediate"

LEGACY_DIRS: Final[dict[str, str]] = {"pH": "harmonized_soilpH_data",
               **{v: f"harmonized_soil{v}_data" for v in
                  ("TC", "SOC", "DOC", "SOM", "SOCstock", "SIC", "POMC", "LOI", "WEOC", "MAOMC")}}


def variable(var: str) -> Variable:
    """Look up a variable by its key or short alias.

    Args:
        var: A variable key ('Acidity__Soil_pH') or a short alias ('pH', 'TC', 'Caexch').

    Returns:
        The variable definition.

    Raises:
        KeyError: When `var` is neither a key nor an alias.

    Examples:
        >>> variable("pH").key
        'Acidity__Soil_pH'
        >>> variable("Carbon__Total_carbon").unit
        '% (g C / 100 g dry soil)'
    """
    return VARIABLES[resolve(var)]


def processed_dir(var: str, root: Path | None = None) -> Path:
    """Return the output folder of a variable.

    Args:
        var: A variable key or short alias.
        root: Output root; OUT_ROOT when None.

    Returns:
        <root>/<variable key>.

    Examples:
        >>> processed_dir("pH", Path("/tmp/h")).as_posix()
        '/tmp/h/Acidity__Soil_pH'
    """
    return Path(root or OUT_ROOT) / variable(var).key


def base_columns(var: str) -> list[str]:
    """Return the columns of a harmonized table, without the key column and notes.

    Args:
        var: A variable key or short alias.

    Returns:
        doi, source_file, id, id_type, depth, date, the value and method columns, the variable's extra columns,
        latitude, longitude and IGSN.

    Examples:
        >>> base_columns("pH")[5:9]
        ['date', 'Acidity__Soil_pH', 'acidity__soil_ph_method', 'latitude']
    """
    v = variable(var)
    return (["doi", "source_file", "id", "id_type", "depth", "date", v.value_column, v.method_column]
            + list(v.extra) + ["latitude", "longitude", "IGSN"])


def numeric_columns(var: str) -> list[str]:
    """Return the columns stored as numbers in the Excel copies.

    Args:
        var: A variable key or short alias.

    Returns:
        The value column, latitude and longitude.

    Examples:
        >>> numeric_columns("pH")
        ['Acidity__Soil_pH', 'latitude', 'longitude']
    """
    return [variable(var).value_column, "latitude", "longitude"]


# -------------------------------------------------------------
# Method vocabulary (details such as instrument and extractant go in notes)
# -------------------------------------------------------------
UNKNOWN = "unknown"
# pH
PH_H2O = "pH_H2O"
PH_CACL2 = "pH_CaCl2"
PH_KCL = "pH_KCl"
PH_BACL2 = "pH_BaCl2"
# carbon (harmonize_carbon)
DRY_COMBUSTION = "dry_combustion"            # elemental analyzer / CHN / combustion, no acid pretreatment
TC_MINUS_TIC = "TC_minus_TIC"                # SOC: total C minus inorganic C
ACID_COMBUSTION = "acid_treated_combustion"  # SOC: carbonates removed with acid before combustion
RAMPED_COMBUSTION = "ramped_combustion"      # SOC/SIC: temperature-ramped combustion
ACIDIFICATION = "acidification"              # SIC: CO2 released by acid
TC_MINUS_TOC = "TC_minus_TOC"                # SIC: total C minus organic C
LOI_METHOD = "loss_on_ignition"              # SOM / LOI
DENSITY_FRACTIONATION = "density_fractionation"
SIZE_FRACTIONATION = "size_fractionation"
ASH_COMPLEMENT = "100_minus_ash"
WATER_EXTRACTION = "water_extraction"
SALT_EXTRACTION = "salt_extraction"
POREWATER = "porewater"
STOCK_CALC = "concentration_x_bulk_density_x_thickness"
# general
CALCULATED = "calculated"                    # derived from other reported values; formula in notes
ICP = "ICP"                                  # ICP-OES / ICP-MS after digestion or extraction
XRF = "XRF"
CORE = "core"                                # bulk density / particle density by core or ring

MMOL_C = 12.011  # mg C per mmol C


# -------------------------------------------------------------
# Naming and reading
# -------------------------------------------------------------

def doi_slug(doi: str) -> str:
    """Turn a DOI into the slug used in file and folder names.

    Args:
        doi: A DOI with or without the 'doi:' prefix.

    Returns:
        The DOI without 'doi:', slashes replaced by underscores.

    Examples:
        >>> doi_slug("doi:10.3334/CDIAC/OTG.NDP044")
        '10.3334_CDIAC_OTG.NDP044'
    """
    return doi.replace("doi:", "").replace("/", "_")


def raw_path(doi: str, file_name: str) -> Path:
    """Return the local copy of an ESS-DIVE file.

    Args:
        doi: The package DOI.
        file_name: The file name as listed on ESS-DIVE.

    Returns:
        PACKAGE_DATA/<doi_slug>_<file_name>, or the same name in a subfolder of PACKAGE_DATA when only that exists.

    Examples:
        >>> raw_path("doi:10.15485/1725884", "EastRiverFloodplainBulkDensities.csv").name
        '10.15485_1725884_EastRiverFloodplainBulkDensities.csv'
    """
    name = f"{doi_slug(doi)}_{file_name}"
    p = PACKAGE_DATA / name
    if p.exists():
        return p
    for sub in sorted(PACKAGE_DATA.iterdir()):
        if sub.is_dir() and (sub / name).exists():
            return sub / name
    return p


def _text(doi: str, file_name: str, encoding: str = "utf-8-sig") -> str:
    """Read a raw file as text, falling back to latin-1, with CR / CRLF line endings normalized."""
    raw = raw_path(doi, file_name).read_bytes()
    try:
        t = raw.decode(encoding)
    except UnicodeDecodeError:
        t = raw.decode("latin1")
    return t.replace("\r\n", "\n").replace("\r", "\n")


def read_csv(doi: str, file_name: str, **kw: Any) -> pd.DataFrame:
    """Read a raw CSV file of a package as text.

    Values are taken as written: every column is text and no value is turned into NaN.

    Args:
        doi: The package DOI.
        file_name: The file name as listed on ESS-DIVE.
        **kw: Passed to pandas.read_csv (dtype=str and keep_default_na=False unless given; `encoding` is used to
            decode the file).

    Returns:
        The table.

    Examples:
        >>> read_csv("doi:10.15485/1725884", "EastRiverFloodplainBulkDensities.csv").shape  # doctest: +SKIP
        (33, 9)
    """
    kw.setdefault("dtype", str)
    kw.setdefault("keep_default_na", False)
    enc = kw.pop("encoding", "utf-8-sig")
    return pd.read_csv(io.StringIO(_text(doi, file_name, enc)), **kw)


def read_excel(doi: str, file_name: str, **kw: Any) -> pd.DataFrame:
    """Read a raw Excel file of a package as text.

    Args:
        doi: The package DOI.
        file_name: The file name as listed on ESS-DIVE.
        **kw: Passed to pandas.read_excel (dtype=str and keep_default_na=False unless given).

    Returns:
        The sheet (or {sheet name: table} with sheet_name=None).

    Examples:
        >>> read_excel("doi:10.15485/2480291", "Initial_Characterization_20200410.xlsx",
        ...            sheet_name="pH").columns[0]  # doctest: +SKIP
        'Pit'
    """
    kw.setdefault("dtype", str)
    kw.setdefault("keep_default_na", False)
    return pd.read_excel(raw_path(doi, file_name), **kw)


def strip_bom(df: pd.DataFrame) -> pd.DataFrame:
    """Remove byte-order marks and surrounding spaces from the column names (in place).

    Args:
        df: A table read from a file.

    Returns:
        The same table.

    Examples:
        >>> strip_bom(pd.DataFrame(columns=["\ufeffSample_ID", " pH "])).columns.tolist()
        ['Sample_ID', 'pH']
    """
    df.columns = [str(c).replace("﻿", "").replace("ï»¿", "").strip() for c in df.columns]
    return df


MISSING: Final[set[str]] = {"", "NA", "N/A", "NaN", "nan", "-9999", "-9999.0", "-9999.00", "-", "na", "None", "BDL", "ND"}


def is_missing(s: Field) -> pd.Series:
    """Flag missing values: empty text and the codes in MISSING (NA, -9999, BDL ...).

    Args:
        s: Values (a column, a list or one value).

    Returns:
        A boolean Series, True where the value is missing.

    Examples:
        >>> is_missing(["5.2", "", "NA", "-9999", " 7 "]).tolist()
        [False, True, True, True, False]
    """
    return pd.Series(s).astype(str).str.strip().isin(MISSING)


def num(s: Field) -> pd.Series:
    """Convert text values to numbers.

    Missing codes and non-numeric text become NaN. A value with an uncertainty ('22.27±0.44', '5.1 +/- 0.2')
    gives the value.

    Args:
        s: Values (a column, a list or one value).

    Returns:
        A float Series.

    Examples:
        >>> num(["5.2", "NA", "22.27±0.44", "5.1 +/- 0.2", "<0.1"]).tolist()
        [5.2, nan, 22.27, 5.1, nan]
    """
    v = pd.Series(s)
    v = v.where(~is_missing(v)).astype(str).str.replace(r"\s*(±|\+/-|\+-).*$", "", regex=True).str.strip()
    return pd.to_numeric(v, errors="coerce")


def fmt_num(v: float | str) -> str:
    """Format a number without trailing zeros.

    Args:
        v: A number, or text holding one.

    Returns:
        The number as text: integers without a decimal point, others in the shortest form.

    Examples:
        >>> fmt_num(5.0), fmt_num("7.50"), fmt_num(0.00012)
        ('5', '7.5', '0.00012')
    """
    v = float(v)
    return str(int(v)) if v.is_integer() else f"{v:g}"


def depth_range(top: float | str, bottom: float | str) -> str:
    """Format a depth interval as 'top-bottom' (no unit; cm in the harmonized tables).

    Args:
        top: Upper depth.
        bottom: Lower depth.

    Returns:
        The interval, e.g. '0-5'.

    Examples:
        >>> depth_range("0", 15.0)
        '0-15'
    """
    return f"{fmt_num(top)}-{fmt_num(bottom)}"


def checked_depth(top: float | str, bottom: float | str) -> tuple[str, str]:
    """Format a depth interval, swapping the depths when the source lists top > bottom.

    Args:
        top: Upper depth as given in the source.
        bottom: Lower depth as given in the source.

    Returns:
        The interval and a note for the notes column ('' when the order was right).

    Examples:
        >>> checked_depth(0, 10)
        ('0-10', '')
        >>> checked_depth(20, 10)[0]
        '10-20'
    """
    if float(top) > float(bottom):
        return depth_range(bottom, top), f"; source depth {fmt_num(top)}-{fmt_num(bottom)} has top > bottom, written as {fmt_num(bottom)}-{fmt_num(top)}"
    return depth_range(top, bottom), ""


def fmt_value(v: float | str | None, digits: int = 6) -> str:
    """Round a converted value to strip float noise.

    Args:
        v: The value; None or NaN give ''.
        digits: Decimal places kept.

    Returns:
        The value as text.

    Examples:
        >>> fmt_value(5.2300000001), fmt_value(None), fmt_value(float("nan"))
        ('5.23', '', '')
    """
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    return f"{round(float(v), digits):g}" if abs(float(v)) < 1e15 else str(v)


fmt_tc = fmt_value  # name used by the carbon harmonizers


def iso_date(s: Field, fmt: str | None = None) -> pd.Series:
    """Format dates as YYYY-MM-DD.

    Args:
        s: Date values (a column, a list or one value).
        fmt: strptime format of the source dates; inferred when None.

    Returns:
        A Series of 'YYYY-MM-DD' strings, '' where the date is missing or cannot be parsed.

    Examples:
        >>> iso_date(["10/27/2014", "NA", "not a date"], fmt="%m/%d/%Y").tolist()
        ['2014-10-27', '', '']
    """
    d = pd.to_datetime(pd.Series(s).where(~is_missing(s)), format=fmt, errors="coerce")
    return d.dt.strftime("%Y-%m-%d").fillna("")


def must_match(pattern: str, text: str, flags: int = 0) -> re.Match[str]:
    """Search text that must have an expected form.

    Args:
        pattern: Regular expression.
        text: Text from a source file.
        flags: re flags.

    Returns:
        The match.

    Raises:
        ValueError: When the pattern is not found (the source changed form).

    Examples:
        >>> must_match("([0-9]+)-([0-9]+)[.]raw$", "pit3_10-20.raw").groups()
        ('10', '20')
        >>> must_match("[0-9]+", "no number")
        Traceback (most recent call last):
            ...
        ValueError: '[0-9]+' not found in 'no number'
    """
    m = re.search(pattern, text, flags)
    if m is None:
        raise ValueError(f"{pattern!r} not found in {text[:80]!r}")
    return m


def join_id(df: pd.DataFrame, cols: list[str]) -> tuple[pd.Series, str]:
    """Build the id and id_type columns from the source's identifying columns.

    Args:
        df: The source table.
        cols: Identifying columns, in order.

    Returns:
        The values joined with ':' (a blank part becomes 'NA') and the column names joined with ':'.

    Examples:
        >>> ids, id_type = join_id(pd.DataFrame({"Site": ["A", "B"], "Rep": ["1", ""]}), ["Site", "Rep"])
        >>> ids.tolist(), id_type
        (['A:1', 'B:NA'], 'Site:Rep')
    """
    parts = [df[c].astype(str).str.strip().replace("", "NA") for c in cols]
    out = parts[0]
    for p in parts[1:]:
        out = out + ":" + p
    return out, ":".join(cols)


# -------------------------------------------------------------
# Coordinates
# -------------------------------------------------------------

def utm_to_latlon(easting: float, northing: float, zone: int, north: bool = True) -> tuple[float, float]:
    """Convert UTM coordinates to latitude and longitude (WGS84).

    Uses the inverse transverse Mercator series of Snyder (1987), accurate to well under a metre inside a zone.

    Args:
        easting: UTM easting in metres.
        northing: UTM northing in metres.
        zone: UTM zone number.
        north: True in the northern hemisphere.

    Returns:
        Latitude and longitude in decimal degrees.

    Examples:
        >>> lat, lon = utm_to_latlon(500000, 4300000, 13)
        >>> round(lat, 5), round(lon, 5)
        (38.84882, -105.0)
    """
    a = 6378137.0
    f = 1 / 298.257223563
    e2 = f * (2 - f)
    ep2 = e2 / (1 - e2)
    k0 = 0.9996
    x = easting - 500000.0
    y = northing if north else northing - 10000000.0
    m = y / k0
    mu = m / (a * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    p = (mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu)
         + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu)
         + (151 * e1 ** 3 / 96) * math.sin(6 * mu)
         + (1097 * e1 ** 4 / 512) * math.sin(8 * mu))
    c1 = ep2 * math.cos(p) ** 2
    t1 = math.tan(p) ** 2
    n1 = a / math.sqrt(1 - e2 * math.sin(p) ** 2)
    r1 = a * (1 - e2) / (1 - e2 * math.sin(p) ** 2) ** 1.5
    d = x / (n1 * k0)
    lat = p - (n1 * math.tan(p) / r1) * (
        d ** 2 / 2
        - (5 + 3 * t1 + 10 * c1 - 4 * c1 ** 2 - 9 * ep2) * d ** 4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1 ** 2 - 252 * ep2 - 3 * c1 ** 2) * d ** 6 / 720)
    lon = (d - (1 + 2 * t1 + c1) * d ** 3 / 6
           + (5 - 2 * c1 + 28 * t1 - 3 * c1 ** 2 + 8 * ep2 + 24 * t1 ** 2) * d ** 5 / 120) / math.cos(p)
    return math.degrees(lat), (zone - 1) * 6 - 180 + 3 + math.degrees(lon)


def dms_to_decimal(text: str) -> float:
    """Convert a degrees-minutes-seconds coordinate to decimal degrees.

    Args:
        text: The coordinate with its hemisphere letter, e.g. 38°54'19.56"N; missing minutes or seconds are 0.

    Returns:
        Decimal degrees, negative for W and S.

    Examples:
        >>> round(dms_to_decimal("38 54 19.56 N"), 6)
        38.905433
        >>> dms_to_decimal("106 30 W")
        -106.5
    """
    nums = [float(x) for x in re.findall(r"[\d.]+", text)]
    while len(nums) < 3:
        nums.append(0.0)
    val = nums[0] + nums[1] / 60 + nums[2] / 3600
    return -val if re.search(r"[WSws]", text) else val


def kml_points(doi: str, file_name: str) -> dict[str, tuple[float, float]]:
    """Read the point placemarks of a package's KML file.

    Args:
        doi: The package DOI.
        file_name: The KML file name as listed on ESS-DIVE.

    Returns:
        {placemark name: (latitude, longitude)}.

    Examples:
        >>> kml_points("doi:10.15485/3377028", "PARCHED_field_sites.kml")["Sherman Crane (SC) 1C"]  # doctest: +SKIP
        (39.16..., -120.84...)
    """
    kml = raw_path(doi, file_name).read_text(errors="replace")
    out = {}
    for pm in re.findall(r"<Placemark.*?</Placemark>", kml, re.S):
        name = re.search(r"<name>(.*?)</name>", pm, re.S)
        coords = re.search(r"<coordinates>\s*([-\d.]+),([-\d.]+)", pm)
        if name and coords:
            lon, lat = coords.groups()
            out[name.group(1).strip()] = (float(lat), float(lon))
    return out


# -------------------------------------------------------------
# Assembly and output
# -------------------------------------------------------------

def assemble(df: pd.DataFrame, var: str, extra: list[str] | None = None, drop_empty: bool = True,
             tidy_values: bool = True, raw: bool = False) -> pd.DataFrame:
    """Put one variable's rows into the harmonized layout.

    Columns are ordered as base_columns(var) + extra + notes; missing columns are added empty. Rows may carry the
    value as `value` and the method as `method` instead of the variable's own column names. Rows without latitude
    or longitude are always dropped.

    Args:
        df: Rows of one variable.
        var: A variable key or short alias.
        extra: Extra key columns (e.g. source_row) written before notes.
        drop_empty: Drop rows without a numeric value.
        tidy_values: Write values with up to 10 significant digits (strips Excel float noise such as
            2.6399999999999997 without rounding away source precision).
        raw: Only order the columns: values and rows as given (the packages ported from harmonize_ph).

    Returns:
        The harmonized table.

    Examples:
        >>> rows = pd.DataFrame({"doi": "doi:10.0/x", "id": ["a", "b", "c"], "value": ["5.2", "NA", "6.39999999999"],
        ...                      "method": "pH_H2O", "latitude": ["38.9", "38.9", ""], "longitude": "-106.9"})
        >>> t = assemble(rows, "pH")
        >>> t[["id", "Acidity__Soil_pH", "acidity__soil_ph_method"]].values.tolist()
        [['a', '5.2', 'pH_H2O']]
        >>> list(t.columns[-4:])
        ['latitude', 'longitude', 'IGSN', 'notes']
    """
    v = variable(var)
    extra = extra or []
    df = df.rename(columns={"value": v.value_column, "method": v.method_column, **v.legacy_columns})
    cols = base_columns(var)
    for c in cols + ["notes"]:
        if c not in df.columns:
            df[c] = ""
    df = df[cols + extra + ["notes"]].copy()
    if raw:
        return df.reset_index(drop=True)
    for c in ("latitude", "longitude"):  # some sources pad coordinates with (non-breaking) spaces
        df[c] = df[c].astype(str).str.replace("\xa0", "", regex=False).str.strip()
    keep = ~is_missing(df["latitude"]) & ~is_missing(df["longitude"])
    values = num(df[v.value_column].astype(str).str.strip())
    if drop_empty:
        keep &= values.notna()
    df, values = df[keep].reset_index(drop=True), values[keep].reset_index(drop=True)
    if tidy_values:
        df[v.value_column] = ["" if pd.isna(x) else f"{float(x):.10g}" for x in values]
    return df


def emit(base: pd.DataFrame, var: str, value: Field, method: str | Sequence[str] | pd.Series,
         notes: str | Sequence[str] | pd.Series, extra: list[str] | None = None, **cols: Field) -> pd.DataFrame:
    """Build one variable's harmonized table from a base table of sample rows.

    Args:
        base: Sample rows: doi, source_file, id, id_type, depth, date, latitude, longitude, IGSN, key columns.
        var: A variable key or short alias.
        value: The values, row-aligned (or one value for every row).
        method: The method, one for every row or row-aligned.
        notes: The notes, one for every row or row-aligned.
        extra: Extra key columns, as for `assemble`.
        **cols: Other columns of the variable (e.g. a unit column), scalars or row-aligned.

    Returns:
        The harmonized table (see `assemble`).

    Examples:
        >>> base = pd.DataFrame({"doi": "doi:10.0/x", "id": ["a", "b"], "latitude": "38.9", "longitude": "-106.9"})
        >>> emit(base, "pH", ["7.4", "7.54"], "pH_H2O", "1:1 water")["Acidity__Soil_pH"].tolist()
        ['7.4', '7.54']
    """
    df = base.copy()
    df["value"] = _as_column(value)
    df["method"] = _as_column(method)
    df["notes"] = _as_column(notes)
    for k, val in cols.items():
        df[k] = _as_column(val)
    return assemble(df, var, extra)


def _as_column(x: Field) -> Any:
    """Keep a scalar (pandas repeats it on every row) and turn a sequence into a row-aligned list."""
    return x if x is None or isinstance(x, (str, int, float)) else list(x)


def write_table_xlsx(df: pd.DataFrame, path: str | Path, var: str, sheet: str | None = None) -> None:
    """Write the Excel copy of a harmonized table.

    The value, latitude and longitude are numbers; every other column is stored as text, so depths such as 5-15
    are not turned into dates. The header row is frozen and column widths are set.

    Args:
        df: A harmonized table.
        path: The .xlsx file to write.
        var: A variable key or short alias.
        sheet: Sheet name; 'soil_<variable key>' (cut to Excel's 31 characters) when None.

    Examples:
        >>> import tempfile
        >>> t = pd.DataFrame({"doi": ["doi:10.0/x"], "depth": ["5-15"], "Acidity__Soil_pH": ["7.4"],
        ...                   "latitude": ["38.9"], "longitude": ["-106.9"]})
        >>> with tempfile.TemporaryDirectory() as d:
        ...     write_table_xlsx(t, f"{d}/t.xlsx", "pH")
        ...     pd.read_excel(f"{d}/t.xlsx").loc[0, "depth"]
        '5-15'
    """
    sheet = sheet or f"soil_{variable(var).key}"[:31]  # Excel limit
    x = df.copy()
    numeric = numeric_columns(var)
    for c in numeric:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    with pd.ExcelWriter(path, engine="openpyxl") as w:
        x.to_excel(w, index=False, sheet_name=sheet)
        ws = w.sheets[sheet]
        for i, col in enumerate(x.columns, 1):
            letter = get_column_letter(i)
            if col not in numeric:
                for cell in ws[letter][1:]:
                    cell.number_format = "@"
            width = max(len(col), int(x[col].astype(str).str.len().max() or 0)) + 2
            ws.column_dimensions[letter].width = min(width, 60)
        ws.freeze_panes = "A2"


def package_csv(doi: str, var: str, root: Path | None = None) -> Path:
    """Return the path of a package's harmonized CSV for a variable.

    Args:
        doi: The package DOI.
        var: A variable key or short alias.
        root: Output root; OUT_ROOT when None.

    Returns:
        <root>/<variable key>/<doi_slug>/<doi_slug>_soil_<variable key>.csv.

    Examples:
        >>> package_csv("doi:10.15485/1725884", "pH", Path("/tmp/h")).as_posix()
        '/tmp/h/Acidity__Soil_pH/10.15485_1725884/10.15485_1725884_soil_Acidity__Soil_pH.csv'
    """
    slug = doi_slug(doi)
    return processed_dir(var, root) / slug / f"{slug}_soil_{variable(var).key}.csv"


def legacy_csv(doi: str, var: str, root: Path | None = None) -> Path | None:
    """Return the earlier harmonize_ph / harmonize_carbon output of a package, if that variable had one.

    Args:
        doi: The package DOI.
        var: A variable key or short alias.
        root: Folder holding harmonized_soil<V>_data/; data/processed when None (e.g. a scratch --out-dir of
            harmonize_carbon/run.py).

    Returns:
        The CSV path (it may not exist), or None for variables the earlier harmonizers did not cover.

    Examples:
        >>> legacy_csv("doi:10.15485/1725884", "pH", Path("/tmp")).as_posix()
        '/tmp/harmonized_soilpH_data/10.15485_1725884/10.15485_1725884_soil_pH.csv'
        >>> legacy_csv("doi:10.15485/1725884", "Physical__Dry_bulk_density") is None
        True
    """
    short = variable(var).short
    if short not in LEGACY_DIRS:
        return None
    slug = doi_slug(doi)
    return Path(root or PROJECT_ROOT / "data" / "processed") / LEGACY_DIRS[short] / slug / f"{slug}_soil_{short}.csv"


def write_package(df: pd.DataFrame, var: str, root: Path | None = None) -> Path:
    """Write a package's harmonized table for a variable as CSV and Excel.

    Args:
        df: The harmonized table of one package.
        var: A variable key or short alias.
        root: Output root; OUT_ROOT when None.

    Returns:
        The CSV path (see `package_csv`); the .xlsx copy is written next to it.

    Examples:
        >>> import tempfile
        >>> t = pd.DataFrame({"doi": ["doi:10.0/x"], "Acidity__Soil_pH": ["7.4"], "latitude": ["1"],
        ...                   "longitude": ["2"]})
        >>> with tempfile.TemporaryDirectory() as d:
        ...     write_package(t, "pH", Path(d)).name
        '10.0_x_soil_Acidity__Soil_pH.csv'
    """
    csv_path = package_csv(df["doi"].iloc[0], var, root)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    write_table_xlsx(df, csv_path.with_suffix(".xlsx"), var)
    return csv_path


def verify(df: pd.DataFrame, reference_csv: Path, var: str, tol: float = 1e-6, legacy: bool = False) -> list[str]:
    """Compare a rebuilt table with a reference CSV.

    Args:
        df: The rebuilt harmonized table.
        reference_csv: The CSV written earlier.
        var: A variable key or short alias.
        tol: Tolerance for the numeric columns (value, latitude, longitude).
        legacy: The reference uses the short-key column names of harmonize_ph / harmonize_carbon.

    Returns:
        One message per difference (columns, row count, or the first differing row of each column); empty when
        the tables agree.

    Examples:
        >>> import tempfile
        >>> t = pd.DataFrame({"id": ["a"], "Acidity__Soil_pH": ["7.4"], "latitude": ["1"], "longitude": ["2"]})
        >>> with tempfile.TemporaryDirectory() as d:
        ...     t.to_csv(f"{d}/ref.csv", index=False)
        ...     verify(t, Path(f"{d}/ref.csv"), "pH"), verify(t.assign(id="b"), Path(f"{d}/ref.csv"), "pH")
        ([], ["id: 1 rows differ, e.g. row 0: 'b' vs 'a'"])
    """
    numeric = numeric_columns(var)
    ref = pd.read_csv(reference_csv, dtype=str, keep_default_na=False)
    if legacy:
        ref = ref.rename(columns=variable(var).legacy_columns)
    new = df.astype(str).replace({"nan": "", "None": ""})
    issues = []
    if list(ref.columns) != list(new.columns):
        return [f"columns differ: {list(new.columns)} vs {list(ref.columns)}"]
    if len(ref) != len(new):
        return [f"row count {len(new)} vs {len(ref)}"]
    for c in ref.columns:
        if c in numeric:
            a = pd.to_numeric(new[c], errors="coerce")
            b = pd.to_numeric(ref[c], errors="coerce")
            bad = pd.Series(~(((a - b).abs() <= tol) | (a.isna() & b.isna())))
        else:
            bad = pd.Series(new[c].values != ref[c].values)
        n = int(bad.sum())
        if n:
            i = int(bad.to_numpy().argmax())
            issues.append(f"{c}: {n} rows differ, e.g. row {i}: {new[c].iloc[i]!r} vs {ref[c].iloc[i]!r}")
    return issues
