"""Locate the samples of a table, with the location-to-sample logic of the soil pH harmonization.

Each row of a data table gets latitude / longitude from the first source that works, in this order:

- group 1: latitude / longitude columns in the table itself (per sample);
- group 3: joined by a site / plot / sample key from another table of the package, a KML / KMZ file or a named
  point in the package metadata;
- group 4: UTM easting / northing columns in the table, converted (zone from a zone column or the metadata);
- group 2: the package metadata when it gives one point (all spatialCoverage points identical);
- bbox: centre of the metadata extent, noted as 'metadata bounding box centre (±N km)' (user decision 2026-10-07;
  N is half the extent's diagonal).

The source is written at the start of notes ('lat/long source: ...') and returned as the group label.

Attributes:
    MIN_JOIN_SHARE: Share of data rows a join key must match.
    Point: (latitude, longitude).
    Extent: (north, west, south, east).
    Place: (name, north, west, south, east).
    KeyedPoints: Normalized join key -> point.
    LocationSource: (description for notes, keyed points).
    US: Place names in the United States (to correct positive longitudes, a sign error seen in ESS-DIVE metadata).
    STOP: Words left out of a place name's initials.
"""

from __future__ import annotations

import json
import math
import re
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Final, TypeAlias

import pandas as pd

from ..common import doi_slug, is_missing, num, utm_to_latlon
from .config import META_DIR, PACKAGE_DATA
from .fields import Fields, detect
from .tables import package_tables, read_table, source_name

MIN_JOIN_SHARE: Final = 0.5     # share of data rows a join key must match

Point: TypeAlias = tuple[float, float]                      # (latitude, longitude)
Extent: TypeAlias = tuple[float, float, float, float]       # (north, west, south, east)
Place: TypeAlias = tuple[str, float, float, float, float]   # (name, north, west, south, east)
KeyedPoints: TypeAlias = dict[str, Point]                   # normalized join key -> point
LocationSource: TypeAlias = tuple[str, KeyedPoints]         # (description for notes, points)


@dataclass
class Location:
    """The locations of a table's rows.

    Attributes:
        lat: Latitude per row (None where not found).
        lon: Longitude per row.
        note: 'lat/long source: ...' per row.
        group: '1', '3', '4', '2' or 'bbox'.
    """
    lat: list[float | None]
    lon: list[float | None]
    note: list[str]     # per row 'lat/long source: ...'
    group: str          # '1', '3', '4', '2', 'bbox'


# ---------------------------------------------------------------------------------------------------------------
# metadata
# ---------------------------------------------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _meta_index() -> dict[str, list[dict[str, Any]]]:
    """Read the spatialCoverage of every package: {doi: places} (cached)."""
    out: dict[str, list[dict[str, Any]]] = {}
    for f in META_DIR.glob("ess-dive_meta_*.json"):
        ds = json.loads(f.read_text()).get("dataset", {})
        out[ds.get("@id", "")] = ds.get("spatialCoverage") or []
    return out


# Places in the United States written with a positive longitude (a sign error seen in ESS-DIVE metadata) are flipped.
US = re.compile(r"united states|\busa\b|\bu\.s\.|, ?(AK|AL|AZ|CA|CO|CT|FL|GA|ID|IL|IN|KS|KY|LA|MA|MD|ME|MI|MN|MO|MT|NC|"
                r"ND|NE|NH|NJ|NM|NV|NY|OH|OK|OR|PA|SC|SD|TN|TX|UT|VA|VT|WA|WI|WV|WY)\b|alaska|colorado|tennessee|"
                r"minnesota|california|oregon|washington|michigan|massachusetts")


def places(doi: str) -> list[Place]:
    """Return the spatialCoverage places of a package.

    US place names with positive longitudes are corrected (a sign error seen in ESS-DIVE metadata): once one place names
    a US location, every positive longitude of the package in the US range is flipped.

    Args:
        doi: The package DOI.

    Returns:
        (name, north, west, south, east) per place.

    Examples:
        >>> places("doi:10.15485/1898051")[1]  # doctest: +SKIP
        ('Bartlett Experimental Forest, NH [longitude sign corrected]', 44.0647, -71.288, 44.0647, -71.288)
    """
    out: list[Place] = []
    for p in _meta_index().get(doi, []):
        g = {x.get("name"): x for x in p.get("geo") or [] if isinstance(x, dict)}
        if "Northwest" in g and "Southeast" in g:
            nw, se = g["Northwest"], g["Southeast"]
            try:
                out.append((str(p.get("description", "")), float(nw["latitude"]), float(nw["longitude"]),
                            float(se["latitude"]), float(se["longitude"])))
            except (KeyError, TypeError, ValueError):
                continue
    # once one place names a US location, every positive longitude of the package in the US range is flipped
    if any(US.search(n) and w > 0 for n, _, w, _, _ in out):
        out = [(n + " [longitude sign corrected]", a, -e, c, -w) if w > 0 and 60 < w < 170 and 18 < a < 72
               else (n, a, w, c, e) for n, a, w, c, e in out]
    return out


def _km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in km between two points.

    Examples:
        >>> round(_km(38.9, -106.9, 39.0, -106.9), 2)
        11.12
    """
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * r * math.asin(math.sqrt(min(1.0, a)))


def extent(doi: str) -> Extent | None:
    """Return the extent of every metadata place of a package: (north, west, south, east), or None without places."""
    ps = places(doi)
    if not ps:
        return None
    lats = [x for p in ps for x in (p[1], p[3])]
    lons = [x for p in ps for x in (p[2], p[4])]
    return max(lats), min(lons), min(lats), max(lons)


def _inside(lat: float, lon: float, ext: Extent | None, pad: float = 1.0) -> bool:
    """Tell whether a point lies inside an extent padded by `pad` degrees (always True without an extent).

    Examples:
        >>> _inside(39.0, -107.0, (40.0, -108.0, 38.0, -106.0)), _inside(10.0, 10.0, (40.0, -108.0, 38.0, -106.0))
        (True, False)
    """
    if ext is None:
        return True
    n, w, s, e = ext
    return s - pad <= lat <= n + pad and w - pad <= lon <= e + pad


# ---------------------------------------------------------------------------------------------------------------
# join keys
# ---------------------------------------------------------------------------------------------------------------
def _norm(v: Any) -> str:
    """Normalize a join key: lower case, letters and digits only.

    Examples:
        >>> _norm(" Plot-A 1 ")
        'plota1'
    """
    return re.sub(r"[^a-z0-9]", "", str(v).lower())


def _key_columns(df: pd.DataFrame, f: Fields) -> list[str]:
    """List the join-key candidates of a table: id / site-like columns, then mostly-text columns."""
    texty = [c for c in df.columns if c not in (f.lat, f.lon, f.east, f.north)
             and num(df[c]).notna().mean() < 0.5 and (~is_missing(df[c])).mean() > 0.5]
    return list(dict.fromkeys(f.ids + f.sites + texty))


def _kml_points(path: Path) -> KeyedPoints:
    """Read the point placemarks of a KML or KMZ file: {name: (latitude, longitude)}.

    Examples:
        >>> import tempfile
        >>> kml = "<Placemark><name>P1</name><Point><coordinates>-106.9,38.9,0</coordinates></Point></Placemark>"
        >>> with tempfile.TemporaryDirectory() as d:
        ...     _ = (Path(d) / "s.kml").write_text(kml)
        ...     _kml_points(Path(d) / "s.kml")
        {'P1': (38.9, -106.9)}
    """
    if path.suffix.lower() == ".kmz":
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".kml")]
            text = z.read(names[0]).decode("utf-8", "replace") if names else ""
    else:
        text = path.read_text(errors="replace")
    out: KeyedPoints = {}
    for pm in re.findall(r"<Placemark.*?</Placemark>", text, re.S):
        name = re.search(r"<name>(.*?)</name>", pm, re.S)
        c = re.search(r"<coordinates>\s*([-\d.]+)\s*,\s*([-\d.]+)", pm)
        if name and c:
            out[name.group(1).strip()] = (float(c.group(2)), float(c.group(1)))
    return out


@lru_cache(maxsize=512)
def location_sources(doi: str) -> list[LocationSource]:
    """Collect every keyed location source of a package (cached).

    Sources are the package's other tables with coordinate columns (one per key column), its KML / KMZ files and its
    named metadata points; keys whose points are more than 1 km apart are dropped.

    Args:
        doi: The package DOI.

    Returns:
        (description for notes, {normalized key: (latitude, longitude)}) per source.
    """
    from .candidates import headers  # cached header table
    h = headers()
    out: list[LocationSource] = []
    ext = extent(doi)
    for file, sheet in package_tables(doi, h):
        try:
            t = read_table(file, sheet)
        except Exception:  # noqa: BLE001 - unreadable tables are simply not a location source
            continue
        f = detect(t.data)
        if f.lat:
            lat, lon = num(t.data[f.lat]), num(t.data[f.lon])
        elif f.east:
            continue
        else:
            continue
        ok = lat.notna() & lon.notna()
        for key in _key_columns(t.data, f):
            vals = t.data.loc[ok, key].map(_norm)
            if (vals == "").mean() > 0.2 or vals.nunique() < 2:
                continue
            m: dict[str, list[Point]] = {}
            for k, a, b in zip(vals, lat[ok], lon[ok]):
                if k and _inside(a, b, ext):
                    m.setdefault(k, []).append((a, b))
            keyed = _unambiguous(m)
            if keyed:
                out.append((f"{doi}:{source_name(file)}{' [' + sheet + ']' if sheet else ''} (joined on {key})", keyed))
    for p in sorted(PACKAGE_DATA.glob(doi_slug(doi) + "_*")):
        if p.suffix.lower() in (".kml", ".kmz"):
            try:
                pts = _kml_points(p)
            except Exception:  # noqa: BLE001
                continue
            if pts:
                out.append((f"{doi}:{source_name(p.name)} (KML placemark)",
                            {_norm(k): v for k, v in pts.items() if _inside(v[0], v[1], ext)}))
    named: dict[str, list[Point]] = {}
    for name, n, w, s, e in places(doi):
        if _km(n, w, s, e) < 1.0:
            for k in _place_keys(name):
                named.setdefault(k, []).append(((n + s) / 2, (w + e) / 2))
    named_points = _unambiguous(named)
    if named_points:
        out.append((f"{doi} package spatialCoverage named point", named_points))
    return out


STOP = {"of", "the", "and", "at", "in", "on", "for", "a", "an", "site", "station"}


def _place_keys(name: str) -> set[str]:
    """Build the join keys of a metadata place.

    Keys are the full name, each part between ',' or ';', and the initials of the first part.

    Examples:
        >>> sorted(_place_keys("Harvard Forest, MA"))
        ['harvardforest', 'harvardforestma', 'hf']
    """
    name = name.replace(" [longitude sign corrected]", "")
    parts = [p.strip() for p in re.split(r"[;,]", name) if p.strip()]
    keys = {_norm(name)} | {_norm(p) for p in parts if len(_norm(p)) >= 3}
    if parts:
        words = [w for w in re.findall(r"[A-Za-z]+", parts[0]) if w.lower() not in STOP]
        if len(words) >= 2:
            keys.add("".join(w[0] for w in words).lower())
    return {k for k in keys if k}


def _unambiguous(m: dict[str, list[Point]]) -> KeyedPoints:
    """Average each key's points, dropping keys whose points are more than 1 km apart.

    Examples:
        >>> _unambiguous({"a": [(38.9, -106.9), (38.9, -106.9)], "b": [(38.9, -106.9), (39.9, -106.9)]})
        {'a': (38.9, -106.9)}
    """
    out: KeyedPoints = {}
    for k, pts in m.items():
        a, b = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
        if all(_km(a, b, x, y) <= 1.0 for x, y in pts):
            out[k] = (a, b)
    return out


def _join(df: pd.DataFrame, f: Fields,
          sources: Sequence[LocationSource]) -> tuple[pd.Series, pd.Series, str] | None:
    """Join the table rows onto the best location source: exact key first, then the longest key prefix.

    Args:
        df: The table.
        f: Its fields.
        sources: The package's location sources.

    Returns:
        Latitude and longitude per row and the note, or None when no key matches MIN_JOIN_SHARE of the rows.

    Examples:
        >>> df = pd.DataFrame({"Site": ["HF", "HF", "BEF"], "pH": "5"})
        >>> lat, lon, note = _join(df, Fields(sites=["Site"]), [("metadata", {"hf": (42.5, -72.2), "bef": (44.1, -71.3)})])
        >>> lat.tolist(), note
        ([42.5, 42.5, 44.1], 'lat/long source: metadata; data key Site')
    """
    best: tuple[float, str, str, KeyedPoints, str] | None = None
    keys = _key_columns(df, f)
    for desc, m in sources:
        for col in keys:
            vals = df[col].map(_norm)
            if (vals == "").all():
                continue
            share = float(vals.isin(m).mean())
            if share >= MIN_JOIN_SHARE and (best is None or share > best[0]):
                best = (share, col, desc, m, "exact")
    if best is None:
        for desc, m in sources:
            ks = sorted((k for k in m if len(k) >= 3), key=len, reverse=True)
            for col in (f.ids + f.sites)[:4]:
                vals = df[col].map(_norm)
                hit = vals.map(lambda v: next((k for k in ks if v.startswith(k)), None))
                share = float(hit.notna().mean())
                if share >= MIN_JOIN_SHARE and (best is None or share > best[0]):
                    best = (share, col, desc, {v: m[k] for v, k in zip(vals, hit) if k}, "prefix")
    if best is None:
        return None
    share, col, desc, m, how = best
    vals = df[col].map(_norm)
    lat = vals.map(lambda v: m.get(v, (None, None))[0])
    lon = vals.map(lambda v: m.get(v, (None, None))[1])
    return lat, lon, f"lat/long source: {desc}; data key {col}" + (" (key prefix match)" if how == "prefix" else "")


def locate(doi: str, df: pd.DataFrame, f: Fields, file: str, sheet: str) -> Location | None:
    """Locate the rows of a table (see the module docstring for the order of the sources).

    Args:
        doi: The package DOI.
        df: The table.
        f: Its fields.
        file: The table's file (relative to package_data).
        sheet: Its sheet.

    Returns:
        The locations, or None when the package has no location at all.

    Examples:
        >>> df = pd.DataFrame({"Lat": ["38.9"], "Lon": ["-106.9"]})
        >>> loc = locate("doi:10.0/x", df, Fields(lat="Lat", lon="Lon"), "x.csv", "")
        >>> loc.group, loc.lat
        ('1', [38.9])
    """
    n = len(df)
    src = f"{doi}:{source_name(file)}" + (f" [{sheet}]" if sheet else "")
    ext = extent(doi)
    if f.lat:
        return Location(list(num(df[f.lat])), list(num(df[f.lon])),
                        [f"lat/long source: {src} (per-sample columns {f.lat}, {f.lon})"] * n, "1")
    j = _join(df, f, location_sources(doi))
    if j:
        lat, lon, note = j
        return Location(list(lat), list(lon), [note] * n, "3")
    if f.east:
        zone, north = None, True
        if f.zone:
            z = df[f.zone].astype(str).str.extract(r"(\d{1,2})\s*([A-Za-z]?)").iloc[:, 0]
            zone = int(z.dropna().iloc[0]) if z.notna().any() else None
        if zone is None and ext:
            zone = int(((ext[1] + ext[3]) / 2 + 180) // 6) + 1
            north = (ext[0] + ext[2]) / 2 >= 0
        if zone:
            e, no = num(df[f.east]), num(df[f.north])
            ll = [utm_to_latlon(a, b, zone, north) if pd.notna(a) and pd.notna(b) else (None, None) for a, b in zip(e, no)]
            ok = [x for x in ll if x[0] is not None]
            if ok and all(_inside(a, b, ext) for a, b in ok):
                return Location([x[0] for x in ll], [x[1] for x in ll],
                                [f"lat/long source: {src} (UTM zone {zone}{'N' if north else 'S'} from {f.east}, {f.north})"] * n, "4")
    ps = places(doi)
    if ps:
        pts = {(round((p[1] + p[3]) / 2, 5), round((p[2] + p[4]) / 2, 5)) for p in ps if _km(p[1], p[2], p[3], p[4]) < 1.0}
        boxes = [p for p in ps if _km(p[1], p[2], p[3], p[4]) >= 1.0]
        if len(pts) == 1 and not boxes:
            (a, b), = pts
            return Location([a] * n, [b] * n, [f"lat/long source: {doi} package spatialCoverage point"] * n, "2")
        if ext is None:
            return None
        north_, west, south, east = ext
        clat, clon = (north_ + south) / 2, (west + east) / 2
        r = _km(north_, west, south, east) / 2
        return Location([clat] * n, [clon] * n,
                        [f"lat/long source: {doi} metadata bounding box centre (±{r:.1f} km)"] * n, "bbox")
    return None


__all__ = ["Location", "locate", "places", "extent", "is_missing"]
