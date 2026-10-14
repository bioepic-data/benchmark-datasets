"""Read the column headers of the downloaded package files (data/source/package_data/), one row per column.

Every csv / txt / tsv / tab / xls / xlsx file is read once, including files extracted from archives
(package_data/extracted/<doi_slug>_<archive>/...). For a data file the header row is located among the first rows
and the numeric values below each column are counted. A group row above the header (e.g. "Soil pH" over
"0.01 M CaCl2", "Depth" over "(cm)") is kept as `group` and names blank or unit-only header cells. Data dictionaries
(_dd, _flmd, "dictionary", "readme" files or sheets, and "metadata" files whose header looks like a dictionary:
column / unit / definition) list column names as rows, so every short text cell is kept instead. The table is cached
in the output folder and reused until --rescan.

Attributes:
    COLUMNS: Columns of the header cache.
    LOG_COLUMNS: Columns of the scan log.
    DICT_FILE: File names of data dictionaries.
    META_FILE: "metadata" file names, dictionaries only when their header looks like one.
    DICT_HEADER: Header words of a dictionary (column / unit / definition).
    UNIT_ONLY: A header cell that is only a unit in brackets.
    DICT_SHEET: Sheet names of dictionaries.
    DEF_NAME: Name column of a dictionary.
    DEF_TEXT: Definition column of a dictionary.
"""

from __future__ import annotations

import csv
import itertools
import os
import re
import sys
from collections.abc import Iterable, Iterator
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Final

import pandas as pd

from ..download_files import slug_of
from .config import (DOWNLOADED, HEADER_SCAN_ROWS, MAX_COLUMN_CHARS, MAX_FILE_BYTES, MAX_ROWS, PACKAGE_DATA,
                     SENTINELS, TABLE_EXTENSIONS)
from .datatypes import DoiIndex, HeaderRow, Pattern, ScanResult, TableRow

csv.field_size_limit(10 ** 8)

COLUMNS: Final[list[str]] = ["doi", "file", "sheet", "column", "is_dictionary", "n_rows", "n_numeric", "group"]
LOG_COLUMNS: Final[list[str]] = ["doi", "file", "message"]
DICT_FILE: Final[Pattern] = re.compile(r"(_dd|_flmd|dictionary|data_dict|readme)\b|(_dd|_flmd)\.", re.I)
META_FILE: Final[Pattern] = re.compile(r"metadata|_meta\b", re.I)   # a dictionary only when its header looks like one
DICT_HEADER: Final[list[Pattern]] = [re.compile(p, re.I) for p in (r"column|field|variable|attribute|parameter|header",
                                                                   r"unit", r"definition|description|meaning")]
UNIT_ONLY: Final[Pattern] = re.compile(r"[\(\[][^\)\]]*[\)\]]")
DICT_SHEET: Final[Pattern] = re.compile(r"dictionary|metadata|readme|notes|description", re.I)
_NUM: Final[Pattern] = re.compile(r"^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$")


def doi_by_path(dois: Iterable[str]) -> DoiIndex:
    """Index the ways to find the DOI of a local file.

    Args:
        dois: Every package DOI.

    Returns:
        File / extracted-folder name -> DOI from package_data_downloaded.tsv, and the DOI slugs, longest first.

    Examples:
        >>> doi_by_path(["doi:10.15485/1", "doi:10.15485/12"]).slugs
        [('10.15485_12', 'doi:10.15485/12'), ('10.15485_1', 'doi:10.15485/1')]
    """
    out: dict[str, str] = {}
    if DOWNLOADED.exists():
        d = pd.read_csv(DOWNLOADED, sep="\t", dtype=str, keep_default_na=False)
        out.update(zip(d.local_name, d.doi))
        ex = d[d.extracted_to != ""]
        out.update(zip(ex.extracted_to.str.replace(r" \(\d+ files\)$", "", regex=True).str.split("/").str[-1], ex.doi))
    return DoiIndex(out, sorted(((slug_of(x), x) for x in dois), key=lambda t: -len(t[0])))


def _doi_of(rel: str, index: DoiIndex) -> str:
    """Find the DOI of a file under package_data from its path (download record first, then the longest DOI slug).

    Examples:
        >>> idx = DoiIndex({}, [("10.15485_12", "doi:10.15485/12"), ("10.15485_1", "doi:10.15485/1")])
        >>> _doi_of("10.15485_12_soil.csv", idx), _doi_of("extracted/10.15485_1_Data/a/b.csv", idx)
        ('doi:10.15485/12', 'doi:10.15485/1')
    """
    parts = rel.split("/")
    name = parts[1] if parts[0] == "extracted" and len(parts) > 1 else parts[0]
    if name in index.by_path:
        return index.by_path[name]
    for slug, doi in index.slugs:  # longest slug first
        if name.upper().startswith(slug.upper() + "_"):
            return doi
    return ""


def _is_num(v: Any) -> bool:
    """Tell whether a cell holds a number (thousands separators allowed).

    Examples:
        >>> _is_num("1,234.5"), _is_num("-3e-2"), _is_num("pH")
        (True, True, False)
    """
    return bool(_NUM.match(str(v).strip().replace(",", "")))


def _header_row(raw: pd.DataFrame) -> int:
    """Find the row, among the first HEADER_SCAN_ROWS, that looks most like a header: many text cells, few numbers.

    Examples:
        >>> raw = pd.DataFrame([["Site data", None, None], ["ID", "pH", "Depth"], ["a", "7.1", "5"]])
        >>> _header_row(raw)
        1
    """
    best, best_score = 0, -1.0
    for i in range(min(len(raw), HEADER_SCAN_ROWS)):
        vals = [v for v in raw.iloc[i].tolist() if v is not None and str(v).strip() not in ("", "nan")]
        if len(vals) < 2:
            continue
        txt = sum(not _is_num(v) for v in vals)
        score = txt - 0.5 * (len(vals) - txt)
        if score > best_score:
            best, best_score = i, score
    return best


def _n_numeric(col: pd.Series) -> int:
    """Count the numeric values of a column (values with an uncertainty count; sentinels such as -9999 do not).

    Examples:
        >>> _n_numeric(pd.Series(["7.1", "22.3±0.4", "-9999", "NA", "1,000"]))
        3
    """
    x = pd.to_numeric(col.astype(str).str.replace(",", "", regex=False)
                      .str.replace(r"\s*(±|\+/-|\+-).*$", "", regex=True).str.strip(), errors="coerce")
    return int((x.notna() & ~x.isin(SENTINELS)).sum())


def _cell(v: Any) -> str:
    """Return a cell as stripped text ('' for None and NaN).

    Examples:
        >>> _cell(" pH "), _cell(None), _cell(float("nan"))
        ('pH', '', '')
    """
    return "" if v is None or str(v) == "nan" else str(v).strip()


def header_names(raw: pd.DataFrame, h: int) -> list[tuple[str, str]]:
    """Name the columns of header row h, using a group row above it when there is one.

    The row above is a group row when it has fewer filled cells than the header and all of them are text; its labels
    are carried right over blank cells. A blank or unit-only header cell takes the group label ('Depth' + '(cm)' ->
    'Depth (cm)').

    Args:
        raw: A table read without a header.
        h: Index of the header row.

    Returns:
        (column name, group label) per column; the group is '' when it equals the name or there is none.

    Examples:
        >>> raw = pd.DataFrame([["Depth", "Soil pH", None], ["(cm)", "0.01 M CaCl2", "Water"], ["0-10", "5.1", "5.6"]])
        >>> header_names(raw, 1)
        [('Depth (cm)', 'Depth'), ('0.01 M CaCl2', 'Soil pH'), ('Water', 'Soil pH')]
    """
    head = [_cell(v) for v in raw.iloc[h].tolist()]
    groups = [""] * len(head)
    if h > 0:
        up = [_cell(v) for v in raw.iloc[h - 1].tolist()]
        filled = [u for u in up if u]
        if (filled and len(filled) < sum(1 for x in head if x) and not any(_NUM.match(u) for u in filled)
                and all(len(u) <= MAX_COLUMN_CHARS for u in filled)):
            last = ""
            for j, u in enumerate(up):
                last = u or last
                groups[j] = last
    out: list[tuple[str, str]] = []
    for c, g in zip(head, groups):
        name = g if not c else f"{g} {c}" if g and UNIT_ONLY.fullmatch(c) else c
        out.append((name, g if g != name else ""))
    return out


def _looks_like_dictionary(raw: pd.DataFrame) -> bool:
    """Tell whether a table's header is that of a data dictionary (two of column / unit / definition words).

    Examples:
        >>> _looks_like_dictionary(pd.DataFrame([["Column_or_Row_Name", "Unit", "Definition"], ["pH", "", "Soil pH"]]))
        True
    """
    head = " | ".join(_cell(v) for v in raw.iloc[_header_row(raw)].tolist())
    return sum(bool(p.search(head)) for p in DICT_HEADER) >= 2


def _table_rows(raw: pd.DataFrame | None, is_dict: bool) -> Iterator[TableRow]:
    """Yield one TableRow per column of a data table, or per short text cell of a dictionary.

    Examples:
        >>> raw = pd.DataFrame([["ID", "pH"], ["a", "7.1"], ["b", "NA"]])
        >>> list(_table_rows(raw, False))
        [TableRow(column='ID', is_dictionary=False, n_rows=2, n_numeric=0, group=''), TableRow(column='pH', is_dictionary=False, n_rows=2, n_numeric=1, group='')]
    """
    if raw is None or raw.empty:
        return
    if is_dict:
        for v in sorted({str(x).strip() for x in raw.values.ravel() if x is not None}):  # sorted: stable cache
            if v and v != "nan" and len(v) <= MAX_COLUMN_CHARS and len(v.split()) <= 6:
                yield TableRow(v, True, None, None, "")
        return
    h = _header_row(raw)
    body = raw.iloc[h + 1:]
    for j, (c, g) in enumerate(header_names(raw, h)):
        if c and len(c) <= MAX_COLUMN_CHARS:
            yield TableRow(c, False, len(body), _n_numeric(body.iloc[:, j]), g)


def scan_file(path: str) -> ScanResult:
    r"""Read the header rows of every sheet of one file.

    Args:
        path: The file.

    Returns:
        The header rows, and an error message when the file could not be read or is too large.

    Examples:
        >>> import tempfile
        >>> with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
        ...     _ = f.write("ID,pH\na,7.1\n")
        >>> scan_file(f.name).rows
        [HeaderRow(sheet='', column='ID', is_dictionary=False, n_rows=1, n_numeric=0, group=''), HeaderRow(sheet='', column='pH', is_dictionary=False, n_rows=1, n_numeric=1, group='')]
        >>> import os; os.remove(f.name)
    """
    ext = os.path.splitext(path)[1].lower()
    is_dict = bool(DICT_FILE.search(os.path.basename(path)))
    try:
        if os.path.getsize(path) > MAX_FILE_BYTES:
            return ScanResult([], f"skipped, larger than {MAX_FILE_BYTES / 1e6:.0f} MB")
        if ext in (".xlsx", ".xls", ".xlsm"):
            out: list[HeaderRow] = []
            for sh, raw in pd.read_excel(path, sheet_name=None, header=None, dtype=str, nrows=MAX_ROWS).items():
                d = is_dict or bool(DICT_SHEET.search(str(sh))) or (
                    bool(META_FILE.search(os.path.basename(path))) and not raw.empty and _looks_like_dictionary(raw))
                out += [HeaderRow(str(sh), *r) for r in _table_rows(raw, d)]
            return ScanResult(out, None)
        with open(path, errors="replace") as fh:
            head = "".join(next(fh, "") for _ in range(HEADER_SCAN_ROWS))
        sep = "\t" if head.count("\t") > head.count(",") else ","
        with open(path, errors="replace", newline="") as fh:  # csv.reader tolerates ragged rows
            raw = pd.DataFrame(list(itertools.islice(csv.reader(fh, delimiter=sep), MAX_ROWS)), dtype=str)
        if not is_dict and META_FILE.search(os.path.basename(path)) and not raw.empty:
            is_dict = _looks_like_dictionary(raw)
        return ScanResult([HeaderRow("", *r) for r in _table_rows(raw, is_dict)], None)
    except Exception as e:  # noqa: BLE001 - unreadable files are logged, not fatal
        return ScanResult([], f"{type(e).__name__}: {str(e)[:150]}")


DEF_NAME: Final[Pattern] = re.compile(r"column|field|variable|attribute|parameter|header", re.I)
DEF_TEXT: Final[Pattern] = re.compile(r"definition|description|meaning", re.I)


def dictionary_definitions(files: Iterable[str], root: Path = PACKAGE_DATA) -> dict[str, str]:
    r"""Read the column definitions of a package's data dictionaries.

    A dictionary table is one with a name column (column / field / variable ...) and a definition column.

    Args:
        files: Dictionary files, relative to `root`.
        root: The package-data folder.

    Returns:
        Column name (lower case) -> definition; the first definition wins.

    Examples:
        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as d:
        ...     _ = (Path(d) / "x_dd.csv").write_text("column_or_row_name,definition,unit\nFe_ugg,HCl-extractable iron,ug/g,\n")
        ...     dictionary_definitions(["x_dd.csv"], Path(d))
        {'fe_ugg': 'HCl-extractable iron'}
    """
    out: dict[str, str] = {}
    for rel in files:
        path = root / rel
        try:
            if path.suffix.lower() in (".xlsx", ".xls", ".xlsm"):
                tables = list(pd.read_excel(path, sheet_name=None, dtype=str).values())
            else:
                with open(path, errors="replace") as fh:
                    head = "".join(next(fh, "") for _ in range(HEADER_SCAN_ROWS))
                sep = "\t" if head.count("\t") > head.count(",") else ","
                # index_col=False: rows with a trailing separator must not shift the columns
                tables = [pd.read_csv(path, dtype=str, keep_default_na=False, encoding_errors="replace",
                                      on_bad_lines="skip", sep=sep, index_col=False)]
        except Exception:  # noqa: BLE001 - an unreadable dictionary just gives no definitions
            continue
        for t in tables:
            t.columns = [_cell(c) for c in t.columns]
            name = next((c for c in t.columns if DEF_NAME.search(c)), None)
            text = next((c for c in t.columns if DEF_TEXT.search(c)), None)
            if name and text and name != text:
                for n, d in zip(t[name], t[text]):
                    if _cell(n) and _cell(d):
                        out.setdefault(_cell(n).lower(), _cell(d))
    return out


def table_files(root: Path = PACKAGE_DATA) -> list[str]:
    """List the table files under the package-data folder (csv, txt, tsv, tab, xls, xlsx; no hidden or lock files).

    Args:
        root: The package-data folder.

    Returns:
        Their paths, sorted.
    """
    return sorted(str(p) for p in Path(root).rglob("*")
                  if p.is_file() and p.suffix.lower() in TABLE_EXTENSIONS and not p.name.startswith((".", "~$")))


def scan_headers(dois: Iterable[str], root: Path = PACKAGE_DATA,
                 workers: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read the headers of every table file, in parallel.

    Args:
        dois: Every package DOI (to name the files' packages).
        root: The package-data folder.
        workers: Worker processes; all cores when None.

    Returns:
        The header table (COLUMNS) and the log of files that could not be read or were skipped.

    Examples:
        >>> headers, log = scan_headers(load_packages().doi)  # doctest: +SKIP
    """
    files = table_files(root)
    index = doi_by_path(dois)
    print(f"scanning headers of {len(files)} files", file=sys.stderr)
    rows: list[tuple[Any, ...]] = []
    log: list[dict[str, str]] = []
    with ProcessPoolExecutor(workers) as ex:
        for i, (path, res) in enumerate(zip(files, ex.map(scan_file, files, chunksize=16)), 1):
            rel = os.path.relpath(path, root)
            doi = _doi_of(rel, index)
            rows += [(doi, rel, *r) for r in res.rows]
            if res.error:
                log.append(dict(doi=doi, file=rel, message=res.error))
            if i % 2000 == 0:
                print(f"  {i}/{len(files)}", file=sys.stderr)
    return pd.DataFrame(rows, columns=COLUMNS), pd.DataFrame(log, columns=LOG_COLUMNS)
