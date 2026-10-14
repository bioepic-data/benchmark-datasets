"""Detect the sample fields of a data table (id, depth, date, coordinates, IGSN) and the unit of a value column.

Everything here works on column names and values only; nothing is specific to a variable.

Examples:
    >>> df = pd.DataFrame({"Sample_ID": ["a", "b"], "Top_depth_cm": ["0", "5"], "Bottom_depth_cm": ["5", "10"],
    ...                    "Latitude": ["38.9", "38.9"], "Longitude": ["-106.9", "-106.9"], "pH": ["7.1", "7.3"]})
    >>> f = detect(df, skip={"pH"})
    >>> f.ids, f.top, f.bottom, f.lat, f.lon
    (['Sample_ID'], 'Top_depth_cm', 'Bottom_depth_cm', 'Latitude', 'Longitude')

Attributes:
    LAT: Latitude column names.
    LON: Longitude column names.
    EAST: UTM easting column names.
    NORTH: UTM northing column names.
    ZONE: UTM zone column names.
    TOP: Upper-depth column names.
    BOTTOM: Lower-depth column names.
    DEPTH: Single depth column names.
    DEPTH_NOT: Depth-like columns that are not the sample depth (water table, thaw depth ...).
    HORIZON: Horizon / layer column names.
    DATE: Date column names.
    DATE_NOT: Date-like columns that are not the sampling date (analysis, incubation ...).
    YEAR: Year column names.
    ID: Sample identifier column names.
    SITE: Site / plot / core-like column names (identifiers and join keys).
    IGSN: IGSN column names.
    TIME: A time of day in a cell.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Set as AbstractSet
from dataclasses import dataclass, field

import pandas as pd

from .. import units
from ..common import fmt_num, is_missing, iso_date, num


def _n(c: str) -> str:
    """Normalize a column name for matching: lower case, runs of space / '_' / '.' -> one space.

    Examples:
        >>> _n("Sample_ID.1")
        'sample id 1'
    """
    return re.sub(r"[\s_.]+", " ", str(c)).strip().lower()


def _rx(p: str) -> re.Pattern[str]:
    """Compile a case-insensitive pattern."""
    return re.compile(p, re.I)


LAT = _rx(r"^lat(itude)?\b|latitude|\blat\b|^lat[ _(]|[ _]lat$|lat ?dd|dec ?lat")
LON = _rx(r"^lon(g|gitude)?\b|longitude|\blong?\b|^lon[ _(]|[ _]long?$|lon ?dd|dec ?lon")
EAST = _rx(r"easting|utm ?e(ast)?\b|^x ?utm|utm ?x\b|^x ?\(m\)|^x coord")
NORTH = _rx(r"northing|utm ?n(orth)?\b|^y ?utm|utm ?y\b|^y ?\(m\)|^y coord")
ZONE = _rx(r"utm ?zone|^zone$")
TOP = _rx(r"(top|upper|start|from|min(imum)?|shallow)\W{0,3}(depth|dep)|(depth|dep)\W{0,3}(top|upper|start|from|min\b|shallow)|^top\b|^upper\b|depth ?1\b")
BOTTOM = _rx(r"(bottom|bot|lower|end|to|max(imum)?|deep)\W{0,3}(depth|dep)|(depth|dep)\W{0,3}(bottom|bot\b|lower|end|to\b|max\b|deep)|^bottom\b|^lower\b|depth ?2\b")
DEPTH = _rx(r"depth|^dep\b|depth ?interval|^increment|sample ?depth|soil ?depth")
DEPTH_NOT = _rx(r"water ?table|thaw|snow|active ?layer|bedrock|total|max(imum)? depth|frost|organic ?layer|o ?horizon|"
                r"thick|wtd|flag|method|note|unit|std|stdev|sd\b")
HORIZON = _rx(r"^horizon|horizon ?(name|code|designation)?$|^layer$|layer ?type|^soil ?layer")
DATE = _rx(r"date|datetime|time ?stamp|^time$|^sampled|collection ?date")
DATE_NOT = _rx(r"analy|process|run|received|extract|incubat|measure|lab|update|flag|doy|julian")
YEAR = _rx(r"^year$|^yr$|sampling ?year|^year ")
ID = _rx(r"sample ?(id|name|code|label|number|no|#)\b|^sample$|^samples?$|^sample ?id|^id$|^lab ?id|^core ?(id|name)|"
         r"^specimen|^field ?id|^unique ?id|^sampleid|^samplename|^igsn")
SITE = _rx(r"^site|site ?(id|name|code)|^plot|plot ?(id|name)|^location|location ?(id|name)|^core\b|^pit\b|^station|"
           r"^transect|^point|^treatment|^block|^replicate|^rep\b|^tree|^subplot|^quadrat|^well|^collar|^sampling ?(site|point|location)")
IGSN = _rx(r"igsn")


@dataclass
class Fields:
    """The sample fields of a table: column names, None when not found.

    Attributes:
        lat: Latitude column.
        lon: Longitude column.
        east: UTM easting column.
        north: UTM northing column.
        zone: UTM zone column.
        top: Upper-depth column.
        bottom: Lower-depth column.
        depth: Single depth column (when there are no top / bottom columns).
        horizon: Horizon / layer column.
        date: Sampling-date column.
        year: Year column (when there is no date column).
        ids: Sample identifier columns (up to two).
        sites: Site / plot / core-like columns (up to four).
        igsn: IGSN column.
    """
    lat: str | None = None
    lon: str | None = None
    east: str | None = None
    north: str | None = None
    zone: str | None = None
    top: str | None = None
    bottom: str | None = None
    depth: str | None = None
    horizon: str | None = None
    date: str | None = None
    year: str | None = None
    ids: list = field(default_factory=list)
    sites: list = field(default_factory=list)   # site / plot / core-like columns, used as join keys
    igsn: str | None = None


def _share_in(s: pd.Series, lo: float, hi: float) -> float:
    """Return the share of filled values that are numbers within [lo, hi].

    Examples:
        >>> _share_in(pd.Series(["38.9", "200", "", "x"]), -90, 90)
        0.3333333333333333
    """
    x = num(s)
    filled = (~is_missing(s)).sum()
    return float(((x >= lo) & (x <= hi)).sum() / filled) if filled else 0.0


def _first(cols: Iterable[str], pat: re.Pattern[str], df: pd.DataFrame | None = None,
           check: Callable[[pd.Series], bool] | None = None, exclude: re.Pattern[str] | None = None) -> str | None:
    """Return the first column whose normalized name matches pat, not exclude, and passes check on its values."""
    for c in cols:
        n = _n(c)
        if pat.search(n) and not (exclude and exclude.search(n)) and (check is None or (df is not None and check(df[c]))):
            return c
    return None


def detect(df: pd.DataFrame, skip: AbstractSet[str] = frozenset()) -> Fields:
    """Detect the sample fields of a table.

    Args:
        df: The table (cells as text).
        skip: Value columns, never taken as a sample field.

    Returns:
        The fields found. Coordinates need both columns and values in range; depth needs numeric values; a date column
        needs parseable dates.

    Examples:
        >>> df = pd.DataFrame({"Plot": ["P1", "P2"], "Depth (m)": ["0.1", "0.3"], "Year": ["2019", "2019"],
        ...                    "Easting": ["325000", "325100"], "Northing": ["4300000", "4300100"], "TC": ["2", "3"]})
        >>> f = detect(df, skip={"TC"})
        >>> f.sites, f.depth, f.year, f.east, f.north
        (['Plot'], 'Depth (m)', 'Year', 'Easting', 'Northing')
    """
    cols = [c for c in df.columns if c not in skip]
    f = Fields()
    f.lat = _first(cols, LAT, df, lambda s: _share_in(s, -90, 90) > 0.8)
    f.lon = _first(cols, LON, df, lambda s: _share_in(s, -180, 180) > 0.8)
    if not (f.lat and f.lon):
        f.lat = f.lon = None
    f.east = _first(cols, EAST, df, lambda s: _share_in(s, 1e5, 9e5) > 0.8)
    f.north = _first(cols, NORTH, df, lambda s: _share_in(s, 1e5, 1e7) > 0.8)
    if not (f.east and f.north):
        f.east = f.north = None
    f.zone = _first(cols, ZONE)
    f.top = _first(cols, TOP, df, lambda s: _share_in(s, -1e4, 1e5) > 0.5, DEPTH_NOT)
    f.bottom = _first(cols, BOTTOM, df, lambda s: _share_in(s, -1e4, 1e5) > 0.5, DEPTH_NOT)
    if not (f.top and f.bottom) or f.top == f.bottom:
        f.top = f.bottom = None
    if not f.top:
        f.depth = _first(cols, DEPTH, df, lambda s: (~is_missing(s)).mean() > 0.3, DEPTH_NOT)
    f.horizon = _first(cols, HORIZON)
    f.date = _first(cols, DATE, df, lambda s: iso_date(s.head(200)).ne("").mean() > 0.5, DATE_NOT)
    if not f.date:
        f.year = _first(cols, YEAR, df, lambda s: _share_in(s, 1900, 2100) > 0.8)
    f.ids = [c for c in cols if ID.search(_n(c)) and c not in (f.lat, f.lon)][:2]
    f.sites = [c for c in cols if SITE.search(_n(c)) and c not in f.ids and not DEPTH.search(_n(c))][:4]
    f.igsn = _first(cols, IGSN)
    return f


TIME = re.compile(r"\b\d{1,2}:\d{2}")


def time_series(df: pd.DataFrame, f: Fields, min_stamps: int = 500, per_day: float = 8) -> str:
    """Find a column with many distinct sub-daily timestamps (a sensor / logger series).

    Args:
        df: The table.
        f: Its fields.
        min_stamps: Minimum number of distinct timestamps.
        per_day: Minimum timestamps per sampled day, on average.

    Returns:
        The column name, or '' when the table is not a time series.

    Examples:
        >>> stamps = pd.date_range("2021-06-01", periods=600, freq="15min").strftime("%Y-%m-%d %H:%M")
        >>> time_series(pd.DataFrame({"DateTime": stamps, "pH": "7"}), Fields())
        'DateTime'
        >>> time_series(pd.DataFrame({"Date": ["2021-06-01"] * 3, "pH": "7"}), Fields())
        ''
    """
    for c in df.columns:
        if not (DATE.search(_n(c)) or re.search(r"time|stamp", _n(c))):
            continue
        s = df[c].astype(str)
        if s.str.contains(TIME).mean() >= 0.5 and s.nunique() >= min_stamps:
            days = s.str.extract(r"(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}/\d{1,2}/\d{2,4})")[0].nunique()
            if s.nunique() / max(days, 1) >= per_day:
                return c
    return ""


# ---------------------------------------------------------------------------------------------------------------
# depth and date strings in the soil pH layout
# ---------------------------------------------------------------------------------------------------------------
def _depth_factor(*names: str | None) -> tuple[float, str]:
    """Return the factor to cm from a depth column name or unit, and a note when it is not cm.

    Examples:
        >>> _depth_factor("Depth (m)"), _depth_factor("depth_cm")
        ((100.0, 'depth converted from m to cm'), (1.0, ''))
    """
    t = " ".join(_n(n) for n in names if n)
    if re.search(r"\bmm\b|\(mm\)|millimet", t):
        return 0.1, "depth converted from mm to cm"
    if re.search(r"\(m\)|\bm\b|meter|metre|\bin m\b|_m$", t) and not re.search(r"\bcm\b|centim", t):
        return 100.0, "depth converted from m to cm"
    if re.search(r"\binch|\bin\b\)", t):
        return 2.54, "depth converted from inches to cm"
    return 1.0, ""


def depths(df: pd.DataFrame, f: Fields, units_row: dict[str, str]) -> tuple[list[str], str]:
    """Build the depth strings of the rows (cm, without unit, as in the soil pH layout).

    Args:
        df: The table.
        f: Its fields.
        units_row: Column -> unit from a units row.

    Returns:
        One depth per row ('0-5', '15', or a horizon code) and a note naming the source columns and any conversion.

    Examples:
        >>> df = pd.DataFrame({"Top": ["0", "0.05"], "Bottom": ["0.05", "0.15"]})
        >>> depths(df, Fields(top="Top", bottom="Bottom"), {"Top": "m"})
        (['0-5', '5-15'], 'depth from Top, Bottom; depth converted from m to cm')
        >>> depths(pd.DataFrame({"Depth": ["0-10", "15", "NA"]}), Fields(depth="Depth"), {})
        (['0-10', '15', ''], 'depth from Depth')
    """
    if f.top:
        k, note = _depth_factor(f.top, units_row.get(f.top, ""))
        assert f.bottom is not None  # set together with f.top
        tops, bottoms = num(df[f.top]) * k, num(df[f.bottom]) * k
        out = ["" if pd.isna(x) or pd.isna(y) else f"{fmt_num(round(min(x, y), 4))}-{fmt_num(round(max(x, y), 4))}"
               for x, y in zip(tops, bottoms)]
        return out, "; ".join(x for x in (f"depth from {f.top}, {f.bottom}", note) if x)
    if f.depth:
        k, note = _depth_factor(f.depth, units_row.get(f.depth, ""))
        out = []
        for s in df[f.depth].astype(str):
            m = re.fullmatch(r"\s*(-?[\d.]+)\s*(?:-|–|to)\s*(-?[\d.]+)\s*(cm|m|mm)?\s*", s)
            if m:
                a, b = float(m.group(1)) * k, float(m.group(2)) * k
                out.append(f"{fmt_num(round(a, 4))}-{fmt_num(round(b, 4))}")
            elif re.fullmatch(r"\s*-?[\d.]+\s*", s) and not is_missing(pd.Series([s])).iloc[0]:
                out.append(fmt_num(round(float(s) * k, 4)))
            else:
                out.append("" if is_missing(pd.Series([s])).iloc[0] else s)
        return out, "; ".join(x for x in (f"depth from {f.depth}", note) if x)
    if f.horizon:
        return list(df[f.horizon].astype(str)), f"depth: horizon from {f.horizon}"
    return [""] * len(df), ""


def dates(df: pd.DataFrame, f: Fields) -> list:
    """Build the dates of the rows: YYYY-MM-DD from a date column, the year from a year column, else ''.

    Examples:
        >>> dates(pd.DataFrame({"Date": ["10/27/2014"]}), Fields(date="Date"))
        ['2014-10-27']
        >>> dates(pd.DataFrame({"Year": ["2019"]}), Fields(year="Year"))
        ['2019']
    """
    if f.date:
        return list(iso_date(df[f.date]))
    if f.year:
        y = num(df[f.year])
        return ["" if pd.isna(x) else str(int(x)) for x in y]
    return [""] * len(df)


# id columns, in the order they are tried (user decision 2026-10-13): sample ids, then core, site, plot, then the other
# site-like columns (location, station, pit, tree, block, replicate, treatment ...); IGSN last, it has its own column
KEY_ORDER = [_rx(r"sample|specimen|^lab ?id|^field ?id|^unique ?id|^id$"), _rx(r"^core|core ?(id|name|code)"),
             _rx(r"^site|site ?(id|name|code)"), _rx(r"^plot|plot ?(id|name|code)|^subplot")]
# site-like columns for the id only (not join keys for locations): 'Field_Site', 'Topographic_Position' (1577267);
# replicates anywhere in the name and sites after a word: 'Field_replicate', 'Lab_replicate', 'Soil Site' (1618870)
KEY_EXTRA = _rx(r"sample ?(site )?code|sample ?label|field ?site|topograph|(landscape|slope|hillslope|catena) ?position|"
                r"micro ?topo|replicate|\brep\b|\bsite\b")
KEY_NOT = _rx(r"date|time|year|depth|horizon|layer|\bunits?\b|method|notes?\b|comments?|description|type|"
              r"elevation|area|size|weight|mass|volume|diameter|dbh")
SIMPLE_ID = re.compile(r"\s*\d+(\.0)?\s*")


def _measurement(s: pd.Series) -> bool:
    """Whether a column holds measurements: at least half of its filled values are decimal numbers (140.91, 4.26).

    Examples:
        >>> _measurement(pd.Series(["140.91", "0.6", "4.26"])), _measurement(pd.Series(["1", "2", "A1"]))
        (True, False)
    """
    v = s.astype(str).str.strip()
    v = v[~is_missing(v) & (v != "")]
    return bool(len(v)) and float(v.str.fullmatch(r"[-+]?\d*\.\d*[1-9]\d*").mean()) >= 0.5


def _key_columns(df: pd.DataFrame, f: Fields, skip: AbstractSet[str] = frozenset()) -> list:
    """The columns that can identify a sample, in the order they are tried; IGSN last.

    Sample / core / site / plot columns first (KEY_ORDER), then the other site-like columns (Fields.sites: location,
    station, treatment, replicate ...). Coordinate, depth, date and empty columns are left out: they are written in
    their own columns (2566016 had id Site_Name:Site_Lat:Site_Long). So are the value columns (skip) and other
    measurement columns ('Site_soil_pH', 'Site_soil_total_P' match '^site', 2523672).
    """
    cols = [c for c in df.columns if (ID.search(_n(c)) or SITE.search(_n(c)) or KEY_EXTRA.search(_n(c)))
            and not KEY_NOT.search(_n(c)) and c not in (f.lat, f.lon, f.east, f.north, f.igsn) and c not in skip
            and not any(p.search(_n(c)) for p in (LAT, LON, EAST, NORTH, DEPTH, TOP, BOTTOM))
            and (~is_missing(df[c].astype(str).str.strip())).any() and not _measurement(df[c])]
    rank = {c: next((i for i, p in enumerate(KEY_ORDER) if p.search(_n(c))), len(KEY_ORDER)) for c in cols}
    cols = sorted(cols, key=lambda c: rank[c])
    return cols + ([f.igsn] if f.igsn and f.igsn in df.columns else [])


def _informative(s: pd.Series) -> bool:
    """Whether a column's values say something on their own: not only small whole numbers (1, 2, 3 ...).

    Examples:
        >>> _informative(pd.Series(["1", "2", "3"])), _informative(pd.Series(["ER-01", "ER-02"]))
        (False, True)
    """
    v = s.astype(str).str.strip()
    v = v[~is_missing(v)]
    return bool(len(v)) and not v.str.fullmatch(SIMPLE_ID).all()


def _key(df: pd.DataFrame, cols: list, extra: list) -> pd.Series:
    """The columns joined with ':' (blank parts 'NA'), then the extra parts (depth, date)."""
    out = pd.Series([""] * len(df), index=df.index, dtype=object)
    parts = [df[c].astype(str).str.strip() for c in cols] + [pd.Series(x, index=df.index, dtype=str) for x in extra]
    for i, p in enumerate(parts):
        p = p.where(~is_missing(p) & (p != ""), "NA")
        out = p if i == 0 else out + ":" + p
    return out


def ids(df: pd.DataFrame, f: Fields, depth: list | None = None, date: list | None = None,
        rows: pd.Series | None = None, skip: AbstractSet[str] = frozenset()) -> tuple[list, str, str]:
    """Build the id and id_type of the rows: unique and informative (user decisions 2026-10-13 and 2026-10-14).

    1. A sample / core / site / plot column whose values are unique and informative (not only 1, 2, 3 ...) is the id.
    2. Otherwise the descriptive columns are joined, informative ones first, each in the order of _key_columns
       (sample ids, core, site, plot, then location, field site, block, topographic position, replicate ... in table
       order), each one only when it tells more rows apart, until the ids are unique.
    3. Still repeated: the depth, then the date, as written in the depth / date columns, when they tell rows apart.
    4. Still repeated, as a last resort: the id columns that are only numbers (a lab number 'Lab_ID_LBNL' 1, 2, 3 ...),
       then IGSN (it has its own column), each when it tells rows apart. doi:10.15485/1577267 gets
       Location:Field_Site:Block:Plot:Topographic_Position:Replicate:depth:date:Lab_ID_LBNL: the descriptive columns
       leave 27 snow-pit cores (three per pit, depth and date) that only the lab number tells apart.
    A column that only adds a suffix to another is left out (_drop_suffix_ids). Ids still repeated are kept, with a
    note (one sample on several rows, 1185213 incubation time points). No id column at all: the row number
    ('source_row').

    Args:
        df: The table.
        f: Its fields.
        depth: The harmonized depth of the rows.
        date: The harmonized date of the rows.
        rows: The rows that are written (with a value); the ids must be unique over these. All rows when None.
        skip: The value columns (never id parts).

    Returns:
        The ids, the names of their parts joined with ':' ('depth', 'date' for those) and a note ('' when unique).

    Examples:
        >>> ids(pd.DataFrame({"Sample_ID": ["a", "b"]}), Fields())
        (['a', 'b'], 'Sample_ID', '')
        >>> ids(pd.DataFrame({"pH": ["7", "8"]}), Fields())
        (['1', '2'], 'source_row', '')
        >>> d = pd.DataFrame({"Site_Name": ["Outer", "Outer"], "Site_Lat": ["9.4", "9.4"]})
        >>> ids(d, Fields(lat="Site_Lat"), depth=["30", "60"])
        (['Outer:30', 'Outer:60'], 'Site_Name:depth', '')
        >>> ids(pd.DataFrame({"Plot": ["A", "A", "B"], "Core": ["1", "2", "1"]}), Fields())
        (['A:1', 'A:2', 'B:1'], 'Plot:Core', '')
        >>> d = pd.DataFrame({"Lab_ID": ["1", "2", "3", "4"], "Plot": ["A1", "A1", "A1", "B1"]})
        >>> ids(d, Fields(), depth=["0-5", "0-5", "5-15", "0-5"])   # the lab number last, only where needed
        (['A1:0-5:1', 'A1:0-5:2', 'A1:5-15:3', 'B1:0-5:4'], 'Plot:depth:Lab_ID', '')
        >>> ids(pd.DataFrame({"transect": ["W", "W"], "igsn": ["I1", "I2"]}), Fields(igsn="igsn"))
        (['W:I1', 'W:I2'], 'transect:igsn', '')
        >>> ids(pd.DataFrame({"Plot": ["A", "A"]}), Fields())
        (['A', 'A'], 'Plot', 'id not unique: 2 rows share an id')
    """
    n = len(df)
    depth = depth if depth is not None else [""] * n
    date = date if date is not None else [""] * n
    sel = rows.to_numpy() if rows is not None and bool(rows.any()) else pd.Series(True, index=df.index).to_numpy()
    cand = _key_columns(df, f, skip)
    if not cand:
        return [str(i + 1) for i in range(n)], "source_row", ""

    def distinct(cols: list, extra: list) -> int:
        return int(_key(df, cols, extra)[sel].nunique())

    def unique(cols: list, extra: list) -> bool:
        return distinct(cols, extra) == int(sel.sum())

    # 1. one unique, informative column
    for c in cand:
        if c != f.igsn and _informative(df[c]) and unique([c], []):
            return list(_key(df, [c], [])), c, ""
    # 2. the descriptive columns; an id column of numbers only and IGSN are kept for the last resort (step 4)
    last = [c for c in cand if c != f.igsn and ID.search(_n(c)) and not _informative(df[c])] + \
           [c for c in cand if c == f.igsn]
    descriptive = [c for c in cand if c not in last and _informative(df[c])] + \
                  [c for c in cand if c not in last and not _informative(df[c])]   # Plot before a Replicate 1, 2, 3
    cols: list = []
    for c in descriptive:
        if not cols or distinct(cols + [c], []) > distinct(cols, []):
            cols.append(c)
        if unique(cols, []):
            break
    # 3. the depth, then the date; 4. the last-resort id columns
    extra: list = []
    names = list(cols)
    for name, vals in (("depth", depth), ("date", date)):
        if not unique(cols, extra) and distinct(cols, extra + [vals]) > distinct(cols, extra):
            extra.append(vals)
            names.append(name)
    tail: list = []
    for c in last:
        if unique(cols + tail, extra):
            break
        if not (cols or extra or tail) or distinct(cols + tail + [c], extra) > distinct(cols + tail, extra):
            tail.append(c)
    keep = _drop_suffix_ids(df, cols + tail)
    cols, tail = [c for c in cols if c in keep], [c for c in tail if c in keep]
    names = [x for x in names if x in cols or x in ("depth", "date")] + tail
    out = _key(df, cols, extra)
    if tail:
        out = out.where(out == "", out + ":") + _key(df, tail, []) if (cols or extra) else _key(df, tail, [])
    dup = int(out[sel].duplicated(keep=False).sum())
    return list(out), ":".join(names), (f"id not unique: {dup} rows share an id" if dup else "")


def _joined(df: pd.DataFrame, cols: list) -> pd.Series:
    """The identifying columns of the rows joined with ':'."""
    return df[cols].astype(str).apply(lambda r: ":".join(x.strip() for x in r), axis=1)


def _drop_suffix_ids(df: pd.DataFrame, cols: list) -> list:
    """Leave out an id column whose every value is another id column's value plus a suffix.

    A column like 'core.id.hor.incub.DNA' (19UW-01-A-LIn-gDNA) only repeats 'core.id.hor.incub' (19UW-01-A-LIn) with
    the DNA library added: the shorter column identifies the sample. The longer one is kept when leaving it out would
    give two rows the same id that were told apart before (1959350).

    Examples:
        >>> d = pd.DataFrame({"a": ["s1", "s2"], "b": ["s1-gDNA", "s2-cDNA"]})
        >>> _drop_suffix_ids(d, ["a", "b"])
        ['a']
        >>> _drop_suffix_ids(pd.DataFrame({"a": ["s1", "s1"], "b": ["s1-gDNA", "s1-cDNA"]}), ["a", "b"])
        ['a', 'b']
        >>> _drop_suffix_ids(pd.DataFrame({"a": ["s1", "s2"], "b": ["x1", "x2"]}), ["a", "b"])
        ['a', 'b']
    """
    cols = list(cols)
    for b in list(cols):
        vb = df[b].astype(str).str.strip()
        for a in cols:
            if a == b:
                continue
            va = df[a].astype(str).str.strip()
            both = ~is_missing(va) & ~is_missing(vb)
            if not both.any() or (is_missing(va) & ~is_missing(vb)).any():
                continue
            extends = [y == x or (y.startswith(x) and y[len(x)] in "-_.: ") for x, y in zip(va[both], vb[both])]
            if not all(extends) or (va[both] == vb[both]).all():
                continue
            rest = [c for c in cols if c != b]
            if _joined(df, rest).duplicated().sum() > _joined(df, cols).duplicated().sum():
                continue
            cols = rest
            break
    return cols


# ---------------------------------------------------------------------------------------------------------------
# units of a value column
# ---------------------------------------------------------------------------------------------------------------
_UNIT_WORDS = {"pct": "%", "percent": "%", "perc": "%", "per": "/", "wt%": "%", "ppm": "ppm", "ppb": "ppb",
               "permil": "permil", "permille": "permil"}


_DRY = re.compile(r"(?i)(dry)?(soil|sed(iment)?|peat|dw|wt)$")


def _clean_unit_token(t: str) -> str:
    """Clean one unit token of a column name: 'per' written together, dry-soil words, units written together.

    Examples:
        >>> _clean_unit_token("mgCpergdrysoil"), _clean_unit_token("gcm3"), _clean_unit_token("mgkg")
        ('mgC/g', 'g/cm3', 'mg/kg')
    """
    t = re.sub(r"(?<=[A-Za-z0-9])per(?=[a-zµ])", "/", t)
    m = re.fullmatch(r"(?i)([munµk]?g)(c?m3|cc|ml|kg|g|l)(-1)?", t)
    if m:
        t = f"{m.group(1)}/{m.group(2)}"
    return "/".join(_DRY.sub("", x) or x for x in t.split("/"))


def _candidates_from_name(name: str) -> list[str]:
    """List the unit candidates found in a column name: bracketed text, text after a comma or dash, and name tails.

    Examples:
        >>> _candidates_from_name("TOC (g/kg)")[:1]
        ['g/kg']
        >>> "mM" in _candidates_from_name("DOC, mM")
        True
    """
    out = []
    if "," in name:
        out.append(name.rsplit(",", 1)[1])
    out += [p for p in name.split("-")[1:] if "/" in p or re.search(r"[a-z]", p)]  # 'EC-12cm-mS/m' -> 'mS/m' 
    # R-style names write 'per' as a dot: 'kg.ha' -> 'kg/ha'
    out += [f"{a}/{b}" for a, b in re.findall(r"(?i)(?<![a-z])([munµk]?g)\.(ha|m2)(?![a-z0-9])", name)]
    name = re.sub(r"(?<=[A-Za-z])\.(?=[A-Za-z])", " ", name)
    for m in re.findall(r"[\(\[]([^\)\]]{1,30})[\)\]]", name):
        out.append(m)
    if "%" in name:
        out.append("%")
    toks = [_clean_unit_token(t) for t in re.split(r"[\s_]+", name.strip()) if t]
    for i in range(1, len(toks)):
        tail = [_UNIT_WORDS.get(t.lower(), t) for t in toks[i:]]
        out.append(" ".join(tail).replace(" / ", "/"))
        if len(tail) == 2:
            out.append(f"{tail[0]}/{tail[1]}")
    for t in toks:
        if t.lower() in _UNIT_WORDS and _UNIT_WORDS[t.lower()] != "/":
            out.append(_UNIT_WORDS[t.lower()])
        if "/" in t:                # a unit followed by a species tag: 'mg/kg_NO3-N' -> 'mg/kg'
            out.append(t)
        m = re.fullmatch(r"([unmµ]?g)([A-Z][a-z]?)?(k?g)(?:soil|dw|dry)?", t)
        if m:                       # run-together units: 'ugNgsoil' -> 'ug N/g'
            out.append(f"{m.group(1)} {m.group(2) or ''}/{m.group(3)}".replace(" /", "/"))
    return out


def _from_text(column: str, text: str) -> list[str]:
    """Find units written after a column name in the package description, as in 'WEOC (mg C kg-1)'.

    Examples:
        >>> _from_text("WEOC", "Water-extractable organic carbon, WEOC (mg C kg-1), was measured")
        ['mg C kg-1']
    """
    if not text or len(column) < 2:
        return []
    return re.findall(rf"\b{re.escape(column)}\b\s*[\(\[]([^\)\]]{{1,25}})[\)\]]", text, re.I)


def unit_of(column: str, units_row: str, dictionary_unit: str, targets: list[str], group: str = "",
            text: str = "", **kw: float | None) -> tuple[str | None, str]:
    """Find the unit of a value column.

    Sources, in order: the units row under the header, the data dictionary, the column name, the group row above it,
    the package description. The first candidate that converts to one of the target units is used.

    Args:
        column: The column name.
        units_row: Its unit from a units row ('' when none).
        dictionary_unit: Its unit from the package's data dictionary ('' when none).
        targets: The variable's standard units.
        group: The label of a group row above it.
        text: The package description.
        **kw: `molar_mass` and `valence`, as for units.factor.

    Returns:
        The source unit and where it was found, or (None, '') when no candidate converts.

    Examples:
        >>> unit_of("TOC (g/kg)", "", "", ["%"])
        ('g/kg', 'column name')
        >>> unit_of("Ca", "", "", ["%"], group="XRF (%)")
        ('%', 'group header')
        >>> unit_of("Moisture", "", "", ["%"])
        (None, '')
        >>> unit_of("P", "mM", "ppm", ["mg kg-1"])     # a units row that does not convert is kept in the note
        ('ppm', "data dictionary; units row says 'mM'")
    """
    conflict = ""
    u = (units_row or "").strip()
    if u and u.lower() not in ("-", "na", "n/a", "none", "unitless", "dimensionless"):
        try:
            units.parse(u)
            if not any(units.convertible(u, t, **kw) for t in targets):
                conflict = f"; units row says '{u}'"
        except units.UnitError:
            pass
    for where, cands in (("units row", [units_row]), ("data dictionary", [dictionary_unit]),
                         ("column name", _candidates_from_name(column)),
                         ("group header", _candidates_from_name(group) if group else []),
                         ("package description", _from_text(column, text))):
        for u in cands:
            u = (u or "").strip()
            if not u or u.lower() in ("-", "na", "n/a", "none", "unitless", "dimensionless"):
                continue
            for t in targets:
                try:
                    units.factor(u, t, **kw)
                    return u, where + conflict
                except units.UnitError:
                    continue
    return None, ""
