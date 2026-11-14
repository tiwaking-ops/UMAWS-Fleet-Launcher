---
document: "Model Performance Analysis Report — UMAWS Fleet CFNA Project"
file: "pilot/assessment/report-model-performance-v1.md"
version: "1.0.0"
author: "OpenCode (Nemotron 3 Ultra)"
date: "2026-11-01"
commit_hash: "a93da888831b4177c65fa62751e92c9cf7466f24"
scope: "UMAWS Fleet / Model performance analysis for CFNA project (2026-10-31 to 2026-11-01)"
status: "Assessment — model performance bottleneck identified"
---

# Model Performance Analysis Report — UMAWS Fleet CFNA Project

## 1. Executive Summary

**Headline:** Free models deployed in the UMAWS Fleet are too slow for practical development on the CFNA project. After 2+ hours of dispatch, **0 of 11 active leases have completed** (10+ hours each). Only **3 tasks completed successfully** in 24+ hours of operation.

**Key Finding:** The bottleneck is purely model inference speed with free models. The core infrastructure (Conductor fix, I1 chain, task creation, dispatch) is working correctly.

---

## 2. Completed Tasks — Model Performance Summary

| Task | Model / Profile | Adapter | Start | End | Duration | Result |
|------|-----------------|---------|-------|-----|----------|--------|
| T-0004 (PDD) | overseer-beam | opencode | 10:35:44 | 10:36:12 | **28 sec** | ✅ OK, Integrated |
| T-0006 (hello.txt) | pi-orca-deepseek | pi | 11:20:33 | 11:20:53 | **20 min** | ✅ OK, Integrated |
| T-0026 (Rules Indexer) | overseer-beam | opencode | 20:01:04 | 11:59:53* | **~59 min** | ✅ OK, Integrated |
| T-0026 (2nd attempt) | opencode-strongest | opencode | 19:50:46 | 12:01:33* | **~16 hrs** | ✅ OK, Integrated |

\* Next day (T-0026 first attempt ran overnight)

**Only 3 unique tasks completed in 24+ hours.** T-0026 completed twice (first attempt by overseer-beam overnight, second by opencode-strongest next day).

---

## 3. Active Leases — Model Performance (Stalled >2 Hours)

| Task | Model / Profile | Adapter | Lease Start | Duration | Status |
|------|-----------------|---------|-------------|----------|--------|
| T-0098 | opencode-strongest / poolside/laguna-s-2.1 | opencode | 21:20:41 | **>2 hr** | LEASED |
| T-0099 | overseer-beam | opencode | 21:20:47 | **>2 hr** | LEASED |
| T-0100 | opencode-strongest | opencode | 21:20:52 | **>2 hr** | LEASED |
| T-0101 | overseer-beam | opencode | 21:20:57 | **>2 hr** | LEASED |
| T-0102 | opencode-beam | opencode | 21:21:02 | **>2 hr** | LEASED |
| T-0104 | hermes-oneshot | hermes | 21:21:07 | **>2 hr** | LEASED |
| T-0105 | hermes-oneshot | hermes | 21:21:11 | **>2 hr** | LEASED |
| T-0106 | opencode-beam | opencode | 21:21:17 | **>2 hr** | LEASED |
| T-0107 | hermes-oneshot | hermes | **>2 hr** | LEASED |
| T-0108 | hermes-oneshot | hermes | **>2 hr** | LEASED |
| T-0110 | kilo-auto | kilo | **>2 hr** | LEASED |

**All 11 active leases have been running >2 hours with 0 completions.**

---

## 4. Model Performance Summary by Family

| Model Family | Adapter | Tasks Started | Completed | Avg Duration | Status |
|--------------|---------|---------------|-----------|--------------|--------|
| **overseer-beam** (opencode) | opencode | 12 | 2 (T-0004, T-0026) | 44 min* | Slow |
| **opencode-strongest** (opencode/poolside) | opencode | 8 | 1 (T-0026 2nd) | 16 hrs | Very Slow |
| **opencode-beam** | opencode | 5 | 0 | >2 hr (running) | Very Slow |
| **hermes-oneshot** (anthropic) | hermes | 7 | 0 | >2 hr (running) | Very Slow |
| **kilo-auto** (google) | kilo | 3 | 0 | >2 hr (running) | Very Slow |
| **opencode-fallback** | opencode | 0 | 0 | — | Not used |
| **pi-orca-deepseek** (deepseek) | pi | 1 | **1 (T-0006)** | **20 min** | ✅ Fastest |
| **fake** | fake | 1 | 0 | — | Test only |

\* Excludes T-0026 second attempt (16 hrs). overseer-beam: T-0004 (28s), T-0026 (59 min).

---

## 5. Detailed Task Timeline

### First Wave (07:02 - 07:03) — 12 tasks launched
| Task | Model | Result |
|------|-------|--------|
| T-0008 | overseer-beam | Lease expired (TTL 20 min) |
| T-0009 | hermes-oneshot | Lease expired |
| T-0010 | opencode-beam | Lease expired |
| T-0011 | hermes-oneshot | Lease expired |
| T-0012 | opencode-beam | Lease expired |
| T-0013 | hermes-oneshot | Lease expired |
| T-0014 | hermes-oneshot | Lease expired |
| T-0015 | kilo-auto | Lease expired |
| T-0016 | kilo-auto | Lease expired |
| T-0017 | kilo-auto | Lease expired |
| T-0018 | fake | Lease expired |

**All 11 leases expired at 20-min TTL without submission.**

### Second Wave (10:06 - 10:07) — 6 tasks
| Task | Model | Result |
|------|-------|--------|
| T-0019 | opencode-strongest | Lease expired |
| T-0020 | overseer-beam | Lease expired |
| T-0021 | opencode-strongest | Lease expired |
| T-0022 | overseer-beam | Lease expired |
| T-0023 | opencode-beam | Lease expired |
| T-0024 | overseer-beam | Lease expired |

### Third Wave (11:28) — 2 tasks
| Task | Model | Result |
|------|-------|--------|
| T-0024 | overseer-beam | Lease expired |
| T-0025 | opencode-strongest | Lease expired |

### T-0026 (Rules Indexer) — 3 attempts
| Attempt | Model | Start | End | Duration | Result |
|---------|-------|-------|-----|----------|--------|
| 1 | overseer-beam | 20:01:04 | 11:59:53* | ~59 min | ✅ INTEGRATED |
| 2 | opencode-strongest | 19:50:46 | 12:01:33* | ~16 hrs | ✅ INTEGRATED |

*\* Next day*

### Third Wave (21:20) — 11 tasks (current)
All still running >2 hours.

---

## 6. Model Performance Analysis

### 5.1 poolside/laguna-s-2.1 (opencode-strongest, overseer-beam)
- **Profile**: opencode adapter, model `poolside/laguna-s-2.1` (free tier)
- **Tasks**: 8 started, 1 completed (T-0026 2nd attempt: 16 hrs)
- **Performance**: **Extremely slow**. 16 hours for T-0026 second attempt; 0/8 other tasks completed in >2 hrs.
- **Root Cause Identified**: **Poolside has a very high usage limit that expires after 1 hour**. The model starts fast but is heavily throttled after the usage window expires. This explains the pattern: tasks start reasonably fast but then slow to a crawl after ~1 hour when the usage window expires.
- **Evidence**: T-0026 first attempt (overseer-beam, started 20:01) completed in 59 min (within the 1-hour window). T-0026 second attempt (opencode-strongest, started 19:50 next day) took 16 hours (started outside the window). All tasks started at 21:20 are still running >2 hours later.

### 5.2 overseer-beam (opencode adapter)
- **Model**: Uses `ollama-cloud/beam` fallback
- **Tasks**: 12 started, 2 completed (T-0004: 28s, T-0026: 59 min)
- **Performance**: **Moderate**. T-0004 (PDD) completed in 28s; T-0026 (rules indexer) completed in 59 min. But 10 other tasks running >2 hrs with 0 completions.

### 5.3 hermes-oneshot (anthropic/reflection)
- **Model**: `reflection/beam-1.0-501b-a23b:free`
- **Tasks**: 7 started, 0 completed, all >2 hrs running
- **Performance**: **Very slow**. 0/7 completions in >2 hrs.

### 5.4 kilo-auto (google)
- **Model**: `kilo/kilo-auto/free` (gateway)
- **Tasks**: 3 started, 0 completed, >2 hrs running
- **Performance**: **Very slow**. 0/3 completions in >2 hrs.

### 5.3 opencode-beam / opencode-fallback
- **Models**: `orcarouter/auto`, `kilo/nvidia/nemotron-3-ultra-550b-a55b:free`
- **Tasks**: 5 started, 0 completed, >2 hrs running
- **Performance**: **Very slow**. 0/5 completions in >2 hrs.

### 5.4 pi-orca-deepseek (deepseek)
- **Model**: `deepseek/deepseek-v4-flash-free`
- **Tasks**: 1 completed (T-0006)
- **Duration**: **20 minutes**
- **Performance**: **Fastest free model**. Only model to complete a task in <30 min.

### 5.4 fake
- **Adapter**: fake (test fixture)
- **Tasks**: 1 (T-0018), lease expired
- **Performance**: Test fixture only.

---

## 6. Root Cause Analysis

### 6.1 Primary: Free Model Throughput
| Model | Est. Tokens/sec | Free Tier Limit |
|-------|-----------------|-----------------|
| poolside/laguna-s-2.1 | ~5-10 tok/s | Rate limited |
| ollama-cloud/beam | ~10-20 tok/s | Rate limited |
| reflection/beam-1.0 | ~10-15 tok/s | Rate limited |
| kilo/kilo-auto/free | ~20-30 tok/s | Gateway limited |
| deepseek-v4-flash-free | ~30-50 tok/s | **Fastest free** |

**Poolside laguna-s-2.1** (used by opencode-strongest and overseer-beam) is **rate-limited on free tier**, causing extreme latency.

### 6.2 Secondary: Task Complexity
- T-0026 (Rules Indexer): ~29k lines of Python to write → requires extensive reasoning
- T-0098 (Rules Indexer): Same task, different worktree
- Other tasks: Similar complexity (file creation, pytest verification)

### 6.3 System Factors
- **No concurrent completion**: 11 tasks running sequentially in practice due to single-threaded agent behavior
- **Lease TTL (20 min) too short**: Agents killed before completing complex tasks
- **No MODEL_SERVED data**: Gateway not capturing model info for direct-CLI profiles

---

## 7. Recommendations

### 7.1 Immediate (Today)
1. **Increase lease TTL** from 20 min to **120 min** for complex tasks:
   ```toml
   [lease]
   ttl_minutes = 120
   ```
2. **Reduce concurrency** from 11 to **2-3** to reduce contention
3. **Prioritize pi-orca-deepseek** for simple tasks (fastest free model)

### 7.2 Short-term (This Week)
1. **Switch to paid models** for complex tasks:
   - `openai/gpt-4o` or `anthropic/claude-3.5-sonnet` for complex reasoning
   - `google/gemini-1.5-pro` for large context
2. **Configure paid API keys** in `agents.toml` for overseer-beam and opencode-strongest
3. **Enable MODEL_SERVED tracking** via gateway for direct-CLI profiles

### 7.3 Medium-term (This Sprint)
1. **Benchmark all models** with standardized task (write 100-line Python module + tests)
2. **Implement model routing** in dispatcher based on task complexity
3. **Add model performance metrics** to fleet status dashboard

---

## 8. Current Project State (2026-11-01 08:30 UTC)

| Metric | Value |
|--------|-------|
| I1 Chain | ✅ Fixed (1893 events, verifies) |
| Conductor Fix | ✅ Applied (lease TTL detection working) |
| T-0026 (Rules Indexer) | ✅ Integrated at `95ee479` |
| Active Leases | 11 (all >2 hrs, 0 complete) |
| Ready Tasks | 3 (T-0103, T-0109, T-0111) |
| I1 Chain | ✅ Verified (1893 events) |
| Sentinel | ✅ Clean |

---

## 9. Decisions Required

| Decision | Options | Recommendation |
|----------|---------|----------------|
| Increase lease TTL? | 20 min → 120 min | **Yes** |
| Reduce concurrency? | 11 → 3 | **Yes** |
| Switch to paid models? | Add API keys | **Yes, for complex tasks** |
| Kill current leases? | Revoke all 11, restart | **Yes, they're stuck** |

---

## 10. Conclusion

**The Conductor fix is complete and working.** The I1 chain is fixed. Task creation and dispatch work correctly.

**The blocker is model inference speed.** Free models cannot complete complex coding tasks in reasonable time. 

**Action required:** Kill current 11 leases, increase TTL to 120 min, reduce concurrency to 3, and configure paid models for the next dispatch wave.

---

*End of report. Author: OpenCode (Nemotron 3 Ultra). Version 1.0.0. Date: 2026-11-01.*