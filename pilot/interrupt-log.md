# Interrupt log (pilot v1 §12.3)

`date | initiator (agent/human) | gate or topic | minutes | avoidable? (y/n) | structural fix proposed`

| date | initiator | gate or topic | minutes | avoidable | structural fix |
|---|---|---|---|---|---|
| 2026-10-22 | human | scope: whole pilot Tier A→C vs Fleet-only | 3 | n | operator preference; recorded D-05 |
| 2026-10-22 | human | repository location | 1 | n | operator preference; recorded D-01 |
| 2026-10-22 | human | CLI probing depth (metadata vs full S-A1) | 2 | n | operator chose to protect free-tier quota; recorded D-03 |
| 2026-10-22 | human | gate behaviour (stop at G0–G3?) | 2 | y | operator said they would supply the rule; agent continued under the pilot-v1 default (hold) and did not cross any gate. A standing "gate posture" in STATE.md would remove the need to ask. |
| 2026-10-22 | human | missing source specs (QuotaGate v1.1, CIP) | 2 | n | agent located and reported the gap; operator supplied both files |
