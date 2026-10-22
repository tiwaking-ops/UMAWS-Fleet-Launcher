"""Land D-41 (ladder results) and update STATE.md."""

from __future__ import annotations

import re
from pathlib import Path

PILOT = Path(r"C:\temp\projects\testproject1\pilot")

DEC = PILOT / "decisions.md"
STATE = PILOT / "STATE.md"

ENTRY = """D-41 | 2026-10-23 | OpenCode (measured) | **Recovery ladder with real CLIs exercised.**  

**L4** `1`/`1` attempts → real QUOTA failure from opencode (live, free-tier), ladder chose L4 → task BLOCKED with queue item `Q-001`, no fence bump.

**L3** with `max_restarts_per_task = 0` → real QUOTA failure, ladder chose L3 → lease revoked, fence **bumped 1→2**, worktree quarantined, task returned READY. No queue item (L3 is not terminal).

**Real recovery** — opencode (QUOTA) → L1 → **kilo-real**. Work submitted, oracle passed, evidence bundle complete. **However, a defect was found**:

*L1* was chosen by the ladder (because opencode's adapter claims `can_resume = True`), but the receiving profile `kilo-real` had `argv_resume = []` — meaning `profile.supports_resume()` is `False`. The dispatcher mode became `"new"`, no handoff note was written, and the order file said `## Handoff none`. The event `AGENT_RESUMED` is misleading; no session was resumed. This needs a fix (write handoff when mode is "new", or choose L2 when resume is impossible), but that decision is deferred.

**L0** remains unexercised — no live CLI reliably produces a `NETWORK` failure. | Treating the ladder as "complete" without noting that L1's label diverges from its actual mode when the receiving profile has no `argv_resume`. Not reporting the defect means it stays latent. | The defect is documented; whether to fix it is operator-decision. |

"""


def main() -> int:
    text = DEC.read_text(encoding="utf-8")
    idx = text.index("D-41 is the operator's call.")
    txt = text[:idx] + "D-40\n\n" + ENTRY + text[idx+4:]  # skip old "D-40"
    # collapse duplicate separators
    txt = re.sub(r"\n\s*---\s*\n\s*---\s*\n\s*---", "\n\n---\n", txt)
    DEC.write_text(txt, encoding="utf-8")

    state = STATE.read_text(encoding="utf-8")
    # update the Next list and the record section
    old = "Still owed: the OpenCode handover test is still owed; G4/G5 held."
    new = ("The recovery ladder with real CLIs was exercised:\n"
           "  - **L4** with live failure (opencode QUOTA) + cooldown.\n"
           "  - **L3** with tightened threshold (`max_restarts=0`).\n"
           "  - **Real recovery**: opencode → kilo, passed.\n"
           "  - **Defect noted**: L1's `AGENT_RESUMED` event when no session\n"
           "    exists; receiving profile had `argv_resume=[]` so mode was new\n"
           "    but no handoff note was written.  Fix deferred.\n"
           "  - **L0** (NETWORK retries) unexercised; no live source.\n\n"
           "Still owed: the OpenCode handover test is still owed; G4/G5 held.")
    assert old in state, "the owed section moved"
    state = state.replace(old, new)

    STATE.write_text(state, encoding="utf-8")
    print("D-41 recorded and STATE updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())