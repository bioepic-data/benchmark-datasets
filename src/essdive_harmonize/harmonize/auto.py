"""Harmonize one variable in one package automatically, from scratch.

For every data table with a strong column match (candidates.matched_columns):

1. read the table (header row, units row) (tables.py);
2. detect the sample fields: id, depth, date, coordinates, IGSN (fields.py);
3. locate the rows: in-file, joined, UTM, metadata point, bounding-box centre (locate.py);
4. per matched column: the unit (units row, data dictionary, column name, group header, package description, or
   the variable's assume_unit), conversion to the standard unit, and the method (column name, then package text
   about the variable);
5. write the rows in the soil pH layout (common.assemble); rows without a value or coordinates are dropped.

Tables that are not soil sample data are skipped (water, porewater, model output, molecular-formula tables, time
series, figure / summary sheets, files excluded for the variable), and statistics columns, replicate columns next to
an average, a quantity repeated in another unit and tables repeated in another file are dropped. A package whose
columns, units and location all resolve is 'written'; otherwise it goes to the review queue with the reasons.
Nothing here is specific to one variable: the settings come from variable_config.csv.

Attributes:
    WATER: File / sheet names of water data.
    SOILISH: File / sheet names that are about soil (they keep a file the water pattern would skip).
    MODEL: File / sheet names of model input or output.
    FORMULA_FILE: File names of molecular-formula tables (FT-ICR-MS, metabolomics); skipped only with FORMULA_DERIVED
        columns.
    FORMULA_COLS: Column names of molecular-formula tables.
    FORMULA_DERIVED: Mass / formula columns of a formula table without atom counts.
    PROXIMATE: Proximate-analysis columns of plant material (plignin, phemicellulose ...).
    PROXIMATE_ELEMENT: Element columns of a proximate analysis ('pC', 'pN'), dropped in a table with PROXIMATE columns.
    STATS: Value columns that hold statistics or flags, not measurements.
    AVERAGE: Average columns (used instead of their replicates).
    REPLICATE: Replicate columns.
    SUMMARY_SHEET: Summary / calculation sheets (skipped when the variable is found in another table).
    FIGURE_SHEET: Figure / chart sheets (always skipped).
    MEDIUM: Medium of an extract or solution, by method (DOC medium column).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from functools import lru_cache

import pandas as pd

from .. import units
from ..common import UNKNOWN, assemble, is_missing, num
from ..variables import Variable
from ..extract import target_unit
from .candidates import headers, matched_columns
from .fields import detect, dates, depths, ids, time_series, unit_of
from .locate import locate
from .documents import package_documents
from .papers import paper_texts
from .metadata import coverage_date, package_text, title
from .tables import dictionary_tables, read_table, source_name, stacked_blocks
from .variables import VarConfig, VARIABLES, config

# Tables about water rather than soil (file / sheet name, or the package title when the file name says nothing),
# skipped unless the file name mentions soil, sediment or peat. Stream / river / creek alone are not used: they are
# often site names ('East_River_Pumphouse_Microbial_Biomass.csv'), not the sample type (user decision 2026-10-12);
# only together with a sample-type word ('stream_chemistry', 'river water') or as a catchment 'outlet'.
WATER = re.compile(r"surface ?water|(stream|river|creek)[ _-]?(water|chemistry|samples?)|(?<![a-z])outlet|"
                   r"groundwater|ground ?water|\bwells?\b|lake|pond|marsh ?water|"
                   r"sonde|\bmanta\b|\bexo\b|sensor ?data|water ?chemistry|water ?quality|precipitation|throughfall|"
                   r"pore ?water|lysimeter|rhizon", re.I)
SOILISH = re.compile(r"soil|sediment|peat|core|horizon|pit\b|profile", re.I)
# Model input / output rather than measurements (file or sheet name).
MODEL = re.compile(r"model|simulat|scenario|\boutput|_output|predict|forcing|ensemble|\bcorpse\b|corpse_|"
                   r"\bclm\b|\belm\b|spin.?up|parameter|\bfit\b|fitted", re.I)
# Molecular formula tables (FT-ICR-MS, metabolomics): C, H, O, N ... are atom counts, not concentrations.
FORMULA_FILE = re.compile(r"fticr|ft.?icr|emeta|formula|metabol|peak|\bms_|_ms\b|mass.?spec|lipid|nmr", re.I)
FORMULA_COLS = re.compile(r"^(mass|calibrated.?mass|m/?z|formula|mol.?form|class|dbe|ai_?mod|nosc|kmd|o.?c|h.?c|error.?ppm)$", re.I)
# The file name alone no longer skips a table (user decision 2026-10-13). It skipped sample tables that only sit in an
# FT-ICR folder or carry "FTICR" in their name: doi:10.15485/1868940 FTC_FTICR_master.zip/.../emsl_cn.csv (93 soil %C
# and %N), soil properties, horizon and NEON biogeochemistry tables; WHONDRS ..._NPOC_FTICR.csv (per-sample NPOC,
# doi:10.15485/1729719, 1969118). A named file is skipped when it also has formula-derived columns: many processed
# FT-ICR tables have no H / O atom counts ('Mass, formula, HC, OC', 'Mass, Class, HC, OC, NOSC'), and their 'OC'
# (O:C ratio) would be read as organic carbon. These columns count only with the name, since a soil table can have a
# 'Mass' (sample mass) column. Dry run: of 51 files skipped by name only, 24 stay skipped and 27 are read.
FORMULA_DERIVED = re.compile(r"^(mass|calibrated.?mass|m/?z|formula|mol.?form)$", re.I)


def _formula_table(df: pd.DataFrame) -> bool:
    """Tell whether a table is a molecular-formula table (atom counts C, H, O, N ... with H and O present).

    Examples:
        >>> _formula_table(pd.DataFrame(columns=["Mass", "C", "H", "O", "N"])), _formula_table(pd.DataFrame(columns=["C", "N", "S", "P"]))
        (True, False)
    """
    cols = {str(c).strip().lstrip("\ufeff") for c in df.columns}
    atoms = len(cols & {"C", "H", "O", "N", "S", "P"})
    # H and O counts only appear in formula tables (soils report C, N, S, P but never H and O)
    return {"H", "O"} <= cols and (atoms >= 4 or any(FORMULA_COLS.match(c) for c in cols))


def _derived_formula_table(df: pd.DataFrame) -> bool:
    """Tell whether a table has formula-derived columns (a mass / formula column, or both H:C and O:C).

    Used only for files whose name is a formula file (FORMULA_FILE).

    Examples:
        >>> _derived_formula_table(pd.DataFrame(columns=["Mass", "formula", "HC", "OC"]))
        True
        >>> _derived_formula_table(pd.DataFrame(columns=["site", "material", "n_perc", "c_perc"]))
        False
    """
    cols = [str(c).strip().lstrip("\ufeff") for c in df.columns]
    return (any(FORMULA_DERIVED.match(c) for c in cols)
            or (any(re.fullmatch(r"h.?c", c, re.I) for c in cols) and any(re.fullmatch(r"o.?c", c, re.I) for c in cols)))


# Element columns of a composition table: an element symbol, then '_', ' ', '(' or the end ('Ca_wt_percent', 'Fe (%)').
ELEMENT_COL = re.compile(r"^(?-i:(" + "|".join(sorted((e for e in units.MOLAR_MASS if re.fullmatch(r"[A-Z][a-z]?", e)),
                                                        key=len, reverse=True)) + r"))(?=[_ (]|$)")


def _normalized_composition(df: pd.DataFrame) -> bool:
    """Tell whether a table is a normalized element composition: >= 5 element columns whose rows sum to 100 %.

    Such a table gives each element's share of the measured elements, not its concentration (user decision 2026-10-13:
    WHONDRS_S19S_Sediment_XRF_ElementalAbundance.csv, doi:10.15485/1729719, sums to 100 % over 11 elements: Si median
    58 %, Ca up to 57 %, Al mostly 0). Sand + silt + clay tables are not affected: they are not element columns.

    Examples:
        >>> t = pd.DataFrame({"Si_wt_percent": [60, 55, 58], "Ca_wt_percent": [20, 25, 20], "Fe_wt_percent": [15, 15, 17],
        ...                   "Mg_wt_percent": [3, 3, 3], "Al_wt_percent": [2, 2, 2]})
        >>> _normalized_composition(t), _normalized_composition(t * 0.5)
        (True, False)
    """
    cols = [c for c in df.columns if ELEMENT_COL.match(str(c).strip())]
    if len(cols) < 5:
        return False
    x = df[cols].apply(num)
    x = x.where(x >= 0)
    rows = x.notna().sum(axis=1) >= 3
    if rows.sum() < 3:
        return False
    total = x[rows].sum(axis=1)
    return bool(((total - 100).abs() <= 1).mean() >= 0.9)


# Value columns that hold statistics or flags, not measurements (any variable). The sample count is a lower-case
# 'n' only: 'N', '%N', 'Total N' are nitrogen.
# 'pC' / 'pN' next to 'plignin', 'phemicellulose', 'psoluble', 'pash' are percent C / N of plant material (litter
# added in doi:10.15485/1835182 Cbud.csv), not soil (2026-10-12). Lignin or cellulose columns alone do not mark a table
# as plant material: peat characteristics (SPRUCE.005) and soil polymer tables have them.
PROXIMATE = re.compile(r"^p(lignin|hemicellulose|cellulose|soluble|ash)$", re.I)
PROXIMATE_ELEMENT = re.compile(r"^p[CN]$")
STATS = re.compile(r"std|stdev|st\.? ?dev|\bsd\b|_sd$|\bse\b|_se$|stderr|std ?err|error|uncert|\bci\b|flag|\bqc\b|"
                   r"(?-i:\bn\b|_n$)|count|deviation|precision|(?<![a-z])sd(?![a-z])|\b(lower|upper)\b|effect.?size|"
                   r"\bcube|transform|residual|detection|\bmdl\b|\blld\b|\bdl\b|_dl$|\brsd\b|\bcv\b|percentile|quantile", re.I)
# Replicate readings next to their average: only the average is used.
AVERAGE = re.compile(r"^(avg|average|mean)\b|[ _.](avg|average|mean)$", re.I)
REPLICATE = re.compile(r"data.?\d+$|rep(licate)?.?\d+$|\br\d+$|[ _.-]\d$|\brun.?\d+$", re.I)


def _same(a: pd.Series, b: pd.Series) -> bool:
    """Tell whether two value columns hold the same values (within 1 %) on at least 90 % of the rows where both are filled.

    Examples:
        >>> a = pd.Series([1.0, 2.0, 3.0, 4.0]); _same(a, a * 1.005), _same(a, a * 10)
        (True, False)
    """
    both = a.notna() & b.notna()
    if both.sum() < max(3, 0.5 * a.notna().sum()):
        return False
    x, y = a[both], b[both]
    return float((((x - y).abs() <= 0.01 * y.abs().clip(lower=1e-9)) | (x == y)).mean()) >= 0.9


# Sheets with summaries or calculations rather than sample rows.
SUMMARY_SHEET = re.compile(r"summary|calc|average|\bmeans?\b|stat", re.I)
# 'fig' followed by a digit or '.' too (2026-10-13): doi:10.15485/1766328 sheets "Fig2a. Relative Conc.", "Fig3a. TN (%)"
# were read as data and wrote pH and total sulfur.
FIGURE_SHEET = re.compile(r"chart|plot|fig(ure)?(\b|\d|\.)|figure|pivot|graph", re.I)   # always skipped
MEDIUM = {"salt_extraction": "salt extract", "water_extraction": "water extract", "porewater": "porewater"}


@dataclass
class Result:
    """The outcome of harmonizing one variable in one package.

    Attributes:
        doi: The package DOI.
        key: The variable key.
        table: The harmonized table, or None.
        status: 'written' or 'review'.
        reasons: Why tables, columns or rows were skipped, or why the package went to review.
        location: Location groups used, joined with '+'.
        columns: '<source file>:<column>' of the columns used.
        assumed_unit: The unit of a column was assumed (not stated in the source).
    """
    doi: str
    key: str
    table: pd.DataFrame | None = None
    status: str = "review"                 # written / review
    reasons: list[str] = field(default_factory=list)
    location: str = ""                     # location groups used
    columns: list[str] = field(default_factory=list)
    assumed_unit: bool = False


@lru_cache(maxsize=512)
def _dictionary(doi: str) -> tuple[dict[str, str], dict[str, str]]:
    """Read a package's data dictionaries: ({column name (lower case): unit}, {column name: definition}) (cached)."""
    units_: dict[str, str] = {}
    defs: dict[str, str] = {}
    for file, sheet in dictionary_tables(doi, headers()):
        try:
            t = read_table(file, sheet).data
        except Exception:  # noqa: BLE001
            continue
        name = next((c for c in t.columns if re.search(r"column|field|variable|attribute|parameter|header", c, re.I)), None)
        unit = next((c for c in t.columns if re.search(r"unit", c, re.I)), None)
        define = next((c for c in t.columns if re.search(r"defin|descri", c, re.I)), None)
        if not name:
            continue
        for k, row in t.iterrows():
            a = str(row[name]).strip().lower()
            if a and unit and row[unit]:
                units_.setdefault(a, str(row[unit]).strip())
            if a and define and row[define]:
                defs.setdefault(a, str(row[define]).strip())
    return units_, defs


def _dictionary_units(doi: str) -> dict[str, str]:
    """Read the units of a package's data dictionaries: {column name (lower case): unit}."""
    return _dictionary(doi)[0]


def _wanted(column: str, cfg: VarConfig, name: str, group: str = "", unit: str = "", definition: str = "") -> bool:
    """Tell whether a matched column passes the variable's column_exclude and require patterns.

    column_exclude is tried on the column name, its group row and its data dictionary definition; require on those,
    its unit and the file / sheet name.

    Examples:
        >>> cfg = VarConfig(column_exclude="fraction.?modern|fm$", require="")
        >>> _wanted("Fraction Modern", cfg, "c14.csv"), _wanted("D14C", cfg, "c14.csv")
        (False, True)
        >>> _wanted("Ca", VarConfig(require="exch|meq|cmol"), "XRF.csv", group="XRF (%)")
        False
    """
    if cfg.get("column_exclude") and any(re.search(cfg["column_exclude"], x, re.I) for x in (column, group, definition) if x):
        return False
    if cfg.get("require") and not re.search(cfg["require"], f"{column} {group} {unit} {definition} {name}", re.I):
        return False
    return True


PER_LITRE = re.compile(r"(?i)(mg|ug|µg|umol|µmol|mmol|nmol)[ _/.]?(per[ _])?l\b|(mg|ug)l$|per[ _]?lit")


def _per_litre(df: pd.DataFrame, units_row: dict[str, str]) -> bool:
    """Tell whether a table reports solution concentrations: a column name or unit is per litre ('oxymgL', 'mg/L').

    Examples:
        >>> _per_litre(pd.DataFrame(columns=["Sample", "oxymgL", "Fe_ppb"]), {})
        True
        >>> _per_litre(pd.DataFrame(columns=["Sample", "Fe_ppm"]), {"Fe_ppm": "ppm"})
        False
    """
    return any(PER_LITRE.search(str(c)) or PER_LITRE.search(units_row.get(c, "")) for c in df.columns)


MATERIAL_COL = re.compile(r"(?i)^(sample_?type|sample_?matrix|material|matrix|media|medium|sample_?material)$")
METHOD_COL = re.compile(r"(?i)extraction|digest|treatment|fraction|method")
# 'liquid' / 'aqueous' since 2026-10-13: doi:10.15485/1969118 Material "Liquid>aqueous" (surface water NPOC, written as
# soil DOC).
NOT_SOIL = re.compile(r"(?i)gas|water|co2|ch4|air|atmos|rain|snow|rock|leaf|leaves|plant|root|litter|wood|needle|"
                      r"grass|ring|emission|stream|river|liquid|aqueous")


# Lab manipulations of field samples (user decision 2026-10-13). A treatment column (name: treatment, trt, trtmt,
# condition, amendment, or incub / burn / amend / manipul) is a lab manipulation when its levels name one
# (incubation, saturation, burn, autoclaved ...) or its name does and the package text names one. Only the levels of the
# field condition are kept (control, unburned, ambient, field, and time zero / initial / pre-incubation); a lab column
# without such a level sends the column to review. A treatment column whose levels do not change the value of one sample
# only labels repeated rows (incubation jars, DNA libraries) and one row per sample is kept. Field experiments (warming
# plots, throughfall exclusion, FACE) are untouched: their treatments are not lab manipulations. Found with
# doi:10.15485/1959350 (cores burned in the lab under a cone calorimeter; 470 rows, 94 core x horizon values of which ~30
# unburned controls, each repeated over 5 incubation / library rows). A level named in a lab sentence of the text is
# not enough (2425968: in situ warming is discussed with lab incubations), nor is 'drought' (field drought plots).
TREAT_COL = re.compile(r"(?i)^(.*[_. ])?(treat(ment)?s?|trt|trtmt|trmt|manipulation|condition|amendments?)([_. ].*)?$")
LAB_NAME = re.compile(r"(?i)incub|burn|amend|manipul")
LAB_TEXT = re.compile(r"(?i)incubat|microcosm|mesocosm|\bjars?\b|burn simulation|simulated (burn|fire|drought|rain)|"
                      r"cone calorimeter|autoclav|inoculat|column experiment|amended in the lab|spiked|freeze.?thaw cycles|"
                      r"rewet|dry.?down|laboratory (experiment|treatment|manipulation)")
LAB_VALUE = re.compile(r"(?i)incubat|saturat|burn|autoclav|inocul|amend|spike|freeze|thaw|rewet|dry.?down|\bjar")
FIELD_FIRST = re.compile(r"(?i)time.?zero|\binitial\b|\bt_?0\b|\bday.?0\b|\bpre[- ]?(incub|burn|treat|wet)")
FIELD_LEVEL = re.compile(r"(?i)^\s*(control|ctrl|ctl|con|fm|unburn(ed|t)?|un.?treated|unamended|ambient|none|"
                         r"no.?(treatment|addition|amendment)|field|baseline|native|reference)\s*$|\bcontrol\b|\bunburn")
MISSING_LEVEL = re.compile(r"(?i)\s*(na|n/a|-9999|nan|none)?\s*")


def _count_column(df: pd.DataFrame, col: str, name: str) -> bool:
    """Tell whether a bare 'N' column is a sample count: whole numbers in a table of statistics.

    A table of statistics has mean +- sd cells, statistics columns (sd, se, stdev ...) or 'summary' / 'mean' / 'average'
    in its file or sheet name (2026-10-13: doi:10.15485/1785525 wsoc_soils_summary.csv 'N' = 5 replicates, next to
    '0.78 +- 0.1', was written as total nitrogen 5 %).

    Examples:
        >>> _count_column(pd.DataFrame({"N": ["5", "5"], "WSOC": ["0.78 ± 0.1", "0.69 ± 0.07"]}), "N", "x.csv")
        True
        >>> _count_column(pd.DataFrame({"N": ["0.3", "0.2"], "C": ["4", "3"]}), "N", "x.csv")
        False
    """
    if col.strip() not in ("N", "n"):
        return False
    v = df[col][df[col].str.strip() != ""].str.strip()
    if not len(v) or not v.str.fullmatch(r"\d+").all():
        return False
    stats = (df.astype(str).apply(lambda s: s.str.contains("±")).to_numpy().any()
             or any(STATS.search(str(c)) for c in df.columns if c != col)
             or bool(re.search(r"(?i)summary|mean|average", name)))
    return bool(stats)


def _level_kind(level: str) -> str:
    """Tell whether a lab treatment level is the field condition ('field', kept) or a manipulation ('lab').

    Examples:
        >>> [_level_kind(v) for v in ["control", "dry", "Time Zero Saturation", "Drought Incubation", "Ambient"]]
        ['field', 'lab', 'field', 'lab', 'field']
    """
    if FIELD_FIRST.search(level):
        return "field"
    if LAB_VALUE.search(level):
        return "lab"
    return "field" if FIELD_LEVEL.search(level) else "lab"


def _treatment_columns(df: pd.DataFrame) -> list[str]:
    """Treatment-like columns: a treatment name, 2-12 levels that are mostly text and not yes / no."""
    out = []
    for c in df.columns:
        if not (TREAT_COL.match(str(c)) or LAB_NAME.search(str(c))):
            continue
        v = df[c][~df[c].map(lambda x: bool(MISSING_LEVEL.fullmatch(str(x))))]
        if 1 < v.nunique() <= 12 and v.str.contains("[A-Za-z]").mean() >= 0.8 \
                and not v.str.fullmatch(r"(?i)y(es)?|no?|true|false").all():
            out.append(c)
    return out


def _sample_key(df: pd.DataFrame, col: str) -> pd.Series | None:
    """Return the sample of each row without the level of `col`.

    An id column is cut at the level's token ('...-A-pb-cDNA' and '...-A-LIn' -> '...-A'); None when no id column
    carries the levels.
    """
    lv = df[col].astype(str)
    for c in df.columns:
        if c == col:
            continue
        ids = df[c].astype(str)
        cut = [re.split(rf"[-_. ]{re.escape(level)}(?=$|[-_. ])", i, maxsplit=1)[0] if level else i
               for i, level in zip(ids, lv)]
        if (pd.Series(cut, index=df.index) != ids).mean() >= 0.5:
            return pd.Series(cut, index=df.index)
    return None


def _field_rows(df: pd.DataFrame, value_cols: list[str], doi: str) -> tuple[pd.DataFrame, str, str]:
    """Keep the field-condition rows of a table with lab manipulations, and one row per repeated sample.

    Returns:
        The rows kept, a note for the written rows ('' when nothing was dropped), and a review reason ('' unless a
        lab treatment column has no field-condition level; the table is then emptied).

    Examples:
        >>> df = pd.DataFrame({"id": ["s1-A", "s1-B", "s2-A", "s2-B"], "burn.trtmt": ["control", "dry", "control", "wet"],
        ...                    "C": ["5", "2", "6", "9"]})
        >>> kept, note, review = _field_rows(df, ["C"], "")
        >>> kept.C.tolist(), note
        (['5', '6'], 'lab treatment rows dropped (burn.trtmt: dry 1, wet 1); kept control')
    """
    text_lab = bool(LAB_TEXT.search(package_text(doi))) if doi else True
    notes: list[str] = []
    repeat_cols = []
    for c in _treatment_columns(df):
        levels = df[c][~df[c].map(lambda x: bool(MISSING_LEVEL.fullmatch(str(x))))].value_counts()
        lab = any(LAB_VALUE.search(str(v)) for v in levels.index) or (bool(LAB_NAME.search(str(c))) and text_lab)
        if not lab:
            continue
        key = _sample_key(df, c)
        if key is not None and value_cols:
            g = pd.DataFrame({"key": key, "lev": df[c], **{v: df[v] for v in value_cols if v in df}})
            per = g.groupby("key").agg(nlev=("lev", "nunique"), **{f"n_{v}": (v, "nunique") for v in value_cols if v in df})
            per = per[per.nlev > 1]
            if len(per) and all((per[f"n_{v}"] == 1).mean() >= 0.9 for v in value_cols if v in df):
                repeat_cols.append((c, key))
                continue
        kinds = {v: _level_kind(str(v)) for v in levels.index}
        kept = [str(v) for v, k in kinds.items() if k == "field"]
        if not kept:
            return df.iloc[:0], "", (f"lab treatment column {c} without a field-condition level "
                                     f"({', '.join(map(str, levels.index[:6]))}); not written")
        drop = df[c].map(lambda x: kinds.get(x) == "lab")
        if drop.any():
            dropped = ", ".join(f"{v} {int(n)}" for v, n in df[c][drop].value_counts().items())
            notes.append(f"lab treatment rows dropped ({c}: {dropped}); kept {', '.join(kept)}")
            df = df[~drop]
    for c, key in repeat_cols:
        rep_rows = df.assign(_key=key.reindex(df.index)).duplicated(["_key", *[v for v in value_cols if v in df]])
        if rep_rows.any():
            notes.append(f"{int(rep_rows.sum())} rows repeating one sample across {c} levels dropped")
            df = df[~rep_rows]
    return df, "; ".join(notes), ""


def _soil_rows(df: pd.DataFrame, cfg: VarConfig) -> tuple[pd.DataFrame, str]:
    """Keep the soil rows of a table that mixes sample materials, and drop rows of an excluded extraction.

    Rows whose sample-type / material value names another material (gas, water, rock, leaves ...) are dropped; a
    table with only such rows is emptied. Rows whose extraction / treatment / method value matches the variable's column_exclude are
    dropped (exchangeable rows for total elements).

    Returns:
        The rows kept and a note ('' when nothing was dropped).

    Examples:
        >>> df = pd.DataFrame({"Sample_Type": ["Soil", "Rock", "Lupin leaves"], "Fe": ["1", "2", "3"]})
        >>> kept, note = _soil_rows(df, VarConfig())
        >>> len(kept), note
        (1, '2 rows of other sample types (Sample_Type) dropped')
        >>> _soil_rows(pd.DataFrame({"material": ["soil pore gas"], "x": ["1"]}), VarConfig())[0].empty
        True
        >>> _soil_rows(pd.DataFrame({"material": ["NA", "liquid>aqueous", "liquid>aqueous"], "x": ["1", "5", "6"]}),
        ...            VarConfig())[0].empty
        True
        >>> len(_soil_rows(pd.DataFrame({"material": ["", "", "water"], "x": ["1", "2", "3"]}), VarConfig())[0])
        2
    """
    notes = []
    for c in [c for c in df.columns if MATERIAL_COL.match(str(c))]:
        v = df[c].astype(str)
        if v.str.strip().eq("").all():
            continue
        soil = ~v.str.contains(NOT_SOIL)          # only rows that name another material are dropped
        # rows without a material that are left after dropping more rows of other materials are metadata rows, not
        # samples (2026-10-13): doi:10.15485/1875296 has 469 'liquid>aqueous' rows and 9 reporting-format header rows
        # (unit, unitBasis ... analysisDetectionLimit) with material 'NA'; the detection-limit row (1) was written as
        # 1 % total carbon. A table that leaves the material blank for most of its soil rows keeps them.
        missing = v.str.strip().str.upper().isin({"", "NA", "N/A", "NAN", "NONE", "-9999"})
        if not soil.all() and (soil & ~missing).sum() == 0 and (soil & missing).sum() < (~soil).sum():
            soil = soil & ~missing
        if not soil.all():
            notes.append(f"{int((~soil).sum())} rows of other sample types ({c}) dropped" if soil.any()
                         else f"no soil samples ({c}: {', '.join(v.drop_duplicates().head(3))})")
            df = df[soil]
    ex = cfg.get("column_exclude")
    if ex and not df.empty:
        for c in [c for c in df.columns if METHOD_COL.search(str(c)) and df[c].astype(str).str.contains("[A-Za-z]").any()]:
            drop = df[c].astype(str).str.contains(ex, case=False, regex=True)
            if drop.any() and not drop.all():
                notes.append(f"{int(drop.sum())} rows of an excluded {c} dropped")
                df = df[~drop]
    return df.reset_index(drop=True), "; ".join(notes)


def _element(v: Variable) -> str | None:
    """Return the element of a variable for mole / charge conversions.

    Uses variable_config's element, else the element in the short key (Ca for Caexch).
    """
    el = config().get(v.key, {}).get("element")
    if el:
        return el
    for e in sorted(units.MOLAR_MASS, key=len, reverse=True):
        if v.short.startswith(e) and (len(v.short) == len(e) or not v.short[len(e)].islower()):
            return e
    return None


# sentences that do not give the method of a bulk-soil measurement: dissolved / extracted / gas carbon (DOC analyzers,
# 'combustion catalytic oxidation'), water quality ('water temperature, and pH', WHONDRS protocols), micro-imaging
# ('μ-XRF imaging ... of Ca', 2350835) and compound-specific lipids ('13C value of methylated fatty acid', 2483574).
# Applied to the sentences found by the loose patterns below and to every sentence of a package document.
NOT_BULK = re.compile(r"(?i)dissolved|extract|leach|pore ?water|water.?soluble|filtrate|surface water|stream water|"
                      r"soil solution|\bin solution\b|\b(DOC|DIC|DON|TDN|WSOC|WEOC)\b|\bgas(es)?\b|\bCO2\b|\bCH4\b|efflux|headspace|"
                      r"water (quality|temperature|samples?|column)|turbidity|alkalinity|salinity|\bORP|"
                      r"\bwater_?ph\b|ph of (the )?(surface )?water|"
                      r"imaging|micro-?x-?ray|μ-?XRF|XANES|microprobe|\bPLFA|fatty acid|\bFAME|n-alkane|lipid")


def _method_sentence_patterns(key: str) -> tuple[list[str], list[str]]:
    """Patterns of the sentences that name a variable, searched for its method: (strict, loose).

    Strict: the short name or the name; for a 'Total X' variable also a coordinated phrase ('total organic and
    inorganic carbon', doi:10.15485/1630815) and 'total' + the element symbol ('total C and N were determined by
    combustion', 1959350). Loose, for a 'Total X' variable with an element: the element named without 'total' ('%C and
    %N on an Elemental Analyzer', 1894515; 'analyzed for C and N concentrations', 'carbon concentration', 1839288;
    'nitrogen and carbon on a Vario EL Cube', 1868940; 'percent carbon', NGT/1810164);
    a loose sentence about dissolved, extracted or gas carbon is not used (NOT_BULK). User decisions 2026-10-13.

    Examples:
        >>> strict, loose = _method_sentence_patterns("Carbon__Total_carbon")
        >>> [bool(re.search(strict[1], s, re.I)) for s in ("Total organic and inorganic carbon were determined",
        ...                                                "Total C and N were measured", "total N and S")]
        [True, False, False]
        >>> [any(re.search(p, s, re.I) for p in loose) for s in ("%C and %N were measured", "analyzed for C and N",
        ...      "carbon concentrations were measured", "N and S contents", "pH 7 was measured")]
        [True, True, True, False, False]
    """
    v = VARIABLES[key]
    strict = [r"\b(" + re.escape(v.short) + "|" + re.escape(v.name) + r")\b"]
    loose: list[str] = []
    m = re.fullmatch(r"(?i)total (\w+)", v.name)
    if m:
        word = m.group(1)
        strict.append(rf"\btotal\W+(?:\w+\W+){{0,2}}and\W+\w+\W+{word}\b")
        el = config().get(key, {}).get("element")
        if el:
            e = rf"(?-i:{re.escape(el)})"
            strict.append(rf"\btotal\W+{e}\b")
            loose = [rf"%\s?{e}\b", rf"(?<![\w-]){e}\s*(and|&|,|/)\s*%?(?-i:[A-Z][a-z]?)\b",
                     rf"\b%?(?-i:[A-Z][a-z]?)\s*(and|&|,|/)\s*%?{e}\b(?![\w-])",
                     rf"\b({word}|{e})\s+(and\s+\w+\s+)?(concentration|content)s?\b", rf"\b(for|of)\s+{e}\b(?![\w-])",
                     # the element as a word in a list: 'nitrogen and carbon', 'carbon (C) and nitrogen (N)',
                     # 'Total nitrogen, carbon, and sulfur' (1868940, 1346200, 1773008); 'percent carbon' (NGT/1810164)
                     rf"\b{word}\b(\s*\([^)]{{1,12}}\))?\s*(,|and\b|&)", rf"(\band|&|,)\s+{word}\b",
                     rf"\bpercent\s+{word}\b|\b{word}\s+percent\b"]
    return strict, loose


def _sentences(text: str) -> list[str]:
    """Split text into sentences (also on line breaks; not on ' | ', which joins the parts of a metadata field)."""
    return [s for s in re.split(r"(?<=[.;])\s+|\n", text) if s.strip()]


MAX_DOC_SENTENCE = 500   # longer 'sentences' of a document are table rows run together


def _methods_in(key: str, text: str, rules: list, document: bool = False, clause_only: bool = False) -> set[str]:
    """The methods whose patterns occur in the sentences of a text that name the variable.

    In a package document (document=True) only sentences of at most MAX_DOC_SENTENCE characters count, and none about
    dissolved, extracted, pore-water or gas samples ('Porewater pH throughout a 2 m soil profile', spruce.043;
    'acidified to pH 2 ... prior solid phase extraction', 2529428).
    """
    strict, loose = _method_sentence_patterns(key)
    sents = [s for s in _sentences(text) if not (document and (len(s) > MAX_DOC_SENTENCE or NOT_BULK.search(s)))]
    # 'N/A' (a missing-value code in dictionaries) is not the element pair 'N / A'
    sents = [s for s in sents if any(re.search(p, s, re.I) for p in strict)
             or (any(re.search(p, re.sub(r"\bN/A\b", "", s), re.I) for p in loose) and not NOT_BULK.search(s))]
    found: set[str] = set()
    for s in sents:
        if clause_only:   # a cited paper: only the clause naming the variable ('the soil bulk density, porosity, ...'
            #               is no porosity method, 2298998)
            found |= {m for c in _clauses(s, strict + loose) for rx, m in rules if rx and re.search(rx, c, re.I)}
            continue
        here = {m for rx, m in rules if rx and re.search(rx, s, re.I)}
        if len(here) > 1:   # several methods in one sentence: those in the clause that names the variable
            near = {m for c in _clauses(s, strict + loose) for rx, m in rules if rx and re.search(rx, c, re.I)}
            here = near or here
        found |= here
    return found


def _clauses(sentence: str, patterns: list[str]) -> list[str]:
    r"""The clauses of a sentence that name the variable: between ',' ';' '|' outside parentheses.

    doi:10.15485/1577267 'soil pH measurements (1:1 w/vol in ddH2O), dissolved nitrogen pools measured in soil extracts
    (2M KCl extractant)' gives pH in water, not KCl (user decision 2026-10-14).

    Examples:
        >>> _clauses("soil pH measurements (1:1 w/vol in ddH2O), N pools in extracts (2M KCl)", [r"\bpH\b"])
        ['soil pH measurements (1:1 w/vol in ddH2O)']
    """
    parts, depth, start = [], 0, 0
    for i, ch in enumerate(sentence):
        depth += (ch == "(") - (ch == ")")
        if ch in ",;|" and depth <= 0:
            parts.append(sentence[start:i])
            start, depth = i + 1, 0
    parts.append(sentence[start:])
    return [c.strip() for c in parts if any(re.search(p, c, re.I) for p in patterns)]


def method_for(key: str, column: str, doi: str, definition: str = "") -> tuple[str, str]:
    """Find the method of a value column.

    The variable's method patterns (variable_config.csv) are tried, in order, on the column name, on its data
    dictionary definition ('Soil carbon from combustion analyzer', doi:10.15485/2588765), on the sentences of the
    package text that name the variable, on those of the package's own documents (user guides, methods files,
    documents.package_documents), and last on the papers the package cites, once downloaded (papers.py). The first source with exactly one method gives it; several methods in one source
    give the default (or 'unknown'). User decision 2026-10-13 for the dictionary and the documents.

    Args:
        key: The variable key.
        column: The column name.
        doi: The package DOI.
        definition: The column's data dictionary definition.

    Returns:
        The method and a note ('' or where it was found).

    Examples:
        >>> method_for("Acidity__Soil_pH", "pH_CaCl2", "doi:10.0/x")
        ('pH_CaCl2', '')
        >>> method_for("Carbon__Total_carbon", "pC", "doi:10.0/x", "Soil carbon from combustion analyzer")
        ('dry_combustion', 'method from the data dictionary')
    """
    rules = config().get(key, {}).get("methods", [])
    default = next((m for rx, m in rules if not rx), None)
    for rx, m in rules:
        if rx and re.search(rx, column, re.I):
            return m, ""
    if definition:
        found = {m for rx, m in rules if rx and re.search(rx, definition, re.I)}
        if len(found) == 1:
            return found.pop(), "method from the data dictionary"
    found = _methods_in(key, package_text(doi), rules)
    if len(found) == 1:
        return found.pop(), "method from the package description"
    if not found:
        per_doc = [(name, _methods_in(key, text, rules, document=True)) for name, text in package_documents(doi)]
        per_doc = [(name, f) for name, f in per_doc if f]
        found = set().union(*(f for _, f in per_doc)) if per_doc else set()
        if len(found) == 1:
            return found.pop(), f"method from {per_doc[0][0]}"
    if not found:   # last: papers the package cites, downloaded after the user approved them (papers.py)
        per_paper = [(cited, _methods_in(key, text, rules, document=True, clause_only=True))
                     for cited, text in paper_texts(doi)]
        per_paper = [(cited, f) for cited, f in per_paper if f]
        found = set().union(*(f for _, f in per_paper)) if per_paper else set()
        if len(found) == 1:
            return found.pop(), f"method from cited paper doi:{per_paper[0][0]}"
    if default:
        return default, ""
    return UNKNOWN, ("several methods described in the package" if len(found) > 1 else "")


def _method_column(df: pd.DataFrame, column: str, short: str) -> str | None:
    """The column naming the method of each row of a value column ('TC Method' for total_carbon, 1342956), if any.

    Examples:
        >>> _method_column(pd.DataFrame({"total_carbon": [], "TC Method": []}), "total_carbon", "TC")
        'TC Method'
    """
    rx = re.compile(rf"(?i)^({re.escape(column)}|{re.escape(short)})[ _.]?method$")
    return next((c for c in df.columns if rx.match(str(c))), None)


def _medium(method: str, unit: str) -> str:
    """Return the medium of an extract or solution from its method, else from its unit.

    Examples:
        >>> _medium("salt_extraction", "mg C kg-1 dry soil"), _medium("unknown", "mg C L-1")
        ('salt extract', 'solution (per volume)')
    """
    if method in MEDIUM:
        return MEDIUM[method]
    return "solution (per volume)" if re.search(r"L-1|/L\b", unit) else "soil extract"


def harmonize(key: str, doi: str) -> Result:
    """Harmonize one variable in one package (see the module docstring).

    Args:
        key: The variable key.
        doi: The package DOI.

    Returns:
        The result: the harmonized table when written, the reasons otherwise.

    Examples:
        >>> r = harmonize("Acidity__Soil_pH", "doi:10.15485/1725884")  # doctest: +SKIP
        >>> r.status, len(r.table), r.location  # doctest: +SKIP
        ('written', 21, '1')
    """
    v, cfg = VARIABLES[key], config().get(key, {})
    res = Result(doi, key)
    m = matched_columns(key, [doi])
    m = m[m.strength == "strong"]
    if m.empty:
        res.reasons.append("no strong column match")
        return res
    frames, groups = [], set()
    # the same table as CSV and Excel (same name): use the CSV
    text_ext = re.compile(r"\.(csv|txt|tsv|tab)$", re.I)
    stems = {text_ext.sub("", f) for f in m.file if text_ext.search(f)}
    m = m[~m.file.map(lambda f: bool(re.search(r"\.xlsx?$", f, re.I)) and re.sub(r"\.xlsx?$", "", f, flags=re.I) in stems)]
    # summary sheets are skipped only when the variable is also found in another table
    all_summary = all(bool(sh) and bool(SUMMARY_SHEET.search(sh)) for sh in m.sheet)
    for keys, g in m.groupby(["file", "sheet"], sort=False):
        file, sheet = str(keys[0]), str(keys[1])
        if sheet and FIGURE_SHEET.search(sheet):
            res.reasons.append(f"{source_name(file)} [{sheet}]: skipped, figure sheet")
            continue
        if sheet and SUMMARY_SHEET.search(sheet) and not all_summary:
            res.reasons.append(f"{source_name(file)} [{sheet}]: skipped, summary sheet")
            continue
        try:
            t = read_table(file, sheet)
        except Exception as e:  # noqa: BLE001
            res.reasons.append(f"{source_name(file)}: cannot read ({type(e).__name__})")
            continue
        # a block after a blank row with another column layout has no header of its own: its values sit under the
        # first block's names (tables.stacked_blocks; user decision 2026-10-13, doi:10.15485/2405147)
        blocks = stacked_blocks(t.data)
        if blocks:
            stacked = [i for a, b, _ in blocks for i in range(a, b + 1)]
            for a, b, ch in blocks:
                res.reasons.append(f"{source_name(file)}{f' [{sheet}]' if sheet else ''}: rows {a + 1}-{b + 1} skipped, "
                                   f"stacked block with another column layout ({ch:.0%} of columns)")
            t = replace(t, data=t.data.drop(index=t.data.index[stacked]).reset_index(drop=True))
        name = f"{source_name(file)} {sheet}"
        if (WATER.search(name) or (re.search(r"water", name, re.I) and WATER.search(title(doi)))) and not SOILISH.search(name):
            res.reasons.append(f"{source_name(file)}: skipped, water data (file name)")
            continue
        if _formula_table(t.data) or (FORMULA_FILE.search(name) and _derived_formula_table(t.data)):
            res.reasons.append(f"{source_name(file)}: skipped, molecular formula table (atom counts)")
            continue
        if _normalized_composition(t.data):
            res.reasons.append(f"{source_name(file)}: skipped, normalized element composition (rows sum to 100 %)")
            continue
        hit = re.search(cfg["exclude_files"], name, re.I) if cfg.get("exclude_files") else None
        # plant terms (litter, root, leaf ...) do not exclude a file that is also about soil; fraction and water terms
        # ('Soil_Pore_Water') always do
        if hit and not (re.search(r"soil", name, re.I)
                        and not re.search(r"frac|density|aggregate|water|lysimeter|rhizon|peeper|^[pg]w$", hit.group(0), re.I)):
            res.reasons.append(f"{source_name(file)}: skipped, file not used for this variable ({cfg['exclude_files']})")
            continue
        if MODEL.search(name):
            res.reasons.append(f"{source_name(file)}: skipped, model input or output (file name)")
            continue
        value_cols = [c for c in dict.fromkeys(g.column) if c in t.data.columns and not STATS.search(c)]
        counts = [c for c in value_cols if _count_column(t.data, c, name)]
        for c in counts:
            res.reasons.append(f"{source_name(file)}: {c} skipped, a sample count (whole numbers in a table of statistics)")
        value_cols = [c for c in value_cols if c not in counts]
        if not value_cols:
            res.reasons.append(f"{source_name(file)}: matched column not found when reading")
            continue
        if any(PROXIMATE.match(str(c)) for c in t.data.columns):
            plant = [c for c in value_cols if PROXIMATE_ELEMENT.match(c)]
            for c in plant:
                res.reasons.append(f"{source_name(file)}: {c} skipped, plant-material proximate analysis (plignin ...)")
            value_cols = [c for c in value_cols if c not in plant]
            if not value_cols:
                continue
        # skip_repeated: a name repeated in the table (numbered '.1', '.2' on reading) is the same quantity under
        # several treatments (extraction steps of total elements): none of the copies is taken
        repeated = {c for c in value_cols if cfg.get("skip_repeated") and f"{re.sub(r'[.]\d+$', '', c)}.1" in t.data.columns}
        for c in repeated:
            res.reasons.append(f"{source_name(file)}: {c} skipped, column name repeated in the table (several treatments)")
        value_cols = [c for c in value_cols if c not in repeated]
        if not value_cols:
            continue
        defs = _dictionary(doi)[1]
        unwanted = [c for c in value_cols if not _wanted(c, cfg, name, (t.groups or {}).get(c, ""), t.units.get(c, ""),
                                                         defs.get(c.lower(), ""))]
        for c in unwanted:
            res.reasons.append(f"{source_name(file)}: {c} skipped, not this variable (column_exclude / require)")
        value_cols = [c for c in value_cols if c not in unwanted]
        if not value_cols:
            continue
        avg = [c for c in value_cols if AVERAGE.search(c)]
        if avg and any(REPLICATE.search(c) for c in value_cols):
            value_cols = [c for c in value_cols if c in avg or not REPLICATE.search(c)]
        df, row_note = _soil_rows(t.data, cfg)
        if df.empty:
            res.reasons.append(f"{source_name(file)}: skipped, {row_note}")
            continue
        if row_note:
            res.reasons.append(f"{source_name(file)}: {row_note}")
        df, field_note, review = _field_rows(df, value_cols, doi)
        if review:
            res.reasons.append(f"{source_name(file)}: {review}")
            continue
        if field_note:
            res.reasons.append(f"{source_name(file)}: {field_note}")
        f = detect(df, skip=set(value_cols))
        ts = "" if cfg.get("time_series") else time_series(df, f)
        if ts:
            res.reasons.append(f"{source_name(file)}: skipped, time series ({df[ts].nunique()} timestamps in {ts})")
            continue
        loc = locate(doi, df, f, file, sheet)
        if loc is None:
            res.reasons.append(f"{source_name(file)}: no location")
            continue
        dep, dep_note = depths(df, f, t.units)
        dt = dates(df, f)
        # no date column: the package's temporal coverage when it falls within one day, month or year (2566016,
        # 'collected in October 2019', coverage 2019-10-01 to 2019-10-30 -> 2019-10)
        date_note = ""
        if all(x == "" for x in dt) and coverage_date(doi):
            dt, date_note = [coverage_date(doi)] * len(df), f"date {coverage_date(doi)} from package temporal coverage"
        # ids unique over the rows with a value: id columns, then depth, then date (fields.ids)
        has_value = pd.concat([~is_missing(df[c].astype(str).str.strip()) for c in value_cols], axis=1).any(axis=1)
        idv, id_type, id_note = ids(df, f, dep, dt, has_value, skip=set(value_cols))
        src = source_name(file) + (f" [{sheet}]" if sheet else "")
        kept: list[str] = []
        kept_vals: list[pd.Series] = []
        for col in value_cols:
            vals = num(df[col])
            if vals.notna().sum() == 0:
                continue
            if any(vals.equals(num(df[k])) for k in kept):  # same values under another name
                continue
            assumed = False
            if cfg.get("unitless"):
                unit, where = None, ""
            else:
                el = _element(v)
                unit, where = unit_of(col, t.units.get(col, ""), _dictionary_units(doi).get(col.lower(), ""),
                                      v.units, group=(t.groups or {}).get(col, ""), text=package_text(doi), molar_mass=units.MOLAR_MASS.get(el) if el else None,
                                      valence=units.VALENCE.get(el) if el else None)
                if unit is None and cfg.get("assume_unit"):
                    # a bare element symbol without a unit is only used in a table that looks like soil samples
                    ttl = title(doi)
                    soil_table = bool(f.top or f.depth or f.horizon or SOILISH.search(name)
                                      or (SOILISH.search(ttl) and not WATER.search(ttl)))
                    if re.fullmatch(r"[A-Z][a-z]?", col.strip()) and not soil_table:
                        res.reasons.append(f"{src}: bare symbol {col} without a unit in a table without soil sample fields")
                        continue
                    # the first assumed unit in which >= 90 % of the values are plausible (after conversion)
                    lo, hi = cfg.get("min"), cfg.get("max")
                    x = vals.dropna()
                    for assume in cfg["assume_unit"].split("|"):
                        try:
                            f_try = target_unit(key, assume)[1]
                        except units.UnitError:
                            continue
                        inside = ((x * f_try >= (lo if lo is not None else -float("inf")))
                                  & (x * f_try <= (hi if hi is not None else float("inf")))).mean()
                        if inside >= 0.9:
                            unit, where, assumed = assume, "assumed (not stated in the source)", True
                            break
                if unit is None and cfg.get("assume_unit"):
                    res.reasons.append(f"{src}: unit of {col} not stated and the values are not plausible in "
                                       f"{cfg['assume_unit'].replace('|', ' or ')}")
                    continue
                if unit is None:
                    res.reasons.append(f"{src}: unit of {col} not found")
                    continue
                if re.fullmatch(r"(?i)\s*pp[mb]\s*", unit) and _per_litre(df, t.units):
                    # ppm / ppb in a table of solution concentrations are mg L-1 / ug L-1, not mass fractions
                    unit = "mg L-1" if unit.strip().lower() == "ppm" else "ug L-1"
                    where += "; ppm / ppb read as per litre (table of solution concentrations)"
            try:
                el = _element(v)
                std, fac = target_unit(key, unit, molar_mass=units.MOLAR_MASS.get(el) if el else None,
                                       valence=units.VALENCE.get(el) if el else None)
            except units.UnitError as e:
                res.reasons.append(f"{src}: {col}: {e}")
                continue
            conv = vals * fac
            # a stated unit whose converted values are mostly outside the plausible range is wrong (user decision
            # 2026-10-13: doi:10.15485/1868940 'clay.gg' holds percent, 21.78, but its name says g/g, which gave
            # 2,178 %); the column goes to review instead of being written. An assumed unit was already checked.
            lo, hi = cfg.get("min"), cfg.get("max")
            x = conv.dropna()
            if not assumed and len(x) and (lo is not None or hi is not None):
                out = ((x < (lo if lo is not None else -float("inf"))) | (x > (hi if hi is not None else float("inf")))).mean()
                if out > 0.5:
                    res.reasons.append(f"{src}: {col} skipped, {out:.0%} of values outside the plausible range "
                                       f"{lo:g}-{hi:g} {std or ''}"
                                       + (f" in the stated unit {unit} (unit from {where}); check the unit" if unit else
                                          "; check the column"))
                    continue
            if any(_same(conv, k) for k in kept_vals):  # same quantity in another unit (C_percent, Carbon_mg/g)
                continue
            kept_vals.append(conv)
            method, mnote = method_for(key, col, doi, defs.get(col.lower(), ""))
            # a per-row method column ('TC Method'): its values give the method where they match a method pattern;
            # other values (instrument program codes 'SOIL 0.20', 1342956) are copied into the notes of their rows
            mcol = _method_column(df, col, v.short)
            methods, row_notes = [method] * len(df), [""] * len(df)
            if mcol:
                for i, x in enumerate(df[mcol].astype(str).str.strip()):
                    if x and not is_missing(pd.Series([x])).iloc[0]:
                        row_method: str | None = next((m for rx, m in cfg.get("methods", [])
                                                       if rx and re.search(rx, x, re.I)), None)
                        methods[i], row_notes[i] = ((row_method, f"method from {mcol}") if row_method
                                                    else (method, f"{mcol}: {x}"))
            parts = [f"source column {col}" + (f" ({unit}, unit from {where})" if unit else ""),
                     units.conversion_note(unit, std, fac) if unit and fac != 1 else "", dep_note, date_note, id_note, mnote, field_note]
            note = "; ".join(p for p in parts if p)
            b = pd.DataFrame({
                "doi": doi, "source_file": src, "id": idv, "id_type": id_type, "depth": dep, "date": dt,
                "value": [("" if pd.isna(x) else f"{x * fac:.10g}") for x in vals], "method": methods,
                # (0, 0) is a missing-value placeholder, not a location
                "latitude": [("" if a is None or pd.isna(a) or (a == 0 and b == 0) else f"{a:.6g}")
                             for a, b in zip(loc.lat, loc.lon)],
                "longitude": [("" if b is None or pd.isna(b) or (a == 0 and b == 0) else f"{b:.7g}")
                              for a, b in zip(loc.lat, loc.lon)],
                "IGSN": list(df[f.igsn]) if f.igsn else "",
                "notes": [f"{n}; {note}" + (f"; {r}" if r else "") for n, r in zip(loc.note, row_notes)],
                "source_row": range(1, len(df) + 1)})
            if v.unit_column:
                b[v.unit_column] = std
            for c in v.extra:
                if c.endswith("_medium"):
                    b[c] = _medium(method, std)
                elif c == "analyte":    # one row per fraction / phase: the source column names it
                    b[c] = col
            frames.append(b)
            kept.append(col)
            groups.add(loc.group)
            res.columns.append(f"{src}:{col}")
            res.assumed_unit |= assumed
    if not frames:
        res.reasons = res.reasons or ["no usable rows"]
        return res
    raw = pd.concat(frames, ignore_index=True)
    # the same samples in several files (subsets, copies for 16S / ITS ...): keep the first occurrence. Within one file
    # too: a sample's value repeated on every row of a time series (1185213 incubations: pH on each time point)
    dup = raw.duplicated(["id", "depth", "date", "value", "method"]) & (raw["value"] != "")
    if dup.any():
        res.reasons.append(f"{int(dup.sum())} rows repeated in another file dropped")
        raw = raw[~dup]
    # a whole table repeated in a later file under other sample ids: drop that file
    # A later file also goes when an earlier kept file is mostly inside it (user decision 2026-10-13): in
    # doi:10.15485/2588765, CN_data.csv (104 %C values, replicates within 10 m averaged) is repeated in
    # ldw_dat_raw.csv (126 values, unaveraged) under other IDs; 85 samples have the same plot coordinates and %C, but
    # that is only 70% of the raw file, so the first test missed it and both were written (230 rows). The coordinates
    # are not in the files (one metadata point for all rows), so the test cannot ask for in-file coordinates. The
    # overlap must be 80% of the smaller file and half of the larger one, so that a small file whose few values
    # happen to occur in a large file is not taken as a copy. The earlier file is kept, as for exact repeats.
    filled = raw[raw["value"] != ""]
    sig = filled[["depth", "date", "value", "latitude", "longitude"]].astype(str).agg("|".join, axis=1)
    seen: set[str] = set()
    kept_sigs: list[set[str]] = []
    drop: list[str] = []
    for src_file in filled.source_file.drop_duplicates():
        s = set(sig[filled.source_file == src_file])
        if (seen and len(s & seen) >= 0.8 * len(s)) or any(
                len(s & k) >= 0.8 * min(len(s), len(k)) and len(s & k) >= 0.5 * max(len(s), len(k)) for k in kept_sigs):
            drop.append(src_file)
        else:
            seen |= s
            kept_sigs.append(s)
    if drop:
        res.reasons.append("repeated table dropped: " + "; ".join(drop))
        raw = raw[~raw.source_file.isin(drop)]
    key_cols = ["id", "date", "depth", "method", "source_file"]
    extra = ["source_row"] if raw[raw["value"] != ""].duplicated(key_cols).any() else []
    table = assemble(raw, key, extra)
    if table.empty:
        res.reasons.append("no rows with both a value and coordinates")
        return res
    res.table, res.status, res.location = table, "written", "+".join(sorted(groups))
    return res


__all__ = ["Result", "harmonize", "method_for", "is_missing"]
