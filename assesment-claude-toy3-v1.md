## Assessment of Toy3 v1.2

**This pass adds almost nothing new, and its main conclusion on the event log is probably wrong.** Toy3 is in the same place as before: a clean, empty project that has never run.

### The I1 conclusion misreads Hermes's own results

- Hermes says the log is broken at seq 261 in `c132d7b`, `bc084cf`, `ce9c4aa` and `4cdf35a`, and concludes no clean version exists.
- The break in those commits comes *later* than seq 84, because verification stops at the first error. So seq 84 passes in those commits and fails only in `787b855`. That supports the hand-edit theory, not "pre-existing since early in the project's history".
- Seq 261 can't be a real gap in those trees, since the largest event count in any commit is 260. The likely cause is leftover untracked event files (newer days, plus the one each sentinel run creates), which `git checkout` leaves behind. This is the `Remove-Item .pm\events\*` step my command had and Hermes dropped. A `git worktree add` gives a tree with no leftovers.
- So the claim that the 584-event clean chain was "incorrect" is unproven. That evidence came from the agent's own earlier raw output.
- **Likely path:** restoring the 2026-10-23 events from `c132d7b` would fix the seq-84 break, and the 261 issue is a separate question.

### Other points

1. **The report contains unedited working notes.** Section 2.8 ends with "wait, no. Let me check… Actually… Let me verify." It never resolves which commit the recovered files are in.
2. **Recovered files may have been committed to the system repo.** That would put scratch files, including a 54 KB ChatGPT proposal, into the source you just "pinned", changing what `a178f5d` contains. Check that commit's file list.
3. **"Sentinel clean on the pinned source" can't be true as written.** The pinned checkout is `testproject1` itself, which holds the broken log. Presumably Toy3's sentinel was run using the pinned code. The raw JSON is identical to v1.1 with no timestamp, so it may not have been re-run.
4. **The pin is unproven.** Nothing shows that `pmk` and `fleet` actually import from the pinned path, given the earlier editable install.
5. **`PDD_COMMITTED` is a Kernel defect.** `project init` logs the event before any PDD exists, with no hash of the file. A hand-written PDD is therefore undetectable. The event should carry the file's SHA-256 at commit time. It goes on the defect list.
6. **The decisions are all marked VERIFIED again.** The report's own §2.8 shows D-15 isn't.
7. **Pass criteria remain unachievable.** With no profiles and no `agents.toml`, "at least 3 profiles" can't be met, and Toy3 can't dispatch anything.

### Checks to run (PowerShell)

```powershell
git -C C:\temp\projects\testproject1 worktree add C:\temp\old-c132 c132d7b
cd C:\temp\old-c132
git status --short
$env:PYTHONPATH="src"; python -m pmk.cli sentinel

git -C C:\temp\projects\testproject1 show --stat a178f5d
$env:PYTHONPATH="C:\temp\system-pinned\src"
python -c "import pmk, fleet; print(pmk.__file__, fleet.__file__)"
```

- The first block shows whether `c132d7b` verifies from a clean tree.
- The second shows which files `a178f5d` contains and where the code actually imports from.

### Where this is heading

This loop has become Hermes working through my checklist item by item, with each new report adding narrative instead of evidence. I'd change the format: raw command output only, no recap. The real blocker is no longer the repo state; it is a first genuine run. For that I need four decisions from you:
1. Which free models respond today, and which should be the Overseer's?
2. Should the Overseer write the PDD (the real H12 test), or should the hand-written one stay?
3. Does the R2/none policy block real dispatch? Hermes can read the code for this; my earlier claim that `spend` doesn't govern direct CLIs is unverified.
4. Which brief: the CSV-to-Markdown toy, or something real?

Tell me those and I'll write the prompt for the first run, with the pre-checks above folded in.