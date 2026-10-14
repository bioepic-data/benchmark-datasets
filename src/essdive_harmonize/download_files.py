"""Download ESS-DIVE package files into data/source/package_data/ as <doi_slug>_<file name>.

Selection, for every file listed in data/source/ess-dive_meta/:

- Size: nothing larger than MAX_MB (50 MB); files between NAME_FILTER_MB and MAX_MB (10-50 MB) only when the file
  name matches NAME_PATTERN ("soil" in any case: soils, Soil_C, topsoil ...). Both apply to archives as well.
- csv, txt, tab, xls, xlsx, kml, kmz, pdf, png, jpg, docx: downloaded.
- zip, tar.gz: downloaded and checked. An archive holding a csv, txt, tab, xls or xlsx file is extracted to
  package_data/extracted/<doi_slug>_<archive name>/ and the archive file removed; any other archive is deleted.
  Extraction drops __MACOSX entries, refuses links and paths outside the folder, and skips archives that unpack to
  more than 2 GB. (The ESS-DIVE server reads a ranged request from the start of the file, so a zip's file list
  cannot be read remotely more cheaply than downloading it.)
- Anything else is not downloaded.

Writes next to package_data/:

- package_data_plan.tsv: every listed file with its decision (--replan rebuilds it from the metadata).
- package_data_log.tsv: one line per finished download attempt, so a rerun resumes where it stopped.
- package_data_downloaded.tsv, package_data_not_downloaded.tsv: doi, file name, size and, for files not
  downloaded, the reason.

Usage (from the repo root, PYTHONPATH=src)::

    python -m essdive_harmonize.download_files                        # plan and records only
    python -m essdive_harmonize.download_files --direct --archives    # download everything selected
    python -m essdive_harmonize.download_files --replan --max-mb 100 --name-filter-mb 20   # other size cutoffs
    python -m essdive_harmonize.download_files --doi-file dois.txt --max-mb 700 --name-filter-mb 700 --direct --archives
                                                                      # only some packages, with other cutoffs

Attributes:
    SOURCE: data/source.
    META_DIR: The per-package metadata files.
    OUT_DIR: The downloaded files (package_data).
    EXTRACT_DIR: Folders of the extracted archives.
    PLAN: The download plan.
    LOG: One line per finished download attempt.
    DOWNLOADED: Record of the downloaded files.
    NOT_DOWNLOADED: Record of the files not downloaded, with the reason.
    DIRECT: Extensions downloaded as they are.
    ARCHIVES: Archive extensions that are downloaded, checked and extracted.
    TABULAR: Extensions that make an archive worth extracting.
    MAX_MB: Size cap in MB.
    NAME_FILTER_MB: Above this size (up to MAX_MB) a file needs NAME_PATTERN in its name.
    NAME_PATTERN: Name pattern of the larger files that are still downloaded.
    MEDIA_PATTERN: Archives named like this (photos, videos, animations) are never downloaded.
    MB: Bytes per MB.
    MAX_UNPACKED_BYTES: Archives that unpack to more are not extracted.
    MAX_WORKERS: Parallel downloads.
"""

import argparse
import json
import os
import re
import shutil
import tarfile
import time
import zipfile
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Final

import pandas as pd
import requests

SOURCE: Final[Path] = Path(__file__).resolve().parents[2] / "data" / "source"
META_DIR: Final[Path] = SOURCE / "ess-dive_meta"
OUT_DIR: Final[Path] = SOURCE / "package_data"
EXTRACT_DIR: Final[Path] = OUT_DIR / "extracted"
PLAN: Final[Path] = SOURCE / "package_data_plan.tsv"
LOG: Final[Path] = SOURCE / "package_data_log.tsv"
DOWNLOADED: Final[Path] = SOURCE / "package_data_downloaded.tsv"
NOT_DOWNLOADED: Final[Path] = SOURCE / "package_data_not_downloaded.tsv"

DIRECT: Final[set[str]] = {"csv", "txt", "tab", "xls", "xlsx", "kml", "kmz", "pdf", "png", "jpg", "docx"}
ARCHIVES: Final[set[str]] = {"zip", "tar.gz"}
TABULAR: Final[set[str]] = {"csv", "txt", "tab", "xls", "xlsx"}
MAX_MB: Final = 50            # files larger than this are not downloaded
NAME_FILTER_MB: Final = 10    # files larger than this (up to MAX_MB) only when the name matches NAME_PATTERN
NAME_PATTERN: Final[re.Pattern[str]] = re.compile(r"soil", re.IGNORECASE)
MEDIA_PATTERN: Final[re.Pattern[str]] = re.compile(r"photo|video|movie|animation", re.IGNORECASE)
MB: Final = 1024 ** 2
MAX_UNPACKED_BYTES: Final = 2 * 1024 ** 3
MAX_WORKERS: Final = 8

_use_token = True


def _headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Return request headers: the ESSDIVE_TOKEN authorization (while it is accepted) plus `extra`."""
    token = os.environ.get("ESSDIVE_TOKEN")
    h = {"Authorization": f"bearer {token}"} if token and _use_token else {}
    return {**h, **(extra or {})}


def _get(url: str, stream: bool = False, headers: dict[str, str] | None = None, timeout: int = 300,
         retries: int = 4) -> requests.Response:
    """GET a URL with retries; an expired or rejected token (401) is dropped and the request repeated without it.

    Args:
        url: The URL.
        stream: Stream the response body.
        headers: Extra request headers.
        timeout: Seconds to wait for the server.
        retries: Retries after a connection error, a timeout, 429 or a 5xx status (with exponential backoff).

    Returns:
        The response.

    Raises:
        requests.RequestException: When the last attempt fails.
    """
    global _use_token
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=_headers(headers), stream=stream, timeout=timeout)
            if r.status_code == 401 and _use_token:
                _use_token = False
                print("warning: ESSDIVE_TOKEN rejected (401); continuing without it")
                r = requests.get(url, headers=_headers(headers), stream=stream, timeout=timeout)
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code} for {url}")
            r.raise_for_status()
            return r
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError):
            if attempt == retries:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable: the last attempt returns or raises")


def ext_of(name: str) -> str:
    """Return the lower-case extension of a file name ('tar.gz' for gzipped tarballs).

    Examples:
        >>> ext_of("Soil_Data.CSV"), ext_of("data.tar.gz"), ext_of("README")
        ('csv', 'tar.gz', '')
    """
    n = name.lower()
    if n.endswith(".tar.gz"):
        return "tar.gz"
    return n.rsplit(".", 1)[-1] if "." in n else ""


def slug_of(doi: str) -> str:
    """Turn a DOI into the slug used in local file names.

    Examples:
        >>> slug_of("doi:10.15485/1725884")
        '10.15485_1725884'
    """
    return doi.replace("doi:", "").replace("/", "_")


def _junk(name: str) -> bool:
    """Tell whether an archive member is macOS metadata (__MACOSX folders, ._ files).

    Examples:
        >>> _junk("__MACOSX/data/._soil.csv"), _junk("data/soil.csv")
        (True, False)
    """
    return "__MACOSX" in name or name.rstrip("/").rsplit("/", 1)[-1].startswith("._")


def _tabular_members(names: Iterable[str]) -> list[str]:
    """Return the csv / txt / tab / xls / xlsx members of an archive, without macOS metadata.

    Examples:
        >>> _tabular_members(["a/soil.csv", "a/fig.png", "__MACOSX/a/._soil.csv", "b.xlsx"])
        ['a/soil.csv', 'b.xlsx']
    """
    return [n for n in names if ext_of(n) in TABULAR and not _junk(n)]


def archive_stem(local_name: str) -> str:
    """Return an archive's local name without .zip / .tar.gz (the name of its extraction folder).

    Examples:
        >>> archive_stem("10.15485_1_Data.tar.gz"), archive_stem("10.15485_1_Data.ZIP")
        ('10.15485_1_Data', '10.15485_1_Data')
    """
    for e in (".tar.gz", ".zip"):
        if local_name.lower().endswith(e):
            return local_name[:-len(e)]
    return local_name


def build_plan(max_mb: float = MAX_MB, name_filter_mb: float = NAME_FILTER_MB,
               dois: set[str] | None = None, write: bool = True) -> pd.DataFrame:
    """Decide, for every file listed in the metadata, whether it is downloaded, and write PLAN.

    Args:
        max_mb: Size cap in MB.
        name_filter_mb: Above this size (up to `max_mb`) a file needs NAME_PATTERN in its name.
        dois: Only these packages (lower-case DOIs compared); all when None.
        write: Write PLAN.

    Returns:
        One row per listed file: doi, file_name, ext, bytes, url, local_name, action ('direct', 'archive' or
        'skip') and reason; one 'skip' row per package that lists no files.

    Examples:
        >>> plan = build_plan()  # doctest: +SKIP
        >>> plan.action.value_counts().to_dict()  # doctest: +SKIP
        {'skip': 12871, 'direct': 7152, 'archive': 844}
    """
    rows = []
    for f in sorted(META_DIR.glob("ess-dive_meta_*.json")):
        d = json.loads(f.read_text())
        doi = d["dataset"]["@id"]
        if dois is not None and doi.lower() not in dois:
            continue
        dist = d["dataset"].get("distribution") or []
        if not dist:
            rows.append(dict(doi=doi, file_name="", ext="", bytes=0, url="", local_name="",
                             action="skip", reason="package lists no files"))
        for x in dist:
            name = x.get("name", "").strip()
            rows.append(dict(doi=doi, file_name=name, ext=ext_of(name),
                             bytes=round(float(x.get("contentSize") or 0) * 1024),
                             url=x.get("contentUrl") or "",
                             local_name=f"{slug_of(doi)}_{name.replace('/', '_')}", action="", reason=""))
    plan = pd.DataFrame(rows)
    named = plan.file_name != ""  # rows of a listed file (not "package lists no files")
    plan.loc[named & ~plan.ext.isin(DIRECT | ARCHIVES), ["action", "reason"]] = ["skip", "file type not selected"]
    sel = named & plan.ext.isin(DIRECT | ARCHIVES)
    media = sel & plan.ext.isin(ARCHIVES) & plan.file_name.str.contains(MEDIA_PATTERN)
    plan.loc[media, ["action", "reason"]] = ["skip", "photos / videos archive"]
    plan.loc[sel & (plan.action == "") & (plan.bytes > max_mb * MB), ["action", "reason"]] = [
        "skip", f"larger than {max_mb:g} MB"]
    mid = sel & (plan.action == "") & (plan.bytes > name_filter_mb * MB)
    no_soil = mid & ~plan.file_name.str.contains(NAME_PATTERN)
    plan.loc[no_soil, ["action", "reason"]] = [
        "skip", f"{name_filter_mb:g}-{max_mb:g} MB and no '{NAME_PATTERN.pattern}' in the file name"]
    plan.loc[named & (plan.action == "") & (plan.url == ""), ["action", "reason"]] = ["skip", "no download URL in metadata"]
    dup = named & (plan.action == "") & plan.duplicated(["doi", "url"])
    plan.loc[dup, ["action", "reason"]] = ["skip", "same file listed twice in the package"]
    plan.loc[named & (plan.action == "") & plan.ext.isin(DIRECT), "action"] = "direct"
    plan.loc[named & (plan.action == "") & plan.ext.isin(ARCHIVES), "action"] = "archive"

    # distinct local names for different files that share a name within a package
    todo = plan.action.isin(["direct", "archive"])
    n = plan[todo].groupby("local_name").cumcount()
    for i in n[n > 0].index:
        stem, dot, ext = str(plan.at[i, "local_name"]).rpartition(".")
        plan.at[i, "local_name"] = f"{stem}_dup{n[i]}{dot}{ext}" if dot else f"{ext}_dup{n[i]}"

    if write:
        plan.to_csv(PLAN, sep="\t", index=False)
    return plan


def _done() -> dict[str, tuple[str, str]]:
    """Read LOG: {local name: (status, detail)} of the finished download attempts."""
    if not LOG.exists():
        return {}
    log = pd.read_csv(LOG, sep="\t", dtype=str, keep_default_na=False, names=["url", "local_name", "status", "detail"])
    return {str(r.local_name): (str(r.status), str(r.detail)) for r in log.itertuples()}


def _log(row: Any, status: str, detail: str = "") -> None:
    """Append one finished attempt (url, local name, status, detail) to LOG."""
    with open(LOG, "a") as fh:
        fh.write(f"{row.url}\t{row.local_name}\t{status}\t{detail.replace(chr(9), ' ').replace(chr(10), ' ')}\n")


def _extract(path: Path, ext: str, dest: Path) -> tuple[int, str]:
    """Extract an archive that holds csv / txt / tab / xls / xlsx files.

    Args:
        path: The downloaded archive.
        ext: 'zip' or 'tar.gz'.
        dest: The extraction folder.

    Returns:
        The number of files extracted and '' or, when nothing was extracted, the reason.

    Examples:
        >>> import tempfile, zipfile
        >>> with tempfile.TemporaryDirectory() as d:
        ...     with zipfile.ZipFile(f"{d}/a.zip", "w") as z:
        ...         z.writestr("data/soil.csv", "pH,7.1"); z.writestr("__MACOSX/data/._soil.csv", "")
        ...     _extract(Path(f"{d}/a.zip"), "zip", Path(f"{d}/out")), (Path(d) / "out/data/soil.csv").exists()
        ((1, ''), True)
    """
    if ext == "zip":
        with zipfile.ZipFile(path) as z:
            entries = [i for i in z.infolist() if not i.is_dir() and not _junk(i.filename)]
            if not _tabular_members([i.filename for i in entries]):
                return 0, "archive holds no csv/txt/tab/xls/xlsx file"
            if sum(i.file_size for i in entries) > MAX_UNPACKED_BYTES:
                return 0, "archive unpacks to more than 2 GB"
            z.extractall(dest, entries)  # zipfile drops absolute paths and '..' components
            return len(entries), ""
    with tarfile.open(path, "r:gz") as t:
        members = [m for m in t.getmembers() if m.isfile() and not _junk(m.name)]
        if not _tabular_members([m.name for m in members]):
            return 0, "archive holds no csv/txt/tab/xls/xlsx file"
        if sum(m.size for m in members) > MAX_UNPACKED_BYTES:
            return 0, "archive unpacks to more than 2 GB"
        t.extractall(dest, members, filter="data")  # refuses links, devices and paths outside dest
        return len(members), ""


def fetch(row: Any) -> None:
    """Download one planned file (and check / extract it when it is an archive), recording the outcome in LOG.

    Args:
        row: A row of the plan (url, local_name, ext, bytes, action ...).
    """
    dest = OUT_DIR / row.local_name
    tmp = dest.with_name(dest.name + ".part")
    try:
        with _get(row.url, stream=True, timeout=600) as r, open(tmp, "wb") as fh:
            for chunk in r.iter_content(1 << 20):
                fh.write(chunk)
        got = tmp.stat().st_size
        if row.bytes and got != row.bytes:
            raise IOError(f"size {got} != expected {row.bytes}")
        if row.action == "archive":
            folder = EXTRACT_DIR / archive_stem(row.local_name)
            try:
                n, why = _extract(tmp, row.ext, folder)
            except Exception as e:  # noqa: BLE001 - a bad archive is recorded, not fatal
                _rmtree(folder)
                n, why = 0, f"{row.ext} could not be extracted ({type(e).__name__}: {e})"[:200]
            tmp.unlink()
            if why:
                _log(row, "skipped", why)
            else:
                _log(row, "ok", f"{folder.relative_to(OUT_DIR)} ({n} files)")
            return
        tmp.rename(dest)
        _log(row, "ok")
    except Exception as e:  # noqa: BLE001 - record any failure and continue with the other files
        tmp.unlink(missing_ok=True)
        _log(row, "failed", f"{type(e).__name__}: {e}"[:200])


def _rmtree(path: Path) -> None:
    """Remove a folder tree when it exists."""
    if path.exists():
        shutil.rmtree(path)


def download(plan: pd.DataFrame, actions: set[str]) -> None:
    """Download the planned files of the given actions that are not finished yet, smallest first.

    Args:
        plan: The download plan.
        actions: 'direct' and / or 'archive'.
    """
    done = _done()
    todo = plan[plan.action.isin(actions)]
    todo = todo[[done.get(n, ("",))[0] not in ("ok", "skipped") for n in todo.local_name]]
    todo = todo.sort_values("bytes")
    print(f"downloading {len(todo)} files ({todo.bytes.sum() / 1e9:.1f} GB): {sorted(actions)}")
    with ThreadPoolExecutor(MAX_WORKERS) as pool:
        for n, _ in enumerate(pool.map(fetch, todo.itertuples()), 1):
            if n % 250 == 0:
                print(f"  {n}/{len(todo)}", flush=True)


def write_records(plan: pd.DataFrame) -> None:
    """Write DOWNLOADED and NOT_DOWNLOADED from the plan and LOG, and print the reasons for files not downloaded.

    Args:
        plan: The download plan.
    """
    done = _done()
    st = plan.local_name.map(lambda n: done.get(n, ("", ""))[0]).where(plan.action != "skip", "")
    detail = plan.local_name.map(lambda n: done.get(n, ("", ""))[1])
    out = plan.assign(size_mb=(plan.bytes / 1024 ** 2).round(3))
    ok = out[(st == "ok").to_numpy()]
    ok = ok.assign(extracted_to=detail[(st == "ok").to_numpy()].where(ok.action == "archive", ""))
    ok[["doi", "file_name", "local_name", "ext", "size_mb", "extracted_to"]].to_csv(DOWNLOADED, sep="\t", index=False)
    reason = out.reason.where(out.action == "skip", "")
    reason = reason.mask((st == "skipped").to_numpy(), detail)
    reason = reason.mask((st == "failed").to_numpy(), "download failed: " + detail)
    reason = reason.mask(((st == "") & (out.action != "skip")).to_numpy(), "not downloaded yet")
    nd = out[(st != "ok").to_numpy()].assign(reason=reason)
    nd[["doi", "file_name", "ext", "size_mb", "reason"]].to_csv(NOT_DOWNLOADED, sep="\t", index=False)
    print(f"downloaded {len(ok)} files; not downloaded {len(nd)}")
    print(nd.reason.str.replace(r" \(.*", "", regex=True).value_counts().to_string())


def main() -> None:
    """Parse the command line, build or read the plan, download and write the records."""
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--direct", action="store_true", help="download files of the direct types")
    p.add_argument("--archives", action="store_true", help="download, check and extract zip and tar.gz archives")
    p.add_argument("--replan", action="store_true", help="rebuild the plan from the metadata")
    p.add_argument("--max-mb", type=float, default=MAX_MB, help=f"size cap with --replan (default {MAX_MB})")
    p.add_argument("--name-filter-mb", type=float, default=NAME_FILTER_MB,
                   help=f"above this size a file needs NAME_PATTERN in its name, with --replan (default {NAME_FILTER_MB})")
    p.add_argument("--doi-file", type=Path,
                   help="only these packages (one DOI per line): their files are replanned with --max-mb / "
                        "--name-filter-mb and merged into the existing plan")
    a = p.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if PLAN.exists() and not a.replan:
        plan = pd.read_csv(PLAN, sep="\t", dtype={"bytes": "int64"}, keep_default_na=False)
    else:
        plan = build_plan(a.max_mb, a.name_filter_mb)
    if a.doi_file:
        dois = {x.strip().lower() for x in a.doi_file.read_text().splitlines() if x.strip()}
        sub = build_plan(a.max_mb, a.name_filter_mb, dois=dois, write=False)
        plan = pd.concat([plan[~plan.doi.str.lower().isin(dois)], sub], ignore_index=True)
        plan.to_csv(PLAN, sep="\t", index=False)
        print(f"replanned {sub.doi.nunique()} packages: {sub.action.value_counts().to_dict()}")
        actions = ({"direct"} if a.direct else set()) | ({"archive"} if a.archives else set())
        if actions:
            download(sub, actions)
        write_records(plan)
        return
    actions = ({"direct"} if a.direct else set()) | ({"archive"} if a.archives else set())
    if actions:
        download(plan, actions)
    write_records(plan)


if __name__ == "__main__":
    main()
