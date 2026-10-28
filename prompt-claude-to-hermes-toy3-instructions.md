You are helping prepare a project called Toy3. Read everything first, then follow the steps in order.

HARD RULES
1. Do NOT call any LLM, model or provider. Do NOT start the Console, the Dispatcher or the Overseer. Do NOT start any worker.
2. Do NOT edit anything under .pm\ (events, evidence, pins, policy). Do NOT call the Kernel API directly. Use only `pmk` commands and normal `git` commits.
3. Do NOT delete files, except worktrees you create yourself under C:\temp\old-*, which you remove with `git worktree remove`.
4. If a step fails or gives an unexpected result, write the raw output, do NOT try to fix it, and go on to the next step.
5. Do not use the words VERIFIED, DONE or "fixed". Write RAN (with the exact command and output), NOT RUN, or UNKNOWN.
6. No narrative report. Write only commands and raw output. For any output over 80 lines, show the first 40 and last 40 lines and the total line count.
7. Use the Python from C:\temp\projects\testproject1\.venv. Print `python --version` once.

PHASE 1: READ-ONLY CHECKS (record the command, exit code and output for each)
1.1 In C:\temp\projects\testproject1, run `git worktree add C:\temp\old-c132 c132d7b`, `git worktree add C:\temp\old-a93 a93da88` and `git worktree add C:\temp\old-787 787b855`. In EACH worktree: run `git status --short` (it must be empty), then `python -c "import pmk; print(pmk.__file__)"` with PYTHONPATH set to that worktree's own `src`, then `python -m pmk.cli sentinel`. Show the first finding, if any. Then remove the three worktrees.
1.2 In C:\temp\projects\toy3: run `grep -E "AGENT_STARTED|CLAIMED|FLEET_ASSIGNED|OVERSEER_WOKEN" .pm/events/*.jsonl`, list `.pm/fleet/logs` recursively if it exists, and show which profiles in agents.toml have enabled = true. Say which profile ran in the earlier 5-second dry dispatch, or write UNKNOWN.
1.3 Show Toy3's `.pm/policy.toml`. Then show `git -C C:\temp\projects\testproject1 diff -- .pm/policy.toml`.
1.4 READ the dispatcher code. Answer in 3 lines: with autonomy R2, external effects none and spend 0/0, does the code refuse to start a real CLI profile? Give file and line numbers, or write "no such check found".
1.5 With PYTHONPATH=C:\temp\system-pinned\src, run `python -c "import pmk, fleet; print(pmk.__file__, fleet.__file__)"`. Run `git -C C:\temp\system-pinned log --oneline -1` and `git -C C:\temp\projects\testproject1 show --stat a178f5d`.
1.6 Run `pip show umaws-fleet`.
1.7 Run `opencode models` and show only the lines containing "beam" or "solar" (case-insensitive). This lists names only and makes no model call.

PHASE 2: PREPARATION (edits only in Toy3, as normal git commits)
2.1 In Toy3: `git rm docs/PDD.md`, then commit "remove hand-written PDD; the Overseer writes it under T-0001". Do not touch .pm.
2.2 Replace docs/BRIEF.md with exactly the text below, then commit.
-----
Build a small Python command-line tool called csv2md.
It reads a CSV file given as an argument and prints the data as a Markdown table.
Requirements: Python 3.12, no third-party packages, pytest tests included, works on Windows.
Cover: a header row, empty cells, and a missing file giving a clear error.
Oracles must work on Windows: use `python -m pytest -q` style commands. Do NOT use `test`, `grep` or `bash` in any oracle.
Pass criteria: state DONE; PDD written by the Overseer under its task lease; at least six task cards; at least three different profiles used; every goal oracle passes; a run report exists; no human input after Run; sentinel clean before and after; no hand edits to events, evidence or pins.
-----
2.3 Do NOT change agents.toml. Instead write a file `agents.toml.proposed` in Toy3 (do not use it yet) in the same format as the existing agents.toml. It must contain: (a) an Overseer entry using the beam model, with the exact model string from step 1.7; (b) every existing worker profile with `enabled = false`. Add a comment above each profile: "untested today". Commit it.
2.4 If your answer to step 1.4 is that the policy BLOCKS real profiles, create a queue item for the policy change with `pmk queue` (run `pmk queue --help` first and show the output). Put the exact before and after text in the item. Do NOT edit policy.toml. If it does not block, write "no policy change needed".
2.5 Run `python -m pmk.cli sentinel` in Toy3 and show the output.

PHASE 3: STOP
Do not run, dispatch or claim anything. Write all the output above, in order, to `pilot/assessment/toy3-prep-output.md` in Toy3 (at most 30 KB). Then reply with at most 20 lines, in plain words for a non-technical reader:
- What the checks found (was the event log clean in any old commit? did any worker start in Toy3?).
- What is now ready.
- What the operator must still decide: which worker profiles to enable, whether to approve the policy diff (give the queue item id), and the exact phrase "GO TOY3" to start the real run.
Then wait.