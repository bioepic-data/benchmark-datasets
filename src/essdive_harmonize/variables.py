"""Define the harmonized variables from data/soil_variable_list.csv (rows with select = 1).

Each variable is identified by a key built from its '<category>:<variable>' label: '/', '(' and ')' are dropped,
runs of spaces become one, then ':' -> '__' and ' ' -> '_'::

    Physical:Dry bulk density                     -> Physical__Dry_bulk_density
    Phosphorus:Resin / extractable phosphate      -> Phosphorus__Resin_extractable_phosphate
    Major and trace elements (total):Total iron   -> Major_and_trace_elements_total__Total_iron

The key is the output folder, the file-name suffix (<slug>_soil_<key>.csv), the value column and the --var value
of the run commands. Per-variable layout: the value column is <key>, the method column <key lower>_method, and the
extra columns are <key>_unit when the standard unit offers alternatives ("mg C L-1 or mg C kg-1 dry soil"),
<key>_medium for DOC, and analyte for variables with one row per fraction or phase.

Short keys (`Variable.short`, e.g. TC, pH, Caexch) come from notebooks/find_soil_variable_candidates.py. Package code
may use them as aliases (the code ported from harmonize_ph / harmonize_carbon does); they are mapped to the keys on
output.

Examples:
    >>> resolve("TC")
    'Carbon__Total_carbon'
    >>> VARIABLES["Carbon__Total_carbon"].method_column
    'carbon__total_carbon_method'

Attributes:
    PROJECT_ROOT: The repository root.
    VARIABLE_LIST: data/soil_variable_list.csv.
    CARBON_KEYS: Short keys of the ten carbon variables, by variable name.
    UNIT_OVERRIDES: Standard units used instead of the list's wording (kept from harmonize_carbon), by short key.
    EXTRA_COLUMNS: Columns written after the method column, by short key. Entries starting with '_' are suffixes of
        the key (DOC: <key>_unit, <key>_medium); others are used as written. <key>_unit is added automatically for
        variables whose standard unit has alternatives.
    VARIABLES: {key: Variable} for every row with select = 1, in list order.
    ALIASES: {short key: key}.
    CATEGORIES: The categories, in list order.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VARIABLE_LIST = PROJECT_ROOT / "data" / "soil_variable_list.csv"

CARBON_KEYS = {"Total carbon": "TC", "Dissolved organic carbon": "DOC", "Soil organic carbon": "SOC",
               "Soil organic matter": "SOM", "Soil organic carbon stock": "SOCstock",
               "Soil inorganic carbon": "SIC", "Particulate organic matter carbon": "POMC",
               "Loss on ignition": "LOI", "Water-extractable organic carbon": "WEOC",
               "Mineral-associated organic matter carbon": "MAOMC"}

UNIT_OVERRIDES = {
    "TC": "% (g C / 100 g dry soil)",
    "SOC": "% (g C / 100 g dry soil)",
    "DOC": "mg C kg-1 dry soil or mg C L-1",
    "SOM": "% (g / 100 g dry soil)",
    "SOCstock": "kg C m-2",
    "SIC": "% (g C / 100 g dry soil)",
    "POMC": "g C kg-1 dry soil",
    "LOI": "% of dry mass",
    "WEOC": "mg C kg-1 dry soil",
    "MAOMC": "g C kg-1 dry soil",
}

EXTRA_COLUMNS = {
    "DOC": ["_unit", "_medium"],
    "Pfractions": ["analyte"],     # one row per fraction (water, base, acid, organic, dithionite ...)
    "Fespecies": ["analyte"],      # one row per fitted Fe phase
    "mineralogy": ["analyte"],     # one row per mineral phase
}


def make_key(category: str, name: str) -> str:
    """Build a variable key from its category and name.

    Args:
        category: The variable's category in the soil variable list.
        name: The variable's name in the soil variable list.

    Returns:
        The key: '/', '(' and ')' dropped, ':' -> '__', spaces -> '_'.

    Examples:
        >>> make_key("Phosphorus", "Resin / extractable phosphate")
        'Phosphorus__Resin_extractable_phosphate'
        >>> make_key("Major and trace elements (total)", "Total iron")
        'Major_and_trace_elements_total__Total_iron'
    """
    label = re.sub(r"[/()]", "", f"{category}:{name}")
    label = re.sub(r"\s+", " ", label).replace(" :", ":").replace(": ", ":").strip()
    return label.replace(":", "__").replace(" ", "_")


def short_key(variable: str, abbreviation: str) -> str:
    """Build the short key of a variable (the key of find_soil_variable_candidates.py).

    Args:
        variable: The variable's name.
        abbreviation: Its abbreviation in the soil variable list.

    Returns:
        The carbon short key (TC, SOC ...) for carbon variables, else the abbreviation without punctuation.

    Examples:
        >>> short_key("Total carbon", "TC")
        'TC'
        >>> short_key("Exchangeable calcium", "Ca_exch")
        'Caexch'
    """
    if variable in CARBON_KEYS:
        return CARBON_KEYS[variable]
    return re.sub(r"[^A-Za-z0-9]", "", abbreviation)


@dataclass(frozen=True)
class Variable:
    """One harmonized variable.

    Attributes:
        key: The variable key (see the module docstring).
        short: The short key / alias (TC, pH, Caexch ...).
        name: The variable's name in the soil variable list.
        category: Its category.
        unit: Standard unit, as written in the outputs ("a or b" lists alternatives).
        specification: Measurement specification from the list.
        extra: Extra columns written after the method column.

    Examples:
        >>> v = Variable("Carbon__Dissolved_organic_carbon", "DOC", "Dissolved organic carbon", "Carbon",
        ...              "mg C kg-1 dry soil or mg C L-1")
        >>> v.units, v.unit_column
        (['mg C kg-1 dry soil', 'mg C L-1'], 'Carbon__Dissolved_organic_carbon_unit')
    """

    key: str
    short: str
    name: str
    category: str
    unit: str
    specification: str = ""
    extra: tuple[str, ...] = field(default_factory=tuple)

    @property
    def value_column(self) -> str:
        """Return the value column name: the key."""
        return self.key

    @property
    def method_column(self) -> str:
        """Return the method column name: '<key lower>_method'."""
        return f"{self.key.lower()}_method"

    @property
    def label(self) -> str:
        """Return the '<category>:<name>' label used in the selection matrices."""
        return f"{self.category}:{self.name}"

    @property
    def units(self) -> list[str]:
        """Return the standard unit alternatives ('a or b' -> [a, b]), parenthetical remarks dropped.

        Examples:
            >>> Variable("k", "k", "n", "c", "% (g C / 100 g dry soil)").units
            ['%']
            >>> Variable("k", "k", "n", "c", "cmol(+) kg-1").units
            ['cmol(+) kg-1']
        """
        u = re.sub(r"\((?!\+\))[^)]*\)", "", self.unit)  # keep cmol(+)
        return [x.strip() for x in re.split(r"\bor\b", u) if x.strip()]

    @property
    def unit_column(self) -> str | None:
        """Return '<key>_unit' when the standard unit has alternatives, else None."""
        return f"{self.key}_unit" if len(self.units) > 1 else None

    @property
    def legacy_columns(self) -> dict[str, str]:
        """Map the short-key column names to the column names of this layout.

        The short-key names are used by the ported package code and the harmonize_ph / harmonize_carbon outputs.

        Examples:
            >>> VARIABLES["Acidity__Soil_pH"].legacy_columns
            {'pH': 'Acidity__Soil_pH', 'ph_method': 'acidity__soil_ph_method'}
        """
        m = {self.short: self.value_column, f"{self.short.lower()}_method": self.method_column}
        for c in self.extra:
            if c.startswith(self.key + "_"):
                m[self.short + c[len(self.key):]] = c
        return m


def _load() -> dict[str, Variable]:
    """Read the rows with select = 1 of the soil variable list as Variables, keyed and in list order."""
    lst = pd.read_csv(VARIABLE_LIST, dtype=str, keep_default_na=False)
    out: dict[str, Variable] = {}
    for r in lst[lst["select"] == "1"].itertuples():
        category, name, spec = str(r.category), str(r.variable), str(r.specification)
        key, short = make_key(category, name), short_key(name, str(r.abbreviation))
        unit = UNIT_OVERRIDES.get(short, str(r.standard_unit))
        extra = [key + c if c.startswith("_") else c for c in EXTRA_COLUMNS.get(short, [])]
        v = Variable(key, short, name, category, unit, spec)
        if v.unit_column and v.unit_column not in extra:
            extra.insert(0, v.unit_column)
        if key in out:
            raise ValueError(f"two variables give the key {key!r}")
        out[key] = Variable(key, short, name, category, unit, spec, tuple(extra))
    return out


VARIABLES: dict[str, Variable] = _load()
ALIASES: dict[str, str] = {v.short: k for k, v in VARIABLES.items()}
CATEGORIES: list[str] = list(dict.fromkeys(v.category for v in VARIABLES.values()))


def resolve(var: str) -> str:
    """Return the variable key for a key or a short alias.

    Args:
        var: A variable key or short alias.

    Returns:
        The key.

    Raises:
        KeyError: When `var` is neither.

    Examples:
        >>> resolve("pH"), resolve("Acidity__Soil_pH")
        ('Acidity__Soil_pH', 'Acidity__Soil_pH')
        >>> resolve("nope")
        Traceback (most recent call last):
            ...
        KeyError: "unknown variable 'nope'; see `run.py --list`"
    """
    if var in VARIABLES:
        return var
    if var in ALIASES:
        return ALIASES[var]
    raise KeyError(f"unknown variable {var!r}; see `run.py --list`")


def by_category(category: str) -> list[str]:
    """Return the keys of a category's variables, in list order.

    Args:
        category: A category of the soil variable list.

    Returns:
        The keys.

    Examples:
        >>> by_category("Acidity")
        ['Acidity__Soil_pH']
    """
    return [k for k, v in VARIABLES.items() if v.category == category]
