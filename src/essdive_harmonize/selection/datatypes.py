"""Define the types shared by the package-selection modules.

Attributes:
    Pattern: A compiled regular expression.
    Strength: Match strength of a column or text hit ('related' only from the graded carbon specs).
    Source: Where the evidence was found.
    Mode: How a Spec matches columns: graded patterns on normalized names (carbon) or raw-text rules (list rules).
    ColumnRule: One raw-text column rule: (column pattern, exclusion pattern).
    ColumnClass: Strength of a column with the full rules and with the rules used outside Spec.rules_context.
    ColumnHits: Column text -> its class, for one variable.
    HitsByVariable: Variable key -> its column hits.
    Restriction: Package restriction of a rule. Every restriction is a test on the package's own metadata and column
        headers (no package lists): 'exch' / 'enzyme' / 'pore' / 'solid_total' require that context
        (rules.EXC_CTX, ENZYME_CTX, PORE_CTX, SOLID_CTX); 'sym_solid' lets the bare element symbol count only in
        soil / sediment packages; 'no_porewater' excludes packages about porewater; ('context', pattern) requires
        the pattern.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal, NamedTuple, Protocol, TypeAlias

if TYPE_CHECKING:
    from .rules import Spec

Pattern: TypeAlias = re.Pattern[str]

# Match strength of a column or text hit ("related" only from the graded carbon specs).
Strength: TypeAlias = Literal["strong", "related"]
# Where the evidence was found.
Source: TypeAlias = Literal["columns", "dictionary", "keywords", "description", "other"]
# How a Spec matches columns: graded patterns on normalized names (carbon) or raw-text rules (list rules).
Mode: TypeAlias = Literal["normalized", "raw"]

# One raw-text column rule: (column pattern, exclusion pattern).
ColumnRule: TypeAlias = tuple["Pattern | None", "Pattern | None"]
# Strength of a column with the full rules and with the rules used outside Spec.rules_context.
ColumnClass: TypeAlias = tuple["Strength | None", "Strength | None"]
# Column text -> its class, for one variable.
ColumnHits: TypeAlias = dict[str, ColumnClass]
# Variable key -> its column hits.
HitsByVariable: TypeAlias = dict[str, ColumnHits]

# Package restriction of a rule in notebooks/soil_variable_list/05_count_packages.py.
# Every restriction is a test on the package's own metadata and column headers (no package lists):
#   exch / enzyme / pore / solid_total   the package must have that context (rules.EXC_CTX, ENZYME_CTX, ...)
#   sym_solid                            the bare element symbol only counts in soil / sediment packages
#   no_porewater                         not in packages about porewater
#   ("context", pattern)                 the package must match this pattern
Restriction: TypeAlias = (Literal["exch", "enzyme", "pore", "solid_total", "sym_solid", "no_porewater"]
                          | tuple[Literal["context"], str] | None)


class RawRule(NamedTuple):
    """One rule of notebooks/soil_variable_list/05_count_packages.py, with its patterns as text.

    Attributes:
        column: Column pattern (raw text, case-insensitive; bare element symbols case-sensitive), or None.
        exclude: Columns matching this are not the variable.
        text: Metadata text pattern, or None.
        restrict: Package restriction (see Restriction).
    """
    column: str | None
    exclude: str | None
    text: str | None
    restrict: Restriction


class TableRow(NamedTuple):
    """One header cell of a table, or one name listed in a data dictionary.

    Attributes:
        column: The column name (a blank or unit-only cell under a group row takes the group label).
        is_dictionary: The name comes from a data dictionary, not a data table.
        n_rows: Rows below the header (None for dictionaries).
        n_numeric: Numeric values below the header (None for dictionaries).
        group: Label of a group row above the header ('' when none).
    """
    column: str
    is_dictionary: bool
    n_rows: int | None
    n_numeric: int | None
    group: str


class HeaderRow(NamedTuple):
    """One row of the header cache without doi and file: a TableRow with its sheet.

    Attributes:
        sheet: Sheet name ('' for text files).
        column: The column name.
        is_dictionary: The name comes from a data dictionary.
        n_rows: Rows below the header.
        n_numeric: Numeric values below the header.
        group: Label of a group row above the header.
    """
    sheet: str
    column: str
    is_dictionary: bool
    n_rows: int | None
    n_numeric: int | None
    group: str


class ScanResult(NamedTuple):
    """The header rows of one file and an error message.

    Attributes:
        rows: One HeaderRow per column (every sheet of an Excel file).
        error: Why the file was not read (unreadable, too large), or None.
    """
    rows: list[HeaderRow]
    error: str | None


class DoiIndex(NamedTuple):
    """Ways to find the DOI of a local file.

    Attributes:
        by_path: Local file or extracted-folder name -> DOI (from package_data_downloaded.tsv).
        slugs: (DOI slug, DOI) pairs, longest slug first (for files not in the download record).
    """
    by_path: dict[str, str]
    slugs: list[tuple[str, str]]


class HasSpec(Protocol):
    """A variable to search for (selection.variable_list.ListVariable)."""

    @property
    def key(self) -> str:
        """Variable key, e.g. 'Acidity__Soil_pH'."""
        ...

    @property
    def category(self) -> str:
        """Category in the variable list."""
        ...

    @property
    def name(self) -> str:
        """Variable name in the variable list."""
        ...

    @property
    def label(self) -> str:
        """'<category>:<name>', the matrix column label."""
        ...

    @property
    def spec(self) -> Spec:
        """The matching rules."""
        ...
