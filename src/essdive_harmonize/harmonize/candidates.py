"""List the candidate packages and matched columns of each variable, from data/intermediate/package_selection.

A package is a candidate for a variable when (user decisions 2026-10-07):

- it has a matching column with numeric values in a data file (evidence source 'columns', n_numeric > 0);
- its soil_context has one of SOIL_TERMS (soil, sediment, peat, permafrost, horizon);
- it has no plant term (PLANT_TERMS) in its exclusion_terms, unless its soil_context has "soil" itself (user decision
  2026-10-12: permafrost or peat alone often comes from project text, as in leaf C and N packages);
- it is not excluded package-wide in triage.csv (variable '*', keep 0: water, plant tissue, modeling ...).

The matched (file, sheet, column) triples come from the cached column headers, classified with the same rules as
the package selection.
"""

from __future__ import annotations

from collections.abc import Iterable
from functools import lru_cache

import pandas as pd

from ..selection.matching import classify_column, combined, organic_defined
from ..selection.rules import ORGANIC_FROM, ORGANIC_TO, spec_for
from .config import EVIDENCE, HEADERS, PLANT_TERMS, SOIL_TERMS, TRIAGE
from .variables import VARIABLES


@lru_cache(maxsize=1)
def evidence() -> pd.DataFrame:
    """Read the evidence table of the package selection (cached)."""
    return pd.read_csv(EVIDENCE, keep_default_na=False)


@lru_cache(maxsize=1)
def headers() -> pd.DataFrame:
    """Read the column-header cache of the package selection (cached), with typed is_dictionary and n_numeric."""
    h = pd.read_csv(HEADERS, dtype=str, keep_default_na=False)
    h["is_dictionary"] = h.is_dictionary.eq("True")
    h["n_numeric"] = pd.to_numeric(h.n_numeric, errors="coerce").fillna(0).astype(int)
    return h


@lru_cache(maxsize=1)
def excluded_packages() -> dict[str, str]:
    """Read the package-wide exclusions of triage.csv.

    Returns:
        {doi: reason} for the rows with variable '*' and keep 0; empty when the file is missing.
    """
    if not TRIAGE.exists():
        return {}
    t = pd.read_csv(TRIAGE, dtype=str, keep_default_na=False)
    t = t[(t.variable == "*") & (t.keep == "0")]
    return {str(d): str(r) for d, r in zip(t.doi, t.reason)}


def _soil(context: str) -> bool:
    """Tell whether a soil_context string has one of SOIL_TERMS.

    Examples:
        >>> _soil("sediment; porewater"), _soil("porewater")
        (True, False)
    """
    return bool(SOIL_TERMS & set(context.split("; ")))


def _terms(values: Iterable[str]) -> set[str]:
    """Split and pool '; '-joined term lists.

    Examples:
        >>> sorted(_terms(["leaf; river", "", "leaf"]))
        ['leaf', 'river']
    """
    return {t for v in values for t in v.split("; ") if t}


@lru_cache(maxsize=1)
def plant_only() -> dict[str, str]:
    """Find the packages with plant terms and no "soil" in their soil context, over all of their evidence rows.

    Returns:
        {doi: 'plant terms: ...; soil context: ...'}.
    """
    out = {}
    for doi, g in evidence().groupby("doi"):
        plant, context = _terms(g.exclusion_terms) & PLANT_TERMS, _terms(g.soil_context)
        if plant and "soil" not in context:
            out[str(doi)] = f"plant terms: {', '.join(sorted(plant))}; soil context: {', '.join(sorted(context))}"
    return out


def candidate_table(key: str) -> pd.DataFrame:
    """List every package with numeric data-column evidence for a variable, with its status.

    Args:
        key: The variable key.

    Returns:
        doi, key, variable, status ('candidate', 'not soil (...)' or 'excluded in triage: ...'), n_columns, n_numeric,
        detail and soil_context.

    Examples:
        >>> candidate_table("Acidity__Soil_pH").status.str.split().str[0].value_counts().to_dict()  # doctest: +SKIP
        {'candidate': 64, 'excluded': 25, 'not': 17}
    """
    v = VARIABLES[key]
    ev = evidence()
    e = ev[(ev.key == key) & (ev.source == "columns") & (ev.n_numeric > 0)].copy()
    exc = excluded_packages()
    e["status"] = "candidate"
    e.loc[~e.soil_context.map(_soil), "status"] = "not soil (" + e.soil_context.replace("", "no soil context") + ")"
    plant = plant_only()
    pl = e.doi.isin(plant) & (e.status == "candidate")
    e.loc[pl, "status"] = "not soil (" + e.loc[pl, "doi"].map(plant) + ")"
    ex = e.doi.isin(exc) & (e.status == "candidate")
    e.loc[ex, "status"] = "excluded in triage: " + e.loc[ex, "doi"].map(exc)
    e["variable"] = v.name
    return e[["doi", "key", "variable", "status", "n_columns", "n_numeric", "detail", "soil_context"]]


def candidates(key: str) -> list[str]:
    """Return the candidate DOIs of a variable, sorted.

    Examples:
        >>> len(candidates("Acidity__Soil_pH"))  # doctest: +SKIP
        64
    """
    t = candidate_table(key)
    return sorted(t.doi[t.status == "candidate"])


def matched_columns(key: str, dois: Iterable[str] | None = None) -> pd.DataFrame:
    """Find the data-file columns that match a variable.

    Args:
        key: The variable key.
        dois: Limit to these packages.

    Returns:
        The header rows (doi, file, sheet, column, n_numeric ...) of data-file columns with numeric values that match
        the variable by name or by '<group> <column>', with their strength. A Total carbon column that the package's
        data dictionary defines as organic carbon belongs to Soil organic carbon instead (rules.organic_definition).

    Examples:
        >>> matched_columns("Acidity__Soil_pH", ["doi:10.15485/1725884"]).column.tolist()  # doctest: +SKIP
        ['pH']
    """
    name = VARIABLES[key].name
    h = headers()
    h = h[~h.is_dictionary & (h.n_numeric > 0)]
    if dois is not None:
        h = h[h.doi.isin(set(dois))]
    m = _by_name(h, name)
    if name in (ORGANIC_FROM, ORGANIC_TO):
        tc = m if name == ORGANIC_FROM else _by_name(h, ORGANIC_FROM)
        organic = tc[organic_defined(tc, headers())] if len(tc) else tc
        if name == ORGANIC_FROM:
            m = m.drop(index=organic.index)
        else:
            m = pd.concat([m, organic.assign(strength="strong")])
            m = m[~m.index.duplicated()]
    return m.reset_index(drop=True)


def _by_name(h: pd.DataFrame, name: str) -> pd.DataFrame:
    """Return the header rows whose column (or '<group> <column>') matches a variable, with their strength."""
    spec = spec_for(name)
    comb = combined(h)
    cls = {c: classify_column(c, spec)[0] for c in pd.concat([h.column, comb]).drop_duplicates()}
    s = h.column.map(cls)
    s = s.where(s.notna(), comb.map(cls))
    return h[s.notna()].assign(strength=s[s.notna()])
