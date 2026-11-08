# Repair evidence findings (P3.1)

Generated from the live ledger bytes, not from the report's summary.

| Question | Finding |
|---|---|
| OQ-1 — who edited `.pm/policy.toml` at 18:38:48Z | **The operator.** Confirmed in the approval interview: they made the edit. The `mtime` matches the second `PINS_CHECKED` mismatch, so the sequence is now explained: authorised edit, then a mismatched check. |
| OQ-2 — who decided Q-077 | See the raw events below. The decision payload and the following check carry different human actor labels. |
| OQ-4 — which session made e08fa8d/ebe46ce | **Unchanged: unknown.** Four commits carry the human identity while neighbouring commits use the repo-local one. No session evidence establishes the actor; recorded as unknown rather than guessed. |
| OQ-5 — working-tree drift | Classified in `pilot/repair-drift-classification-v1.md`; the decisions log was CRLF churn plus D-58…D-61. |
| OQ-6 — T-0150 canary accepted? | **Unknown.** Criteria were not re-adjudicated here; recorded as an open question for D-66. |
| OQ-8 — other exposed spawns | Answered by `tools/check_subprocess_env.py`: 7 reviewed exceptions, each with a reason. |

## Raw ledger events (verbatim JSON)

### Seq 3116

```json
{
  "actor": {
    "agent": "tiwa-pene",
    "kind": "human",
    "model": "",
    "role": "supervisor",
    "session": ""
  },
  "fence": null,
  "hash": "04734bc481da3f62b4e7353811b313e17f4ceb1251f3af429baa33efab7d1a2f",
  "kernel_version": "0.1.0",
  "payload": {
    "choice": "ratify",
    "id": "Q-077"
  },
  "policy_hash": "a348c4c78e911f9cf732143c04d6378636e09646195c41e60664f9d8d0547811",
  "prev_hash": "249036155b3e9d804c75a5122afce71d008168b52aab3e17e66d676b1b93dc17",
  "seq": 3116,
  "subject": "Q-077",
  "ts": "2026-11-07T18:39:15Z",
  "type": "QUEUE_DECIDED"
}
```

### Seq 3117

```json
{
  "actor": {
    "agent": "operator",
    "kind": "human",
    "model": "",
    "role": "supervisor",
    "session": ""
  },
  "fence": null,
  "hash": "d0af7581692f4b1df8039f67014acae1447af0051324262d300c10021f736790",
  "kernel_version": "0.1.0",
  "payload": {
    "note": "the pins were re-recorded",
    "recorded": "C:\\temp\\projects\\testproject1\\.pm\\pins.sha256"
  },
  "policy_hash": "a348c4c78e911f9cf732143c04d6378636e09646195c41e60664f9d8d0547811",
  "prev_hash": "04734bc481da3f62b4e7353811b313e17f4ceb1251f3af429baa33efab7d1a2f",
  "seq": 3117,
  "subject": null,
  "ts": "2026-11-07T18:39:16Z",
  "type": "PINS_CHECKED"
}
```
