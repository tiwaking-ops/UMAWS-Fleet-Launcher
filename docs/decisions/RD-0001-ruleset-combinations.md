# RD-0001: Ruleset combinations for Phase P1

- **Status:** accepted for P1
- **Date:** 2026-11-08
- **Cases:** 2.0, 32, 33, 47, 48, 58
- **Chosen by:** CNA implementation (rule 8.1 order)

## Question

Which module combination does the first playable phase use, and what do the
abstract sections replace?

## Decision

Phase P1 exposes **`LAND_ABSTRACT`** only. It activates the Land Game
sequence (5.2) and the Land Game's abstract supply and air rules (32). The
Air Game (33-47) and Logistics Game (48-58) remain deferred until their
charts and tables are available; the `LAND_AIR`, `LAND_LOGISTICS` and `FULL`
rulesets are named but refused with a clear error.

## Why

The proposal's P1 exit is the Land Game skeleton with a legal AI. Section 32
is the Land Game's own abstract supply/air section, so using it does not
claim that the Air or Logistics Games are implemented. The missing charts
(R-04) and map/unit data (R-05) block the other combinations, and a
placeholder table must not be presented as historical data.

## Alternatives considered

- **Declare all four rulesets and let them run:** rejected; it would imply
  modules exist when they do not.
- **Name only `LAND_ABSTRACT`:** rejected; callers need a stable identifier
  for the deferred combinations and a refusal message that says why.
- **Implement the Air/Logistics sequences now:** rejected for P1; their
  sequence tables and data are not available.

## Affected tests

- `tests/test_rulesets.py` pins the available set and the refusal path.
- `tests/test_ai_soak.py` runs the synthetic P1 loop with `LAND_ABSTRACT`
  semantics (the synthetic fixture does not use historical data).
