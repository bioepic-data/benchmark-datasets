"""Set the paths and limits of the package-selection workflow.

Attributes:
    PROJECT_ROOT: The repository root.
    VARIABLE_LIST: data/soil_variable_list_input.csv, the variables to search for.
    OUT_DIR: data/intermediate/package_selection, the outputs.
    HEADERS_CACHE: File name of the column-header cache in OUT_DIR (gzip: 118 MB as plain CSV, over the GitHub
        file limit; pandas reads and writes it by the extension).
    TABLE_EXTENSIONS: Extensions of the files whose headers are read.
    HEADER_SCAN_ROWS: Rows inspected to locate the header line.
    MAX_ROWS: Rows read per file or sheet to count numeric values.
    MAX_FILE_BYTES: Larger files are not scanned.
    MAX_COLUMN_CHARS: Longer header cells are text, not column names.
    SENTINELS: Numbers that are missing-value codes, not values.
    DOWNLOADED: Record of the downloaded files (from download_files).
    META_DIR: The per-package metadata files (from download_files).
    PACKAGE_DATA: The downloaded package files (from download_files).
"""

from pathlib import Path
from typing import Final

from ..download_files import DOWNLOADED, META_DIR, OUT_DIR as PACKAGE_DATA

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
VARIABLE_LIST: Final[Path] = PROJECT_ROOT / "data" / "soil_variable_list_input.csv"
OUT_DIR: Final[Path] = PROJECT_ROOT / "data" / "intermediate" / "package_selection"
HEADERS_CACHE: Final = "column_headers.csv.gz"

TABLE_EXTENSIONS: Final[tuple[str, ...]] = (".csv", ".txt", ".tsv", ".tab", ".xlsx", ".xls", ".xlsm")
HEADER_SCAN_ROWS: Final = 40        # rows inspected to locate the header line
MAX_ROWS: Final = 50000             # rows read per file or sheet to count numeric values
MAX_FILE_BYTES: Final = 500e6       # larger files are not scanned
MAX_COLUMN_CHARS: Final = 60        # longer header cells are text, not column names
SENTINELS: Final[frozenset[int]] = frozenset({-9999, -999, -99, 9999, -8888, -7777, -6666})

__all__ = ["DOWNLOADED", "META_DIR", "PACKAGE_DATA", "PROJECT_ROOT", "VARIABLE_LIST", "OUT_DIR", "HEADERS_CACHE",
           "TABLE_EXTENSIONS", "HEADER_SCAN_ROWS", "MAX_ROWS", "MAX_FILE_BYTES", "MAX_COLUMN_CHARS", "SENTINELS"]
