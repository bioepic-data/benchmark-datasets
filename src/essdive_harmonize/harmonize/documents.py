"""Read the text of a package's own documents (user guides, methods, readme, data dictionaries) for method sentences.

The metadata text often does not say how a variable was measured while a document of the package does:
doi:10.5440/1109232 'soil_physicochemical_properties_user_guide.pdf' ('% Total Carbon Content of soil analyzed by
combustion'), doi:10.3334/CDIAC/SPRUCE.005 'SPRUCE_Peat_characteristics_data.pdf' ('... on a LECO TruSpec elemental
analyzer'), doi:10.15485/3484503 'TBS_Mineralization_Methods_Codes.csv' (user decision 2026-10-13).

Documents are the package's PDF, Word (.docx), text and Markdown files, and the CSV / Excel files whose name says they
document the data (method, protocol, readme, dictionary, flmd ...). PDFs need pypdf; without it they are skipped.
"""

from __future__ import annotations

import logging
import re
import zipfile
from functools import lru_cache
from pathlib import Path

import pandas as pd

from ..common import doi_slug
from .config import PACKAGE_DATA
from .tables import source_name

DOC_EXT = (".pdf", ".docx", ".txt", ".md")
DOC_TABLE = re.compile(r"(?i)method|protocol|readme|read_me|tableofcontents|table_of_contents|_dd\b|_dd\.|dictionary|"
                       r"flmd|codes?\b|user.?guide|documentation")
MAX_CHARS = 400_000
MAX_PAGES = 60

__all__ = ["document_text", "package_documents"]


def _pdf_text(path: Path) -> str:
    """Text of a PDF ('' without pypdf); line breaks inside a sentence are joined."""
    try:
        import pypdf
    except ImportError:
        return ""
    logging.getLogger("pypdf").setLevel(logging.ERROR)   # 'Ignoring wrong pointing object' on damaged PDFs
    reader = pypdf.PdfReader(str(path))
    text = "\n".join((p.extract_text() or "") for p in reader.pages[:MAX_PAGES])
    # a PDF line break inside a sentence: the next line goes on in lower case, or the line ends with ',' or '-';
    # table rows (column name, unit, description) stay separate lines
    return re.sub(r"(?<=[,\-])\s*\n\s*|\s*\n\s*(?=[a-z(])", " ", text)


def document_text(path: Path) -> str:
    """Return the text of one document ('' when it cannot be read).

    Examples:
        >>> import tempfile
        >>> p = Path(tempfile.mkdtemp()) / "x_methods.txt"
        >>> _ = p.write_text("Total C was measured by combustion.")
        >>> document_text(p)
        'Total C was measured by combustion.'
    """
    ext = path.suffix.lower()
    try:
        if ext in (".txt", ".md", ".csv", ".tsv"):
            return path.read_text(errors="replace")[:MAX_CHARS]
        if ext == ".docx":
            with zipfile.ZipFile(path) as z:
                xml = z.read("word/document.xml").decode("utf-8", "replace")
            return re.sub(r"<[^>]+>", " ", xml.replace("</w:p>", "\n"))[:MAX_CHARS]
        if ext in (".xlsx", ".xls"):
            sheets = pd.read_excel(path, sheet_name=None, header=None, dtype=str)
            return "\n".join(" | ".join(r) for d in sheets.values() for r in d.fillna("").values)[:MAX_CHARS]
        if ext == ".pdf":
            return _pdf_text(path)[:MAX_CHARS]
    except Exception:  # noqa: BLE001  (a damaged or protected document gives no text)
        return ""
    return ""


def _is_document(path: Path) -> bool:
    """Tell whether a package file documents the data (see the module docstring).

    A CSV whose name does not say so is a document when its header starts with a field-name column and names a
    description / definition column (a data dictionary under another name: 2566016 'metadata_bocas_all_master.csv',
    'Field,Description,Units'); data tables with a Description column (2480291 'Pit,Horizon,...,Description', 2572883
    locations.csv) and field metadata tables are data.
    """
    ext = path.suffix.lower()
    if ext in DOC_EXT or (ext in (".csv", ".xlsx", ".xls") and DOC_TABLE.search(path.name)):
        return True
    if ext == ".csv":
        try:
            with open(path, errors="replace") as fh:
                head = fh.readline()
        except OSError:
            return False
        first = re.sub(r"^\W+", "", head.split(",")[0]).strip().lower()
        return (bool(re.fullmatch(r"(column|field|variable|attribute|parameter)s?( ?name)?", first))
                and bool(re.search(r"(?i),\W*(description|definition)\b", head)))
    return False


@lru_cache(maxsize=512)
def package_documents(doi: str) -> tuple[tuple[str, str], ...]:
    """Return the documents of a package as (ESS-DIVE file name, text), downloaded and extracted files (cached).

    Examples:
        >>> package_documents("doi:10.5440/1109232")[0][0]  # doctest: +SKIP
        'Soil_Classification_Barrow_TRC_DEG_20140115.pdf'
    """
    slug = doi_slug(doi)
    files = sorted(p for p in PACKAGE_DATA.glob(slug + "_*") if p.is_file())
    files += sorted(p for d in (PACKAGE_DATA / "extracted").glob(slug + "_*") for p in d.rglob("*") if p.is_file())
    out = []
    for p in files:
        if _is_document(p):
            text = document_text(p)
            if text.strip():
                out.append((source_name(str(p.relative_to(PACKAGE_DATA))), text))
    return tuple(out)
