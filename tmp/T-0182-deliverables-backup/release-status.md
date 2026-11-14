# Release status

This note keeps the two completion scopes separate. It is a status note, not a
new release authority.

## PDD-scoped release

Status: **released for G-001/G-002**.

Authority: `docs/PDD.md`. The PDD defines G-001 (rules implemented, cited and
covered) and G-002 (the computer opponent chooses only legal actions). Its
`gate_cmd` and `pmk project close-check` are release-scope checks only.

A green close-check means the narrowed release gates pass. It is not evidence
that the full CNA digital edition is complete.

## Full product

Status: **incomplete; in progress**.

The full-product scope and phased delivery are defined by:

- `docs/sources/proposal-cfna-game-v1.md`
- `docs/plans/cna-p1b-p4-implementation-plan.md`
- `docs/plans/cna-p1b-p4-case-backlog.csv`

P1b-P4 are not all delivered. The current per-case implementation status is in
`coverage/rules_coverage.json`; full-product progress is determined by the
phase backlog and that coverage report, not by the close-check alone.

Data readiness is a binding constraint. `docs/data-gaps.md` records the open
resources; R-04, R-05 and R-06 are decisive for charts and tables, structured
map data and counters. Synthetic fixtures may exercise engine contracts, but
they are not historical data and do not close those gaps.

## Status language

Use "PDD-scoped release" for the green G-001/G-002 gate and "full product" for
the complete campaign. Do not present the close-check as evidence of
full-product completion, and do not claim full-proposal completion while the
coverage report still contains unimplemented or partial cases.
