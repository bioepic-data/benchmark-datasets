"""Fetch the public ESS-DIVE package list and the metadata of every package.

Writes, under `out_dir` (data/source by default):

- ess-dive_ids.txt: one package id per line.
- ess-dive_dois.txt: one DOI per line, in the same order as the ids.
- ess-dive_meta/ess-dive_meta_<id>.json: the full metadata of each package.

Requires the ESSDIVE_TOKEN environment variable (a token from https://ess-dive.lbl.gov/).

Usage (from the repo root, PYTHONPATH=src)::

    python -m essdive_harmonize.fetch [--out-dir DIR]

Attributes:
    BASE_URL: The ESS-DIVE packages API.
    PAGE_SIZE: Packages per page of the package list.
    MAX_WORKERS: Parallel metadata requests.
    DEFAULT_OUT_DIR: data/source.
"""

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Final

import requests

BASE_URL: Final = "https://api.ess-dive.lbl.gov/packages"
PAGE_SIZE: Final = 100
MAX_WORKERS: Final = 10
DEFAULT_OUT_DIR: Final[Path] = Path(__file__).resolve().parents[3] / "data" / "source"


def _headers() -> dict[str, str]:
    """Return the authorization header from ESSDIVE_TOKEN; exit with a message when the variable is not set."""
    token = os.environ.get("ESSDIVE_TOKEN")
    if not token:
        raise SystemExit(
            "ESSDIVE_TOKEN is not set; export it before running.")
    return {"Authorization": f"bearer {token}"}


def fetch_package_list(session: requests.Session) -> list[dict[str, Any]]:
    """List every public package, following the result pages up to the API's total.

    Args:
        session: A requests session carrying the authorization header.

    Returns:
        The package headers (id, dataset name / DOI ...), in API order.

    Raises:
        requests.HTTPError: When a page request fails.

    Examples:
        >>> s = requests.Session(); s.headers.update(_headers())  # doctest: +SKIP
        >>> len(fetch_package_list(s))  # doctest: +SKIP
        1588
    """
    packages: list[dict[str, Any]] = []
    row_start = 1
    total = None
    while total is None or row_start <= total:
        resp = session.get(
            BASE_URL,
            params={"isPublic": "true", "pageSize": str(PAGE_SIZE),
                    "rowStart": str(row_start)},
            timeout=120,
        )
        resp.raise_for_status()
        page = resp.json()
        total = page["total"]
        result = page.get("result") or []
        if not result:
            break
        packages.extend(result)
        row_start += PAGE_SIZE
    if len(packages) != total:
        print(f"warning: API reported {total} packages "
              f"but {len(packages)} were returned")
    return packages


def fetch_metadata(session: requests.Session, package_id: str) -> dict[str, Any]:
    """Fetch the full metadata of one package.

    Args:
        session: A requests session carrying the authorization header.
        package_id: An ESS-DIVE package id (ess-dive-<hash>-<timestamp>).

    Returns:
        The package metadata (id, dataset with name, description, distribution, spatialCoverage ...).

    Raises:
        requests.HTTPError: When the request fails.
    """
    resp = session.get(f"{BASE_URL}/{package_id}",
                       params={"isPublic": "true"}, timeout=120)
    resp.raise_for_status()
    return resp.json()


def update_source(out_dir: Path | str = DEFAULT_OUT_DIR) -> tuple[list[str], list[str], list[str]]:
    """Refresh the id and DOI lists and the per-package metadata files.

    Args:
        out_dir: Output folder (see the module docstring).

    Returns:
        The package ids, the DOIs (same order) and the ids whose metadata could not be fetched.

    Examples:
        >>> ids, dois, failed = update_source("data/source")  # doctest: +SKIP
    """
    out_dir = Path(out_dir)
    meta_dir = out_dir / "ess-dive_meta"
    meta_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update(_headers())

    packages = fetch_package_list(session)
    ids = [p["id"] for p in packages]
    dois = [p["dataset"]["@id"] for p in packages]
    (out_dir / "ess-dive_ids.txt").write_text("".join(f"{i}\n" for i in ids))
    (out_dir / "ess-dive_dois.txt").write_text("".join(f"{d}\n" for d in dois))
    print(f"wrote {len(ids)} ids and dois to {out_dir}")

    failed = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_metadata, session, i): i for i in ids}
        for n, future in enumerate(as_completed(futures), 1):
            package_id = futures[future]
            try:
                data = future.result()
            except requests.RequestException as e:
                failed.append(package_id)
                print(f"failed {package_id}: {e}")
                continue
            with open(meta_dir / f"ess-dive_meta_{package_id}.json", "w") as f:
                json.dump(data, f, indent=2)
            if n % 100 == 0:
                print(f"metadata {n}/{len(ids)}")
    print(f"wrote metadata for {len(ids) - len(failed)} packages; "
          f"{len(failed)} failed")
    return ids, dois, failed


def main() -> None:
    """Parse the command line and refresh the ESS-DIVE source files."""
    parser = argparse.ArgumentParser(
        description="Refresh ESS-DIVE ids, DOIs and metadata.")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR, type=Path)
    args = parser.parse_args()
    update_source(args.out_dir)


if __name__ == "__main__":
    main()
