"""List the candidate packages of a variable and the keep / exclude decisions for them.

Candidates for a variable are the packages with a matching column in the selected-variable hit matrix (MATRIX,
built by notebooks/find_soil_variable_candidates.py --selected; archived on 2026-10-08), plus any package
harmonized for that variable. The generic workflow takes its candidates from harmonize/candidates.py instead.

Decisions live in triage.csv next to this module (version-controlled; data/ is not), with the columns doi,
variable, keep and reason. `variable` is a variable key (e.g. Physical__Dry_bulk_density), or '*' for a
package-level decision (e.g. water, modeling, lab incubation) that applies to every variable; a variable-specific
row wins over '*'. A package that produced rows for the variable is kept regardless; candidates without rows and
without a decision are listed as "not reviewed"; packages marked keep but without rows as "not harmonized yet".

dois_filtering.xlsx (per variable) has the soil pH columns doi, keep and inclusion_reason, followed by n_rows and
matched_columns.

Attributes:
    TRIAGE: The decisions file, triage.csv.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .common import HITS_DIR, MATRIX, variable

TRIAGE = Path(__file__).with_name("triage.csv")


def candidates(var: str) -> list[str]:
    """Return the candidate DOIs of a variable from the hit matrix.

    Args:
        var: A variable key or short alias.

    Returns:
        The DOIs with a matching column, sorted; empty when the variable is not in the matrix.

    Examples:
        >>> candidates("Acidity__Soil_pH")[:2]  # doctest: +SKIP
        ['doi:10.15485/1454273', 'doi:10.15485/1577267']
    """
    m = pd.read_csv(MATRIX, index_col=0)
    col = variable(var).label
    return sorted(m.index[m[col] == 1]) if col in m.columns else []


def matched_columns(var: str) -> dict[str, str]:
    """Return the matching column names of each candidate package, from the earlier per-variable scans.

    Args:
        var: A variable key or short alias.

    Returns:
        {doi: matching column names joined with '; '} from data files (not dictionaries); empty when the scan
        output is missing.

    Examples:
        >>> matched_columns("Acidity__Soil_pH").get("doi:10.15485/1725884")  # doctest: +SKIP
        'pH'
    """
    short = variable(var).short  # scan outputs of find_soil_variable_candidates.py use the short keys
    f = HITS_DIR / f"ess-dive_all_soil{short}" / f"ess-dive_all_soil{short}_column_hits.csv"
    if not f.exists():
        return {}
    h = pd.read_csv(f, dtype=str, keep_default_na=False)
    h = h[h["is_dict_or_metadata_file"] != "True"]
    joined = h.groupby("doi")["column"].agg(lambda s: "; ".join(dict.fromkeys(s)))
    return {str(doi): str(cols) for doi, cols in joined.items()}


def decisions() -> pd.DataFrame:
    """Read triage.csv.

    Returns:
        The decisions (doi, variable, keep, reason, ...), as text; an empty table when the file is missing.
    """
    if not TRIAGE.exists():
        return pd.DataFrame(columns=["doi", "variable", "keep", "reason"])
    return pd.read_csv(TRIAGE, dtype=str, keep_default_na=False)


def decision(dec: pd.DataFrame, doi: str, var: str) -> tuple[str, str] | None:
    """Find the decision for a package and variable: the variable's own row, else the package's '*' row.

    Args:
        dec: The decisions (see `decisions`).
        doi: The package DOI.
        var: The variable key.

    Returns:
        (keep, reason) of the last matching row, or None when the package was not reviewed.

    Examples:
        >>> dec = pd.DataFrame({"doi": ["d1", "d1"], "variable": ["*", "TC"], "keep": ["1", "0"],
        ...                     "reason": ["soil", "plant tissue"]})
        >>> decision(dec, "d1", "TC"), decision(dec, "d1", "pH"), decision(dec, "d2", "pH")
        (('0', 'plant tissue'), ('1', 'soil'), None)
    """
    for v in (var, "*"):
        r = dec[(dec["doi"] == doi) & (dec["variable"] == v)]
        if len(r):
            return r["keep"].iloc[-1], r["reason"].iloc[-1]
    return None


def filtering_table(var: str, n_rows: dict[str, int]) -> pd.DataFrame:
    """Build the dois_filtering table of a variable.

    Args:
        var: A variable key or short alias.
        n_rows: {doi: harmonized row count} for this variable.

    Returns:
        One row per candidate or harmonized package: doi, keep, inclusion_reason, n_rows, matched_columns; kept
        packages first.
    """
    dec, cols = decisions(), matched_columns(var)
    rows = []
    for doi in sorted(set(candidates(var)) | {d for d, n in n_rows.items() if n}):
        n = n_rows.get(doi, 0)
        d = decision(dec, doi, var)
        if n:
            keep, reason = 1, (d[1] if d and d[0] == "1" and d[1] else "")
        elif d and d[0] == "1":
            keep, reason = 0, "marked keep in triage.csv, not harmonized yet"
        elif d:
            keep, reason = 0, d[1] or "excluded"
        else:
            keep, reason = 0, "not reviewed"
        rows.append(dict(doi=doi, keep=keep, inclusion_reason=reason, n_rows=n, matched_columns=cols.get(doi, "")))
    t = pd.DataFrame(rows, columns=["doi", "keep", "inclusion_reason", "n_rows", "matched_columns"])
    return t.sort_values(["keep", "doi"], ascending=[False, True]).reset_index(drop=True)
