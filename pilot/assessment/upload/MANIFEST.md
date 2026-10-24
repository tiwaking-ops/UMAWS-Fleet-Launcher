# Upload Manifest — UMAWS Completion Report v1.1.0

**Package purpose:** Evidence bundle for the UMAWS completion report (v1.1.0) and Part A3 investigation.

**Total files:** 9
**Total uncompressed size:** 38,480 bytes (37.58 KB) — well under the 300 KB limit.

**SHA-256 hashes:** computed with `hashlib.sha256` on the uploaded files; use `sha256sum -c` or equivalent to verify.

| File | Size (bytes) | SHA-256 |
|---|---|---|
| EB-T-0003-3/bundle.json | 1378 | 1e09d3b69a03a5fa661ecbf3ab0f556691717a8f5a548ffe13995b5767d214dc |
| cli-matrix.md | 6391 | 53d55842a25a71751f5c3cd9b4eaf99329748d4c84af1a8578df17fff9d1dcf8 |
| console-side-effects-ran-now.txt | 3477 | 1a07841f4a7dfaede4d82af69517f11d1ddba24573682d241e52c863e7b271e8 |
| decisions-D41-end.md | 21969 | bcf01fefac9866ad6353bad2d810fc7f1fd96e4a8febdb7f46f68d1089f93f37 |
| event-counts-ran-now.txt | 1822 | 5771d61227ad6d3fc50d1061067aa65eba3f966d7c4003d9ee670074add05d34 |
| g5-summary.json | 198 | 83611f8c3fb7104f9ae94342a70b94b12a265d17f5fd509e37aa8ed9d13012ed |
| opencode-patterns.toml | 305 | d8222e8aef4ac3a0369796aedb90c8175d222bbc78b2a468d60885155bcd1762 |
| scale-f7.json | 315 | 08f04717bff2fd2744bbb311e94e8a6f6bc84a19266e67b98f416a6837e40553 |
| t0003-lifecycle-extract.txt | 2625 | e1c423ddf9c97eacc29cabf03424147a6e33f858753ecf2b92cc1d715f32cd56 |

## File descriptions

1. **console-side-effects-ran-now.txt** — Console smoke test side-effect record (RAN-NOW run A and B). Contains the FLEET_ASSIGNED event counts (319 for T-0002) and confirms the dispatcher defect.
2. **event-counts-ran-now.txt** — Event log per-type counts (584 total events, hash chain ok, 0 repairs).
3. **t0003-lifecycle-extract.txt** — T-0003 lifecycle extract: AGENT_STARTED, CLAIMED, FLEET_ASSIGNED, AGENT_EXITED, AGENT_RESUMED, AGENT_FAILED events from `.pm/events/2026-10-23.jsonl`.
4. **EB-T-0003-3/bundle.json** — Evidence bundle for T-0003 (the REWORK path): outputs, commands, oracle_results, etc.
5. **cli-matrix.md** — S-A1 CLI matrix (cli-matrix.md): hermes, kilo, pi, cline, opencode — headless, session IDs, resume, model swap, classifier.
6. **opencode-patterns.toml** — opencode classifier patterns (`tests/fleet/fixtures/opencode/patterns.toml`). Quota pattern: `pattern = "Rate limit exceeded"` (matches opencode's own formatting, not openrouter's credit-exhaustion error).
7. **g5-summary.json** — G5 capacity run (6 real workers: 3 hermes + 3 kilo): 6/6 DONE, peak 6, min RAM 5162 MB, sentinel ok, close-check ok.
8. **scale-f7.json** — F7 scale drill (100 fake workers): 100/100 DONE in 104.8s, peak 100 slots, min RAM 7491 MB, sentinel ok.
9. **decisions-D41-end.md** — Decisions D-41 to D-end from pilot/decisions.md, including D-51 (two latent defects fixed), D-52 (T-0003 quota pattern finding), D-53 (AGENT_RESUMED mislabel finding), D-54 (pi dispatch real finding).

## Verification

To verify the hashes:

```bat
cd pilot\assessment\upload
certutil -hashfile EB-T-0003-3/bundle.json sha256
certutil -hashfile cli-matrix.md sha256
certutil -hashfile console-side-effects-ran-now.txt sha256
certutil -hashfile decisions-D41-end.md sha256
certutil -hashfile event-counts-ran-now.txt sha256
certutil -hashfile g5-summary.json sha256
certutil -hashfile opencode-patterns.toml sha256
certutil -hashfile scale-f7.json sha256
certutil -hashfile t0003-lifecycle-extract.txt sha256
```

Or with `sha256sum -c MANIFEST.md` (after regenerating the checksum file).
