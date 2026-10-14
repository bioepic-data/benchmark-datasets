"""Define the types shared by the harmonization modules.

The package-selection types are in selection/datatypes.py.

Attributes:
    Tables: Harmonized tables of one package: variable key (or short alias) -> rows in the soil pH layout.
    PackageResult: What a package function returns: tables per variable, or one table for its default variable
        (the ported pH / carbon functions).
    PackageFunc: A package function.
    Field: A field of make_base / emit: a column name of the raw table, one value for every row, or one value per row.
    Cell: A text value read from a CSV / Excel cell (pandas gives str, or float NaN for empty cells).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, TypeAlias

import numpy as np
import pandas as pd

Tables: TypeAlias = dict[str, pd.DataFrame]
PackageResult: TypeAlias = "Tables | pd.DataFrame | None"
PackageFunc: TypeAlias = Callable[[], PackageResult]
Field: TypeAlias = "str | int | float | None | Sequence[Any] | pd.Series | pd.Index | np.ndarray"
Cell: TypeAlias = "str | float | None"
