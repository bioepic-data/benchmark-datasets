"""Load the variables to harmonize and their settings.

The variables are those with select = 1 in data/soil_variable_list_input.csv, minus EXCLUDE_CATEGORIES. Names and
categories come from the input list; standard unit, specification and abbreviation from data/soil_variable_list.csv
(same variable names); plausible ranges and the other settings from variable_config.csv. The Variable objects are
those of essdive_harmonize.variables (same keys, value / method / extra columns), so the shared writers in
essdive_harmonize.common apply unchanged.

Examples:
    >>> "Acidity__Soil_pH" in VARIABLES
    True
    >>> config()["Acidity__Soil_pH"]["unitless"]
    True

Attributes:
    VARIABLES: {key: Variable} in input-list order.
    CATEGORIES: The categories, in input-list order.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TypedDict

import pandas as pd

from ..variables import VARIABLES as LISTED, Variable, make_key
from .config import EXCLUDE_CATEGORIES, VARIABLE_CONFIG, VARIABLE_INPUT


class VarConfig(TypedDict, total=False):
    """One row of variable_config.csv.

    Attributes:
        min: Plausible minimum in the standard unit (None = no limit), checked by qc.py.
        max: Plausible maximum in the standard unit.
        unitless: Values need no unit (pH): the source value is taken as is.
        assume_unit: Units tried, separated by '|', when the source states none; the first in which >= 90 % of the values
            are plausible is used (noted in notes and dois_filtering).
        time_series: Sensor / logger time series are wanted (soil temperature, moisture, fluxes); otherwise tables
            with many sub-daily timestamps are skipped.
        element: Element of the value for mole / charge conversions (C for carbon: mM -> mg C L-1).
        exclude_files: Pattern of file / sheet names not used for this variable (fractions, roots, litter ...).
        methods: (pattern, method) pairs tried on the column name, then on package text about the variable; an empty
            pattern gives the default.
        column_exclude: Pattern of matched column names (or their group row or data dictionary definition) that are
            not this variable (Fraction Modern for radiocarbon, fumigated extracts for DON, exchangeable Ca for total Ca).
        require: Pattern that the column name, its group row, its unit, its data dictionary definition or the file
            name must contain (exchangeable cations: 'exch', 'meq', 'cmol' ..., so total-element columns are not
            taken).
        skip_repeated: Columns whose name is repeated in the table ('Mg', 'Mg.1': one per extraction step) are not
            used (total elements).
    """
    min: float | None
    max: float | None
    unitless: bool
    assume_unit: str
    time_series: bool
    element: str | None
    exclude_files: str
    methods: list[tuple[str, str]]
    column_exclude: str
    require: str
    skip_repeated: bool


def load() -> dict[str, Variable]:
    """Load the variables to harmonize from the input list.

    Returns:
        {key: essdive_harmonize.variables.Variable} in input-list order.

    Raises:
        KeyError: When a selected variable is missing from data/soil_variable_list.csv.
    """
    inp = pd.read_csv(VARIABLE_INPUT, sep="\t", dtype=str, keep_default_na=False)
    inp.columns = [c.strip().lower() for c in inp.columns]
    out: dict[str, Variable] = {}
    for r in inp.itertuples():
        category, name = str(r.category), str(r.variable)
        if str(r.select).strip() != "1" or category in EXCLUDE_CATEGORIES:
            continue
        key = make_key(category, name)
        if key not in LISTED:
            raise KeyError(f"{key} has select = 1 in the input list but not in data/soil_variable_list.csv")
        out[key] = LISTED[key]
    return out


@lru_cache(maxsize=1)
def config() -> dict[str, VarConfig]:
    """Read variable_config.csv.

    Returns:
        {key: VarConfig}; empty when the file is missing.

    Examples:
        >>> c = config()["Carbon__Total_carbon"]
        >>> c["assume_unit"], c["element"], c["min"], c["max"]
        ('%', 'C', 0.0, 60.0)
    """
    if not VARIABLE_CONFIG.exists():
        return {}
    c = pd.read_csv(VARIABLE_CONFIG, dtype=str, keep_default_na=False)
    out: dict[str, VarConfig] = {}
    for row in c.to_dict("records"):
        r = {str(k): str(v) for k, v in row.items()}
        rules = [x.split("=>", 1) for x in r["methods"].split(";") if "=>" in x]
        out[r["key"]] = VarConfig(
            min=_float(r["min"]), max=_float(r["max"]), unitless=r["unitless"].strip() == "1",
            assume_unit=r["assume_unit"].strip(), time_series=r["time_series"].strip() == "1",
            element=r["element"].strip() or None, exclude_files=r["exclude_files"].strip(),
            methods=[(a.strip(), b.strip()) for a, b in rules],
            column_exclude=r.get("column_exclude", "").strip(), require=r.get("require", "").strip(),
            skip_repeated=r.get("skip_repeated", "").strip() == "1")
    return out


def _float(x: str) -> float | None:
    """Read a number from a config cell ('' -> None).

    Examples:
        >>> _float("2.65"), _float(" ")
        (2.65, None)
    """
    return float(x) if x.strip() else None


VARIABLES: dict[str, Variable] = load()
CATEGORIES: list[str] = list(dict.fromkeys(v.category for v in VARIABLES.values()))


def by_category(category: str) -> list[str]:
    """Return the keys of a category's variables, in input-list order.

    Examples:
        >>> by_category("Acidity")
        ['Acidity__Soil_pH']
    """
    return [k for k, v in VARIABLES.items() if v.category == category]
