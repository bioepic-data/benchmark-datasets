"""Classify packages as soil-related and list their soil context.

soil_related (the split used in the reports) follows notebooks/soil_variable_list/02 and 05: the word "soil" or
"soils" in the title, description, keywords or other metadata, or a column header starting with "soil".
soil_context lists the context terms found in the metadata text (and "soil" when a column header starts with
"soil"), e.g. "soil; sediment; porewater"; it is empty when none is found. It is broader than soil_related
(sediment, peat, permafrost, horizons, active layer, porewater ...) and is reported alongside for review.

Attributes:
    SOIL_TEXT: The word soil / soils.
    SOIL_COLUMN: A column header starting with soil.
    SOIL_CONTEXT: Context label -> pattern, in the order they are listed in soil_context.
    SOURCES: Metadata text fields searched.
"""

from __future__ import annotations

import re
from typing import Final

import pandas as pd

from .datatypes import Pattern

SOIL_TEXT: Final[Pattern] = re.compile(r"\bsoils?\b", re.I)
SOIL_COLUMN: Final[Pattern] = re.compile(r"\bsoil", re.I)
# context label -> pattern, in the order they are listed in soil_context
SOIL_CONTEXT: Final[dict[str, Pattern]] = {
    "soil": SOIL_TEXT,
    "sediment": re.compile(r"sediment", re.I),
    "peat": re.compile(r"\bpeat", re.I),
    "permafrost": re.compile(r"permafrost", re.I),
    "horizon": re.compile(r"horizon", re.I),
    "active layer": re.compile(r"active\s+layer", re.I),
    "regolith": re.compile(r"regolith", re.I),
    "porewater": re.compile(r"pore\s*water", re.I),
    "rhizosphere": re.compile(r"rhizosphere", re.I),
    "litter layer": re.compile(r"litter\s+layer", re.I),
}
SOURCES: Final[list[str]] = ["title", "keywords", "description", "other"]


def classify(packages: pd.DataFrame, headers: pd.DataFrame) -> pd.DataFrame:
    """Add the soil classification to the package table.

    Args:
        packages: The package table (metadata.load_packages).
        headers: The column-header cache.

    Returns:
        The packages plus soil_related, soil_evidence (where "soil" was found, e.g. 'title+keywords'), soil_columns
        (up to five soil columns) and soil_context (the context terms found).

    Examples:
        >>> pk = pd.DataFrame({"doi": ["d1", "d2"], "title": ["Soil cores", "Stream chemistry"],
        ...                    "keywords": ["", "PEAT"], "description": ["", ""], "other": ["", ""]})
        >>> hd = pd.DataFrame({"doi": ["d2"], "column": ["Soil_Temp"]})
        >>> classify(pk, hd)[["soil_related", "soil_evidence", "soil_context"]].values.tolist()
        [[True, 'title', 'soil'], [True, 'columns', 'soil; peat']]
    """
    soil_cols = headers[headers.column.str.contains(SOIL_COLUMN)].groupby("doi").column.apply(
        lambda s: "; ".join(sorted(set(s))[:5]))
    out = packages.copy()
    ev = pd.DataFrame({s: out[s].str.contains(SOIL_TEXT) for s in SOURCES})
    ev["columns"] = out.doi.isin(soil_cols.index)
    out["soil_related"] = ev.any(axis=1)
    out["soil_evidence"] = ev.apply(lambda r: "+".join(c for c in ev.columns if r[c]), axis=1)
    out["soil_columns"] = out.doi.map(soil_cols).fillna("")
    text = out[SOURCES].agg(" | ".join, axis=1)
    found = pd.DataFrame({k: text.str.contains(p) for k, p in SOIL_CONTEXT.items()})
    found["soil"] |= ev["columns"]
    out["soil_context"] = found.apply(lambda r: "; ".join(k for k in found.columns if r[k]), axis=1)
    return out
