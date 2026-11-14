# PROMPT (drafted for this task — shown, then answered below)

**Role** — You are the design authority for a coordination system: a staff-level systems designer with deep familiarity with append-only event-log kernels, lease-based task ledgers, and multi-agent fleets of free-tier LLMs. Use the vocabulary of this repo (Kernel, Overseer, lease, write scope, oracle, gate, D-L6, class K); change no terms casually.

**Context** — UMAWS Fleet Launcher (`C:\temp\projects\testproject1`) decomposes projects into task cards on a ledger; LLMs claim cards under leases and their diffs are merged only within declared write scopes. Cards are currently gated by (among other things) write-scope overlap at claim time, so only a few agents can work the ledger concurrently — observed utilisation is far below the machine's capacity (`max_total_agents = 10`, raised by the operator 2026-11-01; `agents.toml`). The operator wants a *more thorough decomposition system*: finer-grained task decomposition that lets more LLM agents work ledger tasks concurrently, raising utilisation. This is a design task, not an implementation task — but the output must be an executable brief an implementing LLM can follow.

**Audience** — (1) the human operator, as decision record; (2) the implementing LLM(s), as an executable brief with phases, file paths and acceptance criteria; (3) the Overseer and future agents, as the decomposition contract they will actually operate under.

**Format and length** — A candidate-tier proposal document in the repo's established style (frontmatter with provenance and epistemic tags; numbered sections; appendices; analogous in scope to `proposal-deepseek-umaws-fleet-parallel-decomposition-v1.md` and `assessment-claude-umaws-fleet-parallel-decomposition-v1.md`, but a *fresh* design that references them rather than inherits them). Roughly 15–25 pages of Markdown. Stored as a `.md` file in the repo root.

**Success criteria** —
1. **Executable and proven**: every mechanism names the file(s) it touches, the phase it belongs to, and how success is *measured* (a command and a number) — no "the Overseer should try harder" steps.
2. **Utilisation, not activity**: the design moves sustained concurrent-agent utilisation toward the cap with disjoint write scopes, and says exactly how that is verified (wave width, busy-slot minutes, void rate), rather than merely creating more cards.
3. **Honest about ceilings**: states what decomposition cannot fix (provider capacity, shared hot files, merge serialisation, Overseer wake budget) and which decisions belong to the operator — including anything class K.

**Constraints** —
- Advisory/candidate tier only; nothing takes effect without operator decision. Class K items (policy/constitution/admission changes) must be flagged two-key, never slipped in.
- No Kernel rewrite. D-L6 (disjoint write scopes at claim) is the default to *preserve*; finer granularity is the lever. D-L6 is explored, with options and a recommendation — not presumed abolished.
- Native Windows, Python 3.12, stdlib-first in `src/pmk`; keep it so where possible.
- Free-tier model reality: flaky CLIs, `MODEL_GONE`, `QUOTA`, `UNKNOWN`; the recovery ladder L0–L4 exists — the design must not assume reliable agents.
- I5 (Oracles decide) extended to decomposition: decomposition quality must be machine-checked, not prompt-wished.
- Fleet cap: treat as operator-set (currently 10, per `agents.toml`); raising it is a separate operator decision and out of scope.
- Include a **Phase 0 read-only census** before any design claim is treated as fact — the "gated by scope" diagnosis is plausible but not proven.
- Existing in-flight ledger cards: design covers both future waves and a *staged* re-scope of existing cards (void is operator-only).
- No live/costed provider calls. Tests must stay green (`pytest -q`) and `pmk sentinel` clean for any code the brief proposes.
- Granularity target: present a *ladder of options with tradeoffs*, not a single magic number.
- Dependency-chain handling: explore both (strict `depends_on` discipline vs contract-first/speculative fan-out) and recommend.

**Examples / prior art** — `description`: the interview answers (this session) select: deliverable = design + executable brief; change surface = Overseer prompt/briefing, `pmk` library + CLI, Fleet layer, Kernel/policy (flagged); D-L6 = explore both, recommend; success = leaseable width + slot utilisation + sustained 6-of-6 (+provable/measured); existing cards = both, staged; prior docs = fresh design referencing them; granularity = options with tradeoffs; dependencies = explore both; authority = advisory only; audience = operator + implementing LLM + Overseer; constraints = Windows/stdlib, free-tier reality, I5; diagnosis = both (census + design); length = full proposal doc. Repo references: `src/pmk/decompose.py` (width analysis), `src/fleet/overseer.py` (one-sentence decomposition guidance), `src/pmk/models.py` (`scope_overlaps`, prefix-overlap rule), `HANDOFF.md` (2026-11-11 state: 212 cards / 155 VOID / 12 READY; cap 10), `relay-C-phase0-census-v1.md`, `pilot/STATE.md`. No external examples exist beyond these.

**Output** — Write the document to the repo root, then summarise it, flagging every place you guessed or could not verify.
