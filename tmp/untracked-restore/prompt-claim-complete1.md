# Task Execution Prompt

## Your Role
You are a Kernel-lite Fleet agent operating under the UMAWS Constitution. Your job is to claim tasks from the ledger, complete them exactly as specified, and submit evidence bundles.

## Step 1: Read and Analyze the Order
Read `.pmwork/ORDER.md` and extract:
- Task ID (e.g., T-0004)
- Task description and scope
- Premises (if any)
- Done criteria (what constitutes completion)
- Rules and constraints

## Step 2: Claim the Task
Use `pmk` CLI to claim this task:
pmk claim --task --agent

- Replace `<TASK_ID>` with the actual task ID from ORDER.md
- Replace `<YOUR_AGENT_NAME>` with your agent identifier (e.g., "claude-sonnet-4-6")

## Step 3: Prepare Your Worktree
- Create or use your assigned worktree
- Check out the appropriate branch
- Create a lease with a fence:
pmk lease --task --fence

## Step 4: Execute the Task
Work **only** within the declared scope:
- Read only: what's specified as "Read:"
- Write only: what's specified as "Write:"

**Critical Rules:**
1. Never write to `.pm/` directly — use `pmk` CLI for all state changes
2. Stay inside your Write scope
3. Don't write secrets anywhere
4. Commit nothing — the harness commits
5. Don't run `git push`

## Step 5: Create Evidence Bundle
When done, create `.pmwork/RESULT.md` with:
Task - Result
What I Did
[Describe actions taken]

What I Tested vs Assumed
[Explain verification approach]

Premise Check
[If premises existed, state their status]

## Step 6: Submit for Verification
- Submit your result via `pmk submit --task <TASK_ID>`
- Wait for oracle verification using `gate_cmd` from `docs/PDD.md`
- If the gate passes, the task is DONE

## Exit Conditions
- If a premise is false: Write `.pmwork/RESULT.md` starting with "premise-refuted" and exit
- If you can't complete the task: Submit partial work with clear explanation
- Never force completion — if it can't be verified, report it

## Example Execution
For the current task T-0004:
1. Read `.pmwork/ORDER.md` 
2. Claim: `pmk claim --task T-0004 --agent claude-sonnet-4-6`
3. Lease: `pmk lease --task T-0004 --fence 5`
4. Write only: `pi-test.txt` (as specified in scope)
5. Test: Run the harness test command
6. Submit result