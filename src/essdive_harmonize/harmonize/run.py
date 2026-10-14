"""Harmonize soil variables from scratch, one variable at a time.

Runs on the packages selected in data/intermediate/package_selection (generic workflow; no package-specific code).

Variables: select = 1 in data/soil_variable_list_input.csv, porewater metals and fluxes excluded (see --list).

\b
Outputs (data/processed/harmonization/, or --out-dir):
    variables.csv                    one row per variable: candidates, packages written, rows, in review
    review_queue.csv                 every package / variable not written, with the reasons
    <key>/<doi_slug>/<doi_slug>_soil_<key>.csv / .xlsx
    <key>/harmonized.csv / .xlsx     all packages of the variable
    <key>/dois_filtering.xlsx        every package with numeric column evidence: keep, inclusion_reason, n_rows,
                                     matched_columns, location_source
    <key>/review_queue.csv           this variable's packages not written
    <key>/qc.csv                     rows outside the plausible range or with invalid coordinates
    <key>/handwritten_check.csv      with --compare: agreement with the hand-written pH / carbon packages

\b
Usage (from the repo root, PYTHONPATH=src):
    python -m essdive_harmonize.harmonize.run --list
    python -m essdive_harmonize.harmonize.run --var Acidity__Soil_pH --write --compare
    python -m essdive_harmonize.harmonize.run --category Carbon --write --compare
    python -m essdive_harmonize.harmonize.run --all --write
    python -m essdive_harmonize.harmonize.run --var Acidity__Soil_pH --doi doi:10.15485/1725884   # dry run
"""  # noqa: D301  (\b keeps click from rewrapping the blocks)

from __future__ import annotations

import shutil
import warnings
from pathlib import Path
from typing import Any, Final

import click
import pandas as pd

warnings.filterwarnings("ignore")

from ..common import base_columns, write_package, write_table_xlsx  # noqa: E402
from .auto import Result, harmonize  # noqa: E402
from .candidates import candidate_table, candidates  # noqa: E402
from .config import OUT_ROOT  # noqa: E402
from .qc import check  # noqa: E402
from .variables import CATEGORIES, VARIABLES, by_category  # noqa: E402

REVIEW_COLUMNS: Final[list[str]] = ["doi", "key", "variable", "reason"]


def _filtering(key: str, results: dict[str, Result]) -> pd.DataFrame:
    """Build dois_filtering.xlsx: one row per package with numeric column evidence for the variable.

    Returns:
        doi, keep, inclusion_reason, n_rows, matched_columns, location_source and unit_assumed; kept packages first.
    """
    rows: list[dict[str, Any]] = []
    for r in candidate_table(key).itertuples():
        res = results.get(str(r.doi))
        if r.status != "candidate":
            rows.append(dict(doi=r.doi, keep=0, inclusion_reason=r.status, n_rows=0, matched_columns=r.detail,
                             location_source="", unit_assumed=""))
            continue
        written = res is not None and res.status == "written" and res.table is not None
        rows.append(dict(doi=r.doi, keep=int(written),
                         inclusion_reason="harmonized" if written else "; ".join(res.reasons) if res else "not run",
                         n_rows=len(res.table) if res is not None and res.table is not None and written else 0,
                         matched_columns="; ".join(res.columns) if res and res.columns else r.detail,
                         location_source=res.location if res is not None and written else "",
                         unit_assumed=("yes" if res and res.assumed_unit else "")))
    cols = ["doi", "keep", "inclusion_reason", "n_rows", "matched_columns", "location_source", "unit_assumed"]
    return pd.DataFrame(rows, columns=cols).sort_values(["keep", "doi"], ascending=[False, True])


def run_variable(key: str, root: Path, write: bool, compare: bool, dois: tuple[str, ...]) -> dict[str, Any]:
    """Harmonize one variable for all its candidates and write its outputs.

    Args:
        key: The variable key.
        root: The output root.
        write: Write the outputs (a full run replaces the variable's folder).
        compare: Compare with the hand-written packages.
        dois: Limit to these packages (no master files are written).

    Returns:
        The variable's summary row of variables.csv.
    """
    v = VARIABLES[key]
    todo = [d for d in candidates(key) if not dois or d in dois]
    results = {d: harmonize(key, d) for d in todo}
    written = {d: r for d, r in results.items() if r.status == "written"}
    tables = [r.table for r in written.values() if r.table is not None]
    summary: dict[str, Any] = dict(key=key, category=v.category, variable=v.name, unit=v.unit, candidates=len(todo),
                   packages_written=len(written), rows=sum(map(len, tables)), in_review=len(todo) - len(written))
    review = pd.DataFrame([dict(doi=d, key=key, variable=v.name, reason="; ".join(r.reasons))
                           for d, r in results.items() if r.status != "written"], columns=REVIEW_COLUMNS)
    if write:
        out = root / key
        if out.exists() and not dois:  # a full run replaces the variable's folder (no stale packages)
            shutil.rmtree(out)
        out.mkdir(parents=True, exist_ok=True)
        for t in tables:
            write_package(t, key, root)
        if not dois:
            if tables:
                cols = base_columns(key) + ["notes"]
                allt = pd.concat([t.reindex(columns=cols) for t in tables], ignore_index=True)
                allt.to_csv(out / "harmonized.csv", index=False)
                write_table_xlsx(allt, out / "harmonized.xlsx", key, sheet="Sheet1")
                qc = pd.concat([check(key, t) for t in tables], ignore_index=True)
                qc.to_csv(out / "qc.csv", index=False)
                summary["qc_flags"] = len(qc)
            _filtering(key, results).to_excel(out / "dois_filtering.xlsx", index=False)
            review.to_csv(out / "review_queue.csv", index=False)
    if compare:
        from .compare import compare as cmp
        c = cmp(key, results)
        if len(c):
            ok = ((c.auto_status == "written") & (c.values_found >= 0.95) & (c.centre_km <= 1)
                  & c.auto_rows.between(0.8 * c.handwritten_rows, 1.2 * c.handwritten_rows))
            summary["handwritten"] = len(c)
            summary["handwritten_close"] = int(ok.sum())
            if write and not dois:
                c.to_csv(root / key / "handwritten_check.csv", index=False)
    return summary


def write_index(root: Path, summaries: list[dict[str, Any]]) -> None:
    """Refresh variables.csv (keeping the rows of variables not run now) and the combined review_queue.csv.

    Args:
        root: The output root.
        summaries: Summary rows of the variables just run.
    """
    f = root / "variables.csv"
    old = pd.read_csv(f) if f.exists() else pd.DataFrame()
    new = pd.DataFrame(summaries)
    if len(old):
        new = pd.concat([old[~old.key.isin(new.key)], new], ignore_index=True)
    order = {k: i for i, k in enumerate(VARIABLES)}
    new.sort_values("key", key=lambda s: s.map(order)).to_csv(f, index=False)
    queues = [pd.read_csv(p, keep_default_na=False) for p in sorted(root.glob("*/review_queue.csv"))]
    pd.concat(queues or [pd.DataFrame(columns=REVIEW_COLUMNS)], ignore_index=True).to_csv(
        root / "review_queue.csv", index=False)


@click.command(help=__doc__)
@click.option("--var", "keys", multiple=True, type=click.Choice(list(VARIABLES)), help="Variable key (repeatable).")
@click.option("--category", "categories", multiple=True, type=click.Choice(CATEGORIES), help="Every variable of a category.")
@click.option("--all", "all_vars", is_flag=True, help="Every variable.")
@click.option("--doi", "dois", multiple=True, help="Limit to these packages (dry checks; no master files).")
@click.option("--write", is_flag=True, help="Write the outputs.")
@click.option("--compare", is_flag=True, help="Compare with the hand-written pH / carbon packages (run in memory).")
@click.option("--out-dir", type=click.Path(file_okay=False, path_type=Path), default=OUT_ROOT, show_default=True)
@click.option("--list", "show_list", is_flag=True, help="List the variables with their candidate counts.")
def main(keys: tuple[str, ...], categories: tuple[str, ...], all_vars: bool, dois: tuple[str, ...], write: bool,
         compare: bool, out_dir: Path, show_list: bool) -> None:
    """Run the harmonization (the command line; see the module docstring)."""
    if show_list:
        rows = [dict(key=k, category=v.category, unit=v.unit, candidates=len(candidates(k))) for k, v in VARIABLES.items()]
        click.echo(pd.DataFrame(rows).to_string(index=False))
        return
    wanted = list(VARIABLES) if all_vars else list(dict.fromkeys(list(keys) + [k for c in categories for k in by_category(c)]))
    if not wanted:
        raise click.UsageError("give --var, --category or --all")
    summaries = []
    for key in wanted:
        s = run_variable(key, out_dir, write, compare, dois)
        summaries.append(s)
        extra = f"  hand-written close {s['handwritten_close']}/{s['handwritten']}" if "handwritten" in s else ""
        click.echo(f"{key:55s} candidates {s['candidates']:3d}  written {s['packages_written']:3d}  "
                   f"rows {s['rows']:6d}  review {s['in_review']:3d}{extra}")
    if write and not dois:
        write_index(out_dir, summaries)
        click.echo(f"outputs in {out_dir}")


if __name__ == "__main__":
    main()
