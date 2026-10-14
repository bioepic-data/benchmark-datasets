"""Define the matching rules for the soil variables: one Spec per variable name of soil_variable_list_input.csv.

The rules are copied from the two scripts that built and counted the soil variable list:

- CARBON: the ten carbon specs of notebooks/find_soil_variable_candidates.py (strong / related patterns on
  normalized column names and on metadata text, with shared exclusions).
- R: the rules of notebooks/soil_variable_list/05_count_packages.py, (column regex, column exclusion, text regex,
  restriction) on the raw column text; bare element symbols are case-sensitive.

Rows of the list that were edited after those scripts are mapped here: "Soil pH" takes the union of the four pH
rules (MERGED), and "Dissolved <element> in soil porewater" takes the porewater trace-metal rule restricted to its
element. The restrictions of 05_count_packages.py, which used hand-checked package lists, are replaced by tests on
each package's own metadata and column headers (see datatypes.Restriction and spec_for): no package is selected or
excluded by name.

Examples:
    >>> spec = spec_for("Soil pH")
    >>> [bool(rc.search("pH_CaCl2")) for rc, _ in spec.raw_rules]
    [False, True, False, False]

Attributes:
    CARBON: The graded carbon specs, by short key.
    R: The list rules, by variable name.
    CARBON_KEYS: Short key of each carbon variable.
    MERGED: List rows that take the union of several rules.
    EXC_CTX: Context of exchangeable cations (CEC, base saturation, NH4OAc ...).
    PORE_CTX: Context of porewater (lysimeter, rhizon, soil solution ...).
    SOLID_CTX: Context of soil / sediment samples.
    ENZYME_CTX: Context of enzyme assays.
    MEHLICH_CTX: Context of Mehlich-3 extractions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, NotRequired, TypedDict

from .datatypes import ColumnRule, Mode, Pattern, RawRule, Restriction


class CarbonSpec(TypedDict):
    """A graded carbon spec of notebooks/find_soil_variable_candidates.py.

    Attributes:
        name: Variable name.
        text_strong: Metadata text patterns for strong matches.
        text_related: Metadata text patterns for related matches.
        col_strong: Patterns on normalized column names for strong matches.
        col_related: Patterns on normalized column names for related matches.
        col_strong_cased: Case-sensitive patterns on the column name (code prefix dropped, not lower-cased) for strong
            matches, for names whose case carries the meaning ('pC' is percent carbon, 'Pc' is not).
        col_exclude: Columns matching this are dropped unless col_rescue matches.
        col_hard_exclude: Columns matching this are always dropped.
        col_rescue: Keeps an excluded column.
    """
    name: str
    text_strong: list[str]
    text_related: list[str]
    col_strong: list[str]
    col_related: list[str]
    col_strong_cased: NotRequired[list[str]]
    col_exclude: NotRequired[str]
    col_hard_exclude: NotRequired[str]
    col_rescue: NotRequired[str]


# ----------------------------------------------------------------------------------------------------------------
# Carbon specs (notebooks/find_soil_variable_candidates.py)
# ----------------------------------------------------------------------------------------------------------------
SOIL_CONTEXT = (r"\bsoils?\b|sediment|peat|permafrost|core|horizon|active\s+layer|"
                r"mineral\s+layer|organic\s+layer|pore\s*water")

# --------------------------------------------------------------------------
# Column patterns shared by all variables.
# Column names are normalized before matching: lower case, "_" and "." -> " ".
# --------------------------------------------------------------------------
# Never a measurement column, regardless of variable.
COMMON_HARD_EXCLUDE = (r"\bsd\b|std|stdev|standard deviation|stderr|\bse\b|\bmdl\b|\blld\b|flag|"
                       r"\bqc\b|\bqa\b|\bunc|error|\bmth\b|\bdate\b|analy[sz]ed\b|"
                       r"\bcsv\b|\bxlsx?\b|setpoint|threshold|\bsite\b|"
                       r"resp\b|respir|co2|ch4|flux|mineraliz|dissolution|\brate\b|"
                       r"\babs ?\d|suva|fluoresc|gibbs|energy|\btsoil\b|\bt soil\b")
# Not this measurement unless the variable's rescue pattern says otherwise.
COMMON_EXCLUDE = (r"temp|°c|deg c|degc|celsius|"
                  r"method|note|comment|\bid\b|identifier|latitude|longitude|\bloc\b|"
                  r"leaf|foliar|needle|stem|wood|plant|veg")
ISOTOPE = r"13c|14c|δ|delta|d13|d14|isotop|\bfm\b|fraction modern"
WATERS = r"stream|river|surface water|groundwater|well\b"
# Exclusion patterns use (?<!concent)ratio, not ratio: "concentration" contains "ratio", which dropped every
# "... concentration" column (e.g. 'Carbon concentration', doi:10.15485/1839288; fixed 2026-10-12).
# Concentration per volume of liquid: water chemistry, not a solid-phase soil measurement.
PER_LITRE = r"\b(m|u|µ|n)?(g|mols?|m) ?(/ ?|per ?)?l\b|l-1\b"

# --------------------------------------------------------------------------
# Variable specs
#   text_strong / text_related : regexes for keywords + description
#   col_strong  / col_related  : regexes for normalized column names
#   col_exclude                : drop a column match unless col_rescue also matches
#   col_hard_exclude           : always drop
# --------------------------------------------------------------------------
CARBON: dict[str, CarbonSpec] = {
    "TC": CarbonSpec(
        name="Total carbon",
        text_strong=[
            # NOTE (2026-10-13, potential fix, not applied): also matches non-soil "total carbon": doi:10.3334/CDIAC/TCM.011
            # (energy use and CO2 emissions from cropland) defines "total carbon" as on-site + off-site energy carbon.
            # Harmless (text evidence only, no data column), so no fix proposed.
            r"total\s+(soil\s+)?carbon",
            r"total\s+C\b",
            # NOTE (2026-10-12, potential fix, not applied): also matches the instrument "TC/EA" (thermal conversion
            # elemental analyzer, for d18O / dD): doi:10.15485/1596123 (tree-ring cellulose and water isotopes) was
            # selected for Total carbon from "pyrolysis-GC-IRMS using a TC/EA". Fix: r"\bTC\b(?!\s*/\s*EA)" (tested:
            # skips "TC/EA", keeps "TC (%)", "TC content", "total carbon (TC)"). Applying it changes matrix_any.csv;
            # rerun selection.
            # NOTE (2026-10-13, potential fix, not applied): also matches author initials in reference lists:
            # doi:10.5440/1728709 (geophysical monitoring, Teller) from "Johnson TC, Versteeg RJ, Ward A, et al
            # (2010)", and doi:10.5440/1559886 (soil thermal and electrical properties) from a citation in its methods.
            # Neither has a carbon column. Fix: case-sensitive and not after a capitalized surname,
            # r"(?-i:(?<![A-Z][a-z]+ )\bTC\b)"; or drop text matches inside reference lists.
            r"\bTC\b",
            r"soil\s+carbon\s+content",
            # NOTE (2026-10-12, potential fix, not applied): also matches "dissolved carbon concentrations" (water):
            # doi:10.15485/1601290 (bedrock weathering, borehole porewater) was selected from "dissolved carbon
            # concentrations were determined with a TOC-LCPN instrument". Fix: r"(?<!dissolved\s)carbon\s+concentration"
            # (tested: skips "dissolved carbon concentrations", keeps "carbon concentration (%)", "soil carbon
            # concentration"). Applying it changes matrix_any.csv; rerun selection.
            r"carbon\s+concentration",
            r"\bC\s*\(%\)|%\s*C\b|percent\s+carbon|carbon\s*\(%\)|weight\s+percent\s+carbon",
            r"elemental\s+(analysis|analyzer|C\b)",
            r"\bCHN\b|\bCN\s+analy[sz]er|C\s*/\s*N\s+analy[sz]er|carbon[- ]nitrogen\s+analy[sz]er",
            # NOTE (2026-10-09, potential fix, not applied): bare "combustion" also matches unrelated uses, e.g. the
            # GC-IRMS "combustion interface" for 13C-CH4 / 13C-CO2 (doi:10.25581/SPRUCE.047/1413216 was selected for
            # Total carbon from that sentence in measurementTechnique; its data are incubation CH4 / CO2 production),
            # sample preparation for 14C ("The CH4 was converted to CO2 via combustion at 580 °C",
            # doi:10.25581/SPRUCE.097/1825084, porewater DOC / DIC data only), a reagent correction ("δ13C of the
            # methanol … determined using elemental combustion analysis", doi:10.25581/SPRUCE.101/1876044, 13C-PLFA
            # data), wood cellulose isotopes ("the d13C was measured by combustion-GC-IRMS", doi:10.15485/1596123,
            # tree rings), or "fossil fuel combustion". Fix: r"dry\s+combustion|combustion\s+(analy[sz]er|method)|
            # high[- ]temperature\s+combustion". The instrument patterns above have a related issue: "CN Analyzer"
            # also selects plant-tissue analyses (doi:10.25581/spruce.121/2503934, needles), and "elemental analyzer"
            # and "% C" in methods text select packages without carbon data: doi:10.25581/spruce.091/1782483 (root
            # ingrowth cores) matched "analyzed for N content on an elemental analyzer" (roots) and "49.0 ± 0.9 % C"
            # (background peat means quoted in the methods); its data are root production and root traits. Also
            # doi:10.25581/spruce.105/1924666: "elemental analysis" from "Plant elemental analysis was performed by the
            # micro-Dumas method" (Sphagnum tissue; its genuine `C` column, "Total %C of the sample", is moss, so only
            # the triage, "plant tissue / plant traits", drops it). Also doi:10.15485/1574502: "elemental analysis of
            # percent organic carbon" describes the study's later carbon estimate; the package only holds floodplain
            # sediment depths and elevations. More plant-tissue examples of "Elemental Analyzer": doi:10.15485/1631262
            # (root tissue N), doi:10.15485/1631278 (foliar C, N), doi:10.15485/1686146 (seedling tissue d13C). Possible
            # fix for these text-only matches: grade them 'related' when the sentence names plant material
            # (exclusion_terms in evidence.csv) or when no data column matches. Applying a fix changes
            # matrix_any.csv; rerun selection.
            r"combustion",
        ],
        text_related=[
            r"soil\s+organic\s+carbon",
            r"\bSOC\b",
            r"\bSOM\b|soil\s+organic\s+matter",
            # NOTE (2026-10-09, potential fix, not applied): with no boundary in front, this also matches the tail of
            # "inorganic carbon" (doi:10.25581/spruce.043/1434643 was selected for Total carbon from its keyword
            # "Dissolved Inorganic Carbon", evidence detail 'organic Carbon'). Fix: r"(?<!in)organic\s+carbon" or
            # r"\borganic\s+carbon", as col_related already does. Same issue in SOC text_strong
            # r"organic\s+carbon\s+(content|concentration)". Applying it changes matrix_any.csv; rerun selection.
            # It also matches "dissolved organic carbon" (DOC, its own variable): doi:10.25581/SPRUCE.062/1500027 was
            # selected for Total carbon from "porewater dissolved organic carbon (DOC)" and the keyword "dissolved
            # organic carbon"; its data are porewater DOC (mg L-1) and incubation CH4 / CO2. Fix: also skip a
            # preceding "dissolved" (fixed-width lookbehinds: r"(?<!dissolved\s)(?<!in)organic\s+carbon").
            # It also matches aerosol "Black Carbon and Organic Carbon" (doi:10.15485/1464237, GEIA global emissions
            # inventory; no soil data). Fix: skip it when "black carbon", "aerosol" or "emission" is in the same
            # sentence (r"black\s+carbon\s+and\s+organic\s+carbon" as a hard exclusion covers this wording). And the
            # extract carbon of microbial biomass methods: "chloroform fumigation extraction method followed by
            # colorimetric determination of organic carbon" (doi:10.15485/1577267; soil N pools, microbial biomass,
            # pH, no carbon content column). More examples: keyword "Particulate/Dissolved Inorganic Carbon"
            # (doi:10.15485/1647038, hyporheic and floodplain water) and DOC of water extracts (doi:10.15485/1618870).
            r"organic\s+carbon",
            # NOTE (2026-10-09, potential fix, not applied): also matches "soil carbon dioxide" (the gas;
            # doi:10.25581/SPRUCE.062/1500027, keyword "soil carbon dioxide") and fluxes ("The whole-soil carbon flux in
            # response to warming", doi:10.15485/1596312, Blodgett soil-gas well CO2 / d13C). Fix:
            # r"soil\s+carbon(?!\s+(dioxide|monoxide|flux|efflux))". Applying it changes matrix_any.csv; rerun selection.
            r"soil\s+carbon",
            r"carbon\s+stock",
            r"\bTOC\b",
            # NOTE (2026-10-12, potential fix, not applied): the GCMD topic keyword "EARTH SCIENCE > AGRICULTURE > SOILS
            # > CARBON" is chosen from a fixed list for any soil carbon-cycle data, fluxes included; it does not mean
            # carbon content was measured. doi:10.15485/1595105 (chamber CH4 / CO2 / N2O fluxes and porewater gas,
            # Columbia River bank) was selected for Total carbon from it alone; 6 of 468 Total carbon packages have
            # it as their only evidence. Also doi:10.15485/1670465 (benchmark data and model runs). Fix: count it only together with another source, or drop it. Applying it
            # changes matrix_any.csv; rerun selection.
            r"SOILS\s*>\s*CARBON",
        ],
        col_strong=[
            # NOTE (2026-10-13, potential fix, not applied): also matches the companion metadata columns of the ESS-DIVE
            # sample-based chemistry reporting format: doi:10.15485/1865731 (the reporting format itself; its
            # examples.zip/examples/Data_opt_example.csv has 'Total_Carbon' and 'Total_Carbon_UTC_offset' (numeric, a time-zone
            # offset), 'Total_Carbon_Notes' ...). It is a Total carbon candidate, not written only because the example has no
            # location. Fix: exclude names ending in utc_offset|notes|method|flag|unit for all variables (STATS does not catch
            # a numeric UTC offset).
            r"total ?c(arbon)?\b",
            # NOTE (2026-10-13, potential fix, not applied): '^tc\b' also matches thermocouple temperatures:
            # doi:10.15485/1463820 (Aspen FACE meteorological and soil data) tower files 12tow201.xls / 12tow224.xls
            # have 'TC' over 'Ref', 'Surf', '0.25m', '0.50m' (and 6999 missing codes). It is a Total carbon
            # candidate and is not written only because those files have no location. Fix: a 'TC' whose group / units
            # row is a depth or height ('Surf', '0.25m') or 'Ref' is a temperature; or triage the package.
            r"^tc\b|[\s(]tc[\s)]|\stc$|^tc[\s(%]",
            # 'perc' and a bare 'perC' added 2026-10-12: 'c_perc' (doi:10.15485/1988078 Y1_CNperc.csv) and 'perC'
            # (doi:10.15485/1894515 Soil_Data_Final.csv) were not matched. '^per ?c$' is exact so 'perC.HF' (a density
            # fraction) is not taken.
            r"^c ?(\(|\[)?\s*(%|pct|perc(ent)?\b|wt|mg ?/? ?g|g ?/? ?kg)",
            r"^% ?c(arbon)?\b|^pct ?c(arbon)?\b|^percent ?c(arbon)?\b|^per ?c(arbon)?$",
            # NOTE (2026-10-12, potential fix, not applied): this also makes "organic carbon content" / "organic carbon
            # (%)" a strong Total carbon column (doi:10.15485/1480328, FACE-MDS model_initialisation_&_parameterisation
            # sheet Soil&Roots: model parameters, dropped only by the triage as modeling); "inorganic carbon content"
            # also matches here but col_exclude drops it. Fix: r"(?<!organic )carbon ?(\(|\[)?\s*(...)" so organic
            # carbon columns fall to col_related (still 'related' evidence). Applying it changes matrix_any.csv;
            # rerun selection.
            r"carbon ?(\(|\[)?\s*(%|pct|percent|content|conc|wt|mg ?/? ?g|g ?/? ?kg)",
            # NOTE (2026-10-13, potential fix, not applied): in a data dictionary '^c$' also matches a unit cell: doi:10.5440/1875917
            # (forced-diffusion chamber CO2 fluxes) nga285_dd.csv row "Temperature,C,Temperature of EOSense chamber"
            # gave strong dictionary evidence for Total carbon; also doi:10.15485/1788230 (PumpHouse sensor suite,
            # "Air_temp_(C)" ...). Fix: match dictionary rows on the name cell only.
            r"^c$|^carbon$|^c (content|conc|concentration)",
            r"^(soil|bulk) ?c(arbon)?\b(?! ?(flux|resp|o2))",
            # Added 2026-10-12 (dictionary-definition dry run): 'carbon_weight_perc' (doi:10.15485/1960313, "Total
            # Carbon, as percentage by weight"), 'C_Tot_wt_perc' (doi:10.15485/3024128), 'C_weight_percent'
            # (doi:10.15485/1631278) were not matched.
            r"^c(arbon)? ?(tot(al)? ?)?(wt|weight) ?(%|perc|pct)",
        ],
        # Added 2026-10-12: 'pC' (doi:10.15485/2588765 CN_data.csv, "Soil carbon from combustion analyzer";
        # doi:10.15485/1835182 Cbud.csv). Case-sensitive: 'Pc' is crystal pressure (1838886) or a photosynthesis
        # variable (1674983). Matching data columns on their dictionary definitions instead was tried as a dry run
        # (404 new matches in 98 packages, mostly wrong: CO2, fractions, detection limits, plant tissue) and not used.
        col_strong_cased=[r"^pC$"],
        col_related=[
            r"\bsoc\b",
            r"(?<!in)organic ?c(arbon)?\b",
            r"\boc\b",
            r"\btoc\b",
        ],
        col_exclude=(r"doc\b|dissolved|\bdic\b|inorganic|tic\b|co2|ch4|flux|resp|"
                     r"c ?[:/]? ?n\b|cn ratio|(?<!concent)ratio|microb|mbc|biomass|pom\b|maom|"
                     r"cation|cec\b|cond|ec\b|root|litter|water|npoc|" + ISOTOPE + "|" + WATERS),
        col_hard_exclude=PER_LITRE + "|" + r"leachate|dissolved|water|(?<!concent)ratio|c:n|c/n|" + ISOTOPE,
        col_rescue=r"total ?c(arbon)?\b",
    ),
    "DOC": CarbonSpec(
        name="Dissolved organic carbon",
        text_strong=[
            r"dissolved\s+organic\s+carbon",
            r"\bDOC\b",
            r"\bNPOC\b|non-?purgeable\s+organic\s+carbon",
            r"extractable\s+organic\s+carbon|salt[- ]extractable\s+(organic\s+)?carbon",
        ],
        text_related=[
            r"dissolved\s+organic\s+matter|\bDOM\b",
            r"K2SO4|potassium\s+sulfate",
            r"pore\s*water\s+chemistry|soil\s+solution|lysimeter",
        ],
        col_strong=[
            r"\bdoc\b",
            r"dissolved organic c(arbon)?\b",
            r"\bnpoc\b",
            r"extractable (organic )?c(arbon)?\b|extr (org )?c\b|\beoc\b",
            r"k2so4 (extractable )?(organic )?c\b",
        ],
        col_related=[
            r"\bdom\b",
        ],
        col_exclude=(r"mbc|microbial|biomass|fumig|(?<!concent)ratio|c ?[:/] ?n|don\b|outflow|inflow|discharge|"
                     + ISOTOPE + "|" + WATERS),
        col_hard_exclude=r"\bdoc ?(id|num|no)\b|" + ISOTOPE,
    ),
    "SOC": CarbonSpec(
        name="Soil organic carbon",
        text_strong=[
            r"soil\s+organic\s+carbon",
            r"\bSOC\b",
            # NOTE (2026-10-09, potential fix, not applied): also matches "inorganic carbon content"; see the note in
            # TC text_related. Fix: r"(?<!in)organic\s+carbon\s+(content|concentration)".
            r"organic\s+carbon\s+(content|concentration)",
            r"total\s+organic\s+carbon",
            r"acid[- ]fumigat|acidified\s+sample|carbonate[- ]free",
        ],
        text_related=[
            r"(?<!in)organic\s+carbon",
            r"\bTOC\b",
            r"soil\s+carbon",
            r"\bCorg\b|C\s*org",
        ],
        col_strong=[
            r"\bsoc\b",
            r"(?<!in)organic ?c(arbon)?\b",
            r"\boc\b",
            r"\btoc\b",
            r"\bc ?org\b|\borg ?c\b|\bcorg\b",
        ],
        col_related=[
            r"soil ?c(arbon)?\b",
        ],
        col_exclude=(r"dissolved|\bdoc\b|extract|leach|npoc|\bweoc\b|porewater|pore water|water|"
                     r"stock|storage|kg ?/ ?m ?2|kg m-2|t ?/ ?ha|mg ?/ ?ha|g ?/ ?m ?2|g m-2|"
                     r"pom\b|particulate|maom|mineral assoc|fraction|"
                     r"flux|resp|co2|(?<!concent)ratio|c ?[:/] ?n\b|microb|mbc|root|litter|" + ISOTOPE + "|" + WATERS),
        col_hard_exclude=(PER_LITRE + "|" + r"\b(u|µ|m)m\b|per (ground )?area|dissolved|(?<!concent)ratio|"
                          + ISOTOPE),
    ),
    "SOM": CarbonSpec(
        name="Soil organic matter",
        text_strong=[
            r"soil\s+organic\s+matter",
            r"\bSOM\b",
            r"organic\s+matter\s+(content|concentration|percent)",
        ],
        text_related=[
            r"(?<!dissolved\s)(?<!particulate\s)organic\s+matter",
            r"loss\s+on\s+ignition|\bLOI\b",
        ],
        col_strong=[
            r"organic matter",
            r"\bsom\b",
            r"\bom ?(\(|\[)?\s*(%|pct|percent|content)|^om$|^% ?om\b",
        ],
        col_related=[
            r"\borg ?matter\b",
        ],
        col_exclude=(r"dissolved|\bdom\b|particulate|\bpom\b|mineral assoc|maom|fraction|"
                     r"water extract|weom|(?<!concent)ratio|" + ISOTOPE + "|" + WATERS),
        col_hard_exclude=PER_LITRE + "|" + r"dissolved|" + ISOTOPE,
    ),
    "SOCstock": CarbonSpec(
        name="Soil organic carbon stock",
        text_strong=[
            r"(soil\s+)?(organic\s+)?carbon\s+stocks?",
            r"\bSOC\s+stocks?",
            r"soil\s+(organic\s+)?carbon\s+(storage|inventory|inventories|pools?)",
        ],
        text_related=[
            r"carbon\s+(storage|inventory|density)",
            r"kg\s*C\s*m-?2|Mg\s*C\s*ha-?1|g\s*C\s*m-?2",
        ],
        col_strong=[
            r"(soc|organic c(arbon)?|soil c(arbon)?|carbon|\bc\b).*(stock|storage|inventory)",
            r"(soc|organic c(arbon)?|soil c(arbon)?|carbon|\bc\b).*(kg ?/ ?m ?2|kg m-?2|kgc m-?2|"
            r"t ?/ ?ha|mg ?/ ?ha|mg ha-?1|t ha-?1|g ?/ ?m ?2|g m-?2|gc m-?2|per ground area|per area)",
        ],
        col_related=[
            r"carbon density|c density|\bsocd\b",
            r"(soc|carbon) (pool|content) (to|0)",
        ],
        col_exclude=(r"flux|resp|co2|ch4|biomass|root|litter|dissolved|\bdoc\b|microb|"
                     r"(?<!concent)ratio|\bn\b|nitrogen|" + ISOTOPE),
        col_hard_exclude=r"flux|resp|co2|" + ISOTOPE,
    ),
    "SIC": CarbonSpec(
        name="Soil inorganic carbon",
        text_strong=[
            r"soil\s+inorganic\s+carbon",
            r"\bSIC\b",
            r"inorganic\s+carbon",
            r"carbonates?\b",
            r"\bCaCO3\b|calcium\s+carbonate",
        ],
        text_related=[
            r"calcite|dolomite",
            r"\bTIC\b",
            r"pedogenic\s+carbonate|caliche",
        ],
        col_strong=[
            r"inorganic ?c(arbon)?\b|\binorg ?c\b|\bc ?inorg\b",
            r"\bsic\b",
            r"\btic\b",
            r"carbonate",
            r"\bcaco3\b",
        ],
        col_related=[
            r"calcite|dolomite",
        ],
        col_exclude=(r"dissolved|\bdic\b|porewater|pore water|water|alkalinity|bicarbonate|hco3|"
                     r"geolog|rock|catchment|bedrock|"
                     r"(?<!concent)ratio|" + ISOTOPE + "|" + WATERS),
        col_hard_exclude=PER_LITRE + "|" + r"dissolved|\bdic\b|" + ISOTOPE,
    ),
    "POMC": CarbonSpec(
        name="Particulate organic matter carbon",
        text_strong=[
            r"particulate\s+organic\s+(matter|carbon)",
            r"\bPOM\b|\bPOC\b",
            r"light\s+fraction|free\s+light\s+fraction|occluded\s+(light\s+)?fraction|\bfLF\b|\boLF\b",
        ],
        text_related=[
            r"density\s+fractionation|size\s+fractionation|physical\s+fractionation",
            r"soil\s+(organic\s+matter\s+)?fractions?",
        ],
        col_strong=[
            r"\bpom\b|\bpomc\b|\bpom ?c\b",
            r"particulate organic",
            r"\bpoc\b",
            r"light fraction|\bflf\b|\bolf\b",
        ],
        col_related=[
            r"\blf\b",
            r"fraction (total )?c(arbon)?\b",
            r"> ?53|>53",
            r"coarse fraction",
        ],
        col_exclude=(r"\bn\b|nitrogen|(?<!concent)ratio|c ?[:/] ?n|\bcn\b|\btn\b|\bgn\b|pern|propn|mass|weight|recovery|yield|"
                     r"\d+ ?- ?\d+|"
                     r"water|size|" + ISOTOPE + "|" + WATERS),
        col_hard_exclude=PER_LITRE + "|" + r"(?<!concent)ratio|" + ISOTOPE,
    ),
    "LOI": CarbonSpec(
        name="Loss on ignition",
        text_strong=[
            r"loss\s+on\s+ignition|\bLOI\b",
        ],
        text_related=[
            r"ash[- ]free\s+dry\s+(mass|weight)|\bAFDM\b",
            r"muffle\s+furnace|ash\s+content",
        ],
        col_strong=[
            r"\bloi\b",
            r"loss on ignition|ignition loss",
        ],
        col_related=[
            r"ash ?free|\bafdm\b|ash content|^ash\b|\bash ?(%|pct|percent)",
        ],
        col_exclude=r"(?<!concent)ratio|litter|root|leaf|" + WATERS,
        col_hard_exclude="",
    ),
    "WEOC": CarbonSpec(
        name="Water-extractable organic carbon",
        text_strong=[
            r"water[- ]extract(able|ed)\s+organic\s+(carbon|matter)",
            r"\bWEOC\b|\bWEOM\b|\bWSOC\b|\bHWEC\b",
            r"water[- ]soluble\s+organic\s+carbon",
            r"hot[- ]water[- ]extract",
        ],
        text_related=[
            r"water\s+extract(ion|s|able)",
        ],
        col_strong=[
            r"\bweoc\b|\bwsoc\b|\bhwec\b|\bhweoc\b|\bcweoc\b",
            r"water extract(able|ed)? (organic )?c(arbon)?\b",
            r"water soluble (organic )?c(arbon)?\b",
        ],
        col_related=[
            r"\bweom\b",
            r"water extract.*(doc|npoc|toc|\boc\b)",
            r"(doc|npoc|toc) .*water extract",
        ],
        col_exclude=r"(?<!concent)ratio|weon|\bn\b|nitrogen|" + ISOTOPE + "|" + WATERS,
        col_hard_exclude=ISOTOPE,
    ),
    "MAOMC": CarbonSpec(
        name="Mineral-associated organic matter carbon",
        text_strong=[
            r"mineral[- ]associated\s+organic\s+(matter|carbon)",
            r"\bMAOM\b|\bMAOC\b|\bMAOM-C\b",
            r"heavy\s+fraction",
        ],
        text_related=[
            r"density\s+fractionation|size\s+fractionation|physical\s+fractionation",
            r"silt\s*(and|\+|-)\s*clay\s+fraction",
        ],
        col_strong=[
            r"\bmaom|\bmaoc\b",
            r"mineral assoc",
            r"heavy fraction|\bhf ?c\b",
        ],
        col_related=[
            r"\bhf\b",
            r"< ?53|<53",
            r"silt ?(and|\+|-)? ?clay (fraction )?c",
            r"fine fraction c",
        ],
        col_exclude=(r"\bn\b|nitrogen|(?<!concent)ratio|c ?[:/] ?n|\bcn\b|\btn\b|\bgn\b|pern|propn|mass|weight|recovery|yield|"
                     r"\d+ ?- ?\d+|"
                     r"maomn|\bmaon\b|\bkw\b|heat|" + ISOTOPE),
        col_hard_exclude=PER_LITRE + "|" + r"(?<!concent)ratio|" + ISOTOPE,
    ),
}


# ----------------------------------------------------------------------------------------------------------------
# Soil variable list rules (notebooks/soil_variable_list/05_count_packages.py)
# ----------------------------------------------------------------------------------------------------------------

def sym(s: str, name: str) -> str:
    """Build the column pattern of an element: its bare symbol or its name.

    The bare symbol is case-sensitive and may be followed by a unit or suffix ('Fe', 'Fe_ppm'); the element name is
    matched at the start of the column ('Iron (mg/kg)', 'total iron').

    Args:
        s: Element symbol, e.g. 'Fe'.
        name: Element name, e.g. 'iron'.

    Returns:
        The pattern (to be compiled case-insensitively; the symbol part stays case-sensitive).

    Examples:
        >>> import re
        >>> p = re.compile(sym("Fe", "iron"), re.I)
        >>> [bool(p.search(c)) for c in ["Fe", "Fe_ppm", "Iron (mg/kg)", "fe", "Feo"]]
        [True, True, True, False, False]
    """
    return rf"(?-i:^{s}(?:$|[ _(\-]|\d|ppb|ppm))|^{name}\b|^total {name}"


FORM_EXCL = r"ascorb|dithio|hot.?acid|oxal|citrat|pyro|exch|\(ii|_ii\b|fe_2|ii\)|(?<!concent)ratio|xanes|_c_|_ca_|speciation|smectite|sulfide|cyst|glutath|histid|acetate|bioconc|_ar$|_ar_|_dl$|_fl$|_sd$|stdev|std_dev|_mdl|flag|notes|lld|mth|error|\bse\b"

# variable -> (column regex, column exclude, text regex, package restriction)
R: dict[str, RawRule] = {}


def add(var: str, col: str | None = None, excl: str | None = None, txt: str | None = None,
        restrict: Restriction = None) -> None:
    """Register a list rule in R.

    Args:
        var: Variable name in the list.
        col: Column pattern.
        excl: Column exclusion pattern.
        txt: Metadata text pattern.
        restrict: Package restriction (see datatypes.Restriction).
    """
    R[var] = RawRule(col, excl, txt, restrict)

# Acidity
add("Soil pH in water", r"^ph$|^soil ph$|ph_h2o|ph_water|soil_ph_water|^initial_ph$|ph 1:1|ph \(h2o|^ph_1$|^soil_ph$|^ph \(", r"cacl|kcl|bacl", r"ph in water|water ph|ph_h2o|\bph \(h2o|soil ph")
add("Soil pH in CaCl2", r"ph.?_?cacl", None, r"cacl2[^.]{0,40}\bph\b|\bph\b[^.]{0,40}cacl2")
add("Soil pH in KCl", r"ph.?_?kcl|kcl 1m", None, r"kcl[^.]{0,40}\bph\b|\bph\b[^.]{0,40}\bkcl\b")
add("Soil pH in BaCl2", r"ph.?_?bacl", None, None)
# Carbon
add("Total carbon", r"^c$|^%c$|^c \(%\)|%carbon|percent.?c\b|percent.total.c|total.?c(arbon)?\b|^carbon$|tc_perc|tc_org|tc_min|total-carbon|initial.total.c|soil_tc\b|c_tot", r"microbial|fraction|radiocarbon|stock|dissolved|root|leaf|foliar|needle|litter|bole|stem|organic|inorganic|_mth|_lld", r"total carbon|carbon content|percent carbon|carbon concentration")
add("Soil organic carbon", r"\btoc\b|\bsoc\b|organic carbon|c_org|soil_toc|total organic c", r"stock|dissolved|_mth|_lld|\bdoc\b", r"soil organic carbon|organic carbon content|\bsoc\b|\btoc\b")
add("Soil inorganic carbon", r"inorganic carbon|soil_tic|c_inorg|carbonates", r"dissolved|\bdic\b|_mth|_lld", r"soil inorganic carbon|carbonate content")
add("Soil organic carbon stock", r"carbon stock|soc.?stock|soc to 1 m", None, r"carbon stock")
add("Soil organic matter", r"organic matter|soil-organic-matter|\bsom\b", r"particulate|sediment|dissolved", r"soil organic matter|organic matter content")
add("Loss on ignition", r"\bloi\b|loss on ignition|loss_on_ignition", None, r"loss on ignition")
add("Dissolved organic carbon", r"\bdoc\b|dissolved organic carbon|\bnpoc\b|extractable_npoc", r"_14c|cams|-0\d\d|\+\d", r"dissolved organic carbon|\bdoc\b")
add("Water-extractable organic carbon", r"weoc|water.extractable.organic|wsoc", None, r"water.extractable organic carbon|\bweoc\b")
add("Particulate organic matter carbon", r"\bpom\b|pom.?c\b|particulate organic", None, r"particulate organic matter|particulate organic carbon")
add("Mineral-associated organic matter carbon", r"maom", None, r"mineral.associated organic")
# Nitrogen
# 'n_perc' / 'N_percent' / 'Nperc' and a case-sensitive 'pN' added 2026-10-12 (doi:10.15485/2428003 '01397_N_percent'
# after its method code is dropped; doi:10.15485/2588765 'pN'; 'Pn' is net photosynthesis in doi:10.15486/NGT/1570408).
# '^total.?n(\b|_)' since 2026-10-12: '\b' fails before '_', so 'Total_N_percent' (doi:10.15485/3484503) was missed.
add("Total nitrogen", r"^n$|^%n$|^n[ _]?perc(ent)?\b|(?-i:^pN$)|%nitrogen|percent_n|percent.total.n|^total.?n(\b|_)|totaln$|tn_perc|^nitrogen$|total nitrogen|total-nitrogen|bulk layer total nitrogen", r"microbial|extractable|fraction|dissolved|nsc|root|leaf|foliar|needle|litter|bole|stem|to 1 m", r"total nitrogen|nitrogen content|percent nitrogen")
add("Carbon to nitrogen ratio", r"^cn$|c.n.ratio|c:n ratio|cn_ratio|soil_cn_ratio|carbon-to-nitrogen|^c/n", r"change|cntl|concentration|root|leaf|litter|microbial|maom|ubial", r"\bc:n\b|c/n ratio|carbon.to.nitrogen ratio")
add("Ammonium nitrogen", r"nh4|ammonium", r"rate|ext_fe|nh4cl|oxalate|\[m\+|nh4ac|_fl$|_dl$|flag", r"ammonium")
add("Nitrate nitrogen", r"no3|nitrate", r"delta|d15n|d18o|_fl$|_dl$|flag|stdev|reduct", r"\bnitrate\b")
add("Dissolved organic nitrogen", r"dissolved organic n|\bdon\b|soil_dissolved_organic_n", None, r"dissolved organic nitrogen|\bdon\b")
add("Total extractable nitrogen", r"extractable_tn|total_extractable_n|\btdn\b|extractable.?n\b", r"_fl$|stdev|delta", r"total extractable nitrogen|total dissolved nitrogen")
add("Net nitrogen mineralization rate", r"n.?mineraliz|ammonrate", None, r"n mineralization|nitrogen mineralization")
add("Net nitrification rate", r"^nitrification|nitrifrate|nnitrification|nitrification_day|net nitrification", r"denitrif", r"(?<!de)nitrification rate|net nitrification")
# Phosphorus
add("Total phosphorus", r"^soil_p$|^total.?p\b|^tp$|p_tot|(?-i:^P$)", r"adj|extractable|evap|qflx", r"total phosphorus", "sym_solid")
add("Bray-1 extractable phosphorus", r"bray", None, r"\bbray\b")
add("Mehlich-3 extractable phosphorus", r"mehlich", None, r"mehlich")
add("Olsen extractable phosphorus", r"olsen|bicarbonate", None, r"\bolsen\b")
add("Resin / extractable phosphate", r"po4|phosphate|extractable_p|resin.?p", r"_fl$|_dl$|flag|ortho|pyrophosphate", r"extractable phosph|available phosph|resin phosph")
add("Phosphorus fractions", r"soluble_p|organic_p|humicacid_p|hedley", None, r"hedley|phosphorus fraction")
add("Oxalate-extractable phosphorus", r"alo-p|feo-p|p_ox|oxalate.?p", None, r"oxalate.extractable p")
# Sulfur
add("Total sulfur", r"^s_tot|total.?sulfur|^total s$|(?-i:^S$)", r"_mth|_lld", r"total sulfur|total sulphur", "sym_solid")
add("Extractable sulfate", r"so4|sulfate|sulphate", r"k2so4|flag|_fl$|_dl$|notes|sulfide", r"extractable sulfate|soil sulfate")
# Base cations (exchangeable): explicit exchangeable columns, or cation columns in packages with CEC / exchangeable context
EXC_CTX = r"exchangeab|\bcec\b|cation exchange|base saturation|nh4oac|ammonium acetate|cmol|meq ?/ ?100|meq100"
for el, nm in [("Ca", "calcium"), ("Mg", "magnesium"), ("K", "potassium"), ("Na", "sodium"), ("Al", "aluminum")]:
    add(f"Exchangeable {nm}", rf"exchangeable {nm}|{el}_exch|exch.?{el}\b|{el}_meq|(?-i:^{el}$)", r"flag|_fl$", rf"exchangeable {nm}|exchangeable {el}\b", "exch")
add("Cation exchange capacity", r"\bcec\b|cation exchange", r"effective", r"cation exchange capacity|\bcec\b")
add("Effective cation exchange capacity", r"effective cation|\becec\b|effective cec", None, r"effective cation exchange|\becec\b")
add("Base saturation", r"base saturation", None, r"base saturation")
# Total elements: packages with soil / sediment context only (solid_total)
ELEM = [("Al", "aluminum"), ("Fe", "iron"), ("Mn", "manganese"), ("Ti", "titanium"), ("Si", "silicon"), ("Ca", "calcium"), ("Mg", "magnesium"),
        ("K", "potassium"), ("Na", "sodium"), ("Zn", "zinc"), ("Cu", "copper"), ("Ni", "nickel"), ("Co", "cobalt"), ("Cr", "chromium"),
        ("Pb", "lead"), ("Cd", "cadmium"), ("As", "arsenic"), ("Hg", "mercury"), ("Mo", "molybdenum"), ("Se", "selenium"), ("Sb", "antimony"),
        ("Sn", "tin"), ("Ag", "silver"), ("Tl", "thallium"), ("Be", "beryllium"), ("Ba", "barium"), ("Sr", "strontium"), ("Li", "lithium"),
        ("Rb", "rubidium"), ("Cs", "cesium"), ("Zr", "zirconium"), ("Ga", "gallium"), ("Ge", "germanium"), ("Th", "thorium"), ("U", "uranium"),
        ("La", "lanthanum"), ("Ce", "cerium"), ("Nd", "neodymium")]
for el, nm in ELEM:
    add(f"Total {nm}", sym(el, nm), FORM_EXCL + r"|^tin\b|tin[ +]|tin_|^lead\b.*connector|silver &", None, "solid_total")
# Plant-available
# Mehlich-3 metals are reported as element columns (Fe, Mn ...): they count in packages that mention Mehlich.
MEHLICH_CTX = r"mehlich"
for el, nm in [("Fe", "iron"), ("Mn", "manganese"), ("Zn", "zinc"), ("Cu", "copper")]:
    add(f"Mehlich-3 extractable {nm}", sym(el, nm), FORM_EXCL, None, ("context", MEHLICH_CTX))
add("Extractable boron", sym("B", "boron"), FORM_EXCL + r"|glucosid|xylosid|activity|ase\b", r"extractable boron|hot.water boron",
    ("context", r"mehlich|hot.?water.{0,20}boron|extractable boron|boron.{0,20}extract"))
add("Resin-supplied metals (Al Fe Mn Cu Zn Pb Cd)", None, None, r"plant.available nutrients|ion.exchange resin|\bprs\b", None)
# Pedogenic oxides
add("Oxalate-extractable iron", r"feo\b|feo-|fe_ox|fe_o$|oxalate.*fe|fe.*oxalate|ironi+oxalate", None, r"oxalate.extractable (fe|iron)|oxalate.extractable", None)
add("Oxalate-extractable aluminum", r"alo\b|alo-|al_ox|al_o$|oxalate.*al", None, r"oxalate.extractable (al|alumin)")
add("Oxalate-extractable manganese", r"mn_ox|mno\b|oxalate.*mn", None, r"oxalate.extractable (mn|mangan)")
add("Dithionite-citrate-extractable iron", r"fe_dithio|fe_d$|dithionite.*fe|citrate.*fe|ironiiicitrate|fe_dcb", None, r"dithionite[- ]?(citrate|extract)|dithionite \(for|\(hcl, dithionite|, dithionite\)")
add("Dithionite-citrate-extractable aluminum", r"al_dithio|al_d$|dithionite.*al", None, None)
add("Dithionite-citrate-extractable manganese", r"mn_dithio|mn_d$|dithionite.*mn", None, None)
add("Ascorbate-extractable iron", r"fe_ascorb", None, r"ascorbate")
add("Ascorbate-extractable aluminum", r"al_ascorb", None, None)
add("Ascorbate-extractable manganese", r"mn_ascorb", None, None)
add("Pyrophosphate-extractable iron", r"fe_p$|fe_pyro|pyrophosphate", None, r"pyrophosphate.extractable")
add("Pyrophosphate-extractable aluminum", r"al_p$|al_pyro|pyrophosphate", None, r"pyrophosphate.extractable")
add("Hot-acid-extractable iron aluminum manganese", r"hotacid|hot.acid", None, None)
add("Exchangeable iron", r"exchangeable_fe|exchangeable fe|fe_exch", r"_fl$", None)
# Iron redox
add("Ferrous iron", r"fe\(ii\)|fe_ii\b|fe_2\b|fe_2$|ferrous|iron.?ii\b|iron_ii|fe2\+|fe \(ii", r"fe\(iii|_fl$|stddev|/fe|(?<!concent)ratio|montmor|ads|citrate|humic|\baq\b|mg_l|_mm$|flags|notes|as_fe|asiron", r"ferrous iron|fe\(ii\)|fe2\+", "no_porewater")
add("Ferric iron", r"fe\(iii\)|fe \(iii\)|ferric|fe_iii\b", r"montmor|humic|_pct", r"ferric iron|fe\(iii\)", "no_porewater")
add("Fe(II) to total Fe ratio", r"fe\(ii\)/fe|fe_2:fe_tot|fe_ii_div_fetot|fe_ratio", None, None)
add("Iron mineral speciation", r"ferrihydrite|goethite|fe_iii_.*_pct|fe_ii_.*_pct|fexanes", None, r"fe k-edge|iron speciation|fe speciation")
add("Copper speciation", r"(?-i:^Cu [A-Z][a-z]+$)", None, r"copper speciation|cu speciation")
add("Nickel speciation", r"ni_smectite|ni_sulfide|ni_cyst|ni_cellulose|(?-i:^Ni [A-Z][a-z]+$)", None, r"nickel speciation|ni speciation")
# Porewater metals: packages with porewater context only (pore)
add("Dissolved aluminum in soil porewater", sym("Al", "aluminum"), r"flag|notes|_fl$|_dl$|stdev|std_dev|_mdl", None, "pore")
add("Dissolved iron in soil porewater", sym("Fe", "iron") + r"|iron_total|iron_ferrous|fe_icp", r"flag|notes|_fl$|_dl$|stdev|std_dev|_mdl", None, "pore")
add("Dissolved manganese in soil porewater", sym("Mn", "manganese"), r"flag|notes|_fl$|_dl$|stdev|std_dev|_mdl", None, "pore")
TRACE = "|".join(sym(s, n) for s, n in [("Zn", "zinc"), ("Cu", "copper"), ("Ni", "nickel"), ("Co", "cobalt"), ("Cr", "chromium"), ("Pb", "lead"),
                                         ("Cd", "cadmium"), ("As", "arsenic"), ("Ba", "barium"), ("Sr", "strontium"), ("Li", "lithium"),
                                         ("Mo", "molybdenum"), ("Ag", "silver"), ("Tl", "thallium"), ("Ti", "titanium")])
add("Dissolved trace metals in soil porewater (Zn Cu Ni Co Cr Pb Cd As Ba Sr Li Mo Ag Tl Ti)", TRACE, r"flag|notes|_fl$|_dl$|stdev|std_dev|_mdl", None, "pore")
# Physical
add("Gravimetric water content", r"\bgwc\b|gravimetric|water content \(g|g h2o per gram|moisture_content|percent.moisture|% moisture|perc_moist|moisture_percent|soil_moisture_(dry|wet)|^moist$|m.moisture|o.moisture", r"vol", r"gravimetric (water|moisture) content|gravimetric soil moisture")
add("Volumetric water content", r"\bvwc\b|\bvsm\b|volumetric|m3 m-3|m3/m3|m³/m³|water_content_vol|soil ?moisture_\d|soilmoisture_\d|\bswc\b|soil water content \(m3", None, r"volumetric (water|soil moisture|moisture)|soil moisture")
add("Dry bulk density", r"bulk.?density|^bd$|bd \(g", r"root|wet", r"bulk density")
add("Particle density", r"particle.?density", None, r"particle density")
add("Porosity", r"porosity", None, r"porosity")
add("Coarse fragment content", r"coarse fragment|rock fragment|>2 ?mm|perc.*gravel|gravel.*(%|sized|cobble)|^gravel$|% wt. gravel|rock ?%|rock wt|rock fraction|rocks \(|rock mass|accounting for rock|a-horizon rock", r"root|elevation|creek|soil type|inclusion|horizons|e\.g\.", r"coarse fragment|rock fragment|gravel content")
add("Sand content", r"^(%\s*)?sand\b|percent.?sand|sand.?(%|percent)|psa_sand|soil_texture_sand|avg\.sand|^sand \(%\)|sand fraction", r"copy|yield|loamy|sandy", r"\bsand\b")
add("Silt content", r"^(%\s*)?silt\b|percent.?silt|silt.?(%|percent)|psa_silt|soil_texture_silt|avg\.silt|^silt \(%\)", r"copy|yield|loam|mud", r"\bsilt\b")
add("Clay content", r"^(%\s*)?clay\b|percent.?clay|clay.?(%|percent)|psa_clay|soil_texture_clay|avg\.clay|^clay \(%\)", r"copy|yield|loam|_dry_clay", r"\bclay content|percent clay")
add("Soil texture class", r"texture class|texture.class|nrcs soil texture|^texture$|textural", None, r"texture class|textural class")
add("Soil temperature", r"soil.?temp|soil_t$|soil-temp|logger temperature", None, r"soil temperature")
add("Electrical conductivity", r"(?-i:^EC\b)|^ec$|electrical conductivity|saturation extract ec|^ec-", None, r"soil electrical conductivity|electrical conductivity")
add("Thermal conductivity", r"thermal.?conductivity", None, r"thermal conductivity")
add("Volumetric heat capacity", r"heat.?capacity", None, r"heat capacity")
add("Thermal diffusivity", r"thermal.?diffusivity", None, r"thermal diffusivity")
add("Thaw depth / active layer thickness", r"thaw|active.?layer", None, r"thaw depth|active layer thickness|active layer depth")
# Morphology
add("Soil horizon designation", r"^horizon$|soil_horizon|^horizon\b|horizon_", r"thickness|depth|volume|loss", r"soil horizon|\bhorizons?\b")
add("Horizon upper depth", r"depth.?top|upper.?depth|depth_upper|top.?depth|depth_cm_top|upper_depth", None, None)
add("Horizon lower depth", r"depth.?bottom|lower.?depth|depth_lower|bottom.?depth|depth_cm_bottom|lower_depth", None, None)
add("Organic layer thickness", r"o.horizon.depth|organic.?layer.?thick|o.?horizon.?thick|moss.?thick|organic.?layer.?depth|o_horizon_depth", None, r"organic layer thickness|organic horizon thickness|o horizon thickness")
add("Munsell color", r"munsell|soil_colou?r|soil colou?r", None, r"munsell|soil colou?r")
# Mineralogy
add("Clay and primary mineralogy", r"\bxrd\b|mineralog|quartz|feldspar|kaolinite|illite|smectite", r"ni_|fe\(ii\)|fe_ii|montmor", r"x-ray diffraction|\bxrd\b|mineralogy")
add("Carbon and calcium speciation", r"nexafs|ca k-edge|c k-edge|xanes", r"fe|ni k|zn k|s k", r"nexafs|stxm|ca k-edge")
# Biology
add("Microbial biomass carbon", r"microbial.?biomass.?c|microbial_c\b|\bmbc\b|mbc\.a|mb_c|microbial c\b", r"cmb_", r"microbial biomass carbon|microbial biomass")
add("Microbial biomass nitrogen", r"microbial.?biomass.?n|microbial_n\b|\bmbn\b|mb_n", None, r"microbial biomass nitrogen")
add("Microbial biomass phosphorus", r"microbial.?biomass.?p|microbial_p\b|\bmbp\b", None, r"microbial biomass phosphorus")
add("Phospholipid fatty acids", r"plfa", None, r"\bplfa|phospholipid fatty")
for ab, nm, rx in [("BG", "beta-glucosidase activity", r"glucosidase"), ("CB", "Cellobiohydrolase activity", r"cellobiohydrolase"),
                   ("NAG", "N-acetyl-beta-glucosaminidase activity", r"glucosaminidase"), ("PHOS", "Acid phosphatase activity", r"phosphatase"),
                   ("XYL", "beta-xylosidase activity", r"xylosidase"), ("LAP", "Leucine aminopeptidase activity", r"aminopeptidase"),
                   ("PER", "Peroxidase activity", r"peroxidase"), ("PPO", "Phenol oxidase activity", r"phenol oxidase")]:
    add(nm, rf"(?-i:^{ab}$)|^\d+\.{ab.lower()}$|{rx}", None, rx, "enzyme" if ab in ("CB", "PER", "BG", "LAP", "PHOS") else None)
add("Bacterial 16S rRNA gene abundance", r"bacteria.?_?copy|16s.?copies|16s.*qpcr", None, r"16s rrna gene (abundance|copies)|bacterial abundance \(qpcr")
add("Archaeal 16S rRNA gene abundance", r"archaea.?_?copy", None, r"archaeal 16s")
add("Fungal ITS / 18S gene abundance", r"fung(i|al).?_?copy", None, r"fungal (its|18s) (gene )?(abundance|copies)")
add("Soil DNA yield", r"dna.?yield", None, r"dna yield")
add("Fine root biomass", r"fine.?root.?biomass|fineroot|live fine root|root biomass|froot|roots \(g\)|root_biomass", r"_c$|_n$|percent", r"fine root biomass|root biomass")
# Fluxes
add("Soil CO2 efflux (respiration)", r"flux_co2|co2.?flux|flux_umol|^flux$|_flux \(|soil.?respiration|efflux", r"se_|r2 of|ch4", r"soil respiration|soil co2 (efflux|flux)|co2 flux")
add("Soil CH4 flux", r"flux_ch4|ch4.?flux|^ch4$", r"se_|r2", r"ch4 flux|methane flux|methane emission")
add("Soil N2O flux", r"n2o", r"aqueous|dissolved", r"n2o flux|nitrous oxide (flux|emission)")
add("Incubation respiration rate", r"co2c_g|cumulative respiration|respiration \(|respiration rate|respired", None, r"incubation[^.]{0,80}respiration|respiration[^.]{0,80}incubation")
# Isotopes
# 'del(ta)?' since 2026-10-12: 'del_13C_per_mil' / 'del_15N_per_mil' (doi:10.15485/3484503), WHONDRS
# '63515_del_13C_permil' (doi:10.15485/1729719) and 'Del 13C' were not matched.
add("Soil organic carbon delta13C", r"d13c|δ13c|î´13c|^13c$|corr 13c|del(ta)?.?13c", r"co2|ch4|plfa|doc|dic|leaf|root", r"δ13c|d13c|stable carbon isotope")
add("Soil nitrogen delta15N", r"d15n|δ15n|î´15n|^15n$|corr 15n|del(ta)?.?15n", r"no3|nh4|tdn|leaf|root|n2o", r"δ15n|d15n|stable nitrogen isotope")
add("Soil organic carbon radiocarbon", r"δ14c|Δ14c|∆14c|î14c|â14c|^14c$|fraction modern|\bfm\b", r"doc|co2|dic|ch4", r"radiocarbon|Δ14c|δ14c")
add("Radiocarbon age", r"14c.?age", r"sigma", r"radiocarbon age|14c age")
add("Radiocarbon-derived carbon turnover time", r"14c tt|turnover time", None, r"turnover time")


# Total carbon spellings found after the original scripts (2026-10-07), on normalized names:
# 'Bulk_Peat_%C', 'BulkSoilC_percent', 'Carbon_total', 'C_avg', 'Soil C (%)'.
CARBON["TC"]["col_strong"] += [r"%\s?c\b(?!:)", r"\bcarbon ?total\b(?! ?organic)", r"\b(bulk ?)?(soil|peat)c\b",
                              r"^c (avg|mean|average)$", r"\b(soil|peat|bulk) c ?(\(|\[)?\s*(%|pct|percent)",
                              r"\btot c\b(?! ?o)", r"\b(soil|peat) c$"]
# DOC of unfumigated extracts is the salt-extractable DOC (the fumigated extract is excluded as microbial biomass).
CARBON["DOC"]["col_rescue"] = r"un ?fumig|non ?fumig"

# Column spellings found after the original scripts (2026-10-07): pH_of_soil_layer (NGEE Arctic), and the solution
# named after "pH" in two-row headers ("Soil pH 0.01 M CaCl2").
R["Soil pH in water"] = R["Soil pH in water"]._replace(
    column=f"{R['Soil pH in water'].column}|^ph_of_soil|^soil ph\\b")
for _n, _x in (("Soil pH in CaCl2", "cacl"), ("Soil pH in KCl", "kcl"), ("Soil pH in BaCl2", "bacl")):
    R[_n] = R[_n]._replace(column=f"{R[_n].column}" + rf"|\bph\b.{{0,25}}{_x}")

# ----------------------------------------------------------------------------------------------------------------
# One Spec per list variable
# ----------------------------------------------------------------------------------------------------------------
CARBON_KEYS: Final[dict[str, str]] = {
    "Total carbon": "TC", "Dissolved organic carbon": "DOC", "Soil organic carbon": "SOC",
    "Soil organic matter": "SOM", "Soil organic carbon stock": "SOCstock", "Soil inorganic carbon": "SIC",
    "Particulate organic matter carbon": "POMC", "Loss on ignition": "LOI",
    "Water-extractable organic carbon": "WEOC", "Mineral-associated organic matter carbon": "MAOMC"}
MERGED: Final[dict[str, list[str]]] = {
    "Soil pH": ["Soil pH in water", "Soil pH in CaCl2", "Soil pH in KCl", "Soil pH in BaCl2"]}
TRACE_PW: Final = "Dissolved trace metals in soil porewater (Zn Cu Ni Co Cr Pb Cd As Ba Sr Li Mo Ag Tl Ti)"
SPLIT_PW: Final[Pattern] = re.compile(r"Dissolved (\w+) in soil porewater")
SYMBOL: Final[dict[str, str]] = {name: s for s, name in ELEM}

# Package context (title, description, keywords, other metadata and column names) required by some rules.
PORE_CTX: Final = r"pore ?water|soil solution|lysimeter|rhizon|suction (cup|sampler)|soil water sampl"
SOLID_CTX: Final = r"\bsoils?\b|sediment|\bpeat|horizon|regolith|saprolite|\bcores?\b|bedrock|\brocks?\b"
ENZYME_CTX: Final = r"enzym"


def _rx(p: str | None) -> Pattern | None:
    """Compile a case-insensitive pattern; None for an empty pattern."""
    return re.compile(p, re.I) if p else None


def _rxs(ps: list[str]) -> tuple[Pattern, ...]:
    """Compile non-empty case-insensitive patterns."""
    return tuple(re.compile(p, re.I) for p in ps if p)


@dataclass(frozen=True)
class Spec:
    """The matching rules of one variable.

    Attributes:
        name: Variable name.
        mode: 'normalized' (carbon specs) or 'raw' (list rules).
        col_strong: Normalized mode: strong column patterns.
        col_related: Normalized mode: related column patterns.
        col_strong_cased: Normalized mode: case-sensitive strong patterns on the column name (not normalized).
        col_exclude: Normalized mode: columns dropped unless col_rescue matches.
        col_hard: Normalized mode: columns always dropped.
        col_rescue: Normalized mode: keeps an excluded column.
        raw_rules: Raw mode: (column pattern, exclusion pattern) pairs.
        raw_rules_no_context: Raw mode: rules used instead in packages without rules_context (bare symbols removed).
        rules_context: Context in which the full raw rules apply.
        text_strong: Metadata text patterns for strong matches.
        text_related: Metadata text patterns for related matches.
        context: The package must match this to count at all.
        exclude_context: The package must not match this.
        definition: A column the package's data dictionary defines must have a definition matching this.
    """
    name: str
    mode: Mode                                       # "normalized" (carbon specs) or "raw" (list rules)
    col_strong: tuple[Pattern, ...] = ()            # normalized: strong column patterns
    col_related: tuple[Pattern, ...] = ()           # normalized: related column patterns
    col_strong_cased: tuple[Pattern, ...] = ()      # normalized: case-sensitive strong patterns on the raw name
    col_exclude: Pattern | None = None              # normalized: dropped unless col_rescue matches
    col_hard: Pattern | None = None                 # normalized: always dropped
    col_rescue: Pattern | None = None
    raw_rules: tuple[ColumnRule, ...] = ()          # raw: ((column pattern, exclusion pattern), ...)
    raw_rules_no_context: tuple[ColumnRule, ...] | None = None  # raw: used instead outside rules_context
    rules_context: Pattern | None = None
    text_strong: tuple[Pattern, ...] = ()
    text_related: tuple[Pattern, ...] = ()
    context: Pattern | None = None                  # package must match this to count at all
    exclude_context: Pattern | None = None          # package must not match this
    definition: Pattern | None = None               # a column the package's data dictionary defines must match this


def _joined(*parts: str | None) -> str:
    """Join the non-empty patterns with '|'."""
    return "|".join(x for x in parts if x)


def _carbon_spec(name: str) -> Spec:
    """Build the Spec of a carbon variable from its graded spec."""
    s = CARBON[CARBON_KEYS[name]]
    return Spec(
        name=name, mode="normalized",
        col_strong=_rxs(s["col_strong"]),
        col_related=_rxs(s["col_related"]),
        col_strong_cased=tuple(re.compile(x) for x in s.get("col_strong_cased", [])),
        col_exclude=_rx(_joined(COMMON_EXCLUDE, s.get("col_exclude"))),
        col_hard=_rx(_joined(COMMON_HARD_EXCLUDE, s.get("col_hard_exclude"))),
        col_rescue=_rx(s.get("col_rescue")),
        text_strong=_rxs(s["text_strong"]),
        text_related=_rxs(s["text_related"]),
    )


def _rules(name: str) -> list[RawRule]:
    """Return the list rules of a variable.

    These are its own rule, the union of its MERGED rules, or the porewater trace-metal rule restricted to its element.

    Raises:
        KeyError: When the variable has no rule.
    """
    if name in MERGED:
        return [R[n] for n in MERGED[name]]
    if name in R:
        return [R[name]]
    m = SPLIT_PW.fullmatch(name)
    if m and m.group(1) in SYMBOL:
        trace = R[TRACE_PW]
        return [RawRule(sym(SYMBOL[m.group(1)], m.group(1)), trace.exclude, None, trace.restrict)]
    raise KeyError(f"no matching rule for variable {name!r}")


def _list_spec(name: str) -> Spec:
    """Build the Spec of a list variable, turning its restriction into package-context tests."""
    parts = _rules(name)
    restrict = parts[0].restrict
    raw: list[tuple[str, str | None]] = [(r.column, r.exclude) for r in parts if r.column]
    context: str | None = None
    definition: str | None = None
    exclude_context: str | None = None
    no_ctx: list[tuple[str, str | None]] | None = None
    if restrict == "exch":
        context = EXC_CTX
    elif restrict == "enzyme":
        context = ENZYME_CTX
    elif restrict == "pore":
        context = PORE_CTX
    elif restrict == "solid_total":
        # total element contents: soil/sediment packages only, never a per-litre (dissolved) column
        context = SOLID_CTX
        raw = [(c, _joined(e, PER_LITRE)) for c, e in raw]
    elif restrict == "sym_solid":
        # the bare element symbol (P, S) only counts in soil/sediment packages
        no_ctx = [(re.sub(r"\|\(\?-i:\^[A-Z]\$\)", "", c), e) for c, e in raw]
    elif restrict == "no_porewater":
        exclude_context = PORE_CTX
    elif isinstance(restrict, tuple) and restrict[0] == "context":
        context = definition = restrict[1]
    texts = [r.text for r in parts if r.text]
    return Spec(
        name=name, mode="raw",
        raw_rules=tuple((_rx(c), _rx(e)) for c, e in raw),
        raw_rules_no_context=tuple((_rx(c), _rx(e)) for c, e in no_ctx) if no_ctx else None,
        rules_context=_rx(SOLID_CTX) if no_ctx else None,
        text_strong=_rxs(texts),
        context=_rx(context),
        definition=_rx(definition),
        exclude_context=_rx(exclude_context),
    )


# Routing by data-dictionary definition (user decision 2026-10-12). A column name such as 'C_percent' or 'percentC'
# matches Total carbon, but some packages define it as organic carbon: the WHONDRS '01395_C_percent' is "Percent
# total organic carbon in less than 2 millimeter sediment samples" (doi:10.15485/1729719, 2428003, 2529428), and
# 'percentC' in doi:10.15485/3030222 is "Percent soil organic carbon". Such a column is taken from Total carbon
# and given to Soil organic carbon. Only a column that already matched Total carbon moves: matching any column on
# its definition was tried as a dry run and added mostly wrong matches. A definition that also says "total
# carbon" stays with Total carbon, and an extract or dissolved pool (doi:10.15485/3367449
# 'Soil_Total_Extractable_Organic_C', "dissolved organic carbon measured in soil extractions") goes to neither.
ORGANIC_FROM: Final[str] = "Total carbon"
ORGANIC_TO: Final[str] = "Soil organic carbon"
ORGANIC_DEFINITION: Final[Pattern] = re.compile(r"(?<!in)organic\s+(carbon|c)\b", re.I)
TOTAL_DEFINITION: Final[Pattern] = re.compile(r"\btotal\s+carbon\b", re.I)
EXTRACT_DEFINITION: Final[Pattern] = re.compile(r"dissolved|extract|leach|\bDOC\b|purgeable", re.I)


def organic_definition(definition: str) -> bool:
    """Tell whether a data-dictionary definition makes a Total carbon column an organic carbon column.

    Examples:
        >>> organic_definition("Percent total organic carbon in less than 2 millimeter sediment samples")
        True
        >>> organic_definition("Total carbon-inorganic carbon"), organic_definition("Total carbon and organic carbon")
        (False, False)
        >>> organic_definition("dissolved organic carbon measured in soil extractions")
        False
    """
    return bool(ORGANIC_DEFINITION.search(definition)) and not (TOTAL_DEFINITION.search(definition)
                                                                or EXTRACT_DEFINITION.search(definition))


def spec_for(name: str) -> Spec:
    """Return the matching rules of one variable of the soil variable list.

    Args:
        name: Variable name as written in the list.

    Returns:
        The Spec: graded carbon patterns for the ten carbon variables, list rules otherwise.

    Raises:
        KeyError: When the variable has no rule.

    Examples:
        >>> spec_for("Total carbon").mode, spec_for("Dry bulk density").mode
        ('normalized', 'raw')
        >>> bool(spec_for("Exchangeable calcium").context.search("CEC (cmol/kg)"))
        True
        >>> spec_for("Mehlich-3 extractable iron").definition.pattern
        'mehlich'
    """
    return _carbon_spec(name) if name in CARBON_KEYS else _list_spec(name)
