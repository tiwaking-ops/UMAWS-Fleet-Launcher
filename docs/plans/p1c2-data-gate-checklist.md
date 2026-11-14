# P1c.2 data-gate checklist — R-04 / R-05 / R-06

- **Status:** draft for operator/overseer review
- **Date:** 2026-11-09
- **Scope:** P1c.2, §60.22 Graziani’s Offensive, Game-Turns 1–6, 18 Operations Stages
- **Target card:** T-0176, “Implement the scenario loader and structured setup data (§§59–60)”
- **Authority:** `docs/PDD.md`; `docs/sources/proposal-cfna-game-v1.md` §§3.2 and 7; `docs/data-gaps.md`; `docs/plans/cna-p1b-p4-implementation-plan.md` P1c.2; `src/cna/data/schema.py`
- **Detailed evidence:** `docs/data-intake.md` (procedure and item IDs `C-*`, `R04-*`, `R05-*`, `R06-*`, `SCN-*`); the review annex is `docs/plans/r04-r05-r06-data-intake-checklist.md`
- **Generated gate:** `python -m cna.tools.data_gaps --gate` — a validated `docs/sources/intake.json` record closes the register entry and the gate in one step
- **Boundary:** this is the gate decision layer, not the intake procedure. It does not replace T-0184’s `docs/data-intake.md`, authorize any source, or mark a resource `HAVE` by itself.

## 0. Gate rule

P1c.2 is **DATA-READY** only when every box in §§2–6 is checked, the non-data preconditions in §1 are met, and the evidence named by each box has been reviewed. Otherwise the gate is **BLOCKED**.

- A checked box means the named evidence exists, has been reviewed, and is attached to the gate record. A resource merely being available is not a checked box.
- Every record used by the real scenario must be `verified`. `ocr_suspect` records may exist only in a review layer; `placeholder` and `synthetic` records must not be mixed into the historical scenario.
- `R-04`, `R-05` and `R-06` are resource-level gaps. Do not mark any of them `HAVE` until its gate below passes and the register is regenerated through the T-0184 procedure.
- The per-resource gate is generated, not hand-entered: `python -m cna.tools.data_gaps --gate` reports `PASS` when the intake record validates, and the same record promotes the register entry to `HAVE`. The register status and the gate close in one step. `BLOCKED` prints the exact intake failure or the current register status.
- A blocked gate must name the smallest unresolved key or item, for example `R05-S01: C4218 missing` or `R06-04: 1 CCNN Div counter unresolved`; “waiting for data” is not an acceptable blocker.
- The real §60.22 claim additionally requires P1c.1’s loader contract and T-0176’s P1b dependencies. Those are not data gates, but they are listed in §1 so a data pass cannot be mistaken for scenario readiness.

### Current snapshot — 2026-11-09

| Gate | Current state | Evidence |
|---|---|---|
| R-04 | **BLOCKED** | `docs/data-gaps.md`: `UNVERIFIED` |
| R-05 | **BLOCKED** | `docs/data-gaps.md`: `NONE-FOUND as structured data` |
| R-06 | **BLOCKED** | `docs/data-gaps.md`: `UNVERIFIED` |
| P1c.2 data gate | **BLOCKED** | `python -m cna.tools.data_gaps --gate`: 0/3 resources closed |
| P1c.2 implementation | **NOT READY** | T-0176 is `PROPOSED`; `src/cna/scenario/` is absent |
| Real §60.22 claim | **NOT CLAIMED** | No verified dataset; loader contract not accepted |

The authoritative per-resource result is the output of `python -m cna.tools.data_gaps --gate`; this snapshot records the 2026-11-09 state for review only. Re-run the command when a resource status changes or any box below is checked.

## 1. Non-data preconditions

- [ ] **P1C2-01 Loader contract:** P1c.1 is accepted; the schema and loader validate headers and records, reject placeholders unless `--allow-placeholder` is explicit, and refuse unresolved keys instead of applying defaults.
- [ ] **P1C2-02 Scenario prerequisites:** T-0176’s P1b dependencies are complete and T-0176 is admitted. The data gate may be assessed as a preflight before admission, but no real §60.22 claim may be made until both the data gate and the implementation prerequisites pass.
- [ ] **P1C2-03 Dataset separation:** the real dataset has a declared manifest and path; synthetic and partially real fixtures remain separate, clearly labelled, and are never loaded as the historical scenario.
- [ ] **P1C2-04 Register currency:** `docs/data-gaps.md` is generated and current; `python -m cna.tools.data_gaps --check` exits `0`. The same state produces the gate result in `python -m cna.tools.data_gaps --gate`.

## 2. R-04 — Charts and tables

R-04 is the dominant setup gate. The minimum set is the §60.22 setup set in `R04-01`–`R04-09`; combat-resolution tables remain downstream and must not be substituted for setup data.

- [ ] **P1C2-R04-01 Minimum setup set:** every §60.22 setup table in `R04-01`–`R04-09` is present, with exact chart page, booklet, and rule-section citations.
- [ ] **P1C2-R04-02 Internal reconciliation:** OA sheets, unit characteristics, and reinforcement schedules agree on every ID code, parent, arrival, `D`/arrival status, and rating used by §60.22; every disagreement is queued and resolved, never averaged or guessed (`R04-A02`, `R04-A03`).
- [ ] **P1C2-R04-03 Scenario-reference coverage:** every unit, parent, ID code, arrival, weather/terrain lookup, facility, supply value, and chart lookup named by §60.31, §60.41, §60.47 and the abstract setup resolves; zero missing references (`R04-A04`).
- [ ] **P1C2-R04-04 Table integrity:** row/column totals, duplicate keys, blank cells, and missing lookups are checked programmatically; no blank is treated as zero; 100% of §60.22 rows and a 10% sample of every extracted table are visually checked (`R04-A01`, `R04-A05`).
- [ ] **P1C2-R04-05 Record status:** every R-04 record used by the real scenario is `verified`; review-layer `ocr_suspect` records are excluded from the playable dataset; no `placeholder` or `synthetic` record is present (`R04-A06`).
- [ ] **P1C2-R04-06 Resource status:** R-04 is marked `HAVE` only after `P1C2-R04-01`–`05` pass and the generated register is updated through the formal procedure (`R04-A07`, `C-09`).

**Gate result:** generated by `python -m cna.tools.data_gaps --gate`; `PASS` when the R-04 intake record validates, and the same record marks the register entry `HAVE`. `BLOCKED` must use the printed blocker.

## 3. R-05 — Structured map data

A map image is evidence, not structured data. The map must use the same hex IDs and terrain vocabulary the scenario text uses.

- [ ] **P1C2-R05-01 Source inventory:** all five sheets A–E are identified by exact scan/edition, boundaries, overlaps, and SHA-256; every sheet used by §60.22 is present (`R05-01`).
- [ ] **P1C2-R05-02 Registration and seams:** pixel-to-hex control points and registration error are recorded for every sheet; sheet seams are reconciled before any scenario hex is accepted (`R05-02`).
- [ ] **P1C2-R05-03 Hex and feature model:** the hex index, official terrain vocabulary, per-hex features, routes, rail, map exits, and off-map boxes are represented as data with stable keys (`R05-03`–`R05-07`).
- [ ] **P1C2-R05-04 Scenario references:** every hex, city, port, airfield, landing strip, flying-boat basin, oasis, map edge, `Anywhere` allocation, and Tripoli/Tunisia box named by §60.22 resolves to an explicit record and placement rule (`R05-S01`–`R05-S04`).
- [ ] **P1C2-R05-05 Topology and quality:** adjacency is symmetric; shared edges and seams have no duplicates or gaps; roads, tracks, and rail connect end to end; unknown terrain codes fail validation rather than defaulting to clear; every playable record is `verified` (`R05-A01`–`R05-A04`).
- [ ] **P1C2-R05-06 Resource status:** R-05 is marked `HAVE` only after all five sheets and every §60.22 reference pass, not after a single sheet or sample map (`R05-A05`).

**Gate result:** generated by `python -m cna.tools.data_gaps --gate`; `PASS` when the R-05 intake record validates, and the same record marks the register entry `HAVE`. `BLOCKED` must use the printed blocker.

## 4. R-06 — Counters and unit identities

R-06 supplies identities and printed ratings; R-04 supplies OA structure and characteristics. The two must reconcile.

- [ ] **P1C2-R06-01 Counter manifest:** every counter has one stable record with nationality, printed name, abbreviation, ID code, unit type/size, parent formation, reverse/step/replacement identity where printed, and all ratings used by §60.22 (`R06-01`, `R06-02`).
- [ ] **P1C2-R06-02 OA crosswalk and scenario coverage:** parent, subordinate, attached, detached, `D`/arrival, `Less`/`Assg`/`Det`/`Consists of`, training, and replacement relationships are recorded; every initial and Game-Turns 1–6 unit in §60.31/§60.41 is covered (`R06-03`, `R06-04`).
- [ ] **P1C2-R06-03 Reinforcements and special pools:** every R-04 reinforcement entry maps to a counter or an explicit replacement/training record; `Anywhere` pools, the Saharan Detachment constraint, the Autoblinda option, broken-down vehicles, and Commonwealth replacement restrictions are explicit (`R06-05`, `R06-06`).
- [ ] **P1C2-R06-04 Count reconciliation:** manifest count equals initial deployment plus scheduled arrivals plus replacements/breakdowns plus explicitly held/unused counters; no counter is duplicated or silently reused (`R06-07`).
- [ ] **P1C2-R06-05 Cross-resource ratings:** R-06 ratings agree with R-04 OA/characteristics entries; conflicts cite the source page and are queued for resolution, never averaged or guessed; R-03 errata corrections are explicit and never exposed alongside uncorrected values (`R06-A02`, `R06-A03`).
- [ ] **P1C2-R06-06 Resource status:** every §60.22 counter and arrival is `verified`; the counter manifest and §60.22 coverage report agree; R-06 is marked `HAVE` only then (`R06-A01`, `R06-A04`–`R06-A06`).

**Gate result:** generated by `python -m cna.tools.data_gaps --gate`; `PASS` when the R-06 intake record validates, and the same record marks the register entry `HAVE`. `BLOCKED` must use the printed blocker.

## 5. Cross-resource and evidence gate

- [ ] **P1C2-X01 Identifier stability:** hex IDs, unit/counter IDs, parent IDs, and chart keys are stable across R-04, R-05, and R-06; historical identities are never generated from display names (`C-08`).
- [ ] **P1C2-X02 Provenance and status:** every dataset has `schema_version`, `source`, and `status`; every record has `provenance` and `status`; the values pass `src/cna/data/schema.py` or the loader’s stricter schema (`C-06`, `C-07`).
- [ ] **P1C2-X03 Conflict register:** all cross-resource disagreements are recorded with both source citations; the register is empty or every entry is resolved before the gate can pass.
- [ ] **P1C2-X04 Evidence pack:** the manifest, hashes, extraction log, validator output, second-pass review notes, scenario-reference coverage report, and source-page citations are attached to the intake record (`C-10`).
- [ ] **P1C2-X05 Register and gate update:** R-04/R-05/R-06 are not marked `HAVE` on the strength of this checklist alone; a validated intake record closes each resource, `python -m cna.tools.data_gaps --check` passes after regeneration, and `--gate` reports the same resource `PASS` (`C-09`).

## 6. §60.22 assembly gate

- [ ] **P1C2-S01 Variant:** the scenario declares `LAND_ABSTRACT` and uses the §60.92 “Air & Logistics Abstracted (Land Game Only)” values; full-game and Air-Game setup values are not mixed in.
- [ ] **P1C2-S02 Scenario identity and length:** scenario ID, sides, start at Game-Turn 1/Operations Stage 1, end at Game-Turn 6/Operations Stage 3, and the expected 18 Operations Stages are recorded.
- [ ] **P1C2-S03 Initial deployment:** every hex/unit pair, `Anywhere` allocation, attachment/detachment choice, and stacking check is complete; a setup that is legal only by leaving units unplaced is invalid.
- [ ] **P1C2-S04 Air, supply, facilities, reinforcements, victory:** air totals and facility assignments (or an explicit statement that the variant does not load air units), dumps/trucks/motorisation, port and repair state, Game-Turns 1–6 arrivals/withdrawals, victory locations, and special first-turn rules are represented as data or explicitly declared out of scope for the loader.
- [ ] **P1C2-S05 Real fixture:** the accepted fixture is assembled from the verified R-04/R-05/R-06 records; it is not a renamed synthetic scenario and contains no unresolved or placeholder values.
- [ ] **P1C2-S06 Loader refusal:** missing, duplicate, unresolved, `ocr_suspect`, `placeholder`, or `synthetic` data in the real dataset is refused with the exact key/path, not replaced by a default.
- [ ] **P1C2-S07 Loader acceptance:** `tests/test_scenario_loader.py` proves both that the real §60.22 fixture loads with the correct sides, turn/stage range and order of battle, and that an incomplete fixture is rejected; `python -m pytest -q tests/test_scenario_loader.py` passes.
- [ ] **P1C2-S08 Register and claim:** `python -m cna.tools.data_gaps --gate` reports all three resources `PASS`, or the remaining generated blocker is stated explicitly and T-0176 is not claimed as a real-setup completion.

**Gate result:** [ ] PASS  [ ] BLOCKED — blocker: `________________`

## 7. Gate record

Complete this record when assessing the gate. A `PASS` entry is invalid unless every applicable box above is checked and the evidence is attached.

| Field | Entry |
|---|---|
| Assessment date | |
| Assessed by | |
| Gate status | `python -m cna.tools.data_gaps --gate` — **BLOCKED** on 2026-11-09 (0/3 resources closed) |
| Smallest blocker | The command prints each resource's exact blocker; record the first, for example `R05-S01: C4218 missing` |
| Evidence pack | |
| Register state | `docs/data-gaps.md`; `python -m cna.tools.data_gaps --check`; `python -m cna.tools.data_gaps --gate` |
| Decision | No real §60.22 setup claim. T-0176 remains `PROPOSED` at this assessment; it may be admitted for loader/synthetic work after its P1b dependencies, but real-setup completion requires this gate. |
| Next review trigger | A resource changes status, a source is authorized, or any gate box is checked |

## 8. Non-goals

- This checklist is not the intake procedure and does not replace T-0184’s `docs/data-intake.md`.
- It does not authorize unofficial sources, VASSAL-derived data, memory, or model-generated values as historical data.
- It does not make R-02, R-03, or R-07 unnecessary. Those remain separate prerequisites for a complete §60.22 claim.
- It does not turn `ocr_suspect` or `placeholder` values into `verified` by review alone; the source page and second-pass evidence are required.
- It does not claim that T-0176 is implemented or that the scenario loader exists.

## 9. References

- `docs/PDD.md` — product constraints and definition of done.
- `docs/sources/proposal-cfna-game-v1.md` §§3.2, 3.3, 7 — resource register, data policy, phase plan.
- `docs/data-gaps.md` — authoritative generated gap register.
- `docs/plans/cna-p1b-p4-implementation-plan.md` P1c.2 — target and exit condition.
- `docs/data-intake.md` — intake procedure, closure-record format, and register closure rule.
- `docs/plans/r04-r05-r06-data-intake-checklist.md` — folded review annex for `R04-*`, `R05-*`, `R06-*`, and `SCN-*`.
- `src/cna/data/schema.py` — `verified` / `ocr_suspect` / `placeholder` / `synthetic` vocabulary and provenance rules.
- `src/cna/tools/data_gaps.py` — register generator, intake validator, and `--gate` command.
