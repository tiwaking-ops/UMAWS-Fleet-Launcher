# CNA P1b–P4 implementation plan

**Status:** draft for operator review  
**Date:** 2026-11-08  
**Coverage snapshot:** `coverage/rules_coverage.json` (1,739 parsed cases)  
**Companion backlog:** `docs/plans/cna-p1b-p4-case-backlog.csv`  
**Phase authority:** proposal §7 and Appendix A, `docs/PDD.md`, `docs/data-gaps.md`, `docs/decisions/RD-0001-ruleset-combinations.md`

## 1. Decision

The remaining CNA rules work is **1,646 cases**: 1,617 unimplemented and 29 partial. Of those, 46 are reference/bookkeeping cases in §§1–4 and §65, leaving **1,600 engine and scenario cases** to schedule across P1b–P4:

| Track | Work cases | Unimplemented | Partial | Deferred gates | Share of 1,600 |
|---|---:|---:|---:|---:|---:|
| P1b Land Game rules | 841 | 813 | 28 | 1 | 52.6% |
| P1c Scenario loader | 62 | 62 | 0 | 0 | 3.9% |
| P2 Logistics Game | 158 | 158 | 0 | 2 | 9.9% |
| P3 Air Game | 431 | 431 | 0 | 2 | 26.9% |
| P4 Full campaign | 108 | 108 | 0 | 0 | 6.8% |
| **Engine/scenario subtotal** | **1,600** | **1,572** | **28** | **5** | **100%** |
| Reference/bookkeeping | 46 | 45 | 1 | 0 | — |
| **Total remaining** | **1,646** | **1,617** | **29** | **5** | — |

“Work” means unimplemented plus partial. The five deferred cases are section-overview gates in §§32, 33, 47, 48 and 58; they are phase-start tasks, not missing rule content. The 88 implemented cases are not scheduled.

This plan preserves the proposal’s phase order: **P1b → P1c → P2 → P3 → P4**. Within P1b it makes one deliberate order change: **§32 abstract supply and air moves ahead of §§19–31**, because `LAND_ABSTRACT` is the P1 ruleset and §32 is its supply/air layer. Organization, maintenance and special operations follow the first playable combat/supply loop.

No calendar estimates are given. The proposal deliberately leaves the timeline open; the unit of planning here is the work package and its exit oracle.

## 2. Prioritization rules

- **P0 — critical path.** Blocks a playable ruleset, a phase entry, or a phase exit. Start these first in their phase.
- **P1 — phase-required.** Needed for the phase’s named scenario or exit, but can follow the first playable slice.
- **P2 — phase-completing.** Required to finish the phase’s scope, but not needed for the first playable slice.
- **P3 — reference/bookkeeping.** No engine behavior; classify, cite and remove from the implementation denominator.

Priority is **within a phase**; the phase order still governs. Two tracks may overlap when they touch different modules and different state, but a later phase must not close before its own data gates are satisfied.

Two rules apply to every package:

1. **Implement the engine first, with synthetic fixtures.** A rule whose official table, map or counter data is missing may be implemented behind a data interface, but its cases remain `partial` with a recorded reason. Synthetic data is labelled `synthetic` and never presented as historical data.
2. **A case is not done without evidence.** “Done” means a citing test and a regenerated coverage status. A case may be `implemented`, `partial` with a reason, `deferred` with a reason, or `not_applicable` with a reason — never silently blank.

## 3. Work packages

Counts below are work cases (unimplemented + partial), with deferred gates shown separately.

| Work package | Sections and case counts | Work | Priority | Starts after | Primary exit |
|---|---|---:|---|---|---|
| **P1b.1 Land foundation completion** | §5 (3), §6 (5), §7 (5), §8 (50), §9 (8), §10 (4), §29 (28) | 103 | P0 | P1a | Every §5–10 and §29 case implemented or partial-with-reason; deterministic foundation soak |
| **P1b.2 Combat core** | §11 (25), §12 (36), §13 (11), §14 (37), §15 (66) | 175 | P0 | P1b.1 | Full Position → Barrage → Retreat → Force Assignment → Anti-Armor → Close Assault path in soak |
| **P1b.3 Patrols, morale, reserve** | §16 (34), §17 (27), §18 (14) | 75 | P1 | P1b.2 | Patrol/recon, morale and reserve actions legal and cited |
| **P1b.4 Abstract supply and air** | §32 (61, plus 1 gate) | 61 | P0 | P1b.2 | `LAND_ABSTRACT` can run a multi-turn soak with supply/air state and conservation checks |
| **P1b.5 Organization and reinforcements** | §19 (58), §20 (53) | 111 | P1 | P1b.2; R-03/R-04/R-06/R-07 | Scenario setup consumes organization, reinforcement, replacement and withdrawal data |
| **P1b.6 Maintenance and construction** | §21 (46), §22 (39), §23 (13), §24 (68), §25 (13), §26 (14) | 193 | P2 | P1b.2, P1b.5 | Breakdown, repair, engineering, construction, fortification and minefield state integrated with movement/combat |
| **P1b.7 Special operations** | §27 (61), §28 (18), §30 (43), §31 (1) | 123 | P2 | P1b.5 | Raiders, POW, Mediterranean Fleet and Rommel cases implemented or explicitly data-gated |
| **P1c.1 Scenario loader contract** | §59 (30) | 30 | P1 | P1b.1 | Schema and loader accept synthetic and partially real fixtures; invalid scenarios are refused with citations |
| **P1c.2 Group One / §60.22** | §60 (32) | 32 | P1 | P1c.1; R-02/R-03/R-04/R-05/R-06/R-07 | §60.22 Graziani’s Offensive loads with 18 Operations Stages, or the exact blocking resource is recorded |
| **P1d Tkinter UI** | no rule cases | 0 | P1 | P1b.1, P1c.1 | Human-vs-AI session completes one Operations Stage; illegal attempts are refused with a citation |
| **P2.1 Logistics sequence and consumables** | §48 (gate), §49 (13), §50 (10), §51 (13), §52 (29) | 65 | P0 | P1b.4 | Ledger and supply-conservation invariants hold across a `LAND_LOGISTICS` soak |
| **P2.2 Transport, coordination, ports, naval, base** | §53 (15), §54 (24), §55 (20), §56 (25), §57 (1) | 85 | P1 | P2.1 | Full logistics flow implemented; conservation still holds |
| **P2.3 Abstract air and ruleset gate** | §58 (8, plus 1 gate) | 8 | P2 | P2.2 | `LAND_LOGISTICS` soak passes the P1 criteria |
| **P3.1 Air sequence, aircraft, squadrons, facilities** | §33 (gate), §34 (45), §35 (20), §36 (17) | 82 | P0 | P1b.2; R-08 | Air phase entry; aircraft and facility state are serialisable and deterministic |
| **P3.2 Flight, maintenance, missions** | §37 (21), §38 (27), §39 (27) | 75 | P1 | P3.1 | Flight, maintenance and mission lifecycle in soak |
| **P3.3 Air combat, bombing, non-combat, Malta, AA** | §40 (52), §41 (60), §42 (39), §43 (12), §44 (25), §45 (34), §46 (20) | 242 | P1 | P3.2 | Fighter/bombing/air-to-air/AA/Malta paths complete and cited |
| **P3.4 Abstract logistics and rulesets** | §47 (32, plus 1 gate) | 32 | P2 | P3.3 | `LAND_AIR` and `FULL` soaks clean |
| **P4.1 Scenario Groups 2–4** | §61 (25), §62 (27), §63 (38) | 90 | P1 | P1c; P2/P3 data | Groups Two–Four load and run as test beds |
| **P4.2 Full campaign** | §64 (18) | 18 | P0 | P4.1; all modules | 333 Operations Stages complete deterministically, with autosave/resume |
| **P4.3 Map, UI, save/resume, performance** | no rule cases | 0 | P0 | P4.1 | Hex-map view and full-campaign resume; performance target measured |
| **REF Reference hygiene** | §1 (1), §2 (1), §3 (16), §4 (27), §65 (1) | 46 | P3 | now | Non-executable prose reclassified with reasons; equipment data linked to P1c |

### P1b — Land Game rules

**P1b.1 is the foundation, not a cleanup pass.** It finishes the partial sequence, capability, initiative, movement, stacking, ZOC and weather contracts. §5.2 and Appendix B must be a data table, not a hand-written state machine; the Air and Logistics sequences must not be merged into it by guesswork. TEC, terrain and weather tables go behind data interfaces. If R-04 or R-05 is still missing, the engine path is implemented with synthetic fixtures and the affected cases stay `partial` with a data-gap reason. Oracle: the six existing foundation test modules plus a deterministic multi-turn run.

**P1b.2 is the first complete combat slice.** It covers the combat framework, secret barrage plot, retreat before assault, force assignment, anti-armor and close assault. The resolver must be one action API call, not a side channel. Official CRT and terrain tables are R-04-gated; use a clearly labelled synthetic table until the charts arrive. Oracle: a combat-specific test module plus a soak that reaches and resolves each combat stage.

**P1b.3** adds patrols/reconnaissance, morale and reserve designation. Morale outcomes must flow from combat events, and reserve designation must be visible to the sequence. R-04 morale tables and R-05 reconnaissance terrain are the principal gates.

**P1b.4 is the P1 exit dependency.** It implements §32’s abstract supply and air layer without claiming the Air Game (§§33–47) or Logistics Game (§§48–58). It must establish unit supply state and the conservation invariant early, because P2 later adds the full logistics ledger that supersedes the abstract layer for `LAND_LOGISTICS`. Oracle: a `LAND_ABSTRACT` soak of at least six Game-Turns with zero illegal actions and no supply created or destroyed without a cited event.

**P1b.5** adds organization/reorganization and reinforcements, replacements and Commonwealth withdrawals. It consumes unit records and schedules; R-03, R-04, R-06 and R-07 are hard data gates. The loader must be able to consume a scenario’s force list without embedding historical numbers in code.

**P1b.6** adds breakdown, repair, engineers, construction, fortifications and minefields. These rules touch movement, combat and terrain, so they come after the combat and organization contracts are stable. Negative quantities, illegal stacking and construction without engineers are invariant failures.

**P1b.7** is the last land cluster: raiders/commandos, POW, the Commonwealth Mediterranean Fleet and Rommel. It is required by the P1 scope (§§5–31) but is not needed for the first playable combat/supply loop. The Mediterranean Fleet cases must not silently activate the Logistics Game; they remain within the land module until P2.

### P1c — Scenario loader

**P1c.1** defines the scenario contract: scenario ID, side, Game-Turn/Operations Stage, deployments, reinforcements, weather, map references and data provenance. It validates against the schema and refuses placeholders unless `--allow-placeholder` is supplied. It can start as soon as P1b.1 has stable unit and map interfaces; synthetic and partially real fixtures are expected.

**P1c.2** targets §60.22 Graziani’s Offensive, Game-Turns 1–6, 18 Operations Stages. This is the first real scenario and the first hard data gate: R-02, R-03, R-04, R-05, R-06 and R-07 are all relevant. The phase decision layer is the [P1c.2 data-gate checklist](p1c2-data-gate-checklist.md); a real §60.22 claim requires that gate to pass. If the data is absent, the loader still gets a fixture-level test and the block is recorded in `docs/data-gaps.md`; the plan does not fabricate a deployment.

### P1d — UI

The Tkinter UI is a thin client over `view(state, side)` and `legal_actions`. It must show the current Game-Turn/Operations Stage, the acting side, available actions, rule citations and save/load/replay controls. It contains no rules logic. It can start after P1b.1 and P1c.1, and it is a P1 exit requirement even though it contributes no rule cases.

### P2 — Logistics Game

P2.1 establishes the logistics sequence and the consumable ledger: fuel, ammunition, stores and water. The central oracle is **conservation**: every quantity is accounted for by issue, consumption, loss or a cited transfer. P2.2 adds trucks/transport, supply coordination, ports, Axis naval supply and the Commonwealth supply base. P2.3 adds §58 and activates `LAND_LOGISTICS`; it must not claim the Air Game. P2 is R-09-gated, with R-04 for consumption tables and R-05 for port/base locations.

### P3 — Air Game

P3.1 establishes the Air sequence, aircraft, squadron ground-support units and air facilities. P3.2 adds flight, maintenance and mission lifecycle. P3.3 adds fighter combat, bombing, non-combat missions, Axis bases, Malta, air-to-air combat and anti-aircraft fire. P3.4 adds §47 and activates `LAND_AIR` and `FULL`. P3 is R-08-gated, with R-04 for aircraft/pilot tables and R-05 for base locations.

### P4 — Full campaign

P4.1 adds Scenario Groups Two–Four (§§61–63) as test beds. P4.2 adds §64 and the full 333-Operations-Stage campaign. P4.3 adds the hex-map view, save/resume and performance work. P4 cannot close on synthetic data: R-03 through R-07 must be resolved, and the full campaign must be deterministic by seed and resumable from any autosave. The proposal’s “under 60 seconds per Operations Stage” is explicitly a guess; measure it and record the result rather than treating it as a contractual number.

## 4. Execution order

| Wave | Work | Outcome |
|---|---|---|
| **0. Now** | REF hygiene; P1b.1 starts | Honest denominator; foundation contracts moving |
| **1. Foundation** | P1b.1, P1c.1 | Sequence/movement/weather stable; loader contract with synthetic fixtures |
| **2. Combat** | P1b.2, P1d shell | Complete land combat path; UI can drive a synthetic session |
| **3. Land breadth** | P1b.3, P1b.4, P1c.2 | Morale and abstract supply/air; first real scenario attempt or recorded block |
| **4. Land completion** | P1b.5, P1b.6, P1b.7 | P1b scope complete; **P1 exit review** |
| **5. Module entry** | P2.1, P3.1 | Logistics and Air phase entries, in parallel if R-09/R-08 allow |
| **6. Module completion** | P2.2, P2.3, P3.2, P3.3 | Logistics and Air rules complete |
| **7. Ruleset closure** | P3.4, P4.1 | `LAND_AIR`/`FULL` soaks; Groups Two–Four load |
| **8. Campaign** | P4.2, P4.3 | Full campaign, map, resume and performance evidence |

Waves 5–6 may overlap Wave 4 because Logistics and Air touch different modules, but they must not be used to declare P1 complete. The P1 exit is defined by P1b + P1c + P1d and the four P1 exit criteria below.

**Capacity assumption:** the proposal records a measured capacity of about six concurrent workers. A reasonable allocation is three land workers, one scenario/UI worker, one logistics worker and one air worker once the later phases open. Do not assign multiple workers to the same state file or the same sequence module.

## 5. Phase exits and oracles

### P1 exit (proposal §7)

1. `python -m cna.tools.soak --seeds 20 --turns 6` runs a full synthetic scenario with **zero illegal actions, zero exceptions, zero infinite loops**; the same seed produces an identical event-log hash.
2. A human-vs-AI session in `python -m cna.ui.tk_app` completes at least one Operations Stage without a crash; illegal attempts are refused with a rule citation.
3. `coverage/rules_coverage.json` is regenerated and accurate; every implemented case has a citing test; every skipped case has a recorded reason.
4. Any real-data block is listed in `docs/data-gaps.md`.

The existing deep soak (100 seeds × 12 turns, 6,264 steps, zero illegal actions) is useful evidence for the engine contract, but it does **not** replace the phase-exit run or the UI check.

### P2 exit

`LAND_LOGISTICS` passes the P1 soak criteria, and supply-conservation invariants hold: nothing is created or destroyed except by a cited rule.

### P3 exit

`LAND_AIR` and `FULL` soaks run clean under the same criteria.

### P4 exit

A headless AI-vs-AI run completes Game-Turn 1 Operations Stage 1 through Game-Turn 111 Operations Stage 3 (333 Operations Stages) on the operator’s machine, with no illegal actions or crashes, resumable from any autosave and deterministic by seed. Record measured wall time per Operations Stage; the 60-second target is a guess, not a promise.

### Package-level oracles

Every package must leave `python -m pytest -q` and `python -m cna.tools.coverage --check` green. The package’s cases must be either implemented with a citing test or partial/deferred/not-applicable with a reason. A package that only compiles or only adds a stub does not pass.

## 6. Data gates

The authoritative gap list is `docs/data-gaps.md`; this table is the planning view. The per-resource P1c.2 gate and its evidence requirements are in the [P1c.2 data-gate checklist](p1c2-data-gate-checklist.md).

| Gap | Missing resource | Phase blocks | Planning consequence |
|---|---|---|---|
| R-02 | Original rules PDF | P1b, P1c | Cross-check OCR; do not “fix” the transcription silently |
| R-03 | SPI errata, September 1979 | P1b, P1c | Official corrections and schedules; P1b.5 and P1c.2 are gated |
| R-04 | Charts and tables booklets | P1b, P1c, P2, P3 | Dominant gate: combat, terrain, weather, breakdown, OA, reinforcement and air tables |
| R-05 | Structured map/terrain/hex data | P1b, P1c, P4 | No verified hex source; map images are not structured data |
| R-06 | Counter set / unit identities and ratings | P1b, P1c, P4 | Unit records cannot be populated officially; P1b.5 and scenario data are gated |
| R-07 | TOE log-sheet layouts | P1c | Per-unit digital log sheet layout |
| R-08 | Air Game charts | P3 | Aircraft characteristics and pilot tables |
| R-09 | Logistics Game charts | P2 | Production, convoy and port-capacity tables |

`docs/data-gaps.md` is the authoritative phase-level list; section-level needs can be narrower or broader. In particular, R-05 is also needed for specific port/base hex locations in P2/P3, even though the register’s phase column lists P1b/P1c/P4. The CSV records the section-level gate.

Policy, from `docs/data-gaps.md`:

- The engine refuses to start a rulebook scenario when required data is `placeholder`, unless `--allow-placeholder` is supplied.
- Tests use `synthetic` fixtures and never mix them with real data.
- Placing an official resource in `docs/sources/` is the operator’s authorization; it must then be reviewed and labelled.
- A phase stays incomplete while any gap in its `Blocks` column is open.

The practical consequence: P1b.1–P1b.4 can build engine behavior with synthetic tables, but they cannot honestly claim historical completeness. P1c.2, P1b.5, P2 and P3 have hard data gates. Do not fill a missing table with remembered values.

## 7. Coverage and reference hygiene

The 46 reference cases are not engine work. §§1–3 and §65 are primer, glossary and conclusion prose. §4 is equipment/counter prose; some of it may define data that P1c needs, but it does not define engine behavior. The REF task should review each case and mark it `not_applicable` with a reason where that is true, or link it to `reference.data` where it is a data definition. Do not mark a case `implemented` because a heading exists.

Until that review is complete, the plan keeps the 46 cases visible in the companion CSV under `phase=Reference`, `disposition=reference`. This is why the full remaining count is 1,646 while the engine denominator is 1,600.

Coverage mechanics:

- Add `RULE:` citations and case-naming tests as each rule is implemented.
- Regenerate with `python -m cna.tools.coverage`; never hand-edit `coverage/rules_coverage.json`.
- Use `CASE_STATUS` overrides only for genuinely exceptional cases, and include a reason.
- Partial cases need a reason that names the missing behavior or data, not “not finished.”
- Deferred cases need a reason and a phase gate; they are not a substitute for implementation.

## 8. Starter task cards

These are the first cards to write; they are ordered for the critical path, not by section number.

| Card | Work | Scope | Oracle |
|---|---|---|---|
| **PLAN-001** | REF | Classify §§1–4 and §65; link §4 data to P1c where needed | `python -m cna.tools.coverage --check`; reasons present |
| **P1B-101** | P1b.1 | §5 sequence/phase mechanics; §6 capability points; §7 initiative | `python -m pytest -q tests/test_sequence.py tests/test_capability.py tests/test_initiative_weather.py` |
| **P1B-102** | P1b.1 | §8 movement; §9 stacking; §10 ZOC partials | `python -m pytest -q tests/test_movement.py tests/test_stacking.py tests/test_zoc.py` |
| **P1B-103** | P1b.1 | §29 weather and map-wide effects | `python -m pytest -q tests/test_initiative_weather.py`; synthetic weather fixture |
| **P1B-201** | P1b.2 | §11 combat framework and resolver contract | New combat tests; combat path reaches a resolved assault |
| **P1B-202** | P1b.2 | §12 barrage, secret plot and resolution | New barrage tests; commitment hash/replay check |
| **P1B-203** | P1b.2 | §13 retreat before assault; §14 anti-armor; §15 close assault | Combat tests for each stage; zero illegal actions in soak |
| **P1B-301** | P1b.3 | §16 patrols/recon; §17 morale; §18 reserve | New patrol/morale/reserve tests; combat-event linkage |
| **P1B-401** | P1b.4 | §32 abstract supply/air; `LAND_ABSTRACT` | Six-turn soak; conservation invariant; no Air/Logistics claims |
| **P1B-501** | P1b.5 | §19 organization; §20 reinforcements/replacements/withdrawals | Organization tests; scenario force-list fixture |
| **P1C-101** | P1c.1 | §59 loader contract; synthetic/partial fixtures | `tests/test_scenario_loader.py`; invalid scenario refusal |
| **P1D-101** | P1d | Tkinter shell over `view()`/`legal_actions` | One Operations Stage; illegal attempt shows citation |

## 9. Risks and controls

| Risk | Control |
|---|---|
| R-04 is the dominant gate and can stall most of P1b | Build data interfaces now; keep affected cases `partial` with a precise reason; do not invent CRT/terrain values |
| P1b is 841 cases, over half the engine backlog | Keep cards small; require a package exit every wave; do not start P2/P3 to avoid a hard P1b package |
| P1c.2 is externally blocked | Start P1c.1 with synthetic fixtures; record the exact missing resource; do not let P1b wait on real map data |
| P4’s 60-second target is a guess | Measure per-stage wall time; report the distribution; do not treat the guess as an acceptance failure |
| Coverage can drift from code | Regenerate on every package; `--check` in CI/oracle; review `partial` reasons |
| Six-worker capacity can cause file contention | Assign one owner per module/state file; parallelize independent modules, not the same sequence |
| §4 equipment may hide data needed by P1c | REF review links equipment cases to `reference.data` instead of discarding them |

## 10. Recommended immediate sequence

1. **PLAN-001** — classify the 46 reference cases, so the engine denominator is honest.
2. **P1B-101 and P1B-102 in parallel** — finish the foundation contracts and the movement/stacking/ZOC partials.
3. **P1C-101 in parallel** — define the scenario schema against synthetic fixtures; do not wait for §60.22.
4. **P1B-201** — begin combat only after the P1b.1 sequence and movement contracts are stable.
5. **P1D-101** — build the UI shell once the state/action interface is stable.
6. **P1B-401** — implement §32 before starting P2, so `LAND_ABSTRACT` is a real ruleset rather than a label.

Do not start P2 or P3 merely because a chart arrives; their sequences and data must be reviewed first, and `LAND_ABSTRACT` must remain the only claim until its exit evidence is complete.

## Appendix A. Companion case backlog

`docs/plans/cna-p1b-p4-case-backlog.csv` contains one row for every non-implemented case:

- 1,600 rows with `disposition=implement`
- 5 rows with `disposition=phase_gate`
- 46 rows with `disposition=reference`
- **1,651 rows total**

Columns: `phase`, `work_package`, `priority`, `section`, `section_title`, `case`, `title`, `status`, `disposition`, `target_module`, `data_gaps`, `rules_file`, `line`, `source`, `tests`, `coverage_reason`.

The CSV is a generated planning view, not the source of truth. Change rule status through the coverage tool and citing tests, then regenerate the backlog. Implemented cases are intentionally absent, so the 88 implemented cases do not appear.

## Appendix B. Count reconciliation

| Bucket | Cases |
|---|---:|
| Implemented | 88 |
| Partial | 31 |
| Unimplemented | 1,615 |
| Deferred | 5 |
| **Total parsed** | **1,739** |
| Remaining work (partial + unimplemented) | 1,646 |
| Reference/bookkeeping subset | 46 |
| Engine/scenario backlog | 1,600 |

The 1,600 figure is the only denominator used for P1b–P4 completion percentages. A package is not complete because its files exist; it is complete when its cases are implemented with citing tests, or explicitly partial/deferred/not-applicable with a reason.
