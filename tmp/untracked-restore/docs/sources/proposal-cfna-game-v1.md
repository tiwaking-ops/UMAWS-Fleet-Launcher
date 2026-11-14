---
document: "Digital Edition of The Campaign for North Africa — Formal Project Proposal"
file: "proposal-cfna-game-v1.md"
version: "1.0.0"
author: "Claude (Sonnet 5.5, Anthropic)"
date: "2026-10-31"
status: "Proposal. Operator reviews once, then hands to the UMAWS Overseer."
audience: "Primary: the operator (a single person). Secondary: the UMAWS Overseer LLM and its worker agents."
rules_source: "github.com/tonicebrian/TheCampaignForNorthAfrica @ 75a037f27346a7cd920a765a2f3cae965b1e07a3 (verified by cloning)"
target_platform: "Windows 10, native. No WSL. No Linux port."
language: "Python >= 3.11"
project_dir: "C:\\temp\\projects\\cfna"
---

# Digital Edition of *The Campaign for North Africa: The Desert War 1940-43*

## 0. Summary (read this first)

**What this is.** A plan for building a single-player, Windows-only digital version of SPI's 1979 board wargame *The Campaign for North Africa* (CNA), played by one human against one computer opponent, built almost entirely by LLM agents running under the UMAWS Fleet.

**What the game is, in one paragraph.** CNA simulates the 1940-43 desert war one week per Game-Turn (111 turns, three Operations Stages each). It is the most logistics-heavy wargame ever published: every unit has a paper log sheet, every action costs Capability Points, and fuel, ammunition, water, stores and trucks decide who can move or fight. The rulebook itself recommends 8-10 players and says fewer than four creates excessive workload (§2.0). It is "unplayable" because of paperwork, not because the rules are hard. A computer can do that paperwork. That is the whole case for this project.

**What you (the operator) have to do.** Almost nothing about the game. You cannot be asked rules questions and agents are forbidden from asking you any (§8). You will be asked to do three kinds of things only:

1. Fetch and drop missing files into a folder when the Overseer queues a request (§3.2 lists what is missing and where I believe it lives).
2. Start UMAWS and say GO (§9.1).
3. Play the result and report what feels wrong.

**What you will get, honestly.** CNA has 65 rule sections with 1,737 numbered anchors, sections and cases (counted from the transcription) plus about 180 charts and tables that are not in that transcription. A complete, correct implementation is a very large job. This proposal therefore delivers in stages, each ending in something runnable (§7). Your "phase one" (the computer opponent makes legal moves) is reached at the end of Phase P1.

**What "great" looks like** (success criteria, used to judge every milestone):

- **S1 Traceable.** Every implemented rule cites its case number (e.g. `6.13`), and a generated coverage report shows, per case, whether it is unimplemented, partial, implemented, or deliberately skipped. No silent claims.
- **S2 Legal.** The computer opponent never makes an illegal action across many seeded AI-vs-AI games, and the engine refuses illegal human actions with a message citing the rule.
- **S3 Honest about gaps.** Missing data (map, unit charts) is visible in a gap register and never invented without being labelled `placeholder`.
- **S4 Always runnable.** At every milestone the program starts, saves, loads, and replays deterministically from a seed.

A mediocre result would be a pile of plausible-looking code with no case citations, rules the agents guessed, made-up unit statistics presented as real, and a "legal AI" that was never soak-tested.

---

## 1. How to use this document

- **Operator:** read §0, skim §2, read §3.2 (missing resources) and §9.1 (the runbook). The rest is for the agents.
- **Overseer and workers:** this document is the authority for scope, architecture, policy and task shape. Do **not** paste it into `CLAUDE.md` or `AGENTS.md` and do **not** use `@`-imports for it or for the rules text; both are too large for Claude Code's memory limit (this already happened once on this system). Instead, `AGENTS.md` stays under 60 lines (seed text in §9.4) and points here by path. Read this file in slices by heading.
- Requirement keywords: MUST, MUST NOT, SHOULD, MAY carry their usual meaning. IDs such as `R-04`, `G-07`, `RD-0001` are stable and may be cited in task cards.

---

## 2. Primer: what the game is (plain English)

You do not need this to run the project, but agents and you will both benefit. Rule citations are in parentheses.

**Setting and scale.** North Africa, September 1940 to early 1943 (§1.0). One hex is about 8 km. One Game-Turn is about one week. Units range from companies (about 100 men) to divisions (about 15,000). The full campaign starts at Game-Turn 1, Operations Stage 1, and ends after Game-Turn 111, Operations Stage 3 (§64.2). A shorter campaign starts at Rommel's arrival, Game-Turn 26 Operations Stage 3 (§64.2, §61).

**Two sides.** Axis (Italian and German) versus Commonwealth. In the box, each side is run by a team: a commander-in-chief, a logistics commander, a rear-area commander, an air commander and a front-line commander (§2.0). **In this project you command a whole side alone and the software does the bookkeeping that the team and its paper log sheets would do.**

**Three games in one box (§2.0).**

| Module | Rule sections | What it adds |
|---|---|---|
| Land Game | §§1-32 | Movement, combat, morale, organisation, repair, construction. Uses abstract supply and very simple air rules (§32). |
| Air Game | §§33-47 | Individual aircraft, pilots, missions, air combat, Malta. |
| Logistics Game | §§48-58 | Fuel, ammunition, stores, water, trucks, ports, naval supply. Replaces the abstract supply rules. |
| Scenarios | §§59-65 | Five scenario groups; Group Five is the full campaign (§64). |

The rulebook says the modules can be combined in any way: Land alone; Land + Air; Land + Logistics; or all three (§2.0). Whichever abstract section applies to a given combination (§32, §47 or §58) must be confirmed by the agents when they implement mode switching (task in §9.6).

**Core ideas an implementer must grasp.**

- **Capability Points (CP).** Every unit has a Capability Point Allowance per Operations Stage. Moving, fighting, loading, constructing: all cost CP. Going over allowance is allowed but earns Disorganization Points, which erode morale (§6.0).
- **TOE Strength Points.** A unit's size, roughly 100 men, or 5-8 armoured vehicles, or 4-8 guns per point (§3.0).
- **Supplies and trucks.** Ammunition, fuel, stores and water are consumed constantly. Trucks move them. Italian units even need extra water to cook pasta (a well-known rule).
- **Log sheets.** The counters on the map do not contain enough information, so each counter has a paper log sheet (§2.0). In software this is simply the per-unit state record.
- **Organization at Arrival (OA) charts, Characteristics charts, Reinforcement schedules** define every unit's ratings, make-up and arrival date (§4.4). They are **not** in the transcription (see §3).
- **Initiative.** Decided once per Game-Turn; the winner chooses to move first or last in each of the three Operations Stages and can therefore take two turns in a row (§7.0).
- **Zones of control** are rigid and active (§3.0, §10.0).
- **Case numbering.** `6.531` means Section 6, Primary Case 5, Secondary Case 31 (front matter of the rules). This is the key we use for traceability.

**Shape of one Game-Turn (Land Game, §5.2).** Initiative Determination (I); Naval Convoy Stage (II); then three Operations Stages (III-V), each containing phases A-L for the first player and F-L repeated for the second player; End of Game-Turn (VI). Appendix B lists the phases. The Air and Logistics Games have their own sequences (§33, §48); agents MUST NOT merge them by guesswork.

**Why it is infamous.** Roughly 1,200 hours of play (the rulebook's own figure, §2.0; box copy says 1,500), about ten hours per Game-Turn, hundreds of counters each with a log sheet, five map sheets about ten feet long, and booklets of charts. Reviewers call it more about logistics than combat. (Sources in Appendix E.)

---

## 3. Source inventory and gaps

### 3.1 What I verified

I cloned `tonicebrian/TheCampaignForNorthAfrica` and inspected it. It is an AsciiDoc transcription, OCR-derived from SPI's original PDF.

- Commit pinned for this project: `75a037f27346a7cd920a765a2f3cae965b1e07a3`.
- 65 section files (`sections/section-01.adoc` ... `section-65.adoc`), about 121,000 words, 1,737 anchors (section level and case level) (anchors look like `[#6_13]`), 104 AsciiDoc tables (mostly scenario set-up data in §§60-64).
- Section titles map directly onto the rules sections (list in Appendix A).
- Cross-references use `<<6_13,6.13>>`-style links, which makes a machine index straightforward.

**Known defects (verified):**

- §4.21-4.24 (sample units, unit-type symbols, counter summary, marker summary) are placeholders with warnings such as "Counter images that need to be worked out". Those pages are missing.
- OCR noise exists (for example a heading reads "SCENARIO GROUP THIREE"). Initial deployments are free text such as `C4218: 1 CCNN Div (I; Att: I(M) [T; Ar/LTC]`, not structured data.
- Charts and tables are referenced about 440 times but are almost entirely absent. Only the scenario tables and a handful of rule-embedded tables are present.
- No licence file is present. The content is SPI's. This project is private; the repository MUST NOT be published.

### 3.2 Missing resources register

The user has no other resources. The table below is what the implementation needs and where I believe it can be found. **Status values:** HAVE (verified), UNVERIFIED (named in search results or other sources but I could not open it), NONE-FOUND (no digital form found). The operator can hunt for these; the Overseer queues each as a Class K item (§9.5) when a milestone is blocked on it.

| ID | Resource | Why needed | Where I believe it is | Status |
|---|---|---|---|---|
| R-01 | Rules text (transcription) | All rules | GitHub repo above | **HAVE** |
| R-02 | Original rules PDF | Cross-check OCR errors, recover §4.2x pages | `spigames.net/PDFv2/CampaignNorthAfrica.pdf` (named in the transcription's README); Internet Archive item `campaign-for-north-africa` (full scan, 644 MB) | UNVERIFIED |
| R-03 | SPI Errata, September 1979 | Official corrections; snippets say entire Italian OA sheets (Sirte, Cirene, Marmarica) were omitted from the original, plus added schedule items and corrected ratings | `spigames.net/db_pages/ERR_CampaignforNorthAfrica.pdf` | UNVERIFIED |
| R-04 | Charts and Tables booklets: Common (16 pp, 49 charts), Axis (36 pp, 73), Commonwealth (32 pp, 58) | Combat Results Tables, Terrain Effects, Weather, Breakdown, Characteristics charts, OA sheets, Reinforcement schedules, Production charts, Air characteristics | Possibly inside the R-02 scan; a VASSAL module is reported to embed charts with errata incorporated; Scribd upload "(SPI) The Campaign For North Africa" (206 pp) | UNVERIFIED |
| R-05 | Map data: five sheets A-E, 31 terrain types, hex IDs like `C4218`, roads, tracks, ports, escarpments | Movement, supply, combat | Map images only: VASSAL modules `CNA.vmod` (ScottishHordes, about 95 MiB) and `Campaign_for_North_Africa_v0.94.vmod` (vfttpete, about 79 MiB); Internet Archive scan | **NONE-FOUND as structured data** |
| R-06 | Counter set (unit identities, ratings) | Unit database | R-04 charts; VASSAL counters | UNVERIFIED |
| R-07 | TOE Log Sheet layouts | Fields of the per-unit state record | Fillable log-sheet PDF linked from a Steam Workshop listing; also R-02 | UNVERIFIED |
| R-08 | Air Game charts (aircraft characteristics, pilot tables) | Phase P3 | R-04 | UNVERIFIED |
| R-09 | Logistics Game charts (production, convoy, port capacity) | Phase P2 | R-04 | UNVERIFIED |
| R-10 | Unofficial house rules (for example the `friendorfoe.com` page) | None | n/a | **EXCLUDED** (official sources only) |

Not a resource for this project: Decision Games' streamlined *North African Campaign* (a different, newer game; pre-order status was reported for 2026).

### 3.3 Policy for gaps: engine first, data later

1. **Build the engine against the rules text and drive it with data files** (`data/`). Rules MUST NOT hard-code unit statistics.
2. Every data record carries `provenance` (`rulebook:§60.31`, `chart:R-04:Table X`, `ocr-suspect`, `placeholder`, `synthetic-test`) and a `status` (`verified`, `ocr_suspect`, `placeholder`, `synthetic`).
3. Where a needed table is missing, agents create a **schema and a clearly labelled placeholder**, add an entry to `docs/data-gaps.md` (generated by `tools/data_gaps.py`), and continue. They MUST NOT fabricate historical numbers and label them real.
4. The engine refuses to start a *rulebook* scenario when required data is `placeholder` unless `--allow-placeholder` is given. Tests use `synthetic` fixtures (for example a tiny invented desert called "Test Oasis"), never mixed with real data.
5. Placing an official resource (R-02, R-03, R-04 ...) in `docs/sources/` is the operator's authorisation to use it. Nothing unofficial is ever used.
6. Map data (R-05) is the hardest gap. Options, in order of preference: (a) operator finds a structured source; (b) human-assisted transcription from map images using vision-capable models, hex by hex, with every hex marked `ocr_suspect` until spot-checked; (c) a coarse abstract map for early phases. Phase P1 deliberately works without a real map (§7).

### 3.4 A correction worth knowing

The operator believed the game had no scenarios. The transcription shows five scenario groups (§§59-64), and §64 defines the full campaign as one of them. "The full game" in this proposal therefore means **Scenario Group Five** (§64, using initial deployments from §60), reached at the end of Phase P4. The smaller scenarios (for example §60.22, Graziani's Offensive, Game-Turns 1-6) are used as milestones and test beds on the way, because the rulebook says smaller slices reach a decision much sooner.

---

## 4. Goals, scope and non-goals

**Goals**

- G1. Implement the CNA rules as written, with citation per case and a live coverage report.
- G2. Support two players: the human and one computer opponent. Either side may be chosen by the human at new-game time.
- G3. Computer opponent v1 chooses uniformly among **legal** actions (seeded). Architected so a smarter opponent can replace it without touching the engine.
- G4. Complete campaign playable end to end (Phase P4), saved and resumable.
- G5. Automate all bookkeeping: unit records, supplies, CP expenditure, breakdown, attrition.
- G6. Help a human who does not know the game: plain-English primer, glossary, rule citations in refusal messages, "why can't I?" explanations.

**Non-goals for v1**

- A strong or "historical" AI; network play; more than two players; Linux or macOS; unofficial or house rules; polished graphics; a distributable installer; mobile.
- Delegating to automated sub-commanders (designed for, not built).

---

## 5. Language and technology options

The operator asked for options and then chose Python. The comparison is kept so the choice is defensible and can be revisited.

| Option | Strengths here | Weaknesses here | Verdict |
|---|---|---|---|
| **Python 3.11+** | Free LLMs write it most reliably; huge stdlib (json, dataclasses, random, sqlite3, tkinter); pytest; UMAWS already runs Python 3.11/3.12 on this machine; trivial data tooling for parsing AsciiDoc and tables | Slower than compiled languages; weak static typing unless enforced | **Chosen** |
| TypeScript (Node) | Excellent typing; UI via browser; Node is installed | Needs a bundler/test stack; more moving parts for weak agents; Windows path pitfalls | Reasonable alternative |
| C# (.NET 8) | Strong typing, WPF UI, fast | Not installed per UMAWS report; free models are less reliable; more setup | Not chosen |
| Java 21 | Strong typing; operator has Java history | Verbose; Swing dated; JDK management; agents slower and error-prone | Not chosen |
| Rust | Fast, safe | Hardest for free models; long compile loops; poor fit for data-heavy rules code | Not chosen |

**Why performance is not a blocker.** The game is turn-based. The full campaign is 333 Operations Stages. The hot spots (supply route search, stacking checks, ZOC tests) are standard-library algorithms (`heapq`, dicts). If a hot spot ever matters, it is profiled and fixed locally.

**Dependency policy.** Standard library plus `pytest`. Anything else needs a recorded decision (`RD-xxxx`) and a pinned version in `requirements.lock`. Python `venv` at `.venv`, activated on Windows with `.venv\Scripts\activate`.

**UI options within Python, and the decision.**

| UI option | Notes |
|---|---|
| Tkinter + ttk (stdlib) | No install; tables via `ttk.Treeview`; `Canvas` can draw a hex map later |
| PySide6 (Qt) | Polished, but a large dependency |
| pygame | Good for a map; poor for tables and text |
| Local web UI (FastAPI + HTML) | Pleasant tables; adds a server and a second language |
| Textual (terminal UI) | Lightweight; weaker for map work |

**Decision:** Phase P1 UI is **Tkinter** (ledger and table views). A **headless CLI** is built first because it is what makes automated AI-vs-AI soak testing possible. The engine knows nothing about any UI (§6.1). A hex-map view arrives in Phase P4.

---

## 6. Architecture

### 6.1 Principles (all MUST)

1. **Engine is pure and deterministic.** `apply(state, action, rng)` returns a new state plus events. No I/O, no clock, no global randomness.
2. **Everything goes through one action API.** The human UI and the AI call the same functions. The AI has no privileged access.
3. **Rules are modules, each citing cases.** One module per rules cluster; every public function has a docstring `RULE: 8.41, 8.42`.
4. **Data drives statistics.** No unit numbers in code.
5. **State is serialisable.** JSON with a schema version; save/load round-trips bit-exact.
6. **Illegal is impossible, not unlikely.** `legal_actions` is the single source of truth; `apply` rejects anything not legal.

### 6.2 Repository layout (`C:\temp\projects\cfna`)

```
AGENTS.md                  lean, <60 lines (seed in §9.4); CLAUDE.md is a one-line pointer to it
docs/
  sources/                 proposal-cfna-game-v1.md; official resources dropped by the operator
  rules/                   vendored transcription at the pinned commit + generated index.json
  decisions/               RD-0001.md ... rules decisions; ADR-xxxx.md architecture decisions
  data-gaps.md             generated
  primer.md                plain-English primer for the operator (generated from §2)
src/cna/
  core/                    ids, dice, rng, events, errors
  state/                   state model, serialisation, hashing, views (hidden information)
  rules/                   sec05_sequence.py, sec06_capability.py, sec08_movement.py, ... one module per cluster
  engine/                  decision points, legal_actions, apply, rulesets (module combinations)
  data/                    loaders and validators; JSON/CSV data files live in /data
  scenario/                scenario loader, set-up builders
  ai/                      Player protocol, RandomLegalPlayer
  ui/                      cli.py, tk_app.py
  tools/                   rules_index.py, coverage.py, data_gaps.py, soak.py, replay.py, show_rule.py
data/                      units, hexes, charts as JSON/CSV with provenance
tests/                     mirrors src; includes rulebook-example tests and soak tests
coverage/rules_coverage.json
```

### 6.3 The decision-point model (the key design idea)

CNA decisions are enormous: a side may move hundreds of units, each along a path, each with options. A "legal move" for the whole turn cannot be enumerated. So the engine exposes **atomic decisions**:

- `engine.pending(state) -> Decision` says who must act and what kind of decision it is, for example `movement.select_unit`, `movement.step`, `combat.assign_force`, `segment.end`.
- `engine.legal_actions(state) -> Iterable[Action]` lists the atomic actions currently legal. Examples: move one unit one hex; declare end of this segment; commit a sealed plot.
- `engine.apply(state, action, rng) -> (state, events)`.
- Every decision includes an **always-legal progress action** (`EndSegment` or equivalent) unless a rule forces something.
- Long human operations (move a stack along a path, assign all trucks) are **macros** in the UI layer that expand into atomic actions and are validated one by one.

This is what makes "the AI makes legal moves" both meaningful and testable.

### 6.4 Hidden information and simultaneous plots

Some steps are secret and simultaneous (barrage plotting, force assignment; see Appendix B). The engine models them as **sealed commitments**: both sides commit actions into a sealed list; when both have committed (the AI commits through the same API), the engine reveals and resolves. `view(state, side)` returns the state redacted to what that side may see. The AI MUST receive only `view(state, side)`.

### 6.5 Dice and RNG

`core/dice.py` provides one die, two dice summed, and the **sequential dice roll** (two dice read as a two-digit number 11-66, larger die first; §3.0). A seeded `random.Random` lives in the game state; every roll is written to the event log with the case that requested it. The same seed and the same actions MUST reproduce the same game.

### 6.6 Persistence

Autosave a snapshot at every segment boundary and keep an append-only JSON-lines event log. `tools/replay.py` rebuilds a game from the log and compares the state hash. Undo is limited to the current atomic action (an unconfirmed UI macro).

### 6.7 Rulesets (module combinations)

`engine/rulesets.py` defines `LAND_ABSTRACT`, `LAND_AIR`, `LAND_LOGISTICS`, `FULL`, selecting which rule modules are active, which abstract section replaces which supply or air rules, and which sequence-of-play table is used. Phase P1 ships `LAND_ABSTRACT` only. The combination table in §2 is confirmed against §2.0, §32, §33, §47, §48 and §58 when this is implemented, and the finding is logged as `RD-xxxx`.

### 6.8 Data model

Per-unit record (the digital log sheet): identity, side, parent/attached links, TOE strength, CPA and CP expended, cohesion level, disorganization points, morale, supply levels (ammo, fuel, stores, water), position, status flags, plus `provenance` and `status`. Hex record: terrain code, features, supply and road attributes. Charts: tables loaded from CSV/JSON by name, each cited by its rule case.

### 6.9 The computer opponent (AI)

```python
class Player(Protocol):
    def choose(self, view: View, decision: Decision, legal: Sequence[Action], rng: Random) -> Action: ...
```

`RandomLegalPlayer` picks uniformly among `legal` with a configurable probability `p_end` of choosing the always-legal progress action, and a hard cap `max_actions_per_segment` after which it ends the segment. Both exist to guarantee termination. It is seeded and logged. Because it is a plugin, later versions (heuristics, an LLM-driven commander, automated sub-commanders for the human) are additions, not rewrites.

### 6.10 Human interface (Phase P1)

Tkinter application with: new game (choose side, seed, ruleset), a decision panel showing the pending decision and legal actions, ledger tables for units and supplies, an event log pane, rule citation text for any refusal, save/load. All screens read state through `view(state, side)`.

### 6.11 Scale expectations

Hundreds of units, 333 Operations Stages, thousands of atomic actions per stage. State size is modest. The risk is action volume, handled by macros and AI caps. A soak target is defined in §7 (P4).


---

## 7. Phased delivery plan

Phases are ordered so that something runnable exists at each exit. "Oracle" means an automated, Windows-safe check (`python -m pytest -q ...` or `python -c ...`, never POSIX `test`/`grep`).

### P0 Foundations (no game rules yet)

Vendor the rules at the pinned commit into `docs/rules/`; build the rules indexer, the coverage tool, the data schemas and the gap register; set up the test harness; write `AGENTS.md`.

**Exit:** `python -m pytest -q` is green. `python -m cna.tools.rules_index` reports 65 sections and 1,737 anchors for the pinned commit. `python -m cna.tools.coverage` lists every case as `unimplemented`. `docs/data-gaps.md` exists. A Class K queue item asks the operator for R-02, R-03, R-04 and R-05 (non-blocking).

### P1 Land Game skeleton with a legal AI (**the operator's "phase one"**)

Rules §§5-31 plus the abstract supply and air rules of §32, `LAND_ABSTRACT` ruleset.

- **P1a Walking skeleton.** Sequence-of-play state machine from §5.2 and Appendix B; Initiative (§7); Weather (§29); dice; events; save/load; replay; `RandomLegalPlayer`; headless runner and soak tool. On a synthetic scenario the game walks several Game-Turns using only progress actions.
- **P1b Rule clusters.** In this order, each with tests built from worked examples in the rules text where they exist: Capability Points (§6); Movement, Stacking, ZOC (§§8-10); Combat framework, Barrage, Retreat Before Assault, Anti-Armor, Close Assault (§§11-15); Patrols, Morale, Reserve (§§16-18); Organization and Reinforcements (§§19-20); Breakdown, Repair, Engineers, Construction, Fortifications, Minefields (§§21-26); Raiders, POW, Mediterranean Fleet, Rommel (§§27-31); abstract supply and air (§32).
- **P1c Scenario loader.** Parse §60 free-text deployments into structured set-up data; first real target is §60.22 (Graziani's Offensive, Game-Turns 1-6, 18 Operations Stages). Blocked on real map and unit data (R-04, R-05) is expected; until then the loader is tested against synthetic and partially real fixtures and the block is recorded in the gap register.
- **P1d Tkinter UI** per §6.10.

**Exit (Definition of Done for your phase one):**

1. AI-vs-AI soak: at least 20 seeds, each running a full synthetic scenario of at least 6 Game-Turns, with **zero illegal actions, zero exceptions, zero infinite loops**. Same seed gives an identical event-log hash.
2. Human-vs-AI session in the Tkinter UI completes at least one Operations Stage without a crash; illegal attempts are refused with a rule citation.
3. `coverage/rules_coverage.json` is regenerated and accurate; every implemented case has a citing test; skipped cases have a recorded reason.
4. Any real-data block is listed in `docs/data-gaps.md`.

### P2 Logistics Game (§§48-57, plus §58 for Land + Logistics)

Fuel, ammunition, stores, water, trucks, supply coordination, ports, Axis naval supply, Commonwealth supply base; the Logistics sequence of play (§48). **Exit:** `LAND_LOGISTICS` ruleset soak passes the P1 criteria; supply conservation invariants hold (nothing created or destroyed except by a cited rule).

### P3 Air Game (§§33-46, plus §47 for Land + Air)

Aircraft, pilots, squadron ground support units, air facilities, flight, maintenance, missions, fighter and bombing combat, Malta, anti-aircraft fire. **Exit:** `LAND_AIR` and `FULL` rulesets soak clean.

### P4 Full campaign (§64 with §60 deployments)

Complete Game-Turn 1 Operations Stage 1 through Game-Turn 111 Operations Stage 3 (333 Operations Stages), all modules, hex-map view, save/resume. **Exit:** AI-vs-AI headless run of the whole campaign finishes on the operator's machine without illegal actions or crashes, resumable from any autosave, deterministic by seed. **Performance target (a guess, see §12):** average under 60 seconds of wall time per Operations Stage.

### P5 and later (not in scope for v1)

Smarter AI, automated sub-commanders for the human, shorter Rommel-start campaign (§61, §64.2), additional scenarios, polish.

---

## 8. Rules ambiguity, errors and verification

The operator cannot adjudicate rules and agents MUST NOT queue rules questions for them. CNA's rules are long and imperfect, so a deterministic policy replaces escalation.

### 8.1 Ambiguity policy (apply in order; log every use as `docs/decisions/RD-xxxx.md`)

1. **Official errata** (R-03) override the rulebook, but only once the operator has placed the file in `docs/sources/`.
2. A **scenario-specific rule** (§§60-64) overrides the general rule, for that scenario only.
3. A **more specific case** overrides a more general one; a case inside the owning major section overrides a passing mention elsewhere.
4. If still ambiguous, choose the **simplest reading that does not grant the acting player an extra advantage**, and register a toggle in `rules_variants.json` so the alternative can be tried later.
5. Never stop work for a rules ambiguity. Record `RD-xxxx` with: case ids, quoted conflicting text (under 25 words each), chosen reading, alternative, affected tests.

### 8.2 OCR and transcription defects

If text is garbled and R-02 is available, consult it. If not, mark the case `ocr-suspect` in the index, choose the most plausible reading, and log an `RD`. Never silently "fix" the vendored transcription: corrections live in `docs/rules/overrides.yaml`, each citing a reason.

### 8.3 Traceability and tests

- Every rule function carries `RULE:` case ids. `tools/coverage.py` reads them, the index and the tests, and writes `coverage/rules_coverage.json` with status per case: `unimplemented | partial | implemented | not_applicable | deferred(reason)`.
- A case may be marked `implemented` only if a test names it. Examples in the rulebook text (search for "Example") are turned into tests.
- **Invariant tests** (run inside the soak): no negative quantities; stacking limits; supply conservation; every action in the log was in `legal_actions` at the time; save/load/replay hash equality.
- **Mutation sanity:** each milestone includes one test that deliberately breaks a rule and proves the test suite notices.

### 8.4 Reading discipline for weak or free models

Workers MUST NOT read the whole rulebook. `python -m cna.tools.show_rule 8.41` prints a case with its cross-referenced cases. A task card lists the case ids and the section files it needs; each task keeps rules input under about 6,000 words.

---

## 9. UMAWS operating instructions

Facts below come from `UMAWS_USER_MANUAL.md` (v1.0.0) and the Completion Report v1.2.0. The report records that the manual is wrong in places (for example it assumes WSL and port 8080 for the console), so **trust the report where they disagree and verify any command with `pmk --help` first**. Anything I could not verify is marked.

### 9.1 Operator runbook (PowerShell, native Windows)

1. **Check UMAWS is healthy.** In the UMAWS repo with its venv active (`.venv\Scripts\activate`): `python -m pmk.cli sentinel` should report all invariants ok. `pmk fleet profiles` should show the profiles in §9.3 (verify; they come from our earlier approved plan, not from the manual).
2. **Create the project folder and seed it:**
   ```
   mkdir C:\temp\projects\cfna
   cd C:\temp\projects\cfna
   git init
   mkdir docs\sources
   copy <wherever>\proposal-cfna-game-v1.md docs\sources\
   git clone https://github.com/tonicebrian/TheCampaignForNorthAfrica docs\sources\cna-rules-upstream
   git -C docs\sources\cna-rules-upstream checkout 75a037f27346a7cd920a765a2f3cae965b1e07a3
   ```
   (Delete `docs\sources\cna-rules-upstream\.git` after checkout if you want the folder tracked as plain files.)
3. **Initialise the project** (per manual, "Project Lifecycle"; verify flags with `pmk project init --help`):
   ```
   pmk project init --brief "Build the CNA digital edition. Authority: docs/sources/proposal-cfna-game-v1.md. Read it by heading, never import it into CLAUDE.md or AGENTS.md. Start with Phase P0." --path C:\temp\projects\cfna
   ```
4. **Let the Overseer write the Project Design Document** from the proposal, then start work (`pmk project run --seconds 300`, or the one-click control in the Console, which per the report listens on `http://127.0.0.1:8765`; start it the way you did for Toy3).
5. **When asked, answer queue items.** `pmk queue list` then `pmk queue decide <Q-id> "<option>"`. Expected items are only about missing files (§3.2) and anything destructive.
6. **To stop:** `pmk stop` (freeze) or create `pilot\STOP`. `pmk resume` to continue.
7. **To play** after P1: from the project folder, `python -m cna.ui.tk_app`. For a headless AI-vs-AI soak: `python -m cna.tools.soak --seeds 20 --turns 6`.

### 9.2 Known UMAWS caveats that affect this project (from Report v1.2)

- Tier A (Foundation) only; Tier C was not achieved. No sandbox: agents can write anywhere your Windows account can. Keep work inside `C:\temp\projects\cfna`.
- Real concurrent capacity measured at 6 workers; the "100 agents" test used fake workers. Do not plan for more than about 6 at once.
- A duplicate-launch concern remains under review (`spawn_slot` called twice on a transition). If you see two agents on one task, `pmk fleet disable` one and note it.
- Task oracles MUST be Windows-safe. The earlier T-0003 failure was a POSIX `test`/`grep` oracle on native Windows. Use `python -m pytest ...` or `python -c "..."`.
- Free models are rate-limited per model; recovery ladder L0-L4 handles exhaustion (manual: Fleet Dispatcher). Token cost is not a constraint here.

### 9.3 Profiles and roles (per the plan approved earlier; verify with `pmk fleet profiles`)

- **Overseer:** `overseer-beam` (OpenCode, `opencode/beam-free`).
- **Workers:** `hermes-oneshot`, `kilo-auto`, `opencode-beam`.
- **Off:** `pi`, `cline-mimo`, `opencode-strongest`, `opencode-fallback`.
- V2 blind review requires a different model family from the author (manual: Verification Levels). If only one family has quota, the review waits; it must not fall back to the same family.

### 9.4 `AGENTS.md` seed (keep under 60 lines; `CLAUDE.md` is a single line "See AGENTS.md")

```
# CNA digital edition: agent rules
Authority: docs/sources/proposal-cfna-game-v1.md (read by heading; never import).
Platform: Windows 10 native, Python >=3.11, stdlib + pytest only. venv: .venv\Scripts\activate
Work only inside C:\temp\projects\cfna. No network except pip for approved packages.
Rules source: docs/rules/ (pinned). Use `python -m cna.tools.show_rule <case>`; never read whole files.
Official sources only. Anything in docs/sources/ placed by the operator counts as authorised.
Never invent historical data. Missing data -> schema + placeholder + docs/data-gaps.md entry.
Every rule function has a docstring `RULE: <case ids>`; a case counts as implemented only if a test names it.
Never ask the operator a rules question. Apply proposal section 8 and write docs/decisions/RD-xxxx.md.
Engine is pure and deterministic. No I/O, clock or global random in src/cna/engine, rules, state.
AI uses view(state, side) only. All actions pass through legal_actions/apply.
Oracles must be Windows-safe: python -m pytest -q <file> or python -c "...". No test/grep/sh.
One task = one module + its tests, <= 45 min, <= 6,000 words of rules input.
Regenerate coverage (python -m cna.tools.coverage) before submitting any task that touches rules.
```

### 9.5 Overseer instructions

1. Write the PDD from this proposal, preserving §§4, 6, 7, 8 as binding. Do not shorten the success criteria.
2. Decompose by the phase plan. One task per rules cluster or tool; no task writes outside its declared scope.
3. Raise **Class K queue items only** for: missing resources (R-xx), destructive actions, or a change to this proposal's scope. Provide a recommended option and a safe default each time. Never queue rules questions.
4. Use `synthetic` fixtures to keep moving when real data is missing. Never mark a milestone "complete" while its data gap is open; mark it "complete with gaps" and cite `docs/data-gaps.md`.
5. After each milestone: run the soak, regenerate coverage, and write `docs/milestones/Mx-report.md` listing what passed, what was skipped, and which guesses were made (cite `RD` ids). Reports MUST NOT claim more than the evidence bundle shows; the earlier UMAWS report overstated results and had to be corrected.
6. Review the `spawn_slot` duplicate-launch concern before scaling beyond a few workers.

### 9.6 First tasks (Phase P0 and P1a). Scopes and oracles are suggestions for the Overseer.

| Task | Title | Write scope | Oracle |
|---|---|---|---|
| T-01 | Repo skeleton, `pyproject.toml` (src layout, pytest `pythonpath = src`, editable install so `python -m cna...` works), `.gitattributes` (LF), `AGENTS.md`, `CLAUDE.md` pointer | root, `tests/test_smoke.py` | `python -m pytest -q tests/test_smoke.py` and `python -c "import cna"` |
| T-02 | Vendor rules at pinned commit into `docs/rules/`, with checksums manifest | `docs/rules/` | `python -c "import json;m=json.load(open('docs/rules/manifest.json'));assert len(m['files'])>=66"` |
| T-03 | Rules indexer: sections, case anchors, xrefs, tables to `docs/rules/index.json` | `src/cna/tools/rules_index.py`, tests | `python -m pytest -q tests/test_rules_index.py` (expects 65 sections, 1,737 anchors at the pinned commit) |
| T-04 | `show_rule` tool (case plus cross-references) | `src/cna/tools/show_rule.py`, tests | `python -m pytest -q tests/test_show_rule.py` |
| T-05 | Coverage tool and initial `coverage/rules_coverage.json` | `src/cna/tools/coverage.py`, tests | `python -m pytest -q tests/test_coverage.py` |
| T-06 | Core: ids, errors, dice (d6, 2d6, sequential 11-66), seeded RNG | `src/cna/core/`, tests | `python -m pytest -q tests/test_dice.py` |
| T-07 | State model, JSON serialisation with schema version, state hash | `src/cna/state/`, tests | `python -m pytest -q tests/test_state_roundtrip.py` |
| T-08 | Event log and replay | `src/cna/core/events.py`, `src/cna/tools/replay.py`, tests | `python -m pytest -q tests/test_replay.py` |
| T-09 | Data schemas, validators, provenance/status fields | `src/cna/data/`, `data/`, tests | `python -m pytest -q tests/test_data_schema.py` |
| T-10 | Gap register generator and the first Class K queue item for R-02..R-05 | `src/cna/tools/data_gaps.py`, `docs/data-gaps.md` | `python -m pytest -q tests/test_data_gaps.py` |
| T-11 | Decision-point model: `Decision`, `Action`, `pending`, `legal_actions`, `apply` | `src/cna/engine/`, tests | `python -m pytest -q tests/test_engine_contract.py` |
| T-12 | Sequence-of-play state machine from §5.2 (Appendix B as data) | `src/cna/rules/sec05_sequence.py`, tests | `python -m pytest -q tests/test_sequence.py` |
| T-13 | Initiative (§7) and Weather (§29), using synthetic tables where real ones are missing | `src/cna/rules/sec07_*.py`, `sec29_*.py`, tests | `python -m pytest -q tests/test_initiative_weather.py` |
| T-14 | Hidden information: `view()`, sealed commitments | `src/cna/state/views.py`, `src/cna/engine/sealed.py`, tests | `python -m pytest -q tests/test_views.py` |
| T-15 | `RandomLegalPlayer`, headless runner, soak tool | `src/cna/ai/`, `src/cna/ui/cli.py`, `src/cna/tools/soak.py`, tests | `python -m cna.tools.soak --seeds 5 --turns 3 --synthetic` (exit code 0) |
| T-16 | Rulesets module (`LAND_ABSTRACT` only now) and the §2.0 combination check logged as an RD | `src/cna/engine/rulesets.py`, `docs/decisions/` | `python -m pytest -q tests/test_rulesets.py` |

After T-16 the Overseer continues with P1b clusters, one task per cluster in the order in §7, each following the pattern: read the cases with `show_rule`, add data schema if needed, implement, cite, test, regenerate coverage, submit.

---

## 10. Constraints (hard boundaries)

- Windows 10 native only. No WSL, no Linux dependencies.
- Python >=3.11, stdlib plus `pytest` unless an RD approves more.
- Official sources only; nothing unofficial is used or fetched.
- No fabricated data presented as real. Placeholders are always labelled.
- Agents work only inside `C:\temp\projects\cfna` and do not delete operator-supplied files.
- The repository is private; do not publish the rules text.
- No paid APIs.
- `CLAUDE.md` and `AGENTS.md` stay lean; no `@`-imports of large files.

---

## 11. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Map and unit charts are not available digitally (R-04, R-05) | High | Engine-first design, synthetic fixtures, gap register, operator asked once, vision-assisted transcription as a later option |
| Action volume makes the AI slow or non-terminating | Medium | Atomic decisions, progress action always legal, per-segment caps, soak tests |
| Agents invent rules or numbers | High | Citation requirement, coverage tool, V2 independent review, RD log, "no fabricated data" rule |
| Free models drift or lose context on a 121k-word rulebook | High | Case-level reading, `show_rule`, small tasks, one module per task |
| Contradictory or garbled rules | High | Section 8 policy, overrides file, never block |
| UMAWS limits (Tier A, no sandbox, 6 real workers, duplicate launches) | Medium | §9.2 caveats, work inside project folder, modest concurrency |
| Scope is enormous (1,737 anchors plus 180 charts) | Certain | Phased delivery; honest "complete with gaps" reporting |
| Rules text copyright | Low for private use | Private repo, no publication |
| Windows-specific failures (paths, POSIX oracles, line endings) | Medium | Windows-safe oracles, `.gitattributes`, UTF-8 (`PYTHONUTF8=1`) |

---

## 12. Assumptions and guesses register

Every item here is something I inferred or decided without confirmation. The operator can overrule any of them.

| ID | Guess or assumption | Basis | If wrong |
|---|---|---|---|
| G-01 | "Full game" means Scenario Group Five (§64) and smaller scenarios are used as milestones | Operator believed there were no scenarios; transcription has five groups | Drop scenario milestones; P4 is unchanged |
| G-02 | Official SPI errata (R-03) count as "official" and are authorised once the operator places the file | Operator said "currently official rulebook" | Remove §8.1 item 1 |
| G-03 | The operator's "phase one" equals Phase P1 here (Land Game, legal AI) | Operator asked for legal moves first and the full game eventually | Re-slice P1 |
| G-04 | Tkinter UI, Python 3.11+, stdlib plus pytest | UMAWS runs 3.11/3.12; operator chose Python and said "default" for UI and packaging | Swap UI in §5 |
| G-05 | Profiles in §9.3 | Earlier approved plan; not in the manual | Edit §9.3 |
| G-06 | UMAWS commands and Console port | Manual plus Report v1.2 (report says 8765; manual says 8080) | Verify with `--help` |
| G-07 | No structured digital map data exists | I found only map images and module files; not exhaustive | Better: use it, skip R-05 workaround |
| G-08 | Human chooses side at new-game time and controls the whole side | Operator picked "default" | Fix the side in the loader |
| G-09 | Performance target under 60 s per Operations Stage | Pure guess | Relax in P4 |
| G-10 | I read the rules selectively (sections 1-7 in full or in part, §32 intro, §59-60, §64, glossary, equipment). The rest I mapped from titles, counts and cross-references | Size (121k words) | Agents must verify section contents when implementing |
| G-11 | Hard "nevers" are minimal (project folder only, no paid APIs, no unofficial sources) | Operator said "no" to extra hard rules | Remove §10 items |
| G-12 | Contents of R-02, R-03, R-04, VASSAL modules and the Internet Archive scan are unverified | I could not open them (blocked or not retrievable) | Operator confirms what each actually contains |
| G-13 | Timeline is open-ended; no estimates are given | Operator chose open-ended | Add dates later |

---

## Appendix A. Rules map (generated from the pinned transcription)

`Cases` is the count of numbered-case anchors; `Words` is approximate. `Phase` shows when the section is first needed.

| § | Title | Words | Cases | Planned module | Phase |
|---|---|---:|---:|---|---|
| 1 | Introduction | 277 | 1 | `Reference / primer / sequence` | P0 |
| 2 | How To Play The Game | 784 | 1 | `Reference / primer / sequence` | P0 |
| 3 | Glossary And Unit Definitions | 2844 | 15 | `Reference / primer / sequence` | P0 |
| 4 | Game Equipment | 4391 | 27 | `Reference / primer / sequence` | P0 |
| 5 | The Sequence Of Play (Land Game) | 1062 | 3 | `Reference / primer / sequence` | P0 |
| 6 | The Capability Point System | 2083 | 20 | `land.core (CPA, initiative)` | P1 |
| 7 | Initiative | 443 | 9 | `land.core (CPA, initiative)` | P1 |
| 8 | Land Movement | 5441 | 80 | `land.movement (move, stacking, ZOC)` | P1 |
| 9 | Stacking | 1659 | 25 | `land.movement (move, stacking, ZOC)` | P1 |
| 10 | Zones Of Control | 1124 | 25 | `land.movement (move, stacking, ZOC)` | P1 |
| 11 | The Combat System | 2456 | 25 | `land.combat` | P1 |
| 12 | Barrage (Artillery Combat) | 1898 | 36 | `land.combat` | P1 |
| 13 | Retreat Before Assault | 406 | 11 | `land.combat` | P1 |
| 14 | Anti-Armor Combat | 1560 | 35 | `land.combat` | P1 |
| 15 | Close Assault | 6841 | 66 | `land.combat` | P1 |
| 16 | Patrols And Reconnaissance | 1643 | 34 | `land.patrol_morale_reserve` | P1 |
| 17 | Morale | 1609 | 27 | `land.patrol_morale_reserve` | P1 |
| 18 | Reserve Status | 693 | 14 | `land.patrol_morale_reserve` | P1 |
| 19 | Organization And Reorganization | 3770 | 58 | `land.organization_reinforcement` | P1 |
| 20 | Reinforcements, Replacements And Commonwealth Withdrawals | 2743 | 53 | `land.organization_reinforcement` | P1 |
| 21 | Breakdown | 2684 | 46 | `land.maintenance_construction` | P1 |
| 22 | Repair | 1900 | 39 | `land.maintenance_construction` | P1 |
| 23 | Engineers | 409 | 12 | `land.maintenance_construction` | P1 |
| 24 | Construction | 2746 | 67 | `land.maintenance_construction` | P1 |
| 25 | Fortifications | 360 | 13 | `land.maintenance_construction` | P1 |
| 26 | Minefields | 616 | 14 | `land.maintenance_construction` | P1 |
| 27 | Desert Raiders & Commandos | 3062 | 61 | `land.special_weather_fleet` | P1 |
| 28 | Prisoners Pow | 896 | 18 | `land.special_weather_fleet` | P1 |
| 29 | Weather | 820 | 28 | `land.special_weather_fleet` | P1 |
| 30 | The Mediterranean Fleet (Commonwealth) | 2073 | 44 | `land.special_weather_fleet` | P1 |
| 31 | Rommel | 280 | 1 | `land.special_weather_fleet` | P1 |
| 32 | Abstract Logistics And Air Rules | 5112 | 68 | `land.abstract_supply_air` | P1 |
| 33 | Sequence Of Play: Air Game | 1659 | 1 | `air.*` | P3 |
| 34 | The Aircraft | 2340 | 45 | `air.*` | P3 |
| 35 | Squadron Ground Support Units | 1259 | 20 | `air.*` | P3 |
| 36 | Air Facilities | 932 | 14 | `air.*` | P3 |
| 37 | Flight | 970 | 21 | `air.*` | P3 |
| 38 | Aircraft Maintenance | 1318 | 27 | `air.*` | P3 |
| 39 | Missions | 1349 | 27 | `air.*` | P3 |
| 40 | Fighter Combat | 2818 | 52 | `air.*` | P3 |
| 41 | Bombing Missions | 3143 | 60 | `air.*` | P3 |
| 42 | Non-Combat Missions | 1466 | 39 | `air.*` | P3 |
| 43 | Axis Italian/Aegean Air Bases | 409 | 12 | `air.*` | P3 |
| 44 | Malta | 1802 | 25 | `air.*` | P3 |
| 45 | Air-To-Air Combat | 3286 | 34 | `air.*` | P3 |
| 46 | Anti-Aircraft Fire | 1181 | 20 | `air.*` | P3 |
| 47 | Abstract Logistics Rules | 1182 | 33 | `air.abstract_logistics (Land+Air only)` | P3 |
| 48 | Sequence Of Play (Logistics Game) | 2126 | 1 | `logistics.*` | P2 |
| 49 | Fuel | 1063 | 13 | `logistics.*` | P2 |
| 50 | Ammunition | 522 | 10 | `logistics.*` | P2 |
| 51 | Stores | 468 | 13 | `logistics.*` | P2 |
| 52 | Water | 1319 | 29 | `logistics.*` | P2 |
| 53 | Trucks And Transport | 1218 | 15 | `logistics.*` | P2 |
| 54 | Supply Co-Ordination | 1161 | 24 | `logistics.*` | P2 |
| 55 | Ports And Supply | 1122 | 20 | `logistics.*` | P2 |
| 56 | The Axis Naval | 1405 | 25 | `logistics.*` | P2 |
| 57 | Commonwealth Supply Base | 89 | 1 | `logistics.*` | P2 |
| 58 | Abstract Air Rules | 486 | 9 | `logistics.abstract_air (Land+Logistics only)` | P2 |
| 59 | Introduction To Scenarios | 2269 | 30 | `scenario.loader (intro)` | P1 |
| 60 | Scenario Group One: The Italians | 3039 | 32 | `scenario.data (test beds)` | P1-P4 |
| 61 | Scenario Group Two: The Desert Fox | 2932 | 25 | `scenario.data (test beds)` | P1-P4 |
| 62 | Scenario Group Three: Operation Crusader | 3462 | 27 | `scenario.data (test beds)` | P1-P4 |
| 63 | Scenario Group Four: El Alamein | 4895 | 38 | `scenario.data (test beds)` | P1-P4 |
| 64 | Scenario Group Five: The Campaign For North Africa | 1515 | 18 | `scenario.campaign (full game)` | P4 |
| 65 | In Conclusion | 2155 | 1 | `Reference` | P0 |

---

## Appendix B. Land Game sequence of play as data (from §5.2)

Agents implement this as a data table in `sec05_sequence.py` and verify it against `docs/rules/` §5.2. The Air and Logistics Games have their own sequences (§33, §48); do not merge them by guesswork.

```
Game-Turn
  I    Initiative Determination Stage                      (§7)
  II   Naval Convoy Stage
         A Naval Convoy Schedule Phase
         B Tactical Shipping Phase
  III  First Operations Stage      } repeated as IV (second) and V (third)
         A Initiative Declaration Phase   (winner states Player A or B for this stage)
         B Weather Determination Phase    (§29)
         C Organization Phase (any order): Reorganization / Construction / Training segments
         D Naval Convoy Arrival Phase
         E Commonwealth Fleet Phase: Assignment, Repair
         F Reserve Designation Phase      (§18)
         G Movement and Combat Phase      (segments 1-4 may repeat, subject to §8.2)
              1 Movement Segment (reaction by Player B where permitted)
              2 Breakdown Determination Segment
              3 Combat Segment: Position Determination -> Barrage (secret plot)
                   -> Retreat Before Assault -> Force Assignment (secret)
                   -> Anti-Armor -> Close Assault
              4 Reserve Release Segment
         H Truck Convoy Movement Phase
         J Commonwealth Rail Movement Phase
         K Repair Phase: Towing, Maintenance
         L Patrol Phase
       then Player B performs phases F through L
  VI   End of Game-Turn
```

Notes: phase letters skip "I" in the source. Phases F-L are performed by Player A, then by Player B. The player with Initiative chooses whether to be A or B in each Operations Stage (§7).

---

## Appendix C. Planned data files

`data/units.json`, `data/oa_chart.json`, `data/reinforcements.json`, `data/hexes.json`, `data/terrain_effects.json`, `data/charts/*.csv` (CRTs, weather, breakdown, production), `data/scenarios/*.json`. Every file begins with a header: `{"schema": n, "source": "...", "status": "verified|ocr_suspect|placeholder|synthetic"}` and every row carries `provenance`.

---

## Appendix D. Plain-English glossary seeds (from §3.0)

Cohesion Level: how combat-effective a unit currently is. CPA: Capability Point Allowance, the per-stage budget for every action. TOE Strength Point: size/equipment measure. Log Sheet: per-unit paper record, our unit state record. OA Chart: Organization at Arrival chart (arrival date, make-up, strength). Reaction: a unit's ability to evade combat. Barrage: artillery attack that removes the need for adjacent infantry assault. Initiative: who chooses to move first or last. ZOC: zone of control (rigid and active here). Shell Unit: a unit under minimum strength. Supplies: ammunition, fuel, stores, water.

---

## Appendix E. Sources consulted

- Rules transcription: github.com/tonicebrian/TheCampaignForNorthAfrica (cloned, inspected, pinned).
- Wikipedia, *The Campaign for North Africa* (box contents, 111 turns, successor game).
- Wargamer, "Two years into the world's most complicated board game" (1,500 hours, pasta rule, two-person team's spreadsheets).
- BoardGameGeek and aggregator listings (8-10 players); SPI *Moves* issue 49 survey (booklet and chart counts, 31 terrain types).
- SPI errata page (September 1979), VASSAL module library pages, Internet Archive item, Steam Workshop listing, Noble Knight listings. All quoted only by search snippet; not opened.
- UMAWS User Manual v1.0.0 and Completion Report v1.2.0 (operator uploads).
- Not accessible to me: the BoardGameGeek thread the operator linked (bot protection). Its contents are unknown to this proposal.

*End of proposal. Author: Claude (Sonnet 5.5, Anthropic). Version 1.0.0. Date: 2026-10-31.*
