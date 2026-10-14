"""Convert harmonized values between units.

Units are parsed into a factor and a dimension vector, so any two units with the same dimensions convert directly
('mg kg-1' -> '%', 'g m-2' -> 'kg m-2', 'ug L-1' -> 'mg L-1', 'Mg ha-1' -> 'kg m-2'). Amounts in moles or charge
equivalents convert to mass when a molar mass (and a valence) is given ('mmol kg-1' Fe -> 'mg kg-1',
'mg kg-1' Ca -> 'cmol(+) kg-1').

Accepted spellings include 'mg kg-1', 'mg/kg', 'mg kg^-1', 'mg C kg-1 dry soil', 'umol g-1', 'µmol/g',
'cmol(+) kg-1', 'meq/100g', '%', 'ppm', 'ppb', 'per mil', 'g cm-3', 'nmol CH4 m-2 s-1', 'mg m-2 h-1', 'dS m-1',
'W m-1 K-1' and the molar concentrations 'M', 'mM', 'uM', 'nM'. Element or species tags (C, N, P, S, CH4, NO3-N ...)
and words such as 'dry soil' are ignored. A bare element symbol after a unit is always a tag, so 'mg Mg kg-1',
'mg K kg-1' and 'mg S kg-1' parse as mg kg-1, while a leading 'Mg' is megagrams ('Mg ha-1') and 'K-1', 'dS' keep their
unit meaning. A unit written together with its element ('gC', 'mgN', 'umolCO2') is the unit. ppm and ppb are mass
fractions (mg kg-1, ug kg-1); for water samples pass 'mg L-1' / 'ug L-1'.

Examples:
    >>> round(factor("mg/kg", "%"), 10)
    0.0001
    >>> factor("Mg ha-1", "kg m-2")
    0.1
    >>> round(factor("cmol(+) kg-1", "mg kg-1", molar_mass=MOLAR_MASS["Ca"], valence=VALENCE["Ca"]), 3)
    200.39

Attributes:
    Dims: Dimension exponents of a unit, e.g. ``{'mass': 1, 'length': -3}`` for g cm-3.
    PREFIX: SI prefixes and their factors ('' = no prefix).
    BASE: Base units: factor to an SI-like base and dimensions.
    DIMENSIONLESS: Dimensionless units and their factors ('%' = 0.01).
    ALIASES: Whole-unit spellings replaced before parsing ('meq/100g' -> 'cmol(+) kg-1').
    EXTRA_PREFIXED: Prefixed units the prefix table does not cover (hectogram, for mg/100 g).
    MOLAR_MASS: Molar masses in g/mol: elements of the soil variable list and the nutrient forms reported "as N",
        "as P", "as S".
    VALENCE: Charge of the exchangeable cations, for cmol(+) conversions.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Final, TypeAlias

Dims: TypeAlias = dict[str, int]

PREFIX: Final[dict[str, float]] = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "c": 1e-2, "d": 1e-1, "": 1.0, "k": 1e3, "M": 1e6, "G": 1e9}
# base unit -> (factor to SI-like base, dimensions)
BASE: Final[dict[str, tuple[float, Dims]]] = {
    "g": (1.0, {"mass": 1}),
    "mol": (1.0, {"amount": 1}),
    "eq": (1.0, {"charge": 1}),
    "L": (1e-3, {"length": 3}),
    "l": (1e-3, {"length": 3}),
    "m": (1.0, {"length": 1}),
    "ha": (1e4, {"length": 2}),
    "s": (1.0, {"time": 1}),
    "sec": (1.0, {"time": 1}),
    "min": (60.0, {"time": 1}),
    "h": (3600.0, {"time": 1}),
    "hr": (3600.0, {"time": 1}),
    "d": (86400.0, {"time": 1}),
    "day": (86400.0, {"time": 1}),
    "yr": (3.15576e7, {"time": 1}),
    "S": (1.0, {"conductance": 1}),
    "W": (1.0, {"power": 1}),
    "K": (1.0, {"temperature": 1}),
}
DIMENSIONLESS: Final[dict[str, float]] = {"%": 1e-2, "percent": 1e-2, "ppm": 1e-6, "ppb": 1e-9, "permil": 1e-3, "ratio": 1.0,
                 "fraction": 1.0, "unitless": 1.0, "pH": 1.0, "BP": 1.0}
# whole-unit spellings tried before token parsing
ALIASES: Final[dict[str, str]] = {
    "meq/100g": "cmol(+) kg-1", "meq 100g-1": "cmol(+) kg-1", "meq/100 g": "cmol(+) kg-1", "meq100g": "cmol(+) kg-1",
    "meq 100 g-1": "cmol(+) kg-1",
    "mmol(+)/kg": "mmol(+) kg-1", "mmolc/kg": "mmol(+) kg-1", "cmolc/kg": "cmol(+) kg-1",
    "g/100g": "%", "g/100 g": "%", "wt%": "%", "wt.%": "%", "wt-%": "%", "wt %": "%", "weight %": "%", "weight%": "%", "weight percent": "%", "% w/w": "%", "mass %": "%",
    "mg/100g": "mg hg-1", "mg/100 g": "mg hg-1",
    "g/cc": "g cm-3", "g/cm3": "g cm-3", "g/cm^3": "g cm-3", "kg/m3": "kg m-3",
    "ms/cm": "mS cm-1", "us/cm": "uS cm-1", "ds/m": "dS m-1",
    "per mil": "permil", "per mille": "permil", "‰": "permil", "o/oo": "permil",
    "years bp": "yr", "years": "yr", "year": "yr", "yr bp": "yr", "14c yr bp": "yr",
    "m3/m3": "m3 m-3", "cm3/cm3": "cm3 cm-3", "v/v": "m3 m-3",
}
EXTRA_PREFIXED: Final[dict[str, tuple[float, Dims]]] = {"hg": (0.1e3, {"mass": 1})}  # hectogram, for mg/100 g


class UnitError(ValueError):
    """Raised when a unit cannot be parsed or two units cannot be converted."""


def _norm(u: str) -> str:
    """Normalize a unit spelling: micro signs, superscripts, per mil, molar units and whole-unit aliases.

    Examples:
        >>> _norm("µmol/g")
        'umol/g'
        >>> _norm("mM")
        'mmol L-1'
        >>> _norm("meq/100g")
        'cmol(+) kg-1'
        >>> _norm("milligrams_of_N_per_gram"), _norm("µg.g-1"), _norm("mg-N/g-soil"), _norm("ug N g soil-1")
        ('mg N/g', 'ug g-1', 'mg N/g soil', 'ug N g-1')
    """
    u = str(u).strip().replace("µ", "u").replace("μ", "u").replace("−", "-").replace("^", "")
    u = re.sub(r"[\ufffd?](?=g|mol|L|m)", "u", u)  # a micro sign lost in a bad encoding (U+FFFD or '?')
    u = u.replace("⁻¹", "-1").replace("⁻²", "-2").replace("⁻³", "-3").replace("²", "2").replace("³", "3")
    u = re.sub(r"\s+", " ", u)
    u = re.sub(r"(?i)per\s?mill?e?|‰|o/oo", "permil", u)
    # written-out units: 'milligrams_of_N_per_gram' -> 'mg N/g'
    for rx, short in ((r"micrograms?", "ug"), (r"milligrams?", "mg"), (r"kilograms?", "kg"), (r"grams?", "g"),
                      (r"micromol(es)?", "umol"), (r"millimol(es)?", "mmol"), (r"lit(er|re)s?", "L")):
        u = re.sub(rf"(?i)(?<![A-Za-z]){rx}(?![A-Za-z])", short, u.replace("_", " "))
    u = re.sub(r"(?i)\s+of\s+", " ", u)
    u = re.sub(r"(?i)\s+per\s+", "/", u)
    u = re.sub(r"(?<=[A-Za-z])[.-](?=[A-Za-z])", " ", u)  # 'ug.g-1', 'mg-N/g-soil'
    u = re.sub(r"(?i)\s+(dry\s+)?(soil|sediment|dw)(?=-1\b)", "", u)  # 'g soil-1' -> 'g-1'
    m = re.fullmatch(r"([munp]?)M", u)  # molar: M, mM, uM, nM (case-sensitive; 'mm' stays millimetre)
    if m:
        return f"{m.group(1)}mol L-1"
    low = u.lower()
    for k in sorted(ALIASES, key=len, reverse=True):
        if low == k:
            return ALIASES[k]
    return u


def _token(tok: str) -> tuple[float, Dims] | None:
    """Parse one token of a unit, with an optional exponent.

    Args:
        tok: One space-separated part of a normalized unit, e.g. 'kg-1' or 'cmol(+)'.

    Returns:
        The factor and dimensions of the token, or None when it is not a unit (a species tag or a word).

    Examples:
        >>> _token("kg-1")
        (0.001, {'mass': -1})
        >>> _token("soil") is None
        True
    """
    m = re.fullmatch(r"([A-Za-z%]+)(\(\+\)|c)?(-?\d)?", tok)
    if not m:
        return None
    sym, charge, exp = m.group(1), m.group(2), int(m.group(3) or 1)
    if not charge and sym.endswith("molc"):  # 'mmolc', 'cmolc' (the letters ran together)
        sym, charge = sym[:-1], "c"
    if sym in DIMENSIONLESS and exp == 1:
        return DIMENSIONLESS[sym], {}
    if charge:  # cmol(+), cmolc: moles of charge = equivalents
        if not sym.endswith("mol"):
            return None
        sym = sym[:-3] + "eq"
    for p, pf in PREFIX.items():
        base = sym[len(p):] if sym.startswith(p) else None
        if base is None or not base:
            continue
        if base in BASE:
            f, dims = BASE[base]
            return (pf * f) ** exp, {k: v * exp for k, v in dims.items()}
    if sym in EXTRA_PREFIXED:
        f, dims = EXTRA_PREFIXED[sym]
        return f ** exp, {k: v * exp for k, v in dims.items()}
    return None


def parse(unit: str) -> tuple[float, Dims]:
    """Parse a unit into a factor and dimension exponents.

    Args:
        unit: The unit as written in the source, e.g. 'mg C kg-1 dry soil', 'g/cm3' or 'cmol(+) kg-1'.

    Returns:
        The factor relative to the SI-like base units and the non-zero dimension exponents.

    Raises:
        UnitError: When nothing in `unit` is a unit.

    Examples:
        >>> f, dims = parse("g/cm3")
        >>> round(f), dims
        (1000000, {'mass': 1, 'length': -3})
        >>> parse("mg C kg-1 dry soil")
        (1e-06, {})
        >>> parse("gC cm-3")[1]
        {'mass': 1, 'length': -3}
        >>> parse("soil")
        Traceback (most recent call last):
            ...
        essdive_harmonize.units.UnitError: cannot parse unit 'soil'
    """
    u = _norm(unit)
    u = re.sub(r"\((?!\+\))[^)]*\)", " ", u)  # drop remarks such as '(dry soil)', keep cmol(+)
    if "/" in u:  # 'mg/kg' -> 'mg kg-1'; 'umol/m2/s' -> 'umol m-2 s-1'
        parts = u.split("/")
        den = []
        for p in parts[1:]:
            for t in p.split():
                m = re.fullmatch(r"(.*?)(\d)?", t)
                assert m is not None  # the pattern matches any token
                den.append(f"{m.group(1)}-{m.group(2) or 1}")
        u = parts[0] + " " + " ".join(den)
    factor, found = 1.0, False
    dims: Counter[str] = Counter()
    for tok in u.replace("*", " ").replace("·", " ").split():
        if found and tok.rstrip("-+") in MOLAR_MASS:
            continue  # element tag after a unit: 'mg Mg kg-1', 'mg K kg-1', 'mg S kg-1' (not Mg, K, S units)
        # unit written together with its element or species: 'gC' -> 'g', 'mgN' -> 'mg', 'umolCO2' -> 'umol'
        m = re.fullmatch(r"([pnumcdkMG]?(?:g|mol|eq))(C|N|P|S|CH4|CO2|N2O|NO3|NH4|PO4|SO4|[A-Z][a-z]?)(-?\d)?", tok)
        if m and m.group(2) in MOLAR_MASS | {"CH4": 0, "CO2": 0, "N2O": 0, "NO3": 0, "NH4": 0, "PO4": 0, "SO4": 0}:
            tok = m.group(1) + (m.group(3) or "")
        parsed = _token(tok)
        if parsed is None:
            continue  # species tag (C, N, CH4) or word (dry, soil)
        found = True
        factor *= parsed[0]
        dims.update(parsed[1])
    if not found:
        raise UnitError(f"cannot parse unit {unit!r}")
    return factor, {k: v for k, v in dims.items() if v}


def factor(src: str, dst: str, molar_mass: float | None = None, valence: float | None = None) -> float:
    """Return the multiplier that converts values in one unit to another.

    Args:
        src: Unit of the source values.
        dst: Target unit.
        molar_mass: Molar mass in g/mol; needed when one unit is in moles and the other in mass.
        valence: Charge of the ion; needed when one unit is in charge equivalents (cmol(+)) and the other is not.

    Returns:
        The factor f such that a value in `src` times f is the value in `dst`.

    Raises:
        UnitError: When a unit cannot be parsed, the dimensions differ, or a molar mass or valence is missing.

    Examples:
        >>> factor("g/kg", "%")
        0.1
        >>> factor("mM", "mg C L-1", molar_mass=12.011)
        12.011
        >>> factor("C/g", "%")
        Traceback (most recent call last):
            ...
        essdive_harmonize.units.UnitError: incompatible units 'C/g' -> '%'
        >>> factor("mmol kg-1", "mg kg-1")
        Traceback (most recent call last):
            ...
        essdive_harmonize.units.UnitError: mmol kg-1 -> mg kg-1 needs a molar mass
    """
    fs, ds = parse(src)
    fd, dd = parse(dst)
    cs, cd = Counter(ds), Counter(dd)
    f = fs / fd

    def move(a: str, b: str) -> None:  # dimension a -> b on both sides
        for d in (cs, cd):
            d[b] += d[a]
            d[a] = 0

    if cs["charge"] != cd["charge"]:  # 1 eq = 1/valence mol
        if not valence:
            raise UnitError(f"{src} -> {dst} needs a valence")
        f *= (1 / valence) ** (cs["charge"] - cd["charge"])
        move("charge", "amount")
    if cs["amount"] != cd["amount"]:  # 1 mol = molar_mass g
        if not molar_mass:
            raise UnitError(f"{src} -> {dst} needs a molar mass")
        f *= molar_mass ** (cs["amount"] - cd["amount"])
        move("amount", "mass")
    # compare every non-zero exponent ('+Counter' would drop the negative ones: g-1 would equal %)
    if {k: v for k, v in cs.items() if v} != {k: v for k, v in cd.items() if v}:
        raise UnitError(f"incompatible units {src!r} -> {dst!r}")
    return f


def convertible(src: str, dst: str, **kw: float | None) -> bool:
    """Tell whether values in one unit can be converted to another.

    Args:
        src: Unit of the source values.
        dst: Target unit.
        **kw: `molar_mass` and `valence`, as for `factor`.

    Returns:
        True when `factor(src, dst, **kw)` succeeds.

    Examples:
        >>> convertible("ug/g", "mg kg-1")
        True
        >>> convertible("g cm-3", "%")
        False
    """
    try:
        factor(src, dst, **kw)
        return True
    except UnitError:
        return False


def fmt_factor(f: float) -> str:
    """Format a conversion factor with up to six significant digits.

    Examples:
        >>> fmt_factor(0.00010000000000000002)
        '0.0001'
    """
    return f"{f:.6g}"


def conversion_note(src: str, dst: str, f: float) -> str:
    """Describe a unit conversion for the notes column.

    Args:
        src: Unit of the source values.
        dst: Target unit.
        f: The conversion factor (`factor(src, dst)`).

    Returns:
        'converted from <src> to <dst> (x <f>)', or '' when no scaling is involved (the same unit spelled
        differently).

    Examples:
        >>> conversion_note("g/kg", "%", 0.1)
        'converted from g/kg to % (x 0.1)'
        >>> conversion_note("mg/kg", "mg kg-1", 1.0)
        ''
    """
    return "" if math.isclose(f, 1.0) else f"converted from {src} to {dst} (x {fmt_factor(f)})"


# g/mol; elements of the soil variable list plus the nutrient forms reported "as N", "as P", "as S"
MOLAR_MASS: Final[dict[str, float]] = {
    "H": 1.008, "Li": 6.94, "Be": 9.0122, "C": 12.011, "N": 14.007, "O": 15.999, "Na": 22.990, "Mg": 24.305,
    "Al": 26.982, "Si": 28.085, "P": 30.974, "S": 32.06, "Cl": 35.45, "K": 39.098, "Ca": 40.078, "Ti": 47.867,
    "Cr": 51.996, "Mn": 54.938, "Fe": 55.845, "Co": 58.933, "Ni": 58.693, "Cu": 63.546, "Zn": 65.38,
    "Ga": 69.723, "Ge": 72.630, "As": 74.922, "Se": 78.971, "Rb": 85.468, "Sr": 87.62, "Zr": 91.224,
    "Mo": 95.95, "Ag": 107.87, "Cd": 112.41, "Sn": 118.71, "Sb": 121.76, "Cs": 132.91, "Ba": 137.33,
    "La": 138.91, "Ce": 140.12, "Nd": 144.24, "Hg": 200.59, "Tl": 204.38, "Pb": 207.2, "Th": 232.04,
    "U": 238.03,
    "NO3": 62.004, "NH4": 18.038, "PO4": 94.971, "SO4": 96.06, "CH4": 16.043, "N2O": 44.013, "CO2": 44.009,
}
VALENCE: Final[dict[str, int]] = {"Ca": 2, "Mg": 2, "K": 1, "Na": 1, "Al": 3, "Fe": 2, "Mn": 2, "H": 1, "S": 2}  # S: sulfate
