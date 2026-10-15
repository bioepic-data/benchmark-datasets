"""Papers a package cites, as the last source of a method (user decision 2026-10-14).

Some packages describe their methods only in a paper: doi:10.15485/1454273 'Methods ... are provided in Grossiord et
al. 2018, Plant, Cell & Environment'. This module finds such papers and, after the user approves a download plan,
keeps their text for method_for (auto.py), which reads it only when the column name, the data dictionary, the
package text and the package's own documents give no method; the notes then say 'method from cited paper <doi>'.

Steps (from the repo root, PYTHONPATH=src):
    python -m essdive_harmonize.harmonize.papers plan --var Acidity__Soil_pH [--var ...]
        For the packages of these variables written with an unknown method: collect the works they cite (DOIs in
        the metadata citation, description, measurement technique and related identifiers, and in the package
        documents; references without a DOI are searched by text), look each up in OpenAlex (api.openalex.org) for
        an open-access PDF, and write data/source/papers/plan.csv (package, variable, cited DOI, title, PDF URL,
        file name, size). Nothing is downloaded.
    python -m essdive_harmonize.harmonize.papers download
        After the user has read plan.csv and set approve = 1 on the rows to fetch: download those PDFs into
        data/source/papers/, extract their text (<file>.txt) and record them in data/source/papers/index.csv.
    python -m essdive_harmonize.harmonize.papers status
        Show the plan and what has been downloaded.

Only DOIs and reference text are sent to OpenAlex. Dataset DOIs (ESS-DIVE, NGEE, CDIAC, Dryad ...) and funder
identifiers are not papers and are left out.
"""

from __future__ import annotations

import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

import click
import pandas as pd

from ..common import doi_slug
from .config import OUT_ROOT, PROJECT_ROOT
from .documents import document_text, package_documents
from .metadata import _index

PAPERS_DIR = PROJECT_ROOT / "data" / "source" / "papers"
PLAN = PAPERS_DIR / "plan.csv"
INDEX = PAPERS_DIR / "index.csv"
OPENALEX = "https://api.openalex.org/works"
DOI_RX = re.compile(r"\b(10\.\d{4,9}/[^\s\"'<>|\]\[,;]+)", re.I)
# dataset repositories and funder ids: not papers
NOT_PAPER = re.compile(r"(?i)^10\.(15485|15486|25581|3334|5440|21952|5061|13039|5066|6073|17632|7910|5281|1594)/")
METADATA_FIELDS = ("citation", "description", "measurementTechnique", "hasPart", "sameAs", "isBasedOn")
MAX_BYTES = 60_000_000

__all__ = ["cited_works", "paper_texts", "PAPERS_DIR"]


def _clean_doi(d: str) -> str:
    """A DOI without trailing punctuation, lower case.

    Examples:
        >>> _clean_doi("10.1111/PCE.13389).")
        '10.1111/pce.13389'
    """
    return re.sub(r"[).:]+$", "", d.strip()).lower()


def _strings(v: Any) -> list[str]:
    """All strings of a metadata value (str, list, dict)."""
    if isinstance(v, str):
        return [v]
    if isinstance(v, list):
        return [s for x in v for s in _strings(x)]
    if isinstance(v, dict):
        return [s for x in v.values() for s in _strings(x)]
    return []


def cited_works(doi: str) -> list[dict[str, str]]:
    """The works a package cites: one dict per DOI or reference, with where it was found.

    Each has 'doi' (cited DOI, '' when only a reference text is known), 'reference' (the citation text, for a search)
    and 'where' (metadata field or document name). The package's own DOI and dataset / funder DOIs are left out.
    """
    ds = _index().get(doi, {})
    own = _clean_doi(doi.replace("doi:", ""))
    out: dict[str, dict[str, str]] = {}

    def add(d: str, ref: str, where: str) -> None:
        d = _clean_doi(d) if d else ""
        if d and (d == own or NOT_PAPER.match(d)):
            return
        k = d or ref.strip().lower()[:200]
        if k and k not in out:
            out[k] = {"doi": d, "reference": ref.strip()[:400], "where": where}

    for field in METADATA_FIELDS:
        for s in _strings(ds.get(field)):
            dois = DOI_RX.findall(s)
            for d in dois:
                add(d, s if field == "citation" else "", field)
            if field == "citation" and not dois and len(s) > 40:
                add("", s, field)   # a reference without a DOI: searched by its text
    for name, text in package_documents(doi):
        for d in DOI_RX.findall(text):
            add(d, "", name)
    return list(out.values())


def _get(params: dict[str, str], url: str = OPENALEX) -> dict[str, Any] | None:
    """One OpenAlex request (None on failure); polite pause between requests."""
    import requests

    time.sleep(0.2)
    try:
        r = requests.get(url, params=params, timeout=30)
        return r.json() if r.ok else None
    except (requests.RequestException, ValueError):
        return None


def _title_matches(title: str, reference: str) -> bool:
    """Whether most words of a found title occur in the reference text (a search hit is the cited work).

    Examples:
        >>> _title_matches("Reductions in tree performance during hotter droughts",
        ...                "Grossiord, C. Reductions in tree performance during hotter droughts are mitigated")
        True
    """
    words = [w for w in re.findall(r"[a-z]{4,}", title.lower())]
    ref = reference.lower()
    return bool(words) and sum(w in ref for w in words) / len(words) >= 0.8


def openalex(work: dict[str, str]) -> dict[str, str]:
    """Look a cited work up in OpenAlex: its DOI, title and an open-access PDF URL ('' when none)."""
    hit: dict[str, Any] | None = None
    if work["doi"]:
        hit = _get({}, f"{OPENALEX}/doi:{work['doi']}")
    elif work["reference"]:
        res = _get({"search": re.sub(r"[^\w\s]", " ", work["reference"])[:300], "per-page": "3"})
        for w in (res or {}).get("results", []):
            if _title_matches(w.get("title") or "", work["reference"]):
                hit = w
                break
    if not hit:
        return {"cited_doi": work["doi"], "title": "", "pdf_url": "", "oa_status": "not found"}
    pdfs = [loc.get("pdf_url") for loc in [hit.get("best_oa_location") or {}, *(hit.get("locations") or [])]
            if loc and loc.get("pdf_url")]
    return {"cited_doi": _clean_doi((hit.get("doi") or "").replace("https://doi.org/", "")) or work["doi"],
            "title": (hit.get("title") or "")[:200], "pdf_url": pdfs[0] if pdfs else "",
            "oa_status": (hit.get("open_access") or {}).get("oa_status", "")}


def _size(url: str) -> str:
    """The size of a file at a URL from a HEAD request ('' when the server does not say)."""
    import requests

    try:
        r = requests.head(url, allow_redirects=True, timeout=30)
        n = int(r.headers.get("Content-Length", 0))
        return f"{n / 1e6:.1f} MB" if n else ""
    except (requests.RequestException, ValueError):
        return ""


def unknown_method_packages(key: str) -> list[str]:
    """The packages of a variable written with an unknown method (any row)."""
    f = OUT_ROOT / key / "harmonized.csv"
    if not f.exists():
        return []
    t = pd.read_csv(f, dtype=str, keep_default_na=False)
    m = f"{key.lower()}_method"
    return sorted(t.doi[t[m] == "unknown"].unique()) if m in t else []


@lru_cache(maxsize=1)
def _index_table() -> pd.DataFrame:
    """The downloaded papers: package, cited_doi, file (cached)."""
    return pd.read_csv(INDEX, dtype=str, keep_default_na=False) if INDEX.exists() else pd.DataFrame(
        columns=["package", "cited_doi", "file"])


def paper_texts(doi: str) -> list[tuple[str, str]]:
    """The text of the downloaded papers a package cites: (cited DOI, text)."""
    t = _index_table()
    out = []
    for r in t[t.package == doi].itertuples():
        txt = PAPERS_DIR / f"{r.file}.txt"
        if txt.exists():
            out.append((r.cited_doi, txt.read_text(errors="replace")))
    return out


@click.group()
def cli() -> None:
    """Cited papers as a method source (see the module docstring)."""


@cli.command()
@click.option("--var", "keys", multiple=True, required=True, help="Variable key (repeatable).")
def plan(keys: tuple[str, ...]) -> None:
    """Write plan.csv: open-access PDFs of the works cited by packages with an unknown method; nothing downloaded."""
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    seen: dict[str, dict[str, str]] = {}
    for key in keys:
        for doi in unknown_method_packages(key):
            for w in cited_works(doi):
                k = w["doi"] or w["reference"][:200]
                if k not in seen:
                    seen[k] = openalex(w)
                o = seen[k]
                name = f"{doi_slug('doi:' + o['cited_doi'])}.pdf" if o["cited_doi"] else ""
                rows.append({"approve": "", "package": doi, "variable": key, "where": w["where"],
                             "reference": w["reference"][:200], **o, "file_name": name,
                             "size": _size(o["pdf_url"]) if o["pdf_url"] else ""})
                print(f"{doi}  {o['cited_doi'] or '-':32} {o['oa_status']:10} {o['pdf_url'][:70]}")
    p = pd.DataFrame(rows)
    p.to_csv(PLAN, index=False)
    n = int((p.pdf_url != "").sum()) if len(p) else 0
    print(f"\n{len(p)} cited works of {p.package.nunique() if len(p) else 0} packages; {n} with an open-access PDF; "
          f"plan written to {PLAN.relative_to(PROJECT_ROOT)} (set approve = 1 on the rows to download)")


@cli.command()
def download() -> None:
    """Download the approved rows of plan.csv into data/source/papers/ and extract their text."""
    import requests

    p = pd.read_csv(PLAN, dtype=str, keep_default_na=False)
    todo = p[(p.approve.str.strip() == "1") & (p.pdf_url != "") & (p.file_name != "")]
    idx = _index_table().copy()
    for r in todo.itertuples():
        out = PAPERS_DIR / r.file_name
        if not out.exists():
            resp = requests.get(r.pdf_url, timeout=60, headers={"User-Agent": "essdive-harmonize (research)"})
            if not resp.ok or len(resp.content) > MAX_BYTES or not resp.content.startswith(b"%PDF"):
                print(f"  {r.cited_doi}: not downloaded (HTTP {resp.status_code}, not a PDF or too large)")
                continue
            out.write_bytes(resp.content)
        (PAPERS_DIR / f"{r.file_name}.txt").write_text(document_text(out))
        idx = pd.concat([idx, pd.DataFrame([{"package": r.package, "cited_doi": r.cited_doi, "file": r.file_name}])])
        print(f"  {r.cited_doi}: {out.name} ({out.stat().st_size / 1e6:.1f} MB)")
    idx.drop_duplicates().to_csv(INDEX, index=False)
    _index_table.cache_clear()


@cli.command()
def status() -> None:
    """Show the plan and the downloaded papers."""
    if PLAN.exists():
        p = pd.read_csv(PLAN, dtype=str, keep_default_na=False)
        print(f"plan: {len(p)} rows, {int((p.pdf_url != '').sum())} with a PDF, {int((p.approve == '1').sum())} approved")
    print(f"downloaded: {len(_index_table())} package-paper pairs")


if __name__ == "__main__":
    cli()
