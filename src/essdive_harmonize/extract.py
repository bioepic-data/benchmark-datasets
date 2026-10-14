"""Map raw table columns to harmonized tables for any variables.

Most package functions only need

1. a base table, row-aligned with the raw data table: doi, source_file, id, id_type, depth, date, latitude,
   longitude, IGSN and notes (the notes start with 'lat/long source: ...'), and
2. a column map {variable: Col(...)} for wide tables, or an analyte map for long tables::

    base = make_base(raw, doi, src, id="Sample_ID", id_type="Sample_ID", depth=..., date=...,
                     latitude="Lat", longitude="Long", notes="lat/long source: doi:...:file (per-sample GPS)")
    return from_columns(base, raw, {
        "TN": Col("TN (%)", "%", DRY_COMBUSTION, "Elementar vario EL cube"),
        "NO3N": Col("NO3-N (mg/kg)", "mg N kg-1", SALT_EXTRACTION, "2 M KCl extract"),
        "Caexch": Col("Ca (mg/kg)", "mg kg-1", SALT_EXTRACTION, "1 M NH4OAc", element="Ca"),
    })

Values are converted to the variable's standard unit (variables.py, units.py), and the source column, source unit
and conversion are written to notes. A variable with alternative standard units (a <V>_unit column) keeps the first
alternative the source unit converts to.

Examples:
    >>> raw = pd.DataFrame({"ID": ["s1", "s2"], "C (g/kg)": ["12", "30"], "Lat": ["38.9", "38.9"],
    ...                     "Lon": ["-106.9", "-106.9"]})
    >>> base = make_base(raw, "doi:10.0/x", "soil.csv", id="ID", id_type="ID", latitude="Lat", longitude="Lon",
    ...                  notes="lat/long source: doi:10.0/x:soil.csv (per-sample)")
    >>> tc = from_columns(base, raw, {"TC": Col("C (g/kg)", "g/kg")})["Carbon__Total_carbon"]
    >>> tc["Carbon__Total_carbon"].tolist()
    ['1.2', '3']
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from . import units
from .datatypes import Field, PackageFunc, Tables
from .common import UNKNOWN, assemble, is_missing, num, variable
from .variables import resolve


@dataclass
class Col:
    """One raw column mapped to a variable.

    Attributes:
        column: Raw column name.
        unit: Source unit; None when the values are already in the variable's standard unit.
        method: Value of the <v>_method column (the method vocabulary of common.py).
        note: Method details for notes (instrument, extractant, ratio ...).
        element: Element or species for mole <-> mass and cmol(+) conversions (a key of units.MOLAR_MASS).
        molar_mass: Molar mass in g/mol, instead of the element's.
        valence: Valence, instead of the element's.
        rows: Boolean mask of the raw rows to use; all rows when None.
        cols: Extra column values of the variable (scalars or row-aligned), e.g. a DOC medium column.

    Examples:
        >>> Col("Ca (cmol/kg)", "cmol(+) kg-1", element="Ca").charge()
        2
    """

    column: str
    unit: str | None = None
    method: str = UNKNOWN
    note: str = ""
    element: str | None = None
    molar_mass: float | None = None
    valence: float | None = None
    rows: pd.Series | None = None
    cols: dict[str, Any] = field(default_factory=dict)

    def mass(self) -> float | None:
        """Return the molar mass for conversions: `molar_mass`, else that of `element`.

        Examples:
            >>> Col("Fe", element="Fe").mass()
            55.845
            >>> Col("TC").mass() is None
            True
        """
        return self.molar_mass or (units.MOLAR_MASS.get(self.element) if self.element else None)

    def charge(self) -> float | None:
        """Return the valence for cmol(+) conversions: `valence`, else that of `element`.

        Examples:
            >>> Col("Mg", element="Mg").charge()
            2
        """
        return self.valence or (units.VALENCE.get(self.element) if self.element else None)


def make_base(raw: pd.DataFrame, doi: str, source_file: str, *, id: Field = None, id_type: str = "",
              depth: Field = "", date: Field = "", latitude: Field = "", longitude: Field = "", IGSN: Field = "",
              notes: Field = "", **extra: Field) -> pd.DataFrame:
    """Build the base table of sample rows, row-aligned with a raw table.

    Each field may be a column name of `raw` (its values are used, stripped), one value for every row, or a
    row-aligned sequence.

    Args:
        raw: The raw data table.
        doi: The package DOI.
        source_file: The data file's name as listed on ESS-DIVE.
        id: Sample identifier.
        id_type: Name of the identifying column(s).
        depth: Depth interval or horizon.
        date: Sampling date (YYYY-MM-DD).
        latitude: Latitude in decimal degrees.
        longitude: Longitude in decimal degrees.
        IGSN: IGSN sample identifier.
        notes: Notes, starting with 'lat/long source: ...'.
        **extra: Other columns (e.g. a unique key column).

    Returns:
        The base table, with the index of `raw`.

    Examples:
        >>> raw = pd.DataFrame({"Sample": [" s1", "s2 "], "Top": ["0", "5"]})
        >>> b = make_base(raw, "doi:10.0/x", "soil.csv", id="Sample", id_type="Sample", depth=["0-5", "5-10"],
        ...               latitude=38.9, longitude=-106.9)
        >>> b[["id", "depth", "latitude"]].values.tolist()
        [['s1', '0-5', 38.9], ['s2', '5-10', 38.9]]
    """
    def pick(x: Field) -> Any:
        if isinstance(x, str) and x in raw.columns:
            return raw[x].astype(str).str.strip().values
        if x is None or isinstance(x, (str, int, float)):
            return x
        return list(x)
    b = pd.DataFrame(index=raw.index)
    b["doi"], b["source_file"] = doi, source_file
    b["id"], b["id_type"] = pick(id if id is not None else ""), id_type
    b["depth"], b["date"] = pick(depth), pick(date)
    b["latitude"], b["longitude"], b["IGSN"] = pick(latitude), pick(longitude), pick(IGSN)
    b["notes"] = pick(notes)
    for k, v in extra.items():
        b[k] = pick(v)
    return b


def target_unit(var: str, src_unit: str | None, **kw: float | None) -> tuple[str, float]:
    """Find the variable's standard unit that a source unit converts to.

    Args:
        var: A variable key or short alias.
        src_unit: Unit of the source values; None when they are already in the (first) standard unit.
        **kw: `molar_mass` and `valence`, as for units.factor.

    Returns:
        The standard unit and the conversion factor.

    Raises:
        units.UnitError: When the source unit converts to none of the standard units.

    Examples:
        >>> target_unit("TC", "g/kg")
        ('%', 0.1)
        >>> target_unit("DOC", "mg/L")
        ('mg C L-1', 1.0)
        >>> target_unit("TC", "g cm-3")
        Traceback (most recent call last):
            ...
        essdive_harmonize.units.UnitError: TC: 'g cm-3' converts to none of ['%'] (incompatible units 'g cm-3' -> '%')
    """
    v = variable(var)
    if src_unit is None:
        return v.units[0], 1.0
    errors = []
    for u in v.units:
        try:
            return u, units.factor(src_unit, u, **kw)
        except units.UnitError as e:
            errors.append(str(e))
    raise units.UnitError(f"{var}: {src_unit!r} converts to none of {v.units} ({'; '.join(errors)})")


def column_table(base: pd.DataFrame, raw: pd.DataFrame, var: str, c: Col, extra: list[str] | None = None,
                 drop_empty: bool = True) -> pd.DataFrame:
    """Build the harmonized rows of one variable from one raw column.

    Args:
        base: Base table row-aligned with `raw` (see `make_base`).
        raw: The raw data table.
        var: A variable key or short alias.
        c: The column mapping.
        extra: Extra key columns, as for common.assemble.
        drop_empty: Drop rows without a numeric value.

    Returns:
        The harmonized table; values converted to the standard unit, the source column, unit and conversion in
        notes.

    Examples:
        >>> raw = pd.DataFrame({"pH": ["7.4", "NA"], "Lat": ["38.9", "38.9"], "Lon": ["-106.9", "-106.9"]})
        >>> base = make_base(raw, "doi:10.0/x", "soil.csv", latitude="Lat", longitude="Lon")
        >>> t = column_table(base, raw, "pH", Col("pH", method="pH_H2O", note="1:1 water"))
        >>> t[["Acidity__Soil_pH", "notes"]].values.tolist()
        [['7.4', 'source column pH; 1:1 water']]
    """
    v = variable(var)
    rows = raw.index if c.rows is None else raw.index[pd.Series(c.rows, index=raw.index).fillna(False).astype(bool)]
    b, r = base.loc[rows].copy(), raw.loc[rows]
    unit, f = target_unit(var, c.unit, molar_mass=c.mass(), valence=c.charge())
    vals = num(r[c.column])
    b["value"] = [] if not len(vals) else [("" if pd.isna(x) else f"{x * f:.10g}") for x in vals]
    b["method"] = c.method
    src = f"{c.column}" + (f" ({c.unit})" if c.unit else "")
    conv = units.conversion_note(c.unit, unit, f) if c.unit else ""
    parts = [p for p in (f"source column {src}", conv, c.note) if p]
    b["notes"] = [(n + "; " if n else "") + "; ".join(parts) for n in b["notes"]]
    if v.unit_column:
        b[v.unit_column] = unit
    for k, val in c.cols.items():
        b[k] = val if isinstance(val, str) else list(pd.Series(val, index=raw.index).loc[rows])
    return assemble(b, var, extra, drop_empty=drop_empty)


def from_columns(base: pd.DataFrame, raw: pd.DataFrame, mapping: dict[str, Col | list[Col]],
                 extra: list[str] | None = None, drop_empty: bool = True) -> Tables:
    """Build harmonized tables from the columns of a wide table.

    Args:
        base: Base table row-aligned with `raw` (see `make_base`).
        raw: The raw data table.
        mapping: {variable key or alias: Col or [Col, ...]}. Several Cols of one variable are stacked (e.g. pH in
            water and in CaCl2, or one variable from two methods).
        extra: Extra key columns, as for common.assemble.
        drop_empty: Drop rows without a numeric value.

    Returns:
        {variable key: harmonized table}, without variables that have no rows.

    Examples:
        >>> raw = pd.DataFrame({"pH_H2O": ["5.5"], "pH_CaCl2": ["4.9"], "Lat": ["1"], "Lon": ["2"]})
        >>> base = make_base(raw, "doi:10.0/x", "soil.csv", latitude="Lat", longitude="Lon")
        >>> t = from_columns(base, raw, {"pH": [Col("pH_H2O", method="pH_H2O"), Col("pH_CaCl2", method="pH_CaCl2")]})
        >>> t["Acidity__Soil_pH"][["Acidity__Soil_pH", "acidity__soil_ph_method"]].values.tolist()
        [['5.5', 'pH_H2O'], ['4.9', 'pH_CaCl2']]
    """
    out: Tables = {}
    for var, spec in mapping.items():
        cs = spec if isinstance(spec, (list, tuple)) else [spec]
        t = pd.concat([column_table(base, raw, var, c, extra, drop_empty) for c in cs], ignore_index=True)
        if len(t):
            out[resolve(var)] = t
    return out


def from_long(base: pd.DataFrame, raw: pd.DataFrame, analyte_col: str, value_col: str,
              mapping: dict[str, tuple[str, dict[str, Any]]], unit_col: str | None = None,
              extra: list[str] | None = None) -> Tables:
    """Build harmonized tables from a long table (one row per sample and analyte).

    Args:
        base: Base table row-aligned with `raw` (see `make_base`).
        raw: The raw data table.
        analyte_col: Column naming the analyte.
        value_col: Column holding the values.
        mapping: {analyte value: (variable, Col keyword arguments)}. The arguments give method / note / element
            and, when there is no unit column, unit. A variable with an `analyte` column gets the analyte there.
        unit_col: Column holding each row's unit, if any.
        extra: Extra key columns, as for common.assemble.

    Returns:
        {variable key: harmonized table}, without variables that have no rows.

    Examples:
        >>> raw = pd.DataFrame({"Analyte": ["TC", "TC", "TN"], "Result": ["12", "1.5", "0.9"],
        ...                     "Units": ["g/kg", "%", "%"], "Lat": "1", "Lon": "2"})
        >>> base = make_base(raw, "doi:10.0/x", "soil.csv", latitude="Lat", longitude="Lon")
        >>> t = from_long(base, raw, "Analyte", "Result", {"TC": ("TC", {"method": "dry_combustion"})}, unit_col="Units")
        >>> t["Carbon__Total_carbon"]["Carbon__Total_carbon"].tolist()
        ['1.2', '1.5']
    """
    frames: dict[str, list[pd.DataFrame]] = {}
    analytes = raw[analyte_col].astype(str).str.strip()
    for analyte, (var, kw) in mapping.items():
        mask = analytes == analyte
        if not mask.any():
            continue
        units_here = raw.loc[mask, unit_col].astype(str).str.strip().unique() if unit_col else [kw.get("unit")]
        for u in units_here:
            m = mask & (raw[unit_col].astype(str).str.strip() == u) if unit_col else mask
            cols = dict(kw.get("cols", {}))
            if "analyte" in variable(var).extra:
                cols.setdefault("analyte", analyte)
            c = Col(value_col, **{**kw, "unit": u or None, "rows": m, "cols": cols,
                                  "note": "; ".join(x for x in (f"{analyte_col} = {analyte}", kw.get("note", "")) if x)})
            frames.setdefault(resolve(var), []).append(column_table(base, raw, var, c, extra))
    return {v: pd.concat(fs, ignore_index=True) for v, fs in frames.items() if sum(map(len, fs))}


def merge_tables(*parts: Tables) -> Tables:
    """Combine the tables of several source files of one package.

    Args:
        *parts: {variable key or alias: table} from each source file.

    Returns:
        {variable key: tables of that variable stacked in order}.

    Examples:
        >>> a = {"pH": pd.DataFrame({"x": [1]})}
        >>> b = {"Acidity__Soil_pH": pd.DataFrame({"x": [2]}), "TC": pd.DataFrame({"x": [3]})}
        >>> {k: t.x.tolist() for k, t in merge_tables(a, b).items()}
        {'Acidity__Soil_pH': [1, 2], 'Carbon__Total_carbon': [3]}
    """
    out: dict[str, list[pd.DataFrame]] = {}
    for p in parts:
        for var, t in p.items():
            out.setdefault(resolve(var), []).append(t)
    return {v: pd.concat(ts, ignore_index=True) for v, ts in out.items()}


def combine(*parts: tuple[str, PackageFunc]) -> Callable[[], Tables]:
    """Make one package function from several.

    Args:
        *parts: (default variable, function) pairs. A function may return {variable: table} or a bare table, which
            is taken as its default variable (the pH and carbon functions ported from harmonize_ph /
            harmonize_carbon).

    Returns:
        A function returning {variable key: tables of all parts stacked}; its __name__ joins the parts' names.

    Examples:
        >>> def ph_x(): return pd.DataFrame({"v": [7.0]})
        >>> def c_x(): return {"TC": pd.DataFrame({"v": [1.2]}), "pH": pd.DataFrame({"v": [6.5]})}
        >>> f = combine(("pH", ph_x), ("TC", c_x))
        >>> f.__name__, {k: t.v.tolist() for k, t in f().items()}
        ('ph_x+c_x', {'Acidity__Soil_pH': [7.0, 6.5], 'Carbon__Total_carbon': [1.2]})
    """
    def package() -> Tables:
        out: Tables = {}
        for default, f in parts:
            r = f()
            got: dict[str, pd.DataFrame | None] = {default: r} if isinstance(r, pd.DataFrame) else dict(r or {})
            for var, t in got.items():
                if t is None:
                    continue
                var = resolve(var)
                out[var] = pd.concat([out[var], t], ignore_index=True) if var in out else t
        return out
    package.__name__ = "+".join(f.__name__ for _, f in parts)
    return package


__all__ = ["Col", "make_base", "from_columns", "from_long", "merge_tables", "combine", "target_unit", "is_missing"]
