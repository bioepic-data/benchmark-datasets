"""Collect the hand-written package functions, grouped by how sample locations were obtained.

The groups (packages/group<N>_*.py):

- Group 1: coordinates in the data file itself.
- Group 2: coordinates from package metadata or text.
- Group 3: coordinates joined from another file or package.
- Group 4: coordinates converted from projected / grid values.

Each module lists PACKAGES = [(doi, func), ...] or [(doi, func, provides), ...]. A package function returns
{variable key or short alias: DataFrame} for every variable it reports; `provides` (keys or aliases) lets run.py skip
the package when none of the requested variables is among them. These functions are the pH and carbon harmonizers
ported from harmonize_ph / harmonize_carbon; the generic workflow (harmonize/) uses them only as a check.

Examples:
    >>> len(PACKAGES), sorted({p.group for p in PACKAGES})
    (75, [1, 2, 3, 4])

Attributes:
    MODULES: The group modules, by group number.
    PACKAGES: Every registered package, in group and module order.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Final

import pandas as pd

from .datatypes import Tables
from .variables import resolve


@dataclass(frozen=True)
class Package:
    """A registered package function.

    Attributes:
        group: Location group (1-4).
        doi: The package DOI.
        func: Returns {variable key or alias: harmonized table}.
        provides: Variables the function reports (keys or aliases); None when not declared.
    """

    group: int
    doi: str
    func: Callable[[], Tables]
    provides: tuple[str, ...] | None = None

    def wants(self, variables: Iterable[str]) -> bool:
        """Tell whether the package should run for the requested variables.

        Args:
            variables: Requested variable keys or aliases; empty means all.

        Returns:
            True when nothing is requested, `provides` is undeclared, or a requested variable is provided.

        Examples:
            >>> p = Package(1, "doi:10.0/x", dict, ("pH", "TC"))
            >>> p.wants([]), p.wants(["Carbon__Total_carbon"]), p.wants(["DOC"])
            (True, True, False)
        """
        return (not variables or self.provides is None
                or bool({resolve(v) for v in variables} & {resolve(v) for v in self.provides}))

    def tables(self) -> Tables:
        """Run the package function.

        Returns:
            {variable key: table} for the variables with rows; short aliases are resolved.

        Examples:
            >>> p = Package(1, "doi:10.0/x", lambda: {"pH": pd.DataFrame({"v": [7.1]}), "TC": pd.DataFrame()})
            >>> {k: t.v.tolist() for k, t in p.tables().items()}
            {'Acidity__Soil_pH': [7.1]}
        """
        out: Tables = {}
        for v, df in self.func().items():
            if df is not None and len(df):
                out[resolve(v)] = df
        return out


MODULES: Final[dict[int, str]] = {
    1: ".packages.group1_infile_coords",
    2: ".packages.group2_metadata_coords",
    3: ".packages.group3_joined_coords",
    4: ".packages.group4_projected_coords",
}

PACKAGES: list[Package] = []
for _group, _name in MODULES.items():
    _mod = importlib.import_module(_name, __package__)
    for _entry in _mod.PACKAGES:
        _doi, _func, *_rest = _entry
        PACKAGES.append(Package(_group, _doi, _func, tuple(_rest[0]) if _rest else None))

_dups = {p.doi for p in PACKAGES if sum(q.doi == p.doi for q in PACKAGES) > 1}
if _dups:
    raise ValueError(f"packages registered twice: {sorted(_dups)}")
