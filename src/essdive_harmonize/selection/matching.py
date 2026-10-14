"""Match the variables against package column headers and metadata text.

Evidence sources (one evidence row per package, variable and source):

- columns: the header of a data file.
- dictionary: a column name listed in a data dictionary or metadata file / sheet.
- keywords: keywords and variableMeasured.
- description: title, alternate name and description.
- other: measurementTechnique, package file names and descriptions, site descriptions.

Strength is 'strong' or 'related' (the carbon specs grade both; list rules only give 'strong'). A metadata text match
also records its context (the sentences it came from) and the exclusion terms in them (plant, litter, root, water:
CONTEXT_TERMS); these are recorded for review only and never drop a match. A variable with a
package-context requirement (exchangeable cations, enzymes, porewater metals, total elements, Mehlich-3 metals) only
counts in packages whose metadata or column headers match that context, and a column that the package's data
dictionary defines must have a matching definition when the rule asks for it. Packages are never selected by name:
all evidence comes from the data and metadata.

Examples:
    >>> from essdive_harmonize.selection.variable_list import ListVariable
    >>> from essdive_harmonize.selection.rules import spec_for
    >>> v = ListVariable("Acidity", "Soil pH", "Acidity__Soil_pH", "Acidity:Soil pH", spec_for("Soil pH"))
    >>> hd = pd.DataFrame({"doi": "d1", "file": "a.csv", "sheet": "", "column": ["pH", "Depth"],
    ...                    "is_dictionary": False, "n_rows": 3, "n_numeric": [3, 3], "group": ""})
    >>> pk = pd.DataFrame({"doi": ["d1"], "title": ["Soil cores"], "keywords": ["SOIL PH"],
    ...                    "description": ["Soil cores"], "other": [""]})
    >>> hits = {v.key: {"pH": ("strong", "strong")}}
    >>> evidence([v], pk, hd, hits)[["doi", "source", "strength", "detail"]].values.tolist()
    [['d1', 'columns', 'strong', 'pH'], ['d1', 'keywords', 'strong', 'SOIL PH']]

Attributes:
    TEXT_SOURCES: Metadata text sources.
    EVIDENCE: Columns of the evidence table.
    CONTEXT_TERMS: Terms recorded in exclusion_terms when they occur in the sentence of a text match (the plant terms of
        the column exclusions, litter, roots, water); recorded only, never used to drop a match.
"""

from __future__ import annotations

import re
import warnings
from collections.abc import Iterable, Sequence
from concurrent.futures import ProcessPoolExecutor
from typing import Any, Final

import pandas as pd

from .config import MAX_COLUMN_CHARS
from .headers import dictionary_definitions
from .datatypes import ColumnClass, ColumnHits, ColumnRule, HasSpec, HitsByVariable, Pattern, Source, Strength
from .rules import ORGANIC_FROM, ORGANIC_TO, Spec, organic_definition

warnings.filterwarnings("ignore", "This pattern is interpreted as a regular expression, and has match groups")

TEXT_SOURCES: Final[list[Source]] = ["keywords", "description", "other"]
EVIDENCE: Final[list[str]] = ["doi", "key", "category", "variable", "source", "strength", "n_columns", "n_numeric",
                              "detail", "context", "exclusion_terms"]
CONTEXT_TERMS: Final[Pattern] = re.compile(r"\b(needles?|leaf|leaves|foliar|foliage|stems?|wood|woody|plants?|"
                                           r"vegetation|roots?|litter|bole|tissue|stream ?water|river|surface ?water|"
                                           r"ground ?water|pore ?water|water samples?)\b", re.I)
_SENTENCE: Final[Pattern] = re.compile(r"(?<=[.;!?])\s+|\n+|\s+\|\s+")
_NUMERIC: Final[Pattern] = re.compile(r"^[-+]?[\d.,eE%:/ ]+$")


def _norm(c: str) -> str:
    """Normalize a column name for the carbon specs: lower case, runs of spaces / '_' / '.' -> one space.

    Examples:
        >>> _norm("TC_wt.%")
        'tc wt %'
    """
    return re.sub(r"[\s_.]+", " ", c).strip().lower()


# A leading 5-digit method code (WHONDRS "01395_C_percent") and a hyphen between letters ("total-carbon-concentration")
# hide a column name from the patterns (user decision 2026-10-12). A hyphen between two capitals is a minus sign
# ("OC (%) (TC-IC)", doi:10.15485/1725884, would otherwise match TC) and is kept.
CODE_PREFIX: Final[Pattern] = re.compile(r"^\d{5}_(?=[A-Za-z])")
WORD_HYPHEN: Final[Pattern] = re.compile(r"(?<=[a-z])-(?=[A-Za-z])|(?<=[A-Za-z])-(?=[a-z])")


def _clean(c: str) -> str:
    """Drop a leading 5-digit method code and turn a hyphen between letters into a space.

    Examples:
        >>> _clean("01395_C_percent"), _clean("total-carbon-concentration"), _clean("0-10 cm"), _clean("OC (TC-IC)")
        ('C_percent', 'total carbon concentration', '0-10 cm', 'OC (TC-IC)')
    """
    return WORD_HYPHEN.sub(" ", CODE_PREFIX.sub("", c))


def _hit(rules: Iterable[ColumnRule], col: str) -> bool:
    """Tell whether a column matches any (column pattern, exclusion) rule."""
    return any(rc is not None and rc.search(col) and not (ex is not None and ex.search(col)) for rc, ex in rules)


def classify_column(col: str, spec: Spec) -> ColumnClass:
    """Classify one column name for a variable.

    Args:
        col: The column name (or '<group> <column>').
        spec: The variable's rules.

    Returns:
        The strength with the full rules and the strength with the rules used outside spec.rules_context ('strong',
        'related' or None).

    Examples:
        >>> from essdive_harmonize.selection.rules import spec_for
        >>> tc = spec_for("Total carbon")
        >>> classify_column("TC (%)", tc), classify_column("SOC", tc), classify_column("DOC", tc)
        (('strong', 'strong'), ('related', 'related'), (None, None))
        >>> classify_column("P", spec_for("Total phosphorus"))
        ('strong', None)
    """
    if spec.mode == "normalized":
        c = _norm(_clean(col))
        strong = any(p.search(c) for p in spec.col_strong) or any(p.search(_clean(col)) for p in spec.col_strong_cased)
        if not (strong or any(p.search(c) for p in spec.col_related)):
            return None, None
        if spec.col_hard and spec.col_hard.search(c):
            return None, None
        if spec.col_exclude and spec.col_exclude.search(c) and not (spec.col_rescue and spec.col_rescue.search(c)):
            return None, None
        s: Strength = "strong" if strong else "related"
        return s, s
    names = dict.fromkeys([col, _clean(col)])  # the cleaned name only adds matches: some raw rules expect hyphens
    full: Strength | None = "strong" if any(_hit(spec.raw_rules, n) for n in names) else None
    if spec.raw_rules_no_context is None:
        return full, full
    return full, ("strong" if full and any(_hit(spec.raw_rules_no_context, n) for n in names) else None)


_COLUMNS: list[str] = []


def _init(columns: list[str]) -> None:
    """Give a worker process the distinct column names to classify."""
    global _COLUMNS
    _COLUMNS = columns


def _match_columns(item: tuple[str, Spec]) -> tuple[str, ColumnHits]:
    """Classify every distinct column for one variable (runs in a worker process)."""
    key, spec = item
    out: ColumnHits = {}
    for c in _COLUMNS:
        full, reduced = classify_column(c, spec)
        if full:
            out[c] = (full, reduced)
    return key, out


def column_hits(variables: Sequence[HasSpec], headers: pd.DataFrame, workers: int | None = None) -> HitsByVariable:
    """Classify every distinct column name (and '<group> <column>') for every variable, in parallel.

    Args:
        variables: The variables.
        headers: The column-header cache.
        workers: Worker processes; all cores when None.

    Returns:
        {variable key: {column text: (strength, strength outside rules_context)}} for the matching columns.
    """
    distinct = pd.concat([headers.column, combined(headers)]).drop_duplicates()
    cols = [c for c in distinct if len(c) <= MAX_COLUMN_CHARS and not _NUMERIC.match(c)]
    with ProcessPoolExecutor(workers, initializer=_init, initargs=(cols,)) as ex:
        return dict(ex.map(_match_columns, [(v.key, v.spec) for v in variables]))


def combined(headers: pd.DataFrame) -> pd.Series:
    """Return '<group> <column>' for columns under a group row, else the column, aligned with the headers.

    Examples:
        >>> combined(pd.DataFrame({"column": ["0.01 M CaCl2", "ID"], "group": ["Soil pH", ""]})).tolist()
        ['Soil pH 0.01 M CaCl2', 'ID']
    """
    g = headers["group"] if "group" in headers else pd.Series("", index=headers.index)
    return (g.where(g == "", g + " ") + headers.column).where(g != "", headers.column)


def row_strength(headers: pd.DataFrame, h: ColumnHits, which: int = 0) -> pd.Series:
    """Look up the strength of each header row by its column name, else by '<group> <column>'.

    Args:
        headers: Header rows.
        h: The column hits of one variable.
        which: 0 for the full rules, 1 for the rules used outside the variable's rules_context.

    Returns:
        The strength per row (None where the column does not match).

    Examples:
        >>> hd = pd.DataFrame({"column": ["0.01 M CaCl2", "ID"], "group": ["Soil pH", ""]})
        >>> row_strength(hd, {"Soil pH 0.01 M CaCl2": ("strong", "strong")}).tolist()
        ['strong', None]
    """
    by_col = headers.column.map(lambda c: h[c][which] if c in h else None)
    by_comb = combined(headers).map(lambda c: h[c][which] if c in h else None)
    return by_col.where(by_col.notna(), by_comb)


def _context_sets(variables: Sequence[HasSpec], packages: pd.DataFrame,
                  headers: pd.DataFrame) -> dict[Pattern, set[str]]:
    """Find, for every context pattern of the variables, the DOIs whose metadata or headers match it."""
    text = packages.set_index("doi")[["title", "keywords", "description", "other"]].agg(" | ".join, axis=1)
    cols = headers.groupby("doi").column.agg(lambda s: " | ".join(set(s)))
    full = text + (" | " + cols.reindex(text.index).fillna(""))  # same index on both sides
    pats = {p for v in variables for p in (v.spec.context, v.spec.exclude_context, v.spec.rules_context) if p}
    return {p: set(full.index[full.str.contains(p)]) for p in pats}


def _defined_as(m: pd.DataFrame, headers: pd.DataFrame, pattern: Pattern) -> pd.Series:
    """Keep the matched columns whose data-dictionary definition, if any, matches the pattern.

    A column the package's dictionary does not define is kept; a defined one is kept only when its definition matches
    (an 'Fe' column defined as 'HCl-extractable iron' is not a Mehlich-3 column).
    """
    keep = pd.Series(True, index=m.index)
    for doi in m.doi.unique():
        dict_files = headers.file[(headers.doi == doi) & headers.is_dictionary].unique()
        defs = dictionary_definitions(dict_files)
        rows = m.index[m.doi == doi]
        keep.loc[rows] = pd.Series([(d := defs.get(str(c).lower())) is None or bool(pattern.search(d))
                                    for c in m.loc[rows, "column"]], index=rows)
    return keep


def organic_defined(m: pd.DataFrame, headers: pd.DataFrame) -> pd.Series:
    """Flag the matched columns whose data-dictionary definition says organic carbon (rules.organic_definition).

    Args:
        m: Matched header rows (doi, column).
        headers: The column-header cache (doi, file, is_dictionary), to find each package's dictionaries.

    Returns:
        A boolean Series on m's index; False for a column the package's dictionary does not define.
    """
    flag = pd.Series(False, index=m.index)
    for doi in m.doi.unique():
        defs = dictionary_definitions(headers.file[(headers.doi == doi) & headers.is_dictionary].unique())
        if not defs:
            continue
        rows = m.index[m.doi == doi]
        flag.loc[rows] = pd.Series([organic_definition(defs.get(str(c).lower(), "")) for c in m.loc[rows, "column"]],
                                   index=rows)
    return flag


def _terms(pattern_list: Iterable[Pattern], text: str, n: int = 5) -> str:
    """Return up to n distinct matched terms of the patterns in a text, joined with '; '.

    Examples:
        >>> import re
        >>> _terms([re.compile("soil ph", re.I)], "Soil pH in water; soil pH in CaCl2")
        'Soil pH'
    """
    found: list[str] = []
    for p in pattern_list:
        for m in p.finditer(text):
            t = m.group(0).strip()
            if t and t.lower() not in (f.lower() for f in found):
                found.append(t)
            if len(found) >= n:
                return "; ".join(found)
    return "; ".join(found)


def _context(pattern_list: Iterable[Pattern], text: str, n: int = 3, width: int = 300) -> tuple[str, str]:
    """Return the sentences of a text that match the patterns and the CONTEXT_TERMS found in them.

    Args:
        pattern_list: The patterns that matched.
        text: The metadata text.
        n: Most sentences returned.
        width: Most characters kept per sentence.

    Returns:
        The sentences joined with ' ... ' and the distinct exclusion terms (lower case) joined with '; '.

    Examples:
        >>> import re
        >>> _context([re.compile(r"CN analyzer", re.I)],
        ...          "Branches were sampled. Needles were analyzed for % carbon (Costech CN Analyzer).")
        ('Needles were analyzed for % carbon (Costech CN Analyzer).', 'needles')
    """
    pats = list(pattern_list)
    sentences = [x.strip() for x in _SENTENCE.split(text) if x.strip() and any(p.search(x) for p in pats)][:n]
    terms = dict.fromkeys(m.group(0).lower() for x in sentences for m in CONTEXT_TERMS.finditer(x))
    return " ... ".join(x[:width] for x in sentences), "; ".join(terms)


def evidence(variables: Sequence[HasSpec], packages: pd.DataFrame, headers: pd.DataFrame,
             hits: HitsByVariable) -> pd.DataFrame:
    """Build the evidence table: one row per package, variable and source.

    Args:
        variables: The variables.
        packages: The package table with its metadata text.
        headers: The column-header cache.
        hits: The column hits (column_hits).

    Returns:
        The EVIDENCE columns: doi, key, category, variable, source, strength, n_columns, n_numeric, detail (matched
        columns or terms), and for text matches context (the matching sentences) and exclusion_terms (CONTEXT_TERMS in
        them; recorded only). A source counts once per package and variable, with its strongest row. Total carbon
        columns that the package's data dictionary defines as organic carbon count for Soil organic carbon instead
        (rules.organic_definition).
    """
    ctx = _context_sets(variables, packages, headers)
    all_dois: set[str] = set(packages.doi) | set(headers.doi)
    allowed_of: dict[str, set[str]] = {}
    for v in variables:
        allowed = all_dois
        if v.spec.context:
            allowed = allowed & ctx[v.spec.context]
        if v.spec.exclude_context:
            allowed = allowed - ctx[v.spec.exclude_context]
        allowed_of[v.key] = allowed

    def matched(v: HasSpec) -> pd.DataFrame:
        """The header rows that match a variable, with their strength."""
        s, h = v.spec, hits.get(v.key, {})
        if not h:
            return headers.iloc[:0].assign(strength=None)
        hd = headers[headers.doi.isin(allowed_of[v.key])]
        m = hd.assign(strength=row_strength(hd, h))
        m = m[m.strength.notna()].copy()
        if s.rules_context is not None:  # outside the context only the reduced rules count
            outside = ~m.doi.isin(ctx[s.rules_context])
            m.loc[outside, "strength"] = row_strength(m[outside], h, 1)
            m = m[m.strength.notna()]
        if s.definition is not None and len(m):
            m = m[_defined_as(m, headers, s.definition)]
        return m

    organic_from = next((v for v in variables if v.spec.name == ORGANIC_FROM), None)
    moved = pd.DataFrame()  # Total carbon columns defined as organic carbon (rules.ORGANIC_FROM)
    if organic_from is not None:
        tc = matched(organic_from)
        moved = tc[organic_defined(tc, headers)] if len(tc) else tc
    rows: list[dict[str, Any]] = []
    for v in variables:
        s = v.spec
        base: dict[str, Any] = dict(key=v.key, category=v.category, variable=v.name)

        # column headers
        m = matched(v)
        if s.name == ORGANIC_FROM and len(moved):
            m = m.drop(index=moved.index, errors="ignore")
        elif s.name == ORGANIC_TO and len(moved):
            m = pd.concat([m, moved.assign(strength="strong")])
            m = m[~m.index.duplicated()]
        if len(m):
            for (doi, is_dict), g in m.groupby(["doi", "is_dictionary"]):
                rows.append(dict(base, doi=doi, source="dictionary" if is_dict else "columns",
                                 strength="strong" if (g.strength == "strong").any() else "related",
                                 n_columns=g.column.nunique(), n_numeric=int(g.n_numeric.fillna(0).sum()),
                                 detail="; ".join(sorted(set(g.column))[:10]), context="", exclusion_terms=""))

        # metadata text
        pk = packages[packages.doi.isin(allowed)]
        graded: tuple[tuple[Strength, tuple[Pattern, ...]], ...] = (("strong", s.text_strong),
                                                                    ("related", s.text_related))
        for src in TEXT_SOURCES:
            for strength, pats in graded:
                if not pats:
                    continue
                hit = pd.Series(False, index=pk.index)
                for p in pats:
                    hit |= pk[src].str.contains(p)
                for r in pk[hit].itertuples():
                    text = str(getattr(r, src))
                    context, terms = _context(pats, text)
                    rows.append(dict(base, doi=r.doi, source=src, strength=strength, n_columns=0, n_numeric=0,
                                     detail=_terms(pats, text), context=context, exclusion_terms=terms))

    ev = pd.DataFrame(rows, columns=EVIDENCE)
    # a source counts once per package and variable: keep its strongest row
    ev["_rank"] = ev.strength.map({"strong": 0, "related": 1})
    ev = ev.sort_values(["key", "doi", "source", "_rank"]).drop_duplicates(["key", "doi", "source"])
    return ev.drop(columns="_rank").reset_index(drop=True)
