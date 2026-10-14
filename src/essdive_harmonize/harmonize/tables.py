"""Read downloaded package tables: header row, optional units row, and ESS-DIVE source file names.

Examples:
    >>> _unique(["pH", "pH", None, "﻿Depth"])
    ['pH', 'pH.1', 'unnamed', 'Depth']
"""

from __future__ import annotations

import csv
import itertools
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from .. import units
from ..download_files import DOWNLOADED
from ..selection.headers import _header_row, header_names
from .config import MAX_TABLE_ROWS, PACKAGE_DATA

csv.field_size_limit(10 ** 8)
_UNITISH = re.compile(r"^[\(\[]?\s*(%|‰|ppm|ppb|per ?mil|unitless|dimensionless|[a-zµμ]{0,6}\s*[/ ]\s*[a-zµμ0-9\- ]{1,12}|"
                      r"[munµμk]?g|[cmk]?m|mm|[munµμ]?mol|meq|cmol.*|ds ?m-1|°c|deg ?c|cm|m|ph units?)\s*[\)\]]?$", re.I)
_NUM = re.compile(r"^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$")


@dataclass
class Table:
    """One data table of a package.

    Attributes:
        file: Path relative to package_data.
        sheet: Sheet name ('' for text files).
        data: All cells as text; columns are the header cells (made unique), empty columns dropped.
        units: Column -> unit from a units row under the header ('' when none).
        header_row: Index of the header row in the file.
        groups: Column -> label of a group row above the header ('' when none).
    """
    file: str                 # path relative to package_data
    sheet: str
    data: pd.DataFrame        # all cells as text, columns = header cells (made unique)
    units: dict[str, str]     # column -> unit from a units row under the header ('' when none)
    header_row: int
    groups: dict[str, str] = field(default_factory=dict)  # column -> label of a group row above the header


def _unique(names: Iterable[Any]) -> list[str]:
    """Make header cells unique, non-empty column names (byte-order marks removed, repeats numbered '.1', '.2' ...)."""
    seen: dict[str, int] = {}
    out: list[str] = []
    for n in names:
        n = str(n).replace("\ufeff", "").replace("ï»¿", "").strip() if n is not None and str(n) != "nan" else ""
        n = n or "unnamed"
        k = seen.get(n, 0)
        out.append(n if k == 0 else f"{n}.{k}")
        seen[n] = k + 1
    return out


def _raw(path: Path, sheet: str) -> pd.DataFrame:
    """Read a file or sheet without a header, every cell as text ('' for empty cells)."""
    ext = path.suffix.lower()
    if ext in (".xlsx", ".xls", ".xlsm"):
        return pd.read_excel(path, sheet_name=sheet or 0, header=None, dtype=str, nrows=MAX_TABLE_ROWS).fillna("")
    with open(path, errors="replace") as fh:
        head = "".join(next(fh, "") for _ in range(40))
    sep = "\t" if head.count("\t") > head.count(",") else ","
    with open(path, errors="replace", newline="") as fh:
        rows = list(itertools.islice(csv.reader(fh, delimiter=sep), MAX_TABLE_ROWS))
    return pd.DataFrame(rows, dtype=str).fillna("")


@lru_cache(maxsize=256)
def _unitish(cell: str) -> bool:
    """Tell whether a cell of a possible units row reads as a unit (pattern, or the unit parser accepts it).

    Examples:
        >>> _unitish("gC kg^-1"), _unitish("m (from ground surface)"), _unitish("Water depth category")
        (True, True, False)
    """
    if _UNITISH.match(cell):
        return True
    try:
        units.parse(cell)
        return True
    except units.UnitError:
        return False


def read_table(file: str, sheet: str = "") -> Table:
    """Read one data table of a package (cached).

    The header row is located as in the header scan, a group row above it names blank or unit-only cells, and a units
    row right under it is taken off the data.

    Args:
        file: Path relative to package_data.
        sheet: Sheet name ('' for text files).

    Returns:
        The table.

    Examples:
        >>> t = read_table("10.15485_1725884_EastRiverFloodplainBulkDensities.csv")  # doctest: +SKIP
        >>> t.header_row, list(t.data.columns)[:2]  # doctest: +SKIP
        (0, ['Sample_ID', 'Latitude'])
    """
    raw = _raw(PACKAGE_DATA / file, sheet)
    h = _header_row(raw)
    names = header_names(raw, h)
    cols = _unique([n for n, _ in names])
    body = raw.iloc[h + 1:].reset_index(drop=True)
    body.columns = cols
    units = {c: "" for c in cols}
    if len(body):
        first = body.iloc[0].astype(str).str.strip()
        # placeholders ('none', 'NA') and data-type or format labels ('Num', 'String', 'YYYYMMDD', 'DegN.dddddd')
        # mark columns without a unit; they neither count for nor against a units row
        none = first.str.fullmatch(r"(?i)none|na|n/a|-|nan|num(eric)?|string|text|integer|float|categoric.*|"
                                   r"[ymdhs]{2,}[ymdhs.:/ -]*|deg[nsew]?[ .]?[d°'\"min.sec]*")
        filled = first[(first != "") & ~none]
        if len(filled) and not filled.str.match(_NUM.pattern).any() and filled.map(_unitish).mean() >= 0.5 \
                and none.sum() < len(first) - (first == "").sum():
            units = {c: ("" if none[c] else first[c]) for c in cols}
            body = body.iloc[1:].reset_index(drop=True)
    body = body.apply(lambda s: s.astype(str).str.strip())
    keep = [c for c in cols if (body[c] != "").any()]
    groups = {c: g for c, (_, g) in zip(cols, names)}
    return Table(file, sheet, body[keep], {c: units[c] for c in keep}, h, {c: groups[c] for c in keep})


def stacked_blocks(body: pd.DataFrame, min_changed: float = 0.25) -> list[tuple[int, int, float]]:
    """Find blocks of rows, after a blank row, that have another column layout than the first block.

    A sheet can hold a second table under the first without a header of its own: its values sit under the first
    table's header names, often shifted (user decision 2026-10-13: doi:10.15485/2405147 SoilCores.xlsx [Soil Cores],
    rows of cores 6-8 after a blank row have elevations under 'pH', depths under 'Total N' and total N under 'Clay %',
    and were written as pH 127, clay 0.3 %). A later block keeps the layout when its columns are filled like the first
    block's; it is another layout when the fill rate of at least `min_changed` of the used columns changes by more than
    half (filled -> empty or empty -> filled). Blocks of the same layout (sites separated by blank rows) are kept.

    Args:
        body: Table cells as text ('' for empty), rows under the header.
        min_changed: Share of used columns whose fill rate must change by more than 0.5.

    Returns:
        (first row, last row, share of changed columns) of each block with another layout, rows as body positions.

    Examples:
        >>> a = pd.DataFrame({"pH": ["4", "5", "", "128", "127"], "Depth": ["0-10", "10-20", "", "", ""],
        ...                   "SOC": ["2", "3", "", "", ""], "x": ["", "", "", "6", "7"]})
        >>> stacked_blocks(a)
        [(3, 4, 0.75)]
        >>> stacked_blocks(pd.DataFrame({"pH": ["4", "", "5"], "SOC": ["2", "", "3"]}))
        []
    """
    filled = body.ne("")
    blank = ~filled.any(axis=1).to_numpy()
    runs: list[tuple[int, int]] = []
    start = None
    for i, b in enumerate(blank):
        if not b and start is None:
            start = i
        if b and start is not None:
            runs.append((start, i - 1))
            start = None
    if start is not None:
        runs.append((start, len(blank) - 1))
    if len(runs) < 2:
        return []
    ref = filled.iloc[runs[0][0]:runs[0][1] + 1].mean()
    out = []
    for a, b in runs[1:]:
        f = filled.iloc[a:b + 1].mean()
        used = (ref > 0) | (f > 0)
        changed = float(((ref - f).abs() > 0.5)[used].mean()) if used.any() else 0.0
        if changed >= min_changed:
            out.append((a, b, round(changed, 2)))
    return out


@lru_cache(maxsize=1)
def _downloaded() -> tuple[dict[str, str], dict[str, str]]:
    """Read the download record: local name -> ESS-DIVE file name, extracted folder -> archive name."""
    d = pd.read_csv(DOWNLOADED, sep="\t", dtype=str, keep_default_na=False)
    names = {str(a): str(b) for a, b in zip(d.local_name, d.file_name)}
    ex = d[d.extracted_to != ""]
    folders = {str(a): str(b) for a, b in zip(
        ex.extracted_to.str.replace(r" \(\d+ files\)$", "", regex=True).str.split("/").str[-1], ex.file_name)}
    return names, folders


def source_name(file: str) -> str:
    """Return the ESS-DIVE file name of a local file.

    Args:
        file: Path relative to package_data.

    Returns:
        The file name as listed on ESS-DIVE; '<archive>/<path inside>' for a file extracted from an archive.

    Examples:
        >>> source_name("10.15485_1725884_EastRiverFloodplainBulkDensities.csv")  # doctest: +SKIP
        'EastRiverFloodplainBulkDensities.csv'
    """
    names, folders = _downloaded()
    parts = file.split("/")
    if parts[0] == "extracted" and len(parts) > 2:
        return f"{folders.get(parts[1], parts[1])}/{'/'.join(parts[2:])}"
    return names.get(file, file)


def package_tables(doi: str, headers: pd.DataFrame) -> list[tuple[str, str]]:
    """List the data tables of a package (not dictionaries) from the header cache.

    Args:
        doi: The package DOI.
        headers: The header cache.

    Returns:
        (file, sheet) pairs.

    Examples:
        >>> h = pd.DataFrame({"doi": "d1", "file": ["a.csv", "a.csv", "a_dd.csv"], "sheet": "",
        ...                   "is_dictionary": [False, False, True]})
        >>> package_tables("d1", h)
        [('a.csv', '')]
    """
    h = headers[(headers.doi == doi) & ~headers.is_dictionary]
    return list(h[["file", "sheet"]].drop_duplicates().itertuples(index=False, name=None))


def dictionary_tables(doi: str, headers: pd.DataFrame) -> list[tuple[str, str]]:
    """List the data-dictionary tables of a package from the header cache.

    Examples:
        >>> h = pd.DataFrame({"doi": "d1", "file": ["a.csv", "a_dd.csv"], "sheet": "", "is_dictionary": [False, True]})
        >>> dictionary_tables("d1", h)
        [('a_dd.csv', '')]
    """
    h = headers[(headers.doi == doi) & headers.is_dictionary]
    return list(h[["file", "sheet"]].drop_duplicates().itertuples(index=False, name=None))
