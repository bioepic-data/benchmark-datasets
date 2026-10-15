# Open issues: generic harmonization (updated 2026-10-09: Acidity, Carbon, Physical, Nitrogen, Base cations, Isotopes, Biology, Phosphorus, Sulfur, total elements)

Status after the Acidity and Carbon runs (`python -m essdive_harmonize.harmonize.run --category Acidity
--category Carbon --write --compare`). "Hand-written" means the earlier pH and carbon package functions in
`essdive_harmonize/packages/`. They are used only as a check, through `<key>/handwritten_check.csv`.
Locations and values are compared with those packages.

Fixed in code means a generic rule could handle it. Data or decision means it needs a person or a decision.

## Acidity: Soil pH

**Location far from the hand-written one (> 5 km).** The hand-written work used PDFs, methods text, another
package or a specific profile file. The automatic run used the bounding-box centre or another join.

| DOI | Automatic location | Distance | Note |
|---|---|---|---|
| doi:10.15485/1835182 | bbox | 170 km | Harvard Forest site from Data_description.pdf |
| doi:10.15485/1898051 | join (3) | 274 km | site names vs metadata places (longitude sign error in metadata) |
| doi:10.15485/2283436 | join (3) | 161 km | joined to the sites table, hand-written used the profile-locations file |
| doi:10.5440/1875838 | bbox | 70 km | point from the package methods text |
| doi:10.5440/1841590 | in-file + join | 50 km | |
| doi:10.15485/2583150 | bbox | 43 km | |
| doi:10.15485/1962817 | bbox | 18 km | |
| doi:10.15485/3030227 | join (3) | 11 km | the automatic run gives one point per site, hand-written gives one kit point for all (automatic may be better) |

**Values differ from the hand-written ones** (share of hand-written values found):
doi:10.15485/2480291 (0.15), doi:10.15485/1898051 (0.48), doi:10.15485/2405147 (0.69),
doi:10.15485/2583150 (0.70), doi:10.15485/2283436 (0.93).

**QC flags.** doi:10.15485/2405147: 30 values above pH 11 (probably not pH, or another scale).
doi:10.15485/2480291: 20 values below pH 2. doi:10.15485/3016270: 1 value below 2.

**Not written:** doi:10.15485/1994876. Its pH is in `MCB2017_density_and_bulk_fractions.csv`, which
`exclude_files` (frac / density) skips for bulk variables. Decision: allow pH from fraction files?

## Carbon

### Total carbon

- **Not candidates** (no numeric data column matched): doi:10.15485/1894515, doi:10.15485/2588765 (`TotalSC`
  in CN_data.csv).
- **Values differ:** doi:10.15485/1835182 (0.00, its bare `C` column), doi:10.5440/1875838 (0.07),
  doi:10.15485/1630815 (0.17), doi:10.15485/1898051 (0.48), doi:10.15485/2583150 (0.68),
  doi:10.15485/2350837 (0.70), doi:10.21952/WTR/1506944 (0.77), doi:10.15485/2480291 (0.79),
  doi:10.15485/2283436 (0.93), doi:10.15485/2564914 (0.93).
- **Location > 5 km:** doi:10.15485/1835182 (bbox, 170 km), doi:10.15485/1898051 (301 km),
  doi:10.15485/2283436 (210 km), doi:10.5440/1875838 (bbox, 70 km), doi:10.15485/2583150 (bbox, 46 km),
  doi:10.25581/ORNLSFA.020/1638590 (in-file, 18 km), doi:10.15485/1892050 (bbox, 5 km).
- **QC, values just above 60 % C** (peat or organic horizons, check): doi:10.15485/2513843,
  doi:10.3334/cdiac/spruce.027, doi:10.5061/DRYAD.0K6DJHB5K (1 row each).

### Dissolved organic carbon

- **Units only in documents** (in review): doi:10.15485/1835182 (`DOC`), doi:10.15485/3367449
  (NEON `Soil_Total_Extractable_Organic_C`), doi:10.5440/1164833 (`DOC`).
- **Fixable in code:** doi:10.15485/3024076, unit `(mg-C/g-soil)` with hyphens is not parsed.
  doi:10.5440/1875838, the unit of `DOC_KCl_2M` is not found.
- **Porewater, skipped by the porewater exclusion** (hand-written kept them). Decision: keep porewater for
  DOC? doi:10.15485/1602783 (marsh porewater, also no soil context), doi:10.5440/1226245 (Barrow water
  chemistry), doi:10.5440/1875838 (`PortPorewater_ColumnExpt`).
- **Values differ:** doi:10.15485/2570819 (0.81).
- **QC:** doi:10.15485/3422709, 22 values below 0.

### Soil organic carbon

- **Not candidates:** doi:10.15485/1630815, doi:10.15485/1910300 (`TOC (dry wt%)`, values with ±, should
  match after the rescan; recheck), doi:10.15485/3024414, doi:10.15485/3030222.
- **Values differ:** doi:10.21952/WTR/1572186 (0.29), doi:10.21952/WTR/1506944 (0.63),
  doi:10.15485/2405147 (0.69).
- **Location > 5 km:** doi:10.5440/1841590 (49 km), doi:10.15485/3003878 (bbox, 28 km).
- **QC, above 60 %:** doi:10.25581/ornlsfa.025/1838660 (7 rows), doi:10.15485/1659374 (1 row).

### Soil inorganic carbon

- **Not candidates:** doi:10.15485/1454273, doi:10.15485/1630815, doi:10.15485/1631972 (`Tot_CO3-C`).
- **Values differ:** doi:10.15485/1631979 (0.01), doi:10.15485/1725884 (0.19),
  doi:10.21952/WTR/1506944 (0.63).
- **QC, below 0:** doi:10.21952/WTR/1572186 (2 rows).

### Soil organic matter

- **QC, below 0:** doi:10.5440/1358456 (2 rows).
- **Location 7 km:** doi:10.15485/3030227.

### Loss on ignition

- **Not written:** doi:10.3334/CDIAC/SPRUCE.005 (no strong column match; hand-written derived it from the
  peat characteristics).
- **QC, above 100 %:** doi:10.15485/2566016 (1 row).

### Soil organic carbon stock

- **Unit:** doi:10.15485/2438343, values around 2,957 with the dictionary unit `kg C m-2`, probably
  g C m-2. All 34 rows are flagged.
- **Values differ:** doi:10.15485/2283436 (0.78, also 186 km), doi:10.15485/2283432 (0.92).

### POM-C, MAOM-C, WEOC

- **POM-C:** doi:10.15485/1894515 (`propC.fLF` / `propC.oLF` are proportions, no unit);
  doi:10.15485/3024414 (values differ, 0.11). Most of the 24 packages in review are false matches (e.g. a
  "point of measurement" height column).
- **MAOM-C:** doi:10.15485/1835182 (`maomc` / `MAOMC`, units only in documents); doi:10.15485/1894515 (no
  strong column match); doi:10.15485/3024414 (values differ).
- **WEOC, not candidates:** the hand-written version took water-extracted DOC as WEOC.
  doi:10.15485/1725884 (`EastRiver_2014_SoilPits_H20ExtractedCarbon.csv`), doi:10.15485/2455027
  (`TOC_leachate`, `DOC`), doi:10.15485/2583150. A file-context rule would be needed (DOC columns in
  water-extract files).

## Physical (run 2026-10-08; no hand-written packages, checked by spot checks and QC)

Texture check: 99 % of the 2,138 samples with sand, silt and clay sum to 95-105 %.

### Dry bulk density
- **Source label wrong:** doi:10.15485/1910300, `Bulk Density (kg/m3)` with values 0.5-2.7 (g cm-3), so it
  is written as 0.0005-0.0027 g cm-3. All 11 rows are QC-flagged. Decision: override the source label?
- **QC below 0.02 g cm-3:** doi:10.3334/CDIAC/SPRUCE.005 and doi:10.3334/cdiac/spruce.027 (8 each, zeros,
  probably missing), doi:10.15485/1959350 (5), doi:10.5440/1346200 (2), doi:10.5440/1185213 (1).
- **QC above 2.65 g cm-3:** doi:10.15485/2480291 (7, one value 10000 = placeholder),
  doi:10.15485/3030222 (3), doi:10.25581/ORNLSFA.020/1638590 (3), doi:10.15485/2438579 (1),
  doi:10.15485/3374640 (1).
- **No depth in the source table:** doi:10.15485/3367449, doi:10.15485/1959350, doi:10.15485/1960313,
  doi:10.15485/3025240, doi:10.15485/2583150, doi:10.15485/3024076.
- **In review:** doi:10.15485/1734577 (pedotransfer-calculated hydraulic parameters; skipped as water by
  name), doi:10.15485/1861432 (model input), doi:10.21952/WTR/1506941 (figure sheet).

### Sand, silt, clay
- **Texture sum about 29 %:** doi:10.15485/2405147 (31 samples; sand is %, silt and clay are probably
  reported differently). doi:10.15485/2350835: 1 sample at 86 %.
- **In review:** doi:10.15485/1734577, doi:10.21952/WTR/1506941 (water by file name),
  doi:10.15486/NGT/1434046 (no rows with coordinates).

### Porosity, particle density, coarse fragments, thermal conductivity
- **Porosity in review:** doi:10.15485/1861432 (model), doi:10.21952/WTR/1506941 (figure sheet).
- **Coarse fragments QC above 100 %:** doi:10.15485/1671826 (4 rows).
- Particle density: only doi:10.15485/2583150 (39 rows; unit read from `particle_density_gcm3`).

### Electrical conductivity
- **Nothing written.** doi:10.15485/2405147 is an EMI geophysics inversion grid (excluded for EC),
  doi:10.6084/M9.FIGSHARE.7834406.V2 has EC at 5/15/50 cm sensor depths with no unit. Neither is
  sample-level soil EC.

## Nitrogen, Base cations, Isotopes (run 2026-10-09; no hand-written packages, checked by spot checks and QC)

Shared changes made for this run (Acidity, Carbon and Physical rerun afterwards: unchanged except DOC +4 packages
and WEOC +1, from the new unit spellings; doi:10.15485/3422709 left DOC because its column is a cube-root effect
size):
- The sample-count filter matched `N`, `%N`, `Total N` (nitrogen); it now only matches lower-case `n`. Stats filter
  also drops `deviation`, `precision`, `SD` inside names, `lower` / `upper`, effect sizes, cube roots, residuals.
- Units: written-out units (`milligrams_of_N_per_gram`), dots and hyphens (`µg.g-1`, `mg-N/g-soil`), `g soil-1`,
  a micro sign lost to bad encoding (`�g`), run-together `mmolc`, `meq100g`; column names with a unit before a
  species tag (`mg/kg_NO3-N`) or run together (`ugNgsoil`).
- variable_config.csv has two new columns: `column_exclude` (column names that are not the variable) and
  `require` (the column name, group row, unit, data dictionary definition or file name must contain it).
- Water terms in `exclude_files` (`pore water`, `soil water`, `lysimeter` ...) now exclude a file even when its
  name also says soil (`Soil_Pore_Water.csv`).

### Total nitrogen (25 of 46 written)
- **Unit assumed (%)** for 11 packages with a bare `N` / `TotalN` column; values look like % except
  doi:10.15485/1835182 (median 0.003: maybe g/g or a fraction file). Check.
- **Not written, decision or data:** doi:10.15485/2405147 (`Total N` values not plausible as %),
  doi:10.15485/1828795 (total N in mg N/L: water), doi:10.15486/NGT/1434046 (no rows with coordinates),
  doi:10.21952/WTR/1495379, doi:10.5440/1299259, doi:10.15485/1985920, doi:10.15485/1830417 (matched column
  is not in the table as read: multi-row headers or summary tables).
- The other reviews are correct exclusions (FT-ICR formula tables, needles, litter, gas tables).

### Nitrate, ammonium, total extractable N, DON
- Standard unit is per soil mass (mg N kg-1), so extract or water concentrations (mg/L, µM) are not converted:
  doi:10.15485/2587853 (`Soil_KCl_NH4_uM`), doi:10.15485/1773008, doi:10.15485/1828795, doi:10.15485/2526684.
  Decision: convert KCl-extract concentrations with the extract ratio from the methods? (not done).
- **Unit not found:** doi:10.15486/NGT/1582598 (`NO3`, `NH4`), doi:10.15485/1874586 (`Ammonium`),
  doi:10.15485/1969113, doi:10.5440/1358456, doi:10.5440/1454263, doi:10.15485/1577267 (`µg N-NO3-`
  without per gram; the DON column of the same file is written).
- doi:10.15485/2530252 `NH4N_KClExtr`: the dictionary says mg N per g but describes Fe(II); written as
  mg N/g (median 44.7 mg N kg-1). Check.
- doi:10.15485/3021477 `Nitrate_ppm`: the dictionary says ppb (written as ppb, median 0.036). Check.
- DON / TEN: fumigated extracts (microbial biomass) are left out; unfumigated kept.

### C:N ratio (23 of 27 written)
- Unitless: the column is taken as a mass ratio. QC above 200 or below 1: doi:10.15485/1896308 (10),
  doi:10.15485/2480291 (10).
- Density-fraction columns (`C/NFLF`, `C/NHF`) are excluded (doi:10.21952/WTR/1572186).

### Base cations (Ca, Mg, K, Na, Al: 3 of 6; ECEC 1; CEC 0)
- `require` keeps only exchangeable columns (`exch`, `meq`, `cmol`, `extract`, `BaCl2`, `NH4OAc` ... in the name,
  unit, group or dictionary definition). Total-element columns are left out: doi:10.15485/2564914 (XRF %),
  doi:10.15485/2350835, doi:10.15485/2405147.
- doi:10.15485/2588765: BaCl2-exchangeable, mg kg-1 converted to cmol(+) kg-1 with the valence (known from the
  dictionary definition).
- **QC Na above 50 cmol(+) kg-1:** doi:10.15485/2583150 (19), doi:10.15485/1960313 (6). Check (saline or units).
- **CEC not written:** doi:10.15485/2283432 `Cation Exchange` has no unit.

### Isotopes
- **Tracer experiments:** files named label / tracer / enrich / pulse are skipped (doi:10.15485/1454273
  `Nitrogen label`). Two 13C-labelling packages are still written and flagged by QC (values above 0 per mil):
  doi:10.3334/CDIAC/ORNLSFA.001 (PiTS-1 13C pulse labelling, 74 of 185 rows) and doi:10.3334/cdiac/ornlsfa.010
  (13C-glucose / cellulose microcosms, 44 of 102). Decision: drop labelled packages entirely?
- doi:10.15485/2480291 `Blodgett_Initial_Characterization_20200410.csv` holds several stacked tables; its 13C
  column mixes delta values with other numbers (20 QC rows). Same file as the pH value mismatch above.
- **Radiocarbon:** Fraction Modern columns are excluded (converting needs the measurement year); Δ14C only.
  Not written for that reason: doi:10.15485/3016270, doi:10.15485/3363470, doi:10.5061/DRYAD.0K6DJHB5K.
  Decision: convert FM to Δ14C with the sampling year?
- doi:10.5440/1364062 (radiocarbon of ecosystem respiration and soil pore-space CO2): its `14C` and `14C_age`
  columns are gas samples (rows by `material`), but the file name does not say so; written for radiocarbon and
  age. Check / exclude.
- Radiocarbon age: calibrated ages are excluded (conventional 14C age only).
- Density fractions (FLF, HF, OLF, MAOM, POM, `Fraction δ13C`) are left out of the bulk-soil isotope variables.

## Biology, Phosphorus, Sulfur (run 2026-10-09; no hand-written packages, checked by spot checks and QC)

Shared changes made for this run (all earlier categories rerun afterwards: unchanged except DOC +2 packages,
doi:10.5440/1410348 and doi:10.5440/1164833, porewater DOC in mg/L now read from a units row with 'NA' cells):
- A units row whose cells are mostly placeholders ('none', 'NA') is now recognized (doi:10.5440/1618325).
- When the units row gives a unit that does not convert and another source does, the other source is used and the
  note says `units row says '<unit>'`. Two cases, one each way:
  doi:10.15485/2438343 SOC stock (units row `g kg-1` is wrong, dictionary `kg C m-2` right) and
  doi:10.15485/2570819 total P (units row `mM`, dictionary `ppm` belongs to the porewater file; the written
  values, median 0.01 mg P kg-1, are probably wrong). Decision: drop 2570819 total P?
- Variables with an `analyte` column (P fractions; later Fe speciation, mineralogy) get the source column name.
- Units: `?g` (lost µ), R-style `kg.ha`; sulfate charge (valence 2) for meq conversions.
- Water exclusion also covers `peeper`, `PW` and `GW` in file names.

### Biology
- **Fine root biomass (2 of 7):** doi:10.15486/NGT/1558773 (kg/ha, < 2 mm), doi:10.5440/1735941 (g m-2).
  Not written: per-core grams without area (doi:10.15485/2999588), per-volume g cm-3 (doi:10.15485/2483574),
  no unit (doi:10.15485/1835182, doi:10.3334/CDIAC/ORNLSFA.001).
- **Microbial biomass C (9 of 11):** method is chloroform fumigation-extraction; whether kEC was applied is not
  recorded. doi:10.15485/2480291 is the raw (uncorrected) column. **QC:** doi:10.15485/3024076 (36 rows above
  10,000 mg C kg-1; source says mg C/g soil, median 6,100 mg C kg-1: probably µg/g). Check.

### Phosphorus
- **Resin / extractable phosphate (3 of 22):** most candidates are water samples (mg/L, µM) or have no unit.
  doi:10.15485/2350835 `Phosphates (%)` is a mineral composition (excluded).
- **Total P (7 of 18):** see the 2570819 conflict above. The rest are FT-ICR formula tables and water files.
- **Mehlich-3, Bray-1:** doi:10.15485/2583150, doi:10.15485/2588765, doi:10.15485/3021477 (dictionary says ppb,
  median 0.05 mg P kg-1: check, as for its nitrate).
- **P fractions:** doi:10.5440/1618325 (Herndon, sequential: water, base, acid, humic, organic, dithionite; mmol
  kg-1 converted). doi:10.15486/NGT/1821683 is litter (excluded).
- **Olsen, oxalate P: nothing written.** The Olsen candidate is a stream bicarbonate column; the oxalate candidate
  (doi:10.15485/1898051 `Feo-p`) has no unit.

### Sulfur
- **Extractable sulfate (3 of 31):** most candidates are water / porewater. doi:10.15485/2583150 converted from
  meq/100 g (8 QC rows above 5,000 mg S kg-1: check). doi:10.15485/1507800 values 0 to 0.035 ppm (59 of 93
  zeros). doi:10.15485/1908426 matched `Initial Ni addition` and doi:10.15485/2350835 a mineral composition
  (both excluded).
- **Total S (4 of 17):** XRF, ICP and an assumed % (doi:10.15485/1908426, 4 rows).

## Major and trace elements, total (run 2026-10-09; 38 variables; checked by spot checks and QC)

10 packages written in all; most elements come from 1 to 7 packages. Written: doi:10.15485/2350835 (XRF-type major
and trace table, wt-% and ppm, 21 elements), doi:10.15485/2564914 (XRF %), doi:10.3334/CDIAC/SPRUCE.005 (peat,
µg/g), doi:10.5440/1860505 (mg/kg), doi:10.15485/2405147 (XRF/XRD sheet, rare earths), doi:10.15485/1908426 (nmol/g),
doi:10.15485/1773008 (wt.%), doi:10.15485/3003878 (`Fe_pct`, `Al_pct`), doi:10.15485/2998779 (7 soil rows),
doi:10.3334/cdiac/spruce.027 (total Hg, ng/g, HNO3 digestion). Nothing written for As, Sb, Se, Ag, Li, Be, Ge, Tl.

How totals are told apart (variable_config.csv): a per-mass unit is required (mg/L and µM fail the conversion),
no unit is assumed; `column_exclude` (now tried on the column name, its group row and its data dictionary
definition) drops exchangeable / extractable / soluble / oxalate / dithionite / HCl / KCl / meq / Fe(II) /
mol-per-mol columns and oxides (`Fe2O3`, `CaO`); files named extract / leach / sequential / exchange / oxalate /
XANES / standards are skipped; `skip_repeated` drops an element repeated in one table (one column per extraction
step, doi:10.21952/WTR/1572186, doi:10.15485/1839189).

Shared changes made for this run (all configured categories rerun; the changes in the earlier outputs are listed):
- **Rows of other materials are dropped** when a sample-type / material / matrix column names them (gas, water,
  rock, leaves, roots ...); a table with only such rows is skipped. Rows whose extraction / treatment / method /
  fraction column matches `column_exclude` are dropped. Effects: doi:10.5440/1364062 (CO2 radiocarbon) is no
  longer written for δ13C, Δ14C or 14C age; doi:10.15485/2513843 TC (leaf and root decomposition, 654 rows) and
  doi:10.5440/1410348 DOC (permafrost water) are gone; doi:10.5061/DRYAD.0K6DJHB5K keeps only bulk rows (δ13C
  247 to 63); doi:10.15485/3021477 and doi:10.15485/2998779 keep only soil rows.
- **ppm / ppb in a table of per-litre concentrations** (another column in mg/L, `oxymgL` ...) are read as mg/L and
  µg/L: doi:10.15485/1507800 nitrate and sulfate are no longer written (piezometer water).
- `wt-%`, `weight %` read as %. doi:10.15485/2350835 total P is now written.
- An empty candidate list no longer stops `--all`.

Check / decide:
- Methods are mostly `unknown`: the column names do not say XRF / digestion, and the package text rarely names
  the variable. doi:10.15485/2350835 and doi:10.15485/2564914 look like XRF (Si in wt-%).
- doi:10.3334/CDIAC/SPRUCE.005: Cd, Cr, Cu, Pb, Mo, Ni medians are 0 (probably below detection written as 0).
- doi:10.15485/2998779: the 7 soil rows kept are `Ash and acid dissolving` / `HF/HClO4` extractions; check that
  these are totals.
- Elements as oxides (`Fe2O3`, `Na2O` in doi:10.5440/1342956 and doi:10.5440/1417652) are skipped. Decision:
  convert oxides to elements?
- doi:10.15485/1839189 and doi:10.21952/WTR/1572186 report elements per extraction step (repeated columns):
  not written.

## Changes 2026-10-12 (from the Total carbon review)

- Water rule (`WATER` in auto.py): stream / river / creek alone no longer mark a file as water (site names such as
  East River); only with a sample-type word (`stream_chemistry`, `river water`) or `outlet`. Effects:
  doi:10.15485/1577267 microbial biomass C now written (322 rows, `East_River_Pumphouse_Microbial_Biomass`);
  doi:10.21952/WTR/1506941 sand, silt, clay now written (Tokunaga et al. sediment particle size, 52 rows each).
- Microbial biomass C: `biomass` removed from its `exclude_files` (it skipped every "Microbial_Biomass" file).
- Sand, silt, clay: `column_exclude` `\+` drops combined fractions (`clay + silt, %`).
- triage.csv: doi:10.15485/1464237 excluded (GEIA atmospheric emissions inventory, no soil data).
- Selection rules: bare `ratio` exclusions are now `(?<!concent)ratio` (they matched inside "concentration");
  Total carbon `col_strong` also takes `C (%)`, `c_perc`, `C_wt`, `C mg/g`, `perC`. Units-row type labels (`num`,
  `string`, `YYYY...`) are no longer taken as units.
- Downloads: 1764443, 1821491, 1785525 and the WHONDRS packages 1923689, 2428003 (`--doi-file`; media archives
  skipped).
- Total carbon: 60 -> 63 written (106 candidates). New: 1839288 (612 rows), 3374640, 1185213, 1764443, 1821491,
  1785525, 1988078 (117), 1894515 (38), 1659374 (20). 2428003 adds pH (614), DOC (1102), TEN (546) but not TC.
- Plant-only packages (`plant_only` in candidates.py): a package with a plant term (PLANT_TERMS) in its
  exclusion_terms and no "soil" in its soil_context is not soil. Found by doi:10.15485/3933967 (leaf C and N,
  Seward 2014; its only soil context, `permafrost`, came from the NGEE Arctic project text), which had been written
  as soil Total carbon and C:N. 54 packages are plant-only; 14 were candidates for some variable (leaf C/N, SPRUCE
  photosynthesis, air isotopes, SPRUCE.018 porewater, litter decomposition); only 3933967 had been written.
- Column names (selection/matching.py `_clean`): a leading 5-digit method code (`01395_C_percent`, WHONDRS) is
  dropped and a hyphen between letters becomes a space (`total-carbon-concentration`, doi:10.5440/1785119) before
  matching; raw-mode rules try both the original and the cleaned name. Added: 1785119 Total carbon and SOM; the
  `01395_C_percent` columns of 1729719, 2428003, 2529428 (sediments, see the WHONDRS item below).
- Matching data columns on their dictionary definitions was tried as a dry run (404 new matches in 98 packages)
  and not used: most were wrong (CO2, organic C fractions, detection limits, plant tissue, char, values normalized to
  organic C; `NaN` -> sodium, `obs` -> lithium). Its few real hits became name patterns instead: Total carbon
  `^c(arbon)? ?(tot(al)? ?)?(wt|weight) ?(%|perc|pct)` (1960313, 3024128, 1631278) and a case-sensitive `pC`
  (2588765, 1835182; new `col_strong_cased` in CarbonSpec, since `Pc` is crystal pressure or photosynthesis);
  Total nitrogen `n_perc` / `N_percent` / `Nperc` and case-sensitive `pN`.
- triage.csv: both rows of doi:10.15485/3484503 deleted (`*` "no other selected variables" and SOM "no data");
  the package has soil Total_C_percent, Total_N_percent (107), Organic_Matter_percent (108), isotopes, N rates
  (user decision 2026-10-12). Total nitrogen `^total.?n(\b|_)` so `Total_N_percent` matches.
- River and stream-bed sediments count as soil (user decision 2026-10-12): WHONDRS river-corridor and EXCHANGE
  sediments (2428003, 2529428, 1923689, 1729719) stay in through `sediment` in SOIL_TERMS.
- Hyphen cleaning keeps a hyphen between two capitals (a minus sign): `OC (%) (TC-IC)` (1725884) had become a
  Total carbon column.
- triage.csv: the `*` "water" row of doi:10.15485/1729719 (WHONDRS S19S global river-corridor sediments) deleted,
  following the sediment decision; its per-variable pH row (`water`) is kept.
- Total carbon -> Soil organic carbon by data-dictionary definition (user decision 2026-10-12;
  `rules.organic_definition`, `matching.organic_defined`, used by the selection evidence and by
  `candidates.matched_columns`). Why: a generic column name such as `C_percent` or `percentC` matches Total carbon,
  but some packages define it as organic carbon. Found in the Total carbon review: the WHONDRS `01395_C_percent` is
  "Percent total organic carbon in less than 2 millimeter sediment samples" (1729719, 2428003, 2529428; 2428003 and
  2529428 had been written as Total carbon, 554 and 84 rows), `percentC` in doi:10.15485/3030222 is "Percent soil
  organic carbon" (203 Total carbon rows), `C_percent` in 3021477 is "Total organic carbon content" (4 rows). A column
  that matched Total carbon and whose definition says organic carbon (not "inorganic", and not also "total carbon")
  is dropped from Total carbon and given to Soil organic carbon as strong. Only already-matched Total carbon columns
  move, because general definition matching was too noisy (dry run, above). The dry run over all 203 Total carbon
  column matches found 16 organic definitions; the other 11 (TOC, OC, Organic_C_EA ...) were already related
  matches, not written as Total carbon, and already written as SOC. An extract or dissolved definition (dissolved,
  extract, leach, DOC, purgeable) does not move: the first run sent doi:10.15485/3367449
  `Soil_Total_Extractable_Organic_C` ("dissolved organic carbon measured in soil extractions", 417 rows) to SOC.
  Result: Total carbon 64 written (9,946 rows), SOC 26 written (4,496 rows), hand-written close TC 16/44, SOC 7/19.
- Isotopes: `del(ta)?.?13c` / `del(ta)?.?15n` so `del_13C_per_mil` (3484503), WHONDRS `63515_del_13C_permil`
  (1729719) and `Del 13C` match. delta13C 22 written, delta15N 9 written.
- doi:10.15485/3484503 now written: Total carbon, Total nitrogen (107 rows each), SOM (108), delta13C, delta15N (107);
  all rows are Material = Soil. Depth and date are empty (the date is only in Sample_Name, e.g. _20240422).
- `pC` / `pN` in a table with proximate-analysis columns (plignin, phemicellulose, psoluble, pash) are skipped
  (auto.py `PROXIMATE`): doi:10.15485/1835182 `Cbud.csv` `pC` is percent C of the added litter, not soil (32 rows had
  been written as Total carbon; the soil %C is `field_data.csv` `C`). Skipping every table with lignin or cellulose
  columns was checked and not used: it would also drop SPRUCE.005 peat characteristics and soil polymer tables.
- triage.csv: the DOC and SOC "no data" rows of doi:10.15485/1729719 deleted (it has `Extractable_NPOC_mg_per_L`,
  508 values, the same column as DOC in 2428003, and organic C routed to SOC). Only its pH row (`water`) is left.
- Repeated tables (auto.py, user decision 2026-10-13): a later file is also dropped when an earlier kept file is
  mostly inside it (overlap >= 80% of the smaller file and >= 50% of the larger, on depth | date | value | lat | lon).
  Why: doi:10.15485/2588765 `ldw_dat_raw.csv` (126 %C, unaveraged) repeats `CN_data.csv` (104, replicates within
  10 m averaged) under other IDs; 85 samples have the same plot coordinates and %C, but that is only 70% of the raw
  file, so the old test (80% of the later file) missed it and 230 rows were written. Its coordinates are one metadata
  point, so the test cannot require in-file coordinates; the 50%-of-larger condition keeps a small file whose few
  values occur in a large one. Simulated on every harmonized variable: only this file is dropped.
- File names no longer skip formula tables on their own (auto.py FORMULA_DERIVED, `_derived_formula_table`; user
  decision 2026-10-13): a file named as FT-ICR / formula / metabolomics is skipped only with formula columns (atom
  counts, or Mass / m/z / formula, or both H:C and O:C). Why: doi:10.15485/1868940 `FTC_FTICR_master.zip/.../emsl_cn.csv`
  (93 soil %C and %N) and its soil property, horizon and NEON biogeochemistry tables, and WHONDRS `..._NPOC_FTICR.csv`
  were skipped by name. Dry run: 51 files skipped by name only; 24 real FT-ICR tables stay skipped. Follow-up fixes from
  the before/after comparison (2026-10-13): figure sheets also when 'Fig' is followed by a digit or '.' (1766328
  "Fig2a. ...", "Fig3a. TN (%)" wrote pH and total sulfur); `\bgain\b` excluded for SOC and the total elements (1868940
  "CO2 Correction Calculations" incubation gain written as SOC and potassium); `nh4.?ac` excluded for the total elements
  (1868940 `Al/Ca/Mg/K/Na_NH4Act.ugg`, NH4OAc-extractable); 'liquid' / 'aqueous' are not soil materials (1969118 surface
  water NPOC written as DOC).
- Normalized element compositions are skipped (auto.py `_normalized_composition`, user decision 2026-10-13): a table
  with >= 5 element columns whose rows sum to 100 % gives shares of the measured elements, not concentrations. Found:
  doi:10.15485/1729719 `WHONDRS_S19S_Sediment_XRF_ElementalAbundance.csv` (11 elements; Si median 58 %, Ca up to 57 %,
  Al mostly 0), which had been written as total Al, Ca, Fe, Mg (276 rows each).
- A stated unit whose converted values are mostly (> 50 %) outside the plausible range sends the column to review
  instead of writing it (auto.py, user decision 2026-10-13). Before, only assumed units were tested; stated units were
  only flagged in qc.csv. Found: doi:10.15485/1868940 `clay.gg` / `sand.gg` / `silt.gg` hold percent but the name says
  g/g (909 - 7,700 %). From the qc.csv files this also sends to review: 1910300 bulk density ("kg/m3", 0-0.003 g cm-3),
  doi:10.5440/1342956 and 1417652 SO4 in "wt. %" (6,100 - 44,100 mg S kg-1), 2438343 C_Stock (308 - 12,021 kg C m-2),
  2480291 pH (0.04 - 6.5) and delta13C (up to +0.76).
- Leftover rows without a material are dropped (auto.py `_soil_rows`, 2026-10-13): after the 'liquid' / 'aqueous'
  change, doi:10.15485/1875296 `SR_2021_ICPOES_TOC_data.csv` (469 pore-water rows, 'liquid>aqueous') kept only its
  reporting-format metadata row analysisDetectionLimit (material 'NA', value 1), written as 1 % total carbon. Rows with
  no material that are fewer than the dropped rows of other materials are now dropped too.
- Result of the 2026-10-13 fixes (formula file names, figure sheets, gain / NH4OAc exclusions, aqueous material,
  normalized compositions, implausible stated units, leftover metadata rows), compared with the outputs before them:
  added 1868940 (pH 313 rows from 7 tables, SOC 188, Total carbon and Total nitrogen 93 each from emsl_cn.csv, bulk
  density 19), 1729719 (DOC 508, clay 273), 1764443 DOC fticr_key.csv (replaces the same data in wsoc.csv), 1821491
  porosity 96. Removed: river / stream water DOC that had been written as soil DOC (Material 'Liquid>aqueous': WHONDRS
  1895159, 1898912, 1898913, 1969118, part of 2406989; about 1,950 rows); 1729719 XRF relative abundances; 1868940
  incubation gain, NH4OAc cations and texture (.gg); 1766328 figure sheets; to review for implausible stated units:
  1910300 bulk density, 1342956 / 1417652 sulfate, 2438343 SOC stock, 2480291 pH and delta13C. Totals: Total carbon 65
  written (9,881 rows, hand-written 17/44), SOC 27, Total nitrogen 34, DOC 31 (7/15), pH 61 (18/37).
- SOC column_exclude (variable_config.csv, user decision 2026-10-13): `\bgain\b|fumig|/\s*tn\b|(?<![a-z])ratio|nacl|
  \bpp\b|pyrophos|extract|\bdoc\b`. Why: doi:10.25581/ornlsfa.025/1838660 `TOC_Fumigated` / `TOC_UnFumigated`
  (chloroform fumigation-extraction extracts, the inputs of microbial biomass C) and doi:10.21952/WTR/1572186 `TOC/TN`
  (a ratio) and the extraction fractions `NaCl-whole OC`, `PP-whole OC`, `PP-AS OC`, `PP >1kD OC`, `PP-SPE OC` were
  written as SOC. Before / after: 1838660 140 -> 0 rows, 1572186 159 -> 67 (TOC 18 + OC 49 kept); nothing else
  changed; SOC 26 written, 4,452 rows, hand-written 7/19. A bare `ratio` matched inside "concentration" (3367449
  Soil_TOC definition) and "Saturation" (1785525 Treatment values, dropped as an excluded treatment), so it is
  `(?<![a-z])ratio`.
- triage.csv (user decision 2026-10-13): doi:10.15486/NGT/1866615 and NGT/1905761 (Panama leaf C and N) excluded as
  plant tissue: their `C_g_m-2` (leaf C per leaf area) had been written as SOC stock (751 rows), and their leaf C
  (`C _mg_gDW-1`) was kept out of Total carbon only by an unparsed unit; soil_context 'soil', so the plant-only rule
  missed them. doi:10.3334/CDIAC/TCM.003 (European no-till mitigation compilation) excluded as metaanalysis like the
  other TCM packages: `westpost2002fulldata.csv` had been written as SOC (1,378 rows). Before / after: only these rows
  removed; SOC 25 written (7/19), SOC stock 3 (1/4), Total carbon 65 (17/44) unchanged.
- Lab manipulations of field samples (auto.py `_field_rows`, user decisions 2026-10-13): a treatment column whose
  levels or name (with lab text) mark a lab manipulation keeps only its field-condition levels (control, unburned,
  ambient, field, time zero / initial / pre-incubation); a lab column without one sends the column to review; a
  treatment column that does not change the value of one sample only labels repeated rows and one row per sample is
  kept. Written rows and the review queue note what was dropped. Why: doi:10.15485/1959350 (cores burned in the lab
  under a cone calorimeter) had 470 Total carbon rows: lab-burned cores plus 5 incubation / DNA rows per core x horizon;
  now 30 rows (the unburned controls), as the hand-written package. Field experiments are untouched (SPRUCE, Blodgett,
  SWELTR in situ warming, AU-DRO drought, FACE, plot experiments). Dry run: lab columns in 1959350, 2438579, 1785525,
  1821491, 1866269, ornlsfa.010. Not caught: 1868940 (levels CON / FTC), 1764443 (Wetting / Drying / FM). Repeats are
  found only through such a column: cutting id suffixes alone merged different horizons and layers (1729719 BULK-M /
  BULK-U, 1618325 -O / -M, 2322568 anoxia_013 / _014).
- Total carbon column_exclude `[._ ]g$` (2026-10-13): masses in grams had been written as % total carbon:
  doi:10.15485/1764443 `TC_targetOD_g`, `TC_targetMoist_g`, `TC_weighed_g` (soil weighed into incubation cores; 325 rows,
  now not written) and doi:10.15485/2438579 `initial.total.C.g` (12 rows; C.percent kept). Concentrations such as
  `Carbon_mg/g` are not affected.
- A bare 'N' column of whole numbers in a table of statistics (mean +- sd cells, sd / se columns, or summary / mean
  in the name) is a sample count (auto.py `_count_column`): doi:10.15485/1785525 wsoc_soils_summary.csv `N` = 5 had
  been written as total nitrogen 5 %.
- Result of the lab-manipulation rule (re-run of 17 variables): 1959350 470 -> 30 rows (TC, TN, C:N, pH; texture 26,
  BD 19); 1821491 95 -> 32 (control cores; DOC 505 -> 169); ornlsfa.010 TC 102 -> 30, MBC / DOC 384 -> 192;
  1785525 SOC 59 -> 15 (Time Zero); 2438579 TC 36 -> 12; field experiments unchanged. Total carbon hand-written 18/44.
- Suffix id columns (fields.py `_drop_suffix_ids`, 2026-10-13): an id column whose every value is another id column's
  value plus a suffix ('core.id.hor.incub.DNA' = 'core.id.hor.incub' + '-gDNA' / '-cDNA', the DNA library) is left
  out of the id, unless that would make ids repeat that were distinct. Re-run of the 74 written variables: only
  doi:10.15485/1959350 changed (7 variables, id_type 'core.id.hor.incub', same rows, no repeated ids).
- Methods from the dictionary, wider sentences and package documents (auto.py `method_for`, `_methods_in`,
  `_method_column`; documents.py; user decision 2026-10-13). After the column name, the method patterns are tried on
  the column's data dictionary definition ('Soil carbon from combustion analyzer', 2588765), then on the package text,
  then on the package's own documents (PDF / docx / txt user guides and methods files, CSVs named method, dd, flmd,
  codes ...; PDFs need pypdf). For 'Total X' variables the sentences also count when they name the element without
  'total' ('%C and %N on an Elemental Analyzer', 1894515; 'carbon concentration', 1839288). Loose sentences and every
  document sentence are skipped when about dissolved / extracted / gas samples, water quality, micro-imaging or
  lipids (NOT_BULK); document sentences over 500 characters (table rows run together) are skipped; 'N/A' is not an
  element pair. A per-row method column ('TC Method') gives the method where its values match a pattern, else its
  value goes in the row's notes (1342956 'SOIL 0.20', LECO program codes). Found by the Total carbon method check
  (tmp/total_carbon_review/tc_method_check.xlsx: 52 of 64 packages report the method, 19 written before). Dry run over
  the written outputs: 58 package columns unknown -> a method, none lost; each checked against its sentence.
  Tightened during the dry run: a first version split metadata sentences on ' | ' (6 methods lost), joined PDF table
  rows into long 'sentences' and took water-quality pH ('water temperature, and pH'), mu-XRF imaging of Ca and PLFA
  'fatty acid' delta13C as methods.
  Second step: the element as a word in a list ('nitrogen and carbon on a Vario EL Cube', 1868940; 'Total nitrogen,
  carbon, and sulfur contents ... combustion elemental analysis', 1773008; 'carbon (C) and nitrogen (N) content',
  1346200), 'percent carbon' (NGT/1810164), and dictionary-like CSVs under other names (header starting with a field
  column and naming a description column: 2566016 metadata_bocas_all_master.csv; data tables with a Description
  column, 2480291 / 2572883, are not documents). Total carbon +12 packages, Total nitrogen +5, nothing lost. Result:
  Total carbon method written for 50 of 64 packages (19 before); the 14 left are the 10 that do not report it, the 2
  unclear (2425968, 1892050, radiocarbon combustion only), 3367449 (TC calculated as ROC + TOC400 + TIC) and 1839288
  (the sentence is cut at 'UC. Davis').
- Method sentences for 'Total X' variables (auto.py `_method_sentence_patterns`, 2026-10-13): the method search also
  reads sentences naming the variable as a coordinated phrase ('Total organic and inorganic carbon were determined
  using a Shimadzu TOC-L ... Solid Sample Combustion Unit', doi:10.15485/1630815) or by its element symbol ('total C
  and N ... Flash EA', 'Total C and N ... Leco Tru-Spec CN combustion analyzer'); the name alone ('total carbon')
  missed them. Dry run over the 74 written variables: 13 package columns unknown -> dry_combustion, all checked
  against their sentence (Total carbon 1630815, 1631972, 1959350, 2438579, 2564914, 2570819 Soil_C and TC, 2583150,
  3024076, ornlsfa.034/2530530, 1785119; Total nitrogen 1959350, 1785119); no other variable changed.
- doi:10.15485/1630815 ExtendedDataTable2.csv is a transposed summary table (properties in rows: Total Carbon (wt.%),
  TIC, TOC, N, S, P; locations Missouri / Florida A, B, C, Mean, SD in columns). The location-C column matches the
  Total carbon pattern 'C', so its six values (TC 20.8, TIC 0.82, TOC 20, N 1.59, S 2.82, P 0.15) are written as Total
  carbon, with the row labels as ids and the bbox centre (+-714 km) though the table gives DMS coordinates. Open:
  send transposed tables to review (first column = property names with units, value column = a sample label).
- PDF reading (documents.py, 2026-10-14): a missing pypdf now gives one warning per run instead of a silent skip. The
  outputs were made with /Users/ukaraoz/miniconda3/bin/python, which has pypdf 6.20.1; the repo's .venv (Python 3.14)
  has neither pypdf nor pandas, so it cannot run the harmonizer, and pyproject.toml declares no dependencies (no
  [project] table yet). Dry run with pypdf blocked: 16 package columns (1,765 rows) lose their method and nothing else
  changes (Total carbon SPRUCE.005, 1109232, 1185213, 1342956, 1346200, 1464956, 1618325; Total nitrogen SPRUCE.005,
  1618325; soil pH 1618325; clay / sand / silt 1346200, 1860505). Open: declare the dependencies.
- Soil pH method names (variable_config.csv; auto.py NOT_BULK; 2026-10-14): 'potassium / calcium / barium chloride'
  count as KCl / CaCl2 / BaCl2, and only 'soil solution' / 'in solution' (not any 'solution') exclude a sentence, so
  '... 1 M KCl solution' is read. doi:10.5440/1618325 ('Soil pH in 1 M potassium chloride (1:5)') unknown -> pH_KCl;
  dry run over the 74 written variables: no other change.
- Soil pH packages still unknown (pH method check 2026-10-14), open:
  reported but not set: 1959350 (0.1 M CaCl2, another sentence adds water), 2405147 (1 M KCl; water only 'to verify
  ... data not shown'), 2283432 (two columns 'Soil pH', 'Soil pH 1:1'; 'pH in water and KCl'), 1725884 (pH of the
  water-extract filtrate, likely H2O);
  probably not soil pH: 1960313 ec1_water_ph_L2.csv (surface water), spruce.043/1434643 (porewater), 1647038
  (hyporheic / floodplain water, field probe), 2529428 and 1898913 (WHONDRS surface water), 3016270 (in situ water
  chemistry), 1544760 and 1735757 (Kougarok soil water), 2523672 (Soil_pH from SoilGrids; Site_soil_pH is measured);
  not reported: 1454273, 1785525, 1659482, 1810163, 1811604, 1813869, 2572883, 2587101.
- Method from the clause that names the variable (auto.py `_methods_in`, `_clauses`; user decision 2026-10-14): when one
  sentence gives several methods, only those in the clause naming the variable count (clauses split at , ; | outside
  parentheses); with none there, the sentence's methods as before. doi:10.15485/1577267 'soil pH measurements (1:1
  w/vol in ddH2O), dissolved nitrogen pools measured in soil extracts (2M KCl extractant)' gave pH_H2O and pH_KCl
  ('several methods', unknown); now pH_H2O (312 rows). Dry run over the 74 written variables: no other change.
- Id order with last-resort ids (fields.py `ids`, `_key_columns`, `_measurement`; user decision 2026-10-14): the
  descriptive columns first (informative ones, then number-only ones such as Replicate), each only when it tells
  more rows apart; then the depth, then the date; as a last resort the id columns of numbers only (a lab number)
  and IGSN. The pruning step that dropped 'redundant' columns is gone (it removed Plot from 1577267).
  doi:10.15485/1577267 Location:Lab_ID_LBNL -> Plot:Location:Field_Site:Topographic_Position:Replicate:depth:date:
  Lab_ID_LBNL (27 snow-pit cores, three per pit, depth and date, differ only by the lab number). Id-only site columns:
  field site, topographic / landscape / slope position, replicate anywhere in the name ('Field_replicate',
  'Lab_replicate', 1618870), 'Soil Site'. The value columns and columns of mostly decimal numbers are never id parts
  ('Site_soil_pH', 'Site_soil_total_P' matched '^site', 2523672). The repeated-row check stays within files too
  (1185213 repeats each sample's pH on every incubation time point); limiting it to other files added ~700 rows, and
  adding the row number to group-like ids broke the same case. Soil pH: 8,142 -> 8,164 rows (1837084 lab replicates
  +8, SPRUCE.005 +14), unique-id tables 64 -> 65 of 86, none lost; hand-written 18/37.
- Ids unique and informative (fields.py `ids`, `_key_columns`, `_informative`; user decision 2026-10-13): a sample /
  core / site / plot column that is unique and not only 1, 2, 3 ... is the id; else the id columns are joined (each
  only when it tells more rows apart, informative ones first, IGSN last since it has its own column); then the
  harmonized depth, then the date; coordinate / depth / date columns are never id columns; ids still repeated get
  'id not unique: N rows share an id'. Uniqueness is checked over the rows with a value. Re-run of the 74 written
  variables: 406 of 743 tables changed id_type; unique ids 413 -> 531 tables (Total carbon 40 -> 53 of 77;
  doi:10.15485/2566016 Site_Name:Site_Lat:Site_Long -> Site_Name:depth, 3367449 IGSN -> SampleSiteCode). Rows that
  the cross-file de-duplication (id, depth, date, value, method) had dropped only because the old ids collapsed are
  kept: Total carbon 8,945 -> 8,955 (doi:10.15485/2425968, whose Sample_ID holds depths; the 10 restored rows are the
  SL and P12 sites with equal values at equal depths, check), delta13C +7 (ORNLSFA.020/1638590), bulk density +1
  (1342956). A first version left IGSN out of the joined columns (1960313 id 'transect_location', 3 values, and pH
  rows lost to the de-duplication); fixed before the final run.
- Date from the package temporal coverage (auto.py, metadata.py `coverage_date`, 2026-10-13): a table with no date
  writes the day, month (YYYY-MM) or year that the coverage start and end share, noted 'date ... from package temporal
  coverage'; a coverage over more than one calendar year gives no date. doi:10.15485/2566016 (collected in October
  2019) -> 2019-10. Before the change 35 of 64 Total carbon packages had no date: 3 one-day, 5 one-month, 6 one-year
  coverages. Re-run of the 74 written variables: dates filled for 29 packages (15 of them Total carbon, 1,216 TC
  rows); no other column changed. A one-day coverage on January 1 is a placeholder and gives the year only (2026-10-13): doi:10.15485/1463804 (Nevada Desert FACE, 1997-01-01, no sampling date in its text) coarse fragments 144 rows 1997-01-01 -> 1997.

Open (from the Total carbon review):

- doi:10.15486/NGT/1434046 (P sorption to 24 tropical soils): `Soil_Sources_Properties_and_Isotherms_2018.csv` has soil
  C (%), N, texture, pH, but its only coordinates are degrees-minutes text in a `Coordinates` column (e.g.
  `19° 50'28.1"N, 155° 7'28.3" W`); NGT0081_locations.csv is the pantropical placeholder (0.0, 0.0). It stays a
  candidate, not written (no DMS parser): user decision 2026-10-13.
- Semicolon-delimited CSVs with decimal commas are split on the commas: doi:10.15485/3325360 (Blodgett warming
  fatty acids and n-alkanes) headers read as '1;1;Control;90–100;2 | 8;27 | ...' instead of ID, Block, Treatment, Depth,
  CPI ... (the header cache and tables.py assume ','). No soil carbon column is lost there (concentrations are per g
  OC), but other packages may be affected.
- doi:10.15485/2405147 SoilCores.xlsx [Soil Cores]: rows 49-78 are a second block stacked under the first (Core 6.1 -
  8.9; 'pH' 126.8-128.5, 'C:N' = core number, SOC and Depth empty); 30 rows are written as pH 127-128 (flagged in qc.csv
  only). Undecided: drop rows outside hard physical limits, detect stacked blocks, or triage.
- ESS-DIVE sample-based reporting-format files (`headerRows_79` in the first column, then rows unit, unitBasis,
  preservationMethodID ... dataStatus, dataRows) are not read as header rows: their metadata rows reach the data
  (doi:10.15485/1875296). tables.py handles the WHONDRS '#Header_Rows' layout only.
- doi:10.15485/1865731 is the reporting format itself (example data); see the NOTE at Total carbon `total ?c(arbon)?\b`
  in rules.py about its companion columns (`Total_Carbon_UTC_offset`, `_Notes`).



## Not related to the generic workflow

- The hand-written pH package for doi:10.15485/3025240 reads `10.15485_3025240_Table_S3.csv`. That file was
  extracted by hand from another package's zip in September and is not in the current download.
