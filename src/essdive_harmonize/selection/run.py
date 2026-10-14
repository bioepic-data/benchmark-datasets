"""Select ESS-DIVE packages for the variables of data/soil_variable_list_input.csv (select column ignored).

Evidence comes from the column headers of the downloaded files (data/source/package_data/, including extracted
archives) and from the package metadata (keywords, description, other metadata); see matching.py. Every package
is searched, then the counts are split by whether the package has soil-related data (soil.py).

Usage (from the repo root, PYTHONPATH=src):
    python -m essdive_harmonize.selection.run              # reuses the cached column headers
    python -m essdive_harmonize.selection.run --rescan     # re-reads every downloaded file first

Outputs (data/intermediate/package_selection/):
    column_headers.csv      cache: one row per column (doi, file, sheet, column, is_dictionary, n_rows, n_numeric)
    packages.csv            one row per package: soil_related (+ where "soil" was found), files scanned, variables found
    evidence.csv            one row per package x variable x source, with strength and matched columns / terms;
                            text matches also give context (the sentences) and exclusion_terms (plant, litter,
                            root, water terms in them; recorded only)
    variable_summary.csv    per variable: packages by evidence kind (<kind>_all / _soil / _nonsoil / _soil_context)
    matrix_any.csv          packages x '<category>:<variable>', 1 if any evidence (soil_related, then soil_context: the context terms found)
    matrix_sources.csv      same, with the sources found: C columns, d dictionary, K keywords, D description,
                            O other metadata
    scan_log.csv            files that could not be read or were skipped
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from . import headers as hdr
from .config import HEADERS_CACHE, OUT_DIR, VARIABLE_LIST
from .matching import column_hits, evidence
from .metadata import load_packages
from .report import write_all
from .soil import classify
from .variable_list import load_variables


def load_headers(packages: pd.DataFrame, out_dir: Path, rescan: bool,
                 workers: int | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the column-header cache, scanning every downloaded file when it is missing or rescan is set.

    Args:
        packages: The package table (its DOIs name the files' packages).
        out_dir: The output folder holding the cache.
        rescan: Re-read every file.
        workers: Worker processes for the scan.

    Returns:
        The header table and the scan log.
    """
    cache, log_file = out_dir / HEADERS_CACHE, out_dir / "scan_log.csv"
    if cache.exists() and not rescan:
        h = pd.read_csv(cache, dtype={"doi": str, "file": str, "sheet": str, "column": str}, keep_default_na=False,
                        na_values={"n_rows": [""], "n_numeric": [""]})
        h["is_dictionary"] = h.is_dictionary.astype(str).eq("True")
        log = pd.read_csv(log_file, keep_default_na=False) if log_file.exists() else pd.DataFrame()
        return h, log
    out_dir.mkdir(parents=True, exist_ok=True)
    h, log = hdr.scan_headers(packages.doi, workers=workers)
    h.to_csv(cache, index=False)
    return h, log


def main() -> None:
    """Run the package selection (the command line; see the module docstring)."""
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--variables", type=Path, default=VARIABLE_LIST, help="tab-separated variable list")
    p.add_argument("--out-dir", type=Path, default=OUT_DIR)
    p.add_argument("--rescan", action="store_true", help="re-read the column headers of every downloaded file")
    p.add_argument("--workers", type=int, help="worker processes (default: all cores)")
    a = p.parse_args()

    variables = load_variables(a.variables)
    packages = load_packages()
    headers, log = load_headers(packages, a.out_dir, a.rescan, a.workers)
    unmatched = headers[headers.doi == ""].file.nunique()
    packages = classify(packages, headers)
    print(f"{len(variables)} variables; {len(packages)} packages ({int(packages.soil_related.sum())} soil-related); "
          f"{headers.file.nunique()} files, {len(headers)} columns scanned"
          + (f"; {unmatched} files without a DOI" if unmatched else ""))

    hits = column_hits(variables, headers, a.workers)
    ev = evidence(variables, packages, headers, hits)
    files = write_all(a.out_dir, variables, packages, headers, log, ev)

    s = files["variable_summary.csv"]
    print(f"packages with evidence for at least one variable: {ev.doi.nunique()} "
          f"({ev[ev.doi.isin(packages.doi[packages.soil_related])].doi.nunique()} soil-related)")
    cols = ["category", "variable", "any_all", "any_soil", "any_nonsoil", "columns_with_data_all",
            "columns_with_data_soil"]
    print(s.sort_values("any_all", ascending=False)[cols].head(20).to_string(index=False))
    print(f"outputs in {a.out_dir}")


if __name__ == "__main__":
    main()
