"""Read package text (title, description, measurement technique, keywords) from data/source/ess-dive_meta/."""

from __future__ import annotations

import json
from functools import lru_cache

from ..selection.metadata import _text
from .config import META_DIR


@lru_cache(maxsize=1)
def _index() -> dict:
    """Read every package's dataset metadata: {doi: dataset} (cached)."""
    out = {}
    for f in META_DIR.glob("ess-dive_meta_*.json"):
        ds = json.loads(f.read_text()).get("dataset", {})
        out[ds.get("@id", "")] = ds
    return out


@lru_cache(maxsize=2048)
def package_text(doi: str) -> str:
    """Return a package's title, description, measurement technique, keywords and variables measured as text (cached).

    Examples:
        >>> "Mehlich" in package_text("doi:10.5440/1860505")  # doctest: +SKIP
        True
    """
    ds = _index().get(doi, {})
    return "\n".join(t for t in (_text(ds.get("name")), _text(ds.get("description")),
                                 _text(ds.get("measurementTechnique")), _text(ds.get("keywords")),
                                 _text(ds.get("variableMeasured"))) if t)


def title(doi: str) -> str:
    """Return a package's title.

    Examples:
        >>> title("doi:10.15485/1725884")[:30]  # doctest: +SKIP
        'East River Floodplain Soil Pit'
    """
    return _text(_index().get(doi, {}).get("name"))


def _coverage_date(start: str, end: str) -> str:
    """The date a temporal coverage pins down: the day, month (YYYY-MM) or year shared by its start and end, else ''.

    Examples:
        >>> _coverage_date("2019-10-01", "2019-10-30")
        '2019-10'
        >>> _coverage_date("2018-06-12T00:00:00", "2018-06-12")
        '2018-06-12'
        >>> _coverage_date("2017-05-01", "2017-09-30")
        '2017'
        >>> _coverage_date("2016-05-01", "2019-09-30"), _coverage_date("", "")
        ('', '')
        >>> _coverage_date("1997-01-01", "1997-01-01")  # January 1: a placeholder day, the year only
        '1997'
    """
    a, b = str(start or "")[:10], str(end or "")[:10]
    # a one-day coverage on January 1 is a placeholder (1463804, Nevada Desert FACE, 1997-01-01, no sampling date in
    # the text): only its year is kept
    for n in ((4,) if a == b and a[4:] == "-01-01" else (10, 7, 4)):
        if len(a) >= n and a[:n] == b[:n]:
            return a[:n]
    return ""


@lru_cache(maxsize=2048)
def coverage_date(doi: str) -> str:
    """Return the sampling date of a package from its metadata temporal coverage (day, YYYY-MM or year), else ''.

    Used for tables with no date column: 2566016 (collected in October 2019, coverage 2019-10-01 to 2019-10-30) gets
    '2019-10'. A coverage of more than one calendar year gives no date.

    Examples:
        >>> coverage_date("doi:10.15485/2566016")  # doctest: +SKIP
        '2019-10'
    """
    tc = _index().get(doi, {}).get("temporalCoverage") or {}
    if isinstance(tc, list):
        tc = tc[0] if len(tc) == 1 and isinstance(tc[0], dict) else {}
    return _coverage_date(tc.get("startDate", ""), tc.get("endDate", "")) if isinstance(tc, dict) else ""
