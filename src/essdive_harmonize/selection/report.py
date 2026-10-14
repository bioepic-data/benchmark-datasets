"""Write the output tables of the package-selection workflow.

Every table covers all packages, then splits them by soil_related, with the broader soil_context (soil-related, or
sediment / peat / permafrost / porewater ...) alongside.

Attributes:
    CODES: One-letter codes of the evidence sources in matrix_sources.csv.
    SOURCES: The evidence sources, in code order.
    Group: A summary group: (evidence flag column, value), or None for all packages.
    GROUPS: Summary column suffix -> group.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Final, Literal, TypeAlias

import pandas as pd

from .datatypes import HasSpec, Source

# one-letter codes of the evidence sources in matrix_sources.csv
CODES: Final[dict[Source, str]] = {"columns": "C", "dictionary": "d", "keywords": "K", "description": "D",
                                   "other": "O"}
SOURCES: Final[list[Source]] = list(CODES)
# summary column suffix -> (evidence flag column, value) selecting the packages, None = all packages
Group: TypeAlias = "tuple[Literal['soil', 'context'], bool] | None"
GROUPS: Final[dict[str, Group]] = {"all": None, "soil": ("soil", True), "nonsoil": ("soil", False),
                                   "soil_context": ("context", True)}


def package_table(packages: pd.DataFrame, headers: pd.DataFrame, ev: pd.DataFrame) -> pd.DataFrame:
    """Build packages.csv: one row per package with its soil classification and evidence counts.

    Args:
        packages: Packages with their soil classification.
        headers: The column-header cache.
        ev: The evidence table.

    Returns:
        doi, package_id, title, provider, n_listed_files, soil fields, n_files_scanned, n_variables_any and
        n_variables_columns; packages with the most variables first.
    """
    n_files = headers.groupby("doi").file.nunique()
    n_vars = ev.groupby("doi").key.nunique()
    n_vars_cols = ev[ev.source == "columns"].groupby("doi").key.nunique()
    out = packages[["doi", "package_id", "title", "provider", "n_listed_files", "soil_related", "soil_evidence",
                    "soil_columns", "soil_context"]].copy()
    out["n_files_scanned"] = out.doi.map(n_files).fillna(0).astype(int)
    out["n_variables_any"] = out.doi.map(n_vars).fillna(0).astype(int)
    out["n_variables_columns"] = out.doi.map(n_vars_cols).fillna(0).astype(int)
    return out.sort_values(["n_variables_any", "doi"], ascending=[False, True])


def variable_summary(variables: Sequence[HasSpec], ev: pd.DataFrame, soil: pd.Series,
                     context: pd.Series) -> pd.DataFrame:
    """Count, per variable, the packages with each kind of evidence.

    Args:
        variables: The variables.
        ev: The evidence table.
        soil: soil_related by DOI.
        context: Whether a package has soil context, by DOI.

    Returns:
        One row per variable: <kind>_all, <kind>_soil, <kind>_nonsoil and <kind>_soil_context for the kinds any,
        strong, columns_with_data and each source.

    Examples:
        >>> from types import SimpleNamespace
        >>> v = SimpleNamespace(key="k", category="c", name="n")
        >>> ev = pd.DataFrame({"doi": ["d1", "d2"], "key": "k", "source": "columns", "strength": "strong",
        ...                    "n_numeric": [5, 0]})
        >>> s = variable_summary([v], ev, pd.Series({"d1": True, "d2": False}), pd.Series({"d1": True, "d2": True}))
        >>> s[["any_all", "any_soil", "columns_with_data_all", "any_soil_context"]].values.tolist()
        [[2, 1, 1, 2]]
    """
    ev = ev.assign(soil=ev.doi.map(soil).fillna(False).astype(bool),
                   context=ev.doi.map(context).fillna(False).astype(bool))
    metrics: dict[str, pd.DataFrame] = {
        "any": ev,
        "strong": ev[ev.strength == "strong"],
        "columns_with_data": ev[(ev.source == "columns") & (ev.n_numeric > 0)],
        **{s: ev[ev.source == s] for s in SOURCES},
    }
    rows: list[dict[str, Any]] = []
    for v in variables:
        r: dict[str, Any] = dict(category=v.category, variable=v.name, key=v.key)
        for m, df in metrics.items():
            d = df[df.key == v.key]
            for g, flag in GROUPS.items():
                dd = d if flag is None else d[d[flag[0]] == flag[1]]
                r[f"{m}_{g}"] = dd.doi.nunique()
        rows.append(r)
    return pd.DataFrame(rows)


def matrices(variables: Sequence[HasSpec], ev: pd.DataFrame, pk: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build the package x variable matrices.

    Args:
        variables: The variables (columns, labelled '<category>:<variable>').
        ev: The evidence table.
        pk: The package table (soil_related, soil_context).

    Returns:
        The 0/1 matrix and the source-code matrix (C columns, d dictionary, K keywords, D description, O other); rows are
        the packages with any evidence, soil-related first, then those with soil context.
    """
    labels = {v.key: v.label for v in variables}
    codes = (ev.assign(code=ev.source.map(CODES), order=ev.source.map(SOURCES.index))
             .sort_values("order").groupby(["doi", "key"]).code.agg("".join).unstack())
    codes = codes.reindex(columns=[v.key for v in variables]).rename(columns=labels)
    flags = pk.set_index("doi")[["soil_related", "soil_context"]].reindex(codes.index)
    codes.insert(0, "soil_related", flags.soil_related.fillna(False).astype(int))
    codes.insert(1, "soil_context", flags.soil_context.fillna(""))
    order = codes.soil_related * 2 + codes.soil_context.ne("")
    codes = codes.loc[order.sort_values(ascending=False, kind="stable").index]
    binary = codes.copy()
    binary.iloc[:, 2:] = binary.iloc[:, 2:].notna().astype(int)
    return binary, codes.fillna("")


def write_all(out_dir: Path, variables: Sequence[HasSpec], packages: pd.DataFrame, headers: pd.DataFrame,
              log: pd.DataFrame, ev: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Write every output table to the output folder.

    Args:
        out_dir: The output folder.
        variables: The variables.
        packages: Packages with their soil classification.
        headers: The column-header cache.
        log: Files that could not be read.
        ev: The evidence table.

    Returns:
        {file name: table} of what was written.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    pk = package_table(packages, headers, ev)
    soil, context = pk.set_index("doi").soil_related, pk.set_index("doi").soil_context
    summary = variable_summary(variables, ev, soil, context.ne(""))
    binary, codes = matrices(variables, ev, pk)
    files: dict[str, pd.DataFrame] = {
        "packages.csv": pk,
        "evidence.csv": ev.assign(soil_related=ev.doi.map(soil).fillna(False),
                                  soil_context=ev.doi.map(context).fillna("")),
        "variable_summary.csv": summary,
        "matrix_any.csv": binary,
        "matrix_sources.csv": codes,
        "scan_log.csv": log,
    }
    for name, df in files.items():
        df.to_csv(out_dir / name, index=name.startswith("matrix"))
    return files
