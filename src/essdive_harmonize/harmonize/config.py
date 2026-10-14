"""Set the paths and settings of the generic harmonization workflow.

Attributes:
    PROJECT_ROOT: The repository root.
    VARIABLE_INPUT: data/soil_variable_list_input.csv; its select column chooses the variables.
    VARIABLE_LIST: data/soil_variable_list.csv: unit, specification and abbreviation of each variable.
    VARIABLE_CONFIG: variable_config.csv next to this module: per-variable settings.
    OUT_ROOT: data/processed/harmonization, the outputs.
    EVIDENCE: evidence.csv of the package selection.
    HEADERS: The column-header cache of the package selection.
    TRIAGE: triage.csv, the package-level keep / exclude review.
    EXCLUDE_CATEGORIES: Categories not harmonized (porewater metals, user decision 2026-10-07; fluxes and
        incubations, user decision 2026-10-09).
    SOIL_TERMS: A package counts as soil when its soil_context has one of these terms.
    PLANT_TERMS: A package with one of these exclusion_terms and no "soil" in its soil_context is not soil.
    MAX_TABLE_ROWS: Rows read per data table.
    META_DIR: The per-package metadata files.
    PACKAGE_DATA: The downloaded package files.
    SELECTION_DIR: Outputs of the package selection.
    HEADERS_CACHE: File name of the header cache.
"""

from pathlib import Path

from ..download_files import META_DIR, OUT_DIR as PACKAGE_DATA
from ..selection.config import HEADERS_CACHE, OUT_DIR as SELECTION_DIR

PROJECT_ROOT = Path(__file__).resolve().parents[3]
VARIABLE_INPUT = PROJECT_ROOT / "data" / "soil_variable_list_input.csv"     # select column: which variables
VARIABLE_LIST = PROJECT_ROOT / "data" / "soil_variable_list.csv"            # unit, specification, abbreviation
VARIABLE_CONFIG = Path(__file__).with_name("variable_config.csv")           # plausible range per variable
OUT_ROOT = PROJECT_ROOT / "data" / "processed" / "harmonization"
EVIDENCE = SELECTION_DIR / "evidence.csv"
HEADERS = SELECTION_DIR / HEADERS_CACHE
TRIAGE = Path(__file__).resolve().parents[1] / "triage.csv"                 # package-level keep/exclude review

# Variables of these categories are not harmonized (user decisions 2026-10-07 and 2026-10-09).
EXCLUDE_CATEGORIES = {"Porewater metals (dissolved)", "Fluxes and incubations"}
# A package counts as soil when its soil_context (selection/soil.py) has one of these terms.
SOIL_TERMS = {"soil", "sediment", "peat", "permafrost", "horizon"}
# Plant terms of the selection's exclusion_terms. A package with one of them and no "soil" in its soil_context is not
# soil: permafrost or peat alone often comes from project text (user decision 2026-10-12, doi:10.15485/3933967 leaf C).
PLANT_TERMS = {"leaf", "leaves", "foliar", "foliage", "needle", "needles", "stem", "stems", "wood", "woody", "plant",
               "plants", "vegetation", "root", "roots", "litter", "tissue", "bole"}

MAX_TABLE_ROWS = 200000     # rows read per data table

__all__ = ["META_DIR", "PACKAGE_DATA", "SELECTION_DIR", "PROJECT_ROOT", "VARIABLE_INPUT", "VARIABLE_LIST",
           "VARIABLE_CONFIG", "OUT_ROOT", "EVIDENCE", "HEADERS", "TRIAGE", "EXCLUDE_CATEGORIES", "SOIL_TERMS",
           "PLANT_TERMS", "MAX_TABLE_ROWS"]
