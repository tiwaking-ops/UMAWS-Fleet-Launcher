# CNA data intake procedure

- **Status:** draft for operator/overseer review (T-0184)
- **Date:** 2026-11-09
- **Owner:** T-0184, “Write the data-intake procedure and register workflow”
- **Target consumer:** T-0176, “Implement the scenario loader and structured setup data (§§59–60)”, and the P1c.2 data gate
- **Authority:** `docs/PDD.md`; `docs/sources/proposal-cfna-game-v1.md` §§3.2, 3.3, 7; `docs/data-gaps.md`; `docs/plans/cna-p1b-p4-implementation-plan.md` P1c.2; `src/cna/data/schema.py`
- **Folded annex:** `docs/plans/r04-r05-r06-data-intake-checklist.md`. Its `C-*`, `R04-*`, `R05-*`, `R06-*` and `SCN-*` item IDs are reproduced here; the annex remains a review record, not a second procedure.
- **Boundary:** this is the general intake procedure and the register workflow. It does not authorize any source, mark a resource `HAVE` by itself, or replace `docs/plans/p1c2-data-gate-checklist.md`, which is the phase-level gate decision layer.

## 0. How to use this procedure

A checked box means the named evidence exists and has been reviewed. It does **not** mean a chart, map or counter is merely known to exist.

- `R-04`, `R-05` and `R-06` are **resource-level** gaps. Do not mark any of them `HAVE` until every required gate for T-0176 is closed.
- Record-level statuses come from `src/cna/data/schema.py`: `verified`, `ocr_suspect`, `placeholder`, `synthetic`.
- T-0176’s real scenario may consume only `verified` records. `ocr_suspect` records may exist in a review layer, but must not silently enter the playable scenario.
- `placeholder` and `synthetic` records must never be mixed with historical scenario data. Synthetic fixtures remain separate tests.
- Placing an official resource in `docs/sources/` is the operator’s authorization to use it, but it still requires checksum, extraction, validation and review.
- `docs/data-gaps.md` is generated. Update the register through this procedure and `python -m cna.tools.data_gaps`; never hand-edit it.
- This procedure is necessary but not sufficient for full §60.22 readiness. R-02/R-03 corrections and the R-07 TOE log-sheet layout remain separate prerequisites.

### 0.1 Intake at a glance

1. **Authorize and identify** the source (`C-01`–`C-03`).
2. **Record integrity** — byte size, SHA-256 and manifest entry (`C-02`).
3. **Extract** under `data/` and log the method (`C-04`).
4. **Review** with a second pass by someone who did not do the first (`C-05`).
5. **Validate** the dataset header and every record (`C-06`, `C-07`).
6. **Stabilize identifiers** across R-04, R-05 and R-06 (`C-08`).
7. **Assemble evidence** (`C-10`).
8. **Close the register** by validating the closure record in §6 (`C-09`).

A resource that fails any step stays open in `docs/data-gaps.md`, and the blocker must name the smallest unresolved item, for example `R05-S01: C4218 missing` or `R06-04: 1 CCNN Div counter unresolved` — not “waiting for data”.

## 1. Common intake gate

Complete these once for each resource, before any scenario data is assembled.

- [ ] **C-01 Source identity:** exact title, edition/printing, physical or digital copy, page/sheet/counter-sheet identifiers, and the path under `docs/sources/`.
- [ ] **C-02 Integrity:** byte size, SHA-256, and a source manifest entry. Hashes must identify the exact files used for extraction.
- [ ] **C-03 Authorization:** operator placement/authorization recorded; no unofficial websites, recollections, VASSAL derivatives or model-generated values used as authority.
- [ ] **C-04 Extraction log:** method (manual transcription, vision-assisted, OCR), tool and version, page images used, and who performed the extraction.
- [ ] **C-05 Review:** a second pass by a reviewer who did not produce the first transcription. Where practical, use a different model family. Record every disagreement, not just the final value.
- [ ] **C-06 Schema:** every dataset has `schema_version`, `source`, and `status`; every record has `provenance` and `status`. Validate through `src/cna/data/schema.py` or the loader’s stricter schema.
- [ ] **C-07 Status discipline:** no record is `verified` while any unresolved OCR uncertainty remains; no `placeholder` or `synthetic` record is present in the real scenario.
- [ ] **C-08 Identifier stability:** hex IDs, unit/counter IDs and parent IDs are stable across R-04, R-05 and R-06. Do not generate historical identities from display names.
- [ ] **C-09 Register update:** the validated closure record closes the resource to `HAVE` through §6 of this procedure, with `python -m cna.tools.data_gaps --check` passing after regeneration.
- [ ] **C-10 Evidence pack:** manifest, hashes, extraction log, validator output, review notes and scenario-reference coverage report are attached to the intake record.

### 1.1 Closure record

Machine-checkable closure lives in one manifest, `docs/sources/intake.json`. It is absent while every resource is open. A closure record names the source, its extraction, the review, and the evidence pack; paths are repository-relative.

```json
{
  "schema_version": 1,
  "resources": {
    "R-04": {
      "status": "HAVE",
      "source": {
        "path": "docs/sources/r04/charts-and-tables.pdf",
        "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
        "bytes": 123456,
        "title": "Charts and Tables",
        "edition": "SPI, 1979 printing",
        "copy": "operator scan",
        "identifiers": ["R-04 booklet p.3", "TEC"]
      },
      "authorization": "operator placed the scan in docs/sources/ on 2026-11-09",
      "extraction": {
        "path": "data/r04/tec.json",
        "method": "manual transcription",
        "tool": "editor 1.0",
        "performed_by": "extractor",
        "pages": ["R-04 p.3"]
      },
      "review": {
        "performed_by": "reviewer",
        "second_pass": true,
        "conflicts": []
      },
      "evidence": {
        "manifest": "docs/sources/r04/source-manifest.json",
        "extraction_log": "docs/sources/r04/extraction-log.md",
        "validator_output": "docs/sources/r04/validator.txt",
        "review_notes": "docs/sources/r04/review.md",
        "coverage_report": "docs/sources/r04/coverage.md"
      },
      "identifiers_stable": true
    }
  }
}
```

The validator enforces the machine-checkable subset:

- `source.path` is a real file under `docs/sources/`; `sha256` and `bytes` match it.
- `extraction.path` is a real JSON file under `data/`; it has `schema_version`, `source` and `status`, its header status is `verified`, its source cites `rulebook:` or `chart:`, and every record is `verified`.
- `authorization` is recorded, `identifiers_stable` is true, and the review is a second pass by a reviewer other than the extractor; every recorded conflict has a resolution.
- All five `C-10` evidence files exist under `docs/sources/` and are non-empty.

Human review still owns source identity, transcription accuracy, cross-resource reconciliation and the coverage report. The validator proves the paperwork is internally consistent; it does not prove the transcription is historically correct.

### 1.2 Commands

```bash
# Validate every closure record; write nothing.
python -m cna.tools.data_gaps --validate-intake

# Report the P1c.2 per-resource gate from the validated closure records.
python -m cna.tools.data_gaps --gate

# Regenerate the register from the static entries plus validated closures.
python -m cna.tools.data_gaps

# Fail if docs/data-gaps.md is stale or any intake claim is invalid.
python -m cna.tools.data_gaps --check

# The T-0184 oracle.
python -m pytest -q tests/test_data_intake.py
```

`--intake PATH` selects a different closure manifest; the default is `docs/sources/intake.json`.

## 2. R-04 — Charts and Tables

R-04 is the dominant gate. The minimum set below is what the §60.22 setup consumes; combat-resolution charts are listed separately because they are needed to *play* the scenario but are not required merely to load its initial state.

### 2.1 Minimum setup set for T-0176

- [ ] **R04-01 Terrain Effects Chart (TEC):** movement costs, terrain prohibitions, stacking/road-track effects, combat/breakdown modifiers and any scenario-relevant terrain columns. Cite the exact chart page and §8–§10/§21 use.
- [ ] **R04-02 Off-Map Land Unit Movement Distance Chart:** the §8.89 table needed for Tripoli/Tunisia movement, including map edges and transit boxes. This is chart data, not a guessed distance formula.
- [ ] **R04-03 Unit Characteristics Charts:** Italian and Commonwealth entries for every ID code used by the units in §60.31/§60.41, including ratings, CPA, stacking, morale and TOE/weapon-system fields.
- [ ] **R04-04 OA Sheets:** every parent formation named or implied by §60.31/§60.41, with subordinate units, `Att`/`Det`/`Less`/`Assg`/`Consists of` notes, `D`/arrival status, and any TOE under/over-strength indicator.
- [ ] **R04-05 Reinforcement Schedules/Tracks:** all land arrivals for Game-Turns 1–6, including training, replacement, withdrawal and Commonwealth restrictions referenced by §60.47.
- [ ] **R04-06 Initial air-strength data:** plane types, available/refitted counts, pilots, SGSUs, facility capacities and Malta data from §60.32/§60.42/§60.46. If `LAND_ABSTRACT` intentionally omits air units, record that choice explicitly rather than silently dropping the records.
- [ ] **R04-07 Weather/terrain-area data:** the §29 weather table and map-section classifications needed to initialise or advance the scenario. Do not infer weather from the calendar.
- [ ] **R04-08 Facility/port/repair data:** airfield, landing-strip, flying-boat and repair-facility classifications; port-efficiency values such as Tobruk’s scenario value; and any chart-backed capacity values. Classify each value’s source before assigning it to R-04.
- [ ] **R04-09 Supply/motorization conversion data:** the tables or rules values used to turn the scenario’s trucks, supply units and dumps into §32 abstract supply/motorization state. Cite §59.63/§59.66 and §60.92/§60.93; do not fill gaps from memory.

### 2.2 Downstream R-04 set

Register these now, but they do not block T-0176’s loader-only acceptance:

- [ ] **R04-D01** Combat Results Table, barrage table, anti-armor table, close-assault table and retreat/advance tables.
- [ ] **R04-D02** Breakdown, repair, construction, fortification and minefield tables.
- [ ] **R04-D03** Air combat, bombing, anti-aircraft and strategic-commitment tables (R-08 adjacent).
- [ ] **R04-D04** Convoy availability, port capacity and production tables (R-09 adjacent).

Do not use an R-08/R-09 table as a substitute for an R-04 setup table, or vice versa. Classify the resource before ingesting it.

### 2.3 R-04 acceptance checks

- [ ] **R04-A01** Every row/column in each extracted table has a source page and a normalized representation; no blank cell is silently treated as zero.
- [ ] **R04-A02** OA Sheets and Reinforcement Schedules agree on arrival dates and `D`/arrival status; every disagreement is queued and resolved.
- [ ] **R04-A03** OA Sheets and Unit Characteristics Charts agree on every ID code and rating used by a scenario unit.
- [ ] **R04-A04** A scenario-reference coverage report resolves every unit, parent, ID code, arrival and chart lookup named in §60.31/§60.41/§60.47.
- [ ] **R04-A05** Row/column totals, duplicate keys and missing lookups are checked programmatically; visual spot checks cover at least 10% of rows and all rows used by §60.22.
- [ ] **R04-A06** Every R-04 record used by T-0176 is `verified`; all review-layer `ocr_suspect` records are excluded from the playable dataset.
- [ ] **R04-A07** R-04 is not marked `HAVE` while any §60.22 unit, parent, arrival or setup table remains unresolved.

## 3. R-05 — Map data

The map must be addressed by the same hex IDs the scenario text uses. A map image is evidence, not structured data.

### 3.1 Source and structure

- [ ] **R05-01 Sheet inventory:** all five map sheets A–E, exact scan/edition, sheet boundaries, overlaps and source identifiers; each sheet has a SHA-256.
- [ ] **R05-02 Registration:** pixel-to-hex control points for every sheet, with registration error recorded. Sheet seams are reconciled before any scenario hex is accepted.
- [ ] **R05-03 Hex index:** unique hex ID, sheet, centre, neighbours and map edge for every hex. IDs such as `C4218` and `A4829` must be stable and unique.
- [ ] **R05-04 Terrain vocabulary:** the official terrain types (the source register says 31) in a controlled vocabulary; no free-text terrain names in playable records.
- [ ] **R05-05 Per-hex features:** terrain, roads, tracks, rail, escarpments/ridges, wadis/depressions, coastal status, cities/towns/oases, ports and air facilities, plus hexside features where the rules distinguish them.
- [ ] **R05-06 Routes and boxes:** rail lines (including the line ending at Mersa Matruh), road/track links, map exits, the Tripoli/Tunisia boxes and all off-map transit points.
- [ ] **R05-07 Map metadata:** map section, stacking/terrain lookup keys, port efficiency, repair facilities and initial construction state. Do not fold TEC values into the map unless the source actually places them there.

### 3.2 Scenario-reference gate

- [ ] **R05-S01** Every hex named in §60.31, §60.41, §60.5, §60.7 and §60.81 resolves to one hex record, including `C4218`, `C4120`, `C4020`, `C3920`, `C3919`, `C3918`, `C3617`, `C4707`, `C4507`, `C4321`, `C4807`, `B4827`, `B5504`, `B5925`, `B4921`, `C1014`, `C3419`, `C3019`, `C0716`, `A4829`, `A4130`, `C4131`, `C3926`, `C3922`, `C3721`, `C3520`, `C3320`, `C3020`, `D3714`, `D3612`, `E1829`, `E3613` / `3714`, `E1430`, `D3418`, `C0127`, `C4021` and the victory locations.
- [ ] **R05-S02** Every named city, port, airfield, landing strip, flying-boat basin, oasis and map-edge exit used by the scenario resolves to a feature record and, where applicable, a hex.
- [ ] **R05-S03** `Anywhere in Libya`, `Anywhere on Map A or B`, `Anywhere, maps`, `Cairo and/or Helwan`, `Alexandria (E3613 &/or 3714)` and the four Tripoli/Tunisia boxes have an explicit placement rule and a validator that prevents illegal placement.
- [ ] **R05-S04** The rail line, the Tobruk port-efficiency value, the absence of initial minefields/fortifications (other than the printed railroad) and the scenario’s temporary/major repair facilities are represented as data, not hard-coded prose.
- [ ] **R05-S05** All scenario hexes are checked against the source image at 100%; a further 10% random sample of every sheet is reviewed for terrain and feature errors.

### 3.3 R-05 acceptance checks

- [ ] **R05-A01** Adjacency is symmetric; every shared edge appears on both hexes; no duplicate or missing coordinates at sheet seams.
- [ ] **R05-A02** Terrain codes are all in the official vocabulary; unknown codes fail validation, not fallback to “clear”.
- [ ] **R05-A03** Roads, tracks and rail connect end to end; every route endpoint and map exit has a valid target.
- [ ] **R05-A04** Every playable record is `verified`; `ocr_suspect` records are restricted to the review layer and cannot be loaded by the real scenario.
- [ ] **R05-A05** R-05 is marked `HAVE` only after all five sheets and all §60.22 references pass, not after a single sheet or a sample map is available.

## 4. R-06 — Counters and unit identities

R-06 supplies the identities and printed ratings; R-04 supplies the OA structure and characteristics tables. They must reconcile.

### 4.1 Counter manifest

- [ ] **R06-01 Counter index:** one stable record per counter, with nationality, printed name, counter abbreviation, ID code, unit type/size, parent formation and any printed reverse/step/replacement identity.
- [ ] **R06-02 Ratings:** attack, defence, anti-armor, barrage, close-assault, morale/cohesion, CPA, stacking points, TOE strength and weapon-system/vehicle type, as printed and as referenced by the characteristics chart.
- [ ] **R06-03 OA crosswalk:** parent, subordinate, attached and detached relationships; `D`/arrival status; `Less`/`Assg`/`Det`/`Consists of` adjustments; training and replacement status.
- [ ] **R06-04 Scenario unit coverage:** every named unit in §60.31/§60.41, including divisions, regiments, battalions, companies, garrisons, HQ counters, artillery, anti-tank, anti-air, reconnaissance and static units.
- [ ] **R06-05 Reinforcement coverage:** every R-04 reinforcement entry for Game-Turns 1–6 maps to a counter or an explicitly recorded replacement/training record.
- [ ] **R06-06 Special pools:** `Anywhere in Libya`, `Anywhere on Map A or B`, `Anywhere, maps`, the Saharan Detachment’s three-hex constraint, the Autoblinda attachment option, broken-down vehicles in Alexandria and the Commonwealth replacement-point restrictions.
- [ ] **R06-07 Count reconciliation:** manifest count = initial deployment + scheduled arrivals + replacements/breakdowns + explicitly held/unused counters; no counter is duplicated or silently reused.

### 4.2 R-06 acceptance checks

- [ ] **R06-A01** Every counter in the §60.22 force list has exactly one stable counter ID and one parent/attachment chain.
- [ ] **R06-A02** R-06 ratings agree with R-04 OA/characteristics entries; conflicts cite the source page and are queued for resolution, never averaged or guessed.
- [ ] **R06-A03** Errata corrections are applied explicitly and cite R-03; an uncorrected and corrected value are never both exposed as playable.
- [ ] **R06-A04** The loader’s unit records can be produced without inventing fields: side, position, parent/attachment, CPA, cohesion, stacking, unit class/kind, motorization, breakdown/TOE values and identity.
- [ ] **R06-A05** Every §60.22 unit and arrival is `verified`; units known only from a name or a historical narrative are not admitted as counters.
- [ ] **R06-A06** R-06 is marked `HAVE` only when the counter manifest and the §60.22 coverage report agree.

## 5. Assemble the §60.22 real scenario

### 5.1 Variant declaration

- [ ] **SCN-01** State the ruleset variant explicitly. For the P1 target this is `LAND_ABSTRACT`; use the §60.92 “Air & Logistics Abstracted (Land Game Only)” setup values. Do not mix in §60.34/§60.44 full-game values or §60.93 Air-Game values.
- [ ] **SCN-02** Record scenario ID, sides, start at Game-Turn 1/OpStage 1, end at Game-Turn 6/OpStage 3, and the expected **18 Operations Stages**.
- [ ] **SCN-03** Record initiative: Italian initiative for Game-Turn 1, then the normal procedure from Game-Turn 2; record special first-turn restrictions such as the Commonwealth fleet movement restriction.

### 5.2 Setup records

- [ ] **SCN-04 Initial deployment:** every hex/unit pair, every `Anywhere` allocation, every attachment/detachment choice, and every stacking check. A setup that is legal only by leaving units unplaced is invalid.
- [ ] **SCN-05 Air:** plane totals, ready/refitted split, pilots, SGSUs and facility assignments, or an explicit statement that the variant does not load air units. Do not infer air capabilities from the plane names.
- [ ] **SCN-06 Supply and trucks:** dump locations, dummy dumps, supply-unit counts and contents, truck points by location, attached/unattached motorization, initial loads and off-map placement restrictions from §59.63/§59.66/§60.92.
- [ ] **SCN-07 Facilities and terrain:** airfields, landing strips, flying-boat basins, repair facilities, port efficiency and initial construction state. All must resolve to R-05/R-04 records.
- [ ] **SCN-08 Reinforcements and withdrawals:** all Game-Turns 1–6 arrivals, training/replacement delays, Commonwealth withdrawal/arrival restrictions and any fleet/convoy restrictions that remain in the abstract variant.
- [ ] **SCN-09 Victory and special rules:** victory locations, supply-trace conditions, Italian first-turn initiative, Tobruk port state and other §60.81/§60.7 rules represented as data or explicitly declared out of scope for the loader.

### 5.3 Loader acceptance

- [ ] **SCN-A01** `tests/test_scenario_loader.py` loads a real §60.22 fixture only when all required records are `verified`; the fixture is not a renamed synthetic scenario.
- [ ] **SCN-A02** The loader returns the correct sides, start/end turn and stage, 18 Operations Stages and a complete initial order of battle.
- [ ] **SCN-A03** Missing, duplicate, unresolved or placeholder data is refused with the missing key/path, not replaced by a default.
- [ ] **SCN-A04** Every scenario reference resolves through the R-04/R-05/R-06 coverage report; zero unresolved names, hexes, counters or chart lookups.
- [ ] **SCN-A05** `python -m pytest -q tests/test_scenario_loader.py` passes, and the test proves both the accepted real fixture and the rejected incomplete fixture.
- [ ] **SCN-A06** `docs/data-gaps.md` no longer lists R-04/R-05/R-06 as blocking P1c, or the remaining block is stated explicitly and T-0176 is not claimed as real-setup complete.

Scenario assembly is validated by the scenario loader, not by `data_gaps.py`: the loader checks the document’s `kind`, sides, turn span, TEC, map topology and unit placement. The intake validator checks the resource extraction that feeds it.

## 6. Register workflow (C-09)

A resource closes in one step: its record in `docs/sources/intake.json` passes validation.

1. **Closure record.** The record names the source, extraction, second-pass review and evidence pack. `python -m cna.tools.data_gaps --validate-intake` must exit `0`.
2. **Register and gate.** The same validated record promotes the resource to `HAVE` in the generated register. `python -m cna.tools.data_gaps` regenerates `docs/data-gaps.md`, `--check` exits `0`, and `--gate` reports that resource `PASS`; there is no separate register edit or gate status to maintain.

The closure rule is enforced, not advisory:

- Validator passes → status `HAVE`; the gap count falls and the P1c.2 gate moves in the same render.
- Validator fails or the record is missing while the static entry says `HAVE` → the rendered status is downgraded to `UNVERIFIED`, the command prints the exact failure, and it exits `1`. The register is not rewritten.
- Neither side claims closure → the static status in `GAPS` is preserved; this is the normal state while a resource is open.

`GAPS` remains the baseline for open statuses (`UNVERIFIED`, `NONE-FOUND as structured data`) and the reviewed resource metadata. It is no longer a second closure switch: a validated intake record is sufficient to close the resource and pass the gate.

The P1c.2 gate reads the same validated records. `python -m cna.tools.data_gaps --gate` reports `PASS` for R-04, R-05 or R-06 when that resource's intake record validates; a blocked resource prints the exact intake failure or the current register status.

`HAVE` is resource-level, not sheet-level or table-level. R-05 is not `HAVE` after one map sheet, and R-04 is not `HAVE` after the TEC alone. Use the acceptance checks in §§2–4 to decide when the resource-level claim is honest; the validator only confirms the evidence pack.

If the source later changes, keep the old evidence and add the replacement as a new manifest entry; do not silently re-hash the same path. A failed re-validation downgrades the rendered status without deleting the record, so the failure is visible.

## 7. Unblock decision for T-0176

T-0176 may be treated as ready for its real §60.22 setup only when all of the following are true:

1. **R-04:** the minimum setup set in §2.1 is verified, schema-valid and covered by the scenario-reference report.
2. **R-05:** all five sheets and every §60.22 hex/feature reference are verified and topologically valid.
3. **R-06:** the counter manifest resolves every initial and Game-Turns 1–6 unit, with ratings reconciled to R-04.
4. **Assembly:** the §60.22 manifest and loader tests accept the real dataset and refuse incomplete or placeholder data.
5. **Register:** the resource-level status and evidence pack are updated through §6.

Until then, T-0176 may continue with the §59 loader contract, synthetic fixtures and a clearly labelled partial fixture, but it must not claim a real §60.22 setup. The block should name the smallest unresolved gate, for example `R05-S01: C4218 missing` or `R06-04: 1 CCNN Div counter unresolved`, rather than “waiting for data”.

## 8. Current register state

As of 2026-11-09, `docs/data-gaps.md` lists eight open gaps and no `HAVE` status. `docs/sources/intake.json` and `data/` do not exist, so no resource has a closure record, `python -m cna.tools.data_gaps --validate-intake` reports no intake records, and `--gate` reports 0/3 P1c.2 resources closed. This snapshot is a status record, not a waiver; re-run the procedure when a resource arrives.

## 9. Explicit non-goals

- This procedure does not authorise using unofficial sources, VASSAL-derived data, memory, or model-generated values as historical data.
- It does not turn `ocr_suspect` or `placeholder` values into `verified` by review alone; the source page and second-pass evidence are required.
- It does not make R-02/R-03/R-07 unnecessary. Those remain separate prerequisites for the complete §60.22 claim.
- It does not claim that T-0176 is implemented; the loader contract and tests remain T-0176’s work.
- The validator does not prove historical accuracy. It proves that the named source, checksum, extraction, second pass and evidence pack exist and agree; a human reviewer still owns the content.

## 10. References

- `docs/PDD.md` — product constraints and definition of done.
- `docs/sources/proposal-cfna-game-v1.md` §§3.2, 3.3, 7 — resource register, data policy, phase plan.
- `docs/data-gaps.md` — authoritative generated gap register.
- `docs/plans/p1c2-data-gate-checklist.md` — phase gate decision layer.
- `docs/plans/r04-r05-r06-data-intake-checklist.md` — folded review annex for the `C-*`, `R04-*`, `R05-*`, `R06-*` and `SCN-*` items.
- `docs/plans/cna-p1b-p4-implementation-plan.md` P1c.2 — target and exit condition.
- `src/cna/data/schema.py` — `verified` / `ocr_suspect` / `placeholder` / `synthetic` vocabulary and provenance rules.
- `src/cna/tools/data_gaps.py` — register generator, intake validator and closure rule.
