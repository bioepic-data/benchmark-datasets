"""Load the variables to search for from data/soil_variable_list_input.csv.

The file is tab-separated with the columns select, category and variable; the select column is ignored.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ..variables import make_key
from .config import VARIABLE_LIST
from .rules import Spec, spec_for


@dataclass(frozen=True)
class ListVariable:
    """One variable of the list, with its matching rules.

    Attributes:
        category: Category in the list.
        name: Variable name in the list.
        key: '<category>__<name>' key (essdive_harmonize.variables.make_key).
        label: '<category>:<name>', the matrix column label.
        spec: The matching rules (rules.spec_for).

    Examples:
        >>> from essdive_harmonize.selection.rules import spec_for
        >>> ListVariable("Acidity", "Soil pH", "Acidity__Soil_pH", "Acidity:Soil pH", spec_for("Soil pH")).spec.mode
        'raw'
    """
    category: str
    name: str
    key: str        # '<category>__<name>' folder/column key of essdive_harmonize.variables.make_key
    label: str      # '<category>:<name>', the matrix column label
    spec: Spec


def load_variables(path: Path = VARIABLE_LIST) -> list[ListVariable]:
    """Load every row of the variable list, in file order, with its matching rules.

    Args:
        path: The tab-separated variable list.

    Returns:
        One ListVariable per row.

    Raises:
        KeyError: When a variable has no matching rule.

    Examples:
        >>> [v.key for v in load_variables()][:2]  # doctest: +SKIP
        ['Acidity__Soil_pH', 'Base_cations__Cation_exchange_capacity']
    """
    df = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False)
    df.columns = [c.strip().lower() for c in df.columns]
    out: list[ListVariable] = []
    for r in df.itertuples():
        cat, name = str(r.category).strip(), str(r.variable).strip()
        out.append(ListVariable(cat, name, make_key(cat, name), f"{cat}:{name}", spec_for(name)))
    return out
