"""Stage the reviewed Caliber output for the G1 baseline install.

CIP section 8.6 step 1 is a **human** step: read every generated file and
delete anything that tells an agent to bypass the Kernel.  This script does
the mechanical part of it and nothing else:

* it copies only the **generated project context** into a staging
  directory -- not Caliber's own hooks, settings, `.gitignore` or cache;
* it removes the spike's own ``HUMAN EDIT`` marker;
* it does **not** remove the dangerous blocks.  The Kernel's sanitiser does
  that during the install, and records what it removed.

The install then goes through the ordinary diff, lint, sanitise and merge
machinery, so the baseline is committed the same way any other change is.

Run:  py -3.12 pilot/spikes/stage_context.py <source> <staging>
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

#: The managed paths, from the policy.
MANAGED = [
    "AGENTS.md", "CLAUDE.md", "CALIBER_LEARNINGS.md",
    ".claude/rules", ".claude/skills", ".opencode/skills",
]

#: Caliber's own operational files, which are not class C.
EXCLUDE = [
    ".claude/skills/find-skills",
    ".claude/skills/save-learning",
    ".claude/skills/setup-caliber",
    ".opencode/skills/find-skills",
    ".opencode/skills/save-learning",
    ".opencode/skills/setup-caliber",
]

#: The marker the S3 spike added by hand.  It is a spike artefact, not
#: content, and it must not ship.
SPIKE_MARKER = """<!-- pilot-spike: a hand-written note -->
HUMAN EDIT
"""


def excluded(relative: str) -> bool:
    normalised = relative.replace("\\", "/")
    return any(normalised == item or normalised.startswith(item + "/")
               for item in EXCLUDE)


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    source = Path(sys.argv[1]).resolve()
    staging = Path(sys.argv[2]).resolve()
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    copied: list[str] = []
    for entry in MANAGED:
        origin = source / entry
        if origin.is_file():
            targets = [origin]
        elif origin.is_dir():
            targets = [p for p in sorted(origin.rglob("*")) if p.is_file()]
        else:
            continue
        for path in targets:
            relative = path.relative_to(source)
            rel = str(relative).replace("\\", "/")
            if excluded(rel):
                continue
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            text = path.read_text(encoding="utf-8", errors="replace")
            text = text.replace(SPIKE_MARKER, "")
            target.write_text(text, encoding="utf-8", newline="\n")
            copied.append(rel)

    print(f"staged {len(copied)} file(s) into {staging}:")
    for rel in copied:
        print(f"  {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
