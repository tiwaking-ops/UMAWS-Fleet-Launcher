# MANIFEST — UMAWS Completion Report Bundle

**Generated:** 2026-10-24  
**Bundle root:** `pilot/assessment/bundle/`  
**Total files:** 58  
**Total size:** 717,278 bytes (700.5 KB)  
**Size limit:** < 3 MB (bundle) and < 150 KB per file  

## Legend

| Label | Meaning |
|---|---|
| `RAN-NOW` | Executed in this session; raw output attached |
| `READ` | Taken from an existing project file; cited with path |

## Files

| Path | Size | SHA-256 | Label | What it proves |
|---|---:|---|---|:---:|
| `fixtures/cline-model-gone.txt` | 693 | `17891bc7f7b5c85a…151f9bba` | READ | Cline MODEL_GONE fixture ('Free model promotion ended') |
| `fixtures/cline-patterns.toml` | 273 | `2e09004359caad38…d5e727e0` | READ | Cline adapter classifier patterns |
| `fixtures/fake-network.txt` | 163 | `58fe57dca189fc25…654129eb` | READ | Fake CLI network failure fixture |
| `fixtures/fake-patterns.toml` | 474 | `2e72e9976eae87c8…c1ac7b46` | READ | Fake CLI classifier patterns |
| `fixtures/fake-quota.txt` | 206 | `5a23e0a941fa9284…e661265a` | READ | Fake CLI quota failure fixture |
| `fixtures/opencode-patterns.toml` | 305 | `d8222e8aef4ac3a0…5bcd1762` | READ | OpenCode adapter classifier patterns |
| `fixtures/opencode-quota.txt` | 872 | `6465add6d75293b4…5d8b5538` | READ | OpenCode QUOTA failure fixture (captured: 'Rate limit exceeded: free-models-p… |
| `raw/cli-help-sweep-ran-now.txt` | 4,159 | `6b0859b84e625753…0f8faf03` | RAN-NOW | pmk --help, task, fleet commands exist with documented flags |
| `raw/console-side-effects-ran-now.txt` | 3,477 | `1a07841f4a7dfaed…e7b271e8` | RAN-NOW | 2 defects found: FLEET_ASSIGNED spam, dispatcher ignores pilot/STOP |
| `raw/console-smoke-ran-now.txt` | 54,847 | `c683ccb889c6612e…631c0cba` | RAN-NOW | Console starts on port 8765, 9 GET endpoints + SSE = 200/streaming |
| `raw/event-counts-ran-now.txt` | 1,822 | `5771d61227ad6d3f…add05d34` | RAN-NOW | 584 events, hash chain verified, 0 repairs, per-type counts |
| `raw/event-log-head-tail-ran-now.txt` | 24,159 | `fdc7d365b502685d…ce52a3ea` | RAN-NOW | Event log head 50, tail 50, T-0001/T-0002/T-0003 lifecycles |
| `raw/full-suite-ran-now.txt` | 1,830 | `9133b48ace1b7872…f3d56ac8` | RAN-NOW | Full test suite: 234 passed in 71.77s (clone) |
| `raw/sentinel-after-console-ran-now.txt` | 189 | `2f170d737e42a16c…bac15f50` | RAN-NOW | pmk sentinel: ok=true, 16 invariants pass (I1,I3,I4,I5,I6,I7,I8',I13,I14,I15,… |
| `raw/tests-fleet-ran-now.txt` | 565 | `7fae819d970f374c…394d0b88` | RAN-NOW | Fleet test suite: 50 passed in 37.79s (fake CLI scenarios) |
| `raw/views-check-ran-now.txt` | 632 | `93c0293a0351e10f…5c7bf39e` | RAN-NOW | I13 verified: all 3 views (ledger, status, queue) match projection byte-for-byte |
| `read/EB-T-0003-3/Bundle.json` | 1,378 | `1e09d3b69a03a5fa…67d214dc` | READ (evidence bundle dir) | EB-T-0003-3: T-0003 evidence bundle file |
| `read/STATE.md` | 11,355 | `16ccfc46b18cb769…a5e2748f` | READ | Current pilot state; gates, scope, open items V-01..V-09; limitations L-F1..L-F5 |
| `read/UMAWS_USER_MANUAL.md` | 22,168 | `48c4d95640fd1b7d…07679234` | READ | User manual with claims to verify (Tier C, port 8080, wrong tabs) |
| `read/agents.toml` | 7,452 | `98873b67d521f686…3b92f7cd` | READ | Fleet profiles: 6 profiles, 5 adapters, families declared (mostly 'unknown') |
| `read/amendment-gates.md` | 9,545 | `508d028178fb6f91…b1292625` | READ | Gate amendment v2: classify by action not gate number; in force (Q-003, D-34) |
| `read/caliber-integration.md` | 45,926 | `603ff0649881190f…f7664033` | READ | CIP Caliber integration spec |
| `read/caliber-s1-s5.md` | 13,492 | `bfa00bb59cdb175e…e88985fe` | READ | Caliber spikes S1-S5: commands exist, version 1.55.2, score 87/A |
| `read/caliber-score.json` | 8,150 | `f87f3e2b6bd89815…3a56fec1` | READ | Caliber score: 87/100, grade A, 22 checks |
| `read/caliber-spike-results.json` | 2,398 | `5194e7903d8aeeee…5ff1e67e` | READ | S2/S3/S5 results: files added, determinism verified, score recorded |
| `read/cli-matrix.md` | 6,391 | `53d55842a25a7175…f9d1dcf8` | READ | S-A1 CLI matrix: 13 requests, 5 CLIs, headless/resume/model-swap measured |
| `read/console-index.html` | 21,992 | `5f5001a3af369913…f7dc8bf2` | READ | Console static HTML: 7 tabs (Projects, Fleet, Tasks, Queue, Overseer, Manual … |
| `read/decisions.md` | 60,369 | `7351c0d8d469ec69…da2c5b45` | READ | D-01 to D-51 decision log; D-48 F7 passes, D-50 agent limit 20->100, D-51 def… |
| `read/file-tree-loc.txt` | 6,096 | `f81c87cf1d5b3a9e…9837364e` | READ | File tree with sizes and line counts: 993 files, 298,852 lines |
| `read/fleet-launcher-proposal.md` | 54,648 | `aeca3eb51a6958e3…5a353cce` | READ | Fleet amendment: FR1-FR15, D-L1-D-L14, F1-F14, H8-H12 |
| `read/g5-live-capacity.md` | 3,207 | `fd8f133b2bfd3dc1…87042ef8` | READ | G5 live capacity: 6 real workers, 6/6 DONE, zero failures |
| `read/g5-summary.json` | 198 | `83611f8c3fb7104f…d13012ed` | READ | G5 summary: tasks_done=6, peak_concurrent=6, min_free_ram=5162MB |
| `read/git-log-oneline.txt` | 5,464 | `15e8a93af882bee4…b68de306` | READ | Last 100 commits; HEAD a93da888 |
| `read/m1-upstream.md` | 5,090 | `67372b4393dfb05b…f463366b` | READ | M1 measurement: usage capturable, NO rate-limit headers, no /v1 on upstream |
| `read/pilot-proposal.md` | 48,645 | `15cc0a7beeecd558…5c6bc8f1` | READ | Pilot v1: H1-H7, gates G0-G6, T1-T6, Q1-Q5, H6, C1, tiers A/B/C |
| `read/pilot-report.md` | 35,974 | `4c165aa57654c3b6…1d241f6d` | READ | Pilot's completion record; claims Tier A, not C |
| `read/policy.toml` | 4,294 | `6e2227c341dd4b80…849cad9e` | READ | Kernel policy: class K pinned, Tier A content, mode=auto (G4 crossed) |
| `read/quota-solar-mini4.md` | 1,124 | `405dfc3c848ac448…7cc82bf8` | READ | Quota ramp: solar-mini4 up to 4rps, no ceiling, latency 889-4250ms |
| `read/quota-step37.md` | 1,127 | `bfc4c84692c209e8…4f827b55` | READ | Quota ramp: step-3.7 up to 4rps, no ceiling, latency 2312-8437ms |
| `read/quotagate-config.toml` | 13,267 | `975d5dd8a40423d9…83a0ec81` | READ | QuotaGate M0-M2 config: 2 upstreams, accounts, deployments, quota rules |
| `read/quotagate-v1-1.md` | 22,288 | `e24ca17a28b31db9…f89f5063` | READ | QuotaGate v1.1 spec (M0-M5) |
| `read/quotagate-v1.md` | 36,465 | `fe0b1608286be36f…c3cd5d58` | READ | QuotaGate v1.0 spec |
| `read/s-p1-platform.md` | 5,595 | `10aedc4206bad865…e2d64009` | READ | S-P1 platform spike: native Windows decided (D-02) |
| `read/s1-live-results.json` | 8,497 | `48557fb99ac7316e…1ec209ce` | READ | S-A1 live results: 5 CLIs, headless, exit codes, session IDs |
| `read/s1-live-resume.json` | 6,335 | `0a1a1f008ffb9c09…7f8f892e` | READ | S-A1 resume results: hermes/kilo/pi resume tested, pi model-swap tested |
| `read/scale-f7.json` | 315 | `08f04717bff2fd27…37e40553` | READ | F7 results: 100/100 DONE, 105s, 100 slots, RAM 7491MB; s_w1 is {} (empty) |
| `read/t4-canary.md` | 5,908 | `66ca7eae87200549…615e7390` | READ | T4/T4b canary methodology and results |
| `read/t4-results.json` | 2,868 | `1d30b34a2358ded7…ad6505a1` | READ | T4 canary: 0/3 injections reached file (inconclusive) |
| `read/t4b-results.json` | 1,211 | `c212e5ccd0d0b13a…b7b982af` | READ | T4b: 3/3 poisoned files caught by lint + sentinel I15/I16 |
| `read/umaws.md` | 89,887 | `3cf7eacdc5f1586e…2c3a29e7` | READ | UMAWS system spec (source document) |
| `scripts/check_views.py` | 2,347 | `9d86a5bc21021cc0…02cff8b3` | RAN-NOW | I13 views check: rebuild views from log, compare to on-disk files |
| `scripts/emit_event_extracts.py` | 2,774 | `4387d2ea764b3fbd…1d724877` | RAN-NOW | Extract head/tail/lifecycle from event log |
| `scripts/event_counts.py` | 1,467 | `79f6496030f5fa8e…ebf6952c` | RAN-NOW | Count events by type, verify hash chain |
| `scripts/file_tree.py` | 1,569 | `38880c2b12dd58ec…bd637531` | RAN-NOW | Generate file tree with sizes and line counts |
| `scripts/write_report.py` | 4,009 | `6f38420b9123d02a…7ca382c1` | RAN-NOW | Report generation scripts (front matter + §1) |
| `scripts/write_report_2.py` | 14,774 | `4ea2c4949c841660…d3c56ef6` | RAN-NOW | Report generation scripts (§2-7) |
| `scripts/write_report_3.py` | 16,962 | `8e3eaf0ffefc6ac5…aa280f3a` | RAN-NOW | Report generation scripts (§8-12) |
| `scripts/write_report_4.py` | 9,591 | `156c8b26d2fdcf98…048608de` | RAN-NOW | Report generation scripts (§13-15) |

## Full SHA-256 hashes

For verification, full hashes:

- `fixtures/cline-model-gone.txt` — 17891bc7f7b5c85a451c7b9b586262b414e2ac55f4e9a6bd49e79390151f9bba
- `fixtures/cline-patterns.toml` — 2e09004359caad38ef7c6c488964c5b16632b609dcec17365e040c84d5e727e0
- `fixtures/fake-network.txt` — 58fe57dca189fc25a658adf39061b63d783762ab4a414a3188cd8c15654129eb
- `fixtures/fake-patterns.toml` — 2e72e9976eae87c85a523c27f1dda66931fb4fe5e21af0fd397d39d8c1ac7b46
- `fixtures/fake-quota.txt` — 5a23e0a941fa9284fc510b379ecad5e6c5653a751e3e9572447dc30ae661265a
- `fixtures/opencode-patterns.toml` — d8222e8aef4ac3a0369796aedb90c8175d222bbc78b2a468d60885155bcd1762
- `fixtures/opencode-quota.txt` — 6465add6d75293b484740583373625111d009ade0340542974c6841b5d8b5538
- `raw/cli-help-sweep-ran-now.txt` — 6b0859b84e62575375ce37592d72523b5f1e75d64e890554d06f80570f8faf03
- `raw/console-side-effects-ran-now.txt` — 1a07841f4a7dfaede4d82af69517f11d1ddba24573682d241e52c863e7b271e8
- `raw/console-smoke-ran-now.txt` — c683ccb889c6612e4e8af29fc8fdd2dc0d45becbaa60c9560a33e1a2631c0cba
- `raw/event-counts-ran-now.txt` — 5771d61227ad6d3fc50d1061067aa65eba3f966d7c4003d9ee670074add05d34
- `raw/event-log-head-tail-ran-now.txt` — fdc7d365b502685dbf74fb0ae71023e299fdcf63da2c5eed55e0e019ce52a3ea
- `raw/full-suite-ran-now.txt` — 9133b48ace1b787257a14cbc1efefa94ed8989fd63e09c268bda54c0f3d56ac8
- `raw/sentinel-after-console-ran-now.txt` — 2f170d737e42a16c7191c7b0b3068f5067475c9eddfb00e7818cbcdabac15f50
- `raw/tests-fleet-ran-now.txt` — 7fae819d970f374c0f016659506e4ffba1ce7f4d6a2fb33e7375b3ba394d0b88
- `raw/views-check-ran-now.txt` — 93c0293a0351e10ff6cbe041ce94a255c705891aceade383c3a195de5c7bf39e
- `read/EB-T-0003-3/Bundle.json` — 1e09d3b69a03a5fa661ecbf3ab0f556691717a8f5a548ffe13995b5767d214dc
- `read/STATE.md` — 16ccfc46b18cb76958f14cf8bac0395ad1efb6329b2f0ccdef3bae48a5e2748f
- `read/UMAWS_USER_MANUAL.md` — 48c4d95640fd1b7df6b425c860838178dcce25bd5bfa483dc730920007679234
- `read/agents.toml` — 98873b67d521f686fab4f17f9e30e049a576caea85cd709195d929983b92f7cd
- `read/amendment-gates.md` — 508d028178fb6f917d33a835d6563e56e58c2f1e5b11fcefbc91e9d3b1292625
- `read/caliber-integration.md` — 603ff0649881190fac89f9bab3150452b8294210a63319305e104361f7664033
- `read/caliber-s1-s5.md` — bfa00bb59cdb175e8f6689f12858ca7409149f7bd258c2efe313494fe88985fe
- `read/caliber-score.json` — f87f3e2b6bd89815bc79ed8a203613a67c2eb41cf5a4b3d9a89568603a56fec1
- `read/caliber-spike-results.json` — 5194e7903d8aeeee823897637cad52654d0bb8eb437d6c8f058d7e285ff1e67e
- `read/cli-matrix.md` — 53d55842a25a71751f5c3cd9b4eaf99329748d4c84af1a8578df17fff9d1dcf8
- `read/console-index.html` — 5f5001a3af369913219212a76230062ae62af4e8536c23e0beebbcadf7dc8bf2
- `read/decisions.md` — 7351c0d8d469ec69f66e44acfceadd98786357e1bcb98ceb5686884eda2c5b45
- `read/file-tree-loc.txt` — f81c87cf1d5b3a9e1a79bd681d473d5b36be03cb9ec5a01428b822959837364e
- `read/fleet-launcher-proposal.md` — aeca3eb51a6958e38df4a685d06db371e62ff6cc017aedac941299165a353cce
- `read/g5-live-capacity.md` — fd8f133b2bfd3dc10cb4e508188dc279180062dad39ffe59f2f6628f87042ef8
- `read/g5-summary.json` — 83611f8c3fb7104f9ae94342a70b94b12a265d17f5fd509e37aa8ed9d13012ed
- `read/git-log-oneline.txt` — 15e8a93af882bee4e5716dc2a75c77192180ef676b5219996868e9d1b68de306
- `read/m1-upstream.md` — 67372b4393dfb05b9430ed7d05117861524fccad59d21771f092c5d0f463366b
- `read/pilot-proposal.md` — 15cc0a7beeecd558269479669bf5dbbd5f05fef10ba981d72c370ba05c6bc8f1
- `read/pilot-report.md` — 4c165aa57654c3b63d0b93312cbe4b856093789682251282159ae3c31d241f6d
- `read/policy.toml` — 6e2227c341dd4b80bc56deeea491c56f89adab7f4cb1fd376e327e05849cad9e
- `read/quota-solar-mini4.md` — 405dfc3c848ac448f3355746257df95d869a956abe2426827fb8a95c7cc82bf8
- `read/quota-step37.md` — bfc4c84692c209e83a380a9c0567c49c7e3eb7c6d377dac3e31435d74f827b55
- `read/quotagate-config.toml` — 975d5dd8a40423d969ebdba7961de042533e518499d6d69a4e72321383a0ec81
- `read/quotagate-v1-1.md` — e24ca17a28b31db9c479198077f31d119864d0b01dfce3117bc1c7b0f89f5063
- `read/quotagate-v1.md` — fe0b1608286be36f6dd0cd99ed13a5f0e5418d39253cf9a44ae2d4ddc3cd5d58
- `read/s-p1-platform.md` — 10aedc4206bad865d0921afea9eaaafb705954b1df75c4ac4168bac0e2d64009
- `read/s1-live-results.json` — 48557fb99ac7316ead883cbc925262122d47885de46d3bc1dcb7e14c1ec209ce
- `read/s1-live-resume.json` — 0a1a1f008ffb9c09c7a340d37b1dbb89d16e50db905237d116933d047f8f892e
- `read/scale-f7.json` — 08f04717bff2fd2744bbb311e94e8a6f6bc84a19266e67b98f416a6837e40553
- `read/t4-canary.md` — 66ca7eae87200549a3df82280d9a7abc14d250527abc89e059056463615e7390
- `read/t4-results.json` — 1d30b34a2358ded73b476f01799e085de6f562f536f3702926a0da4ead6505a1
- `read/t4b-results.json` — c212e5ccd0d0b13ab980853779d9544d8315608ff11588d7720caa91b7b982af
- `read/umaws.md` — 3cf7eacdc5f1586ea428e2f8b74881d607bbbe0ab5316b0de8f4b1182c3a29e7
- `scripts/check_views.py` — 9d86a5bc21021cc0da4f17477e0cc3a2763f6af137da7ebf6a27847c02cff8b3
- `scripts/emit_event_extracts.py` — 4387d2ea764b3fbdf2be8c7cf4f6fad6038e8a593ea9494fb585242e1d724877
- `scripts/event_counts.py` — 79f6496030f5fa8e81c26147a4a3befbf074450d5d9358dbecd9ba0aebf6952c
- `scripts/file_tree.py` — 38880c2b12dd58ecdca9e66160a8645a3c924961e30f4e04acd7fce9bd637531
- `scripts/write_report.py` — 6f38420b9123d02adb9d5340859a3e375670321f763f5703923ece817ca382c1
- `scripts/write_report_2.py` — 4ea2c4949c8416601748fb0f4f7966222a10fd462414a2ef723adcb2d3c56ef6
- `scripts/write_report_3.py` — 8e3eaf0ffefc6ac5e8e195b4eea8dc21ff4290810df0ba7b5ed11c4eaa280f3a
- `scripts/write_report_4.py` — 156c8b26d2fdcf98b2d06ab7cf9a93b8c6748297bebbc5f74c9bc686048608de

## Secret scan

All files in this bundle were scanned for secrets. **No secrets found.**

Categories checked: API keys, bearer tokens, `sk-`-style strings, URLs with credentials,
`.env` contents, environment variable values referenced in config `secret_env` fields.

The `agents.toml`, `policy.toml`, and `quotagate/config.toml` files record only variable NAMES
(e.g. `secret_env = "OMNIROUTE_API_KEY"`), never values. The `m1-upstream.md` record confirms the
API key was used from the environment only and never written to the repository.

## Bundle size audit

| Metric | Value | Limit | Status |
|---|---|---|---|
| Total bundle size | 717,278 bytes | < 3,000,000 | OK |
| Largest file | 89,887 bytes | < 150,000 | OK |
| File count | 58 | — | — |
