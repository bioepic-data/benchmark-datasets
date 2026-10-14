"""Read the package metadata text, split by evidence source, from data/source/ess-dive_meta/.

Attributes:
    Json: A JSON value of the ESS-DIVE metadata: text, numbers, lists and objects.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeAlias

import pandas as pd

from .config import META_DIR

# JSON values of the ESS-DIVE metadata: text, numbers, lists and objects
Json: TypeAlias = "str | int | float | bool | None | list[Json] | dict[str, Json]"


def _text(x: Json) -> str:
    """Flatten a metadata value to text: list items and object values joined with ' | '.

    Examples:
        >>> _text(["SOIL PH", {"name": "pH", "unit": None}, 5])
        'SOIL PH | pH | 5'
    """
    if x is None:
        return ""
    if isinstance(x, list):
        return " | ".join(t for t in (_text(i) for i in x) if t)
    if isinstance(x, dict):
        return " | ".join(t for t in (_text(v) for v in x.values()) if t)
    return str(x)


def load_packages(meta_dir: Path = META_DIR) -> pd.DataFrame:
    """Read one row per DOI (its latest version) with the metadata text of each evidence source.

    The sources are keywords (dataset.keywords + dataset.variableMeasured), description (dataset.name +
    alternateName + description) and other (measurementTechnique, the names and descriptions of the package files, and
    the site descriptions).

    Args:
        meta_dir: Folder of the per-package metadata files.

    Returns:
        doi, package_id, date_uploaded, title, provider, n_listed_files, keywords, description, other.

    Examples:
        >>> load_packages().shape  # doctest: +SKIP
        (1588, 9)
    """
    rows: list[dict[str, Json]] = []
    for f in sorted(Path(meta_dir).glob("ess-dive_meta_*.json")):
        m = json.loads(f.read_text())
        ds = m.get("dataset", {})
        files = ds.get("distribution") or []
        sites = ds.get("spatialCoverage") or []
        rows.append(dict(
            doi=ds.get("@id", ""),
            package_id=m.get("id", ""),
            date_uploaded=m.get("dateUploaded", ""),
            title=_text(ds.get("name")),
            provider=_text((ds.get("provider") or {}).get("name")),
            n_listed_files=len(files),
            keywords=" | ".join(t for t in (_text(ds.get("keywords")), _text(ds.get("variableMeasured"))) if t),
            description=" | ".join(t for t in (_text(ds.get("name")), _text(ds.get("alternateName")),
                                               _text(ds.get("description"))) if t),
            other=" | ".join(t for t in (
                _text(ds.get("measurementTechnique")),
                _text([x.get("name") for x in files]), _text([x.get("description") for x in files]),
                _text([s.get("description") for s in sites if isinstance(s, dict)])) if t),
        ))
    df = pd.DataFrame(rows)
    return df.sort_values("date_uploaded").drop_duplicates("doi", keep="last").reset_index(drop=True)
