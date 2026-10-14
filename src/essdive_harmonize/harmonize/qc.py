"""Check harmonized tables: plausible value range (variable_config.csv) and valid coordinates.

Rows are kept; each problem becomes one row of <key>/qc.csv.

Attributes:
    QC_COLUMNS: Columns of qc.csv.
"""

from __future__ import annotations

import pandas as pd

from .variables import VARIABLES, config

QC_COLUMNS = ["doi", "source_file", "id", "depth", "date", "value", "latitude", "longitude", "flag"]


def check(key: str, table: pd.DataFrame) -> pd.DataFrame:
    """List the rows of a harmonized table with a problem.

    Args:
        key: The variable key.
        table: The harmonized table.

    Returns:
        QC_COLUMNS rows: values outside the plausible range and invalid coordinates (out of range, or 0, 0).

    Examples:
        >>> t = pd.DataFrame({"doi": "d", "source_file": "f", "id": ["a", "b"], "depth": "", "date": "",
        ...                   "Acidity__Soil_pH": ["7.1", "13"], "latitude": ["38.9", "0"], "longitude": ["-106.9", "0"]})
        >>> check("Acidity__Soil_pH", t)[["id", "flag"]].values.tolist()
        [['b', 'value above plausible maximum 11 pH units; invalid coordinates']]
    """
    v, cfg = VARIABLES[key], config().get(key, {})
    x = pd.to_numeric(table[v.value_column], errors="coerce")
    lat = pd.to_numeric(table.latitude, errors="coerce")
    lon = pd.to_numeric(table.longitude, errors="coerce")
    flags = pd.Series("", index=table.index)
    lo, hi = cfg.get("min"), cfg.get("max")
    if lo is not None:
        flags = flags.mask(x < lo, f"value below plausible minimum {lo:g} {v.units[0]}")
    if hi is not None:
        flags = flags.mask(x > hi, f"value above plausible maximum {hi:g} {v.units[0]}")
    bad = (lat.abs() > 90) | (lon.abs() > 180) | ((lat == 0) & (lon == 0))
    flags = flags.mask(bad, (flags + "; ").str.lstrip("; ") + "invalid coordinates")
    out = table[flags != ""].assign(value=x[flags != ""], flag=flags[flags != ""])
    return out[QC_COLUMNS].reset_index(drop=True)
