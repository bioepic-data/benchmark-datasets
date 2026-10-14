"""Check the automatic results against the hand-written package functions (pH and carbon), run in memory.

The hand-written output is never written; it is only compared with the automatic result for the same package and
variable: row counts, share of hand-written values found among the automatic values (as a multiset, rounded to 3
significant digits), and the distance between the mean coordinates.

Attributes:
    COMPARE_COLUMNS: Columns of handwritten_check.csv.
"""

from __future__ import annotations

import math
from collections import Counter
from functools import lru_cache
from typing import Any, Final

import pandas as pd

from ..registry import PACKAGES
from .auto import Result
from .locate import _km


@lru_cache(maxsize=None)
def handwritten(key: str) -> dict[str, pd.DataFrame]:
    """Run every hand-written package that provides a variable (cached; errors are skipped).

    Returns:
        {doi: table}.
    """
    out: dict[str, pd.DataFrame] = {}
    for p in PACKAGES:
        if not p.wants([key]):
            continue
        try:
            t = p.tables().get(key)
        except Exception:  # noqa: BLE001 - e.g. a source file not in the current download
            continue
        if t is not None and len(t):
            out[p.doi] = t
    return out


def _vals(t: pd.DataFrame, key: str) -> Counter[float]:
    """Count a table's values rounded to 3 significant digits.

    Examples:
        >>> _vals(pd.DataFrame({"k": ["7.12", "7.118", "NA"]}), "k")
        Counter({7.12: 2})
    """
    x = pd.to_numeric(t[key], errors="coerce").dropna()
    return Counter(float(f"{v:.3g}") for v in x)


def _centre(t: pd.DataFrame) -> tuple[float, float]:
    """Return the mean latitude and longitude of a table (NaN, NaN without coordinates).

    Examples:
        >>> [float(x) for x in _centre(pd.DataFrame({"latitude": ["38", "39"], "longitude": ["-106", "-107"]}))]
        [38.5, -106.5]
    """
    a, b = pd.to_numeric(t.latitude, errors="coerce"), pd.to_numeric(t.longitude, errors="coerce")
    return (a.mean(), b.mean()) if a.notna().any() else (math.nan, math.nan)


COMPARE_COLUMNS: Final[list[str]] = ["doi", "handwritten_rows", "auto_rows", "auto_status", "location",
                                      "values_found", "centre_km", "reasons"]


def compare(key: str, results: dict[str, Result]) -> pd.DataFrame:
    """Compare the automatic results with the hand-written packages of a variable.

    Args:
        key: The variable key.
        results: {doi: automatic result}.

    Returns:
        One row per hand-written package (COMPARE_COLUMNS); empty, with the columns, for variables without hand-written
        packages.
    """
    rows: list[dict[str, Any]] = []
    for doi, hw in handwritten(key).items():
        r = results.get(doi)
        auto = r.table if r is not None and r.table is not None else None
        row = dict(doi=doi, handwritten_rows=len(hw), auto_rows=0 if auto is None else len(auto),
                   auto_status="not a candidate" if r is None else r.status, location=getattr(r, "location", ""),
                   values_found=0.0, centre_km=math.nan, reasons="" if r is None else "; ".join(r.reasons)[:200])
        if auto is not None:
            a, h = _vals(auto, key), _vals(hw, key)
            row["values_found"] = round(sum((a & h).values()) / max(1, sum(h.values())), 3)
            (la, lo), (lb, lb2) = _centre(auto), _centre(hw)
            if not any(map(math.isnan, (la, lo, lb, lb2))):
                row["centre_km"] = round(_km(la, lo, lb, lb2), 2)
        rows.append(row)
    return pd.DataFrame(rows, columns=COMPARE_COLUMNS).sort_values("doi").reset_index(drop=True)
