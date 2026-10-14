"""Harmonize soil variables with the hand-written package functions (select = 1 in data/soil_variable_list.csv).

Variable keys are the '<category>:<variable>' labels of the list with '/', '(' and ')' dropped, ':' -> '__'
and spaces -> '_' (e.g. Physical__Dry_bulk_density); see --list.

Results go to data/processed/harmonization/<variable key>/<doi_slug>/<doi_slug>_soil_<key>.{csv,xlsx};
--master adds <key>/harmonized.xlsx and <key>/dois_filtering.xlsx, and refreshes variables.csv.

\b
Usage (from the repo root, with src on PYTHONPATH, e.g. export PYTHONPATH=src):
    python -m essdive_harmonize.run --list                              # variables: key, category, name, unit
    python -m essdive_harmonize.run --var Nitrogen__Total_nitrogen --verify    # rebuild, compare with written files
    python -m essdive_harmonize.run --var Nitrogen__Total_nitrogen --var Physical__Dry_bulk_density --write --master
    python -m essdive_harmonize.run --category Physical --write --master
    python -m essdive_harmonize.run --doi doi:10.15485/1725884 --write  # every variable of one package
    python -m essdive_harmonize.run --var Acidity__Soil_pH --compare         # compare with harmonize_ph output
    python -m essdive_harmonize.run --category Carbon --compare --compare-dir /tmp/carbon
    python -m essdive_harmonize.run --var Nitrogen__Total_nitrogen --out-dir /tmp/h    # write under /tmp/h/<key>/
"""  # noqa: D301 - '\b' is click's no-rewrap marker

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import click
import pandas as pd

from .common import (OUT_ROOT, base_columns, legacy_csv, package_csv, processed_dir, verify,
                     write_package, write_table_xlsx)
from .registry import PACKAGES
from .triage import candidates, filtering_table
from .variables import CATEGORIES, VARIABLES, by_category


def list_variables() -> None:
    """Print the variables: key, category, name, unit, number of candidates and of harmonized packages."""
    root_counts = {}
    for k in VARIABLES:
        d = processed_dir(k)
        root_counts[k] = sum(1 for p in d.iterdir() if p.is_dir()) if d.exists() else 0
    rows = [dict(key=k, category=v.category, name=v.name, unit=v.unit, candidates=len(candidates(k)),
                 harmonized=root_counts[k]) for k, v in VARIABLES.items()]
    click.echo(pd.DataFrame(rows).to_string(index=False))


def write_summary(root: Path) -> Path:
    """Write variables.csv: one row per variable with the package and row counts of what is on disk.

    Args:
        root: The output root.

    Returns:
        The path of variables.csv.
    """
    rows = []
    for k, v in VARIABLES.items():
        files = sorted(processed_dir(k, root).glob("*/*_soil_*.csv"))
        n = sum(len(pd.read_csv(f, dtype=str, keep_default_na=False)) for f in files)
        rows.append(dict(key=k, category=v.category, variable=v.name, unit=v.unit,
                         value_column=v.value_column, method_column=v.method_column,
                         extra_columns="; ".join(v.extra), candidates=len(candidates(k)),
                         packages=len(files), rows=n))
    out = Path(root) / "variables.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    return out


@click.command(help=__doc__)
@click.option("--var", "variables", multiple=True, type=click.Choice(list(VARIABLES)),
              help="Variable key (repeatable); see --list.")
@click.option("--category", "categories", multiple=True, type=click.Choice(CATEGORIES),
              help="All variables of a category (repeatable).")
@click.option("--doi", "dois", multiple=True, help="Limit to this DOI (repeatable).")
@click.option("--group", type=click.IntRange(1, 4), help="Limit to one location group (1-4).")
@click.option("--verify", "do_verify", is_flag=True, help="Compare with the files already written under the output root.")
@click.option("--compare", is_flag=True, help="Compare with the earlier harmonize_ph / harmonize_carbon outputs (read-only).")
@click.option("--compare-dir", type=click.Path(file_okay=False, exists=True, path_type=Path),
              help="With --compare: folder holding harmonized_soil<V>_data/ instead of data/processed.")
@click.option("--write", is_flag=True, help="Write per-package files under data/processed/harmonization/.")
@click.option("--out-dir", type=click.Path(file_okay=False, path_type=Path),
              help="Write per-package files under this folder instead.")
@click.option("--master", is_flag=True,
              help="Also write <key>/harmonized.xlsx and <key>/dois_filtering.xlsx, and refresh variables.csv.")
@click.option("--list", "show_list", is_flag=True, help="List the variables and exit.")
def main(variables: tuple[str, ...], categories: tuple[str, ...], dois: tuple[str, ...], group: int | None,
         do_verify: bool, compare: bool, compare_dir: Path | None, write: bool, out_dir: Path | None, master: bool,
         show_list: bool) -> None:
    """Run the package functions for the requested variables (the command line; see the module docstring)."""
    if show_list:
        list_variables()
        return
    wanted = list(dict.fromkeys(list(variables) + [k for c in categories for k in by_category(c)]))
    root = out_dir or OUT_ROOT
    todo = [p for p in PACKAGES if (not dois or p.doi in dois) and (not group or p.group == group)
            and p.wants(wanted)]
    frames, failed = defaultdict(list), 0
    for p in todo:
        try:
            tables = p.tables()
        except Exception as e:  # keep going so one broken package does not hide the others
            click.echo(f"[ERROR] group {p.group} {p.doi}: {type(e).__name__}: {e}")
            failed += 1
            continue
        for var, df in tables.items():
            if wanted and var not in wanted:
                continue
            frames[var].append(df)
            status = f"{len(df)} rows"
            for flag, ref, legacy in ((do_verify, package_csv(p.doi, var, root), False),
                                      (compare, legacy_csv(p.doi, var, compare_dir), True)):
                if not flag:
                    continue
                if ref is None or not ref.exists():
                    status += f"  (no reference {ref})" if ref else "  (no earlier output for this variable)"
                    continue
                issues = verify(df, ref, var, legacy=legacy)
                status += "  OK" if not issues else "  DIFF\n      " + "\n      ".join(issues)
                failed += bool(issues)
            if write or out_dir:
                write_package(df, var, root)
            click.echo(f"group {p.group}  {var:10s} {p.doi:<34} {status}")

    if master:
        for var in (wanted or sorted(frames)):
            out = processed_dir(var, root)
            out.mkdir(parents=True, exist_ok=True)
            fs = frames.get(var, [])
            if fs:
                cols = base_columns(var) + ["notes"]
                write_table_xlsx(pd.concat([f[cols] for f in fs], ignore_index=True), out / "harmonized.xlsx", var,
                                 sheet="Sheet1")
            n_rows = {f["doi"].iloc[0]: len(f) for f in fs}
            filtering_table(var, n_rows).to_excel(out / "dois_filtering.xlsx", index=False)
            click.echo(f"wrote {out}/harmonized.xlsx, dois_filtering.xlsx")
        click.echo(f"wrote {write_summary(root)}")
    counts = ", ".join(f"{v} {len(fs)}" for v, fs in sorted(frames.items()))
    click.echo(f"{len(todo)} packages ({counts or 'no tables'}), {failed} with errors or differences")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
