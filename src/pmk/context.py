"""Context files: the lint, the drift check, and the sync task.

This is CIP Part B sections 14.4 to 14.7, reduced to what does not depend
on a specific generator (decision D-13).  The generator — Caliber — is a
*tool*; the safety machinery is the Kernel's, and it is the same whichever
generator is used.

Three file classes (CIP Part B section 14.3):

``K. Kernel-pinned``
    ``.pm/constitution.md``, ``.pm/policy.toml``, Kernel code, gate and
    sandbox definitions.  Hash-pinned, two-key.
``C. Generated context``
    ``AGENTS.md``, ``CLAUDE.md``, ``CALIBER_LEARNINGS.md`` and the
    generated skill and rule files.  Auto-synced, hash *recorded* per sync
    (I16), linted (I15), reversible.
``H. Authored guidance``
    ``docs/``, ``.pm/memory/``, decision files.  Normal artifact rules; the
    generator does not manage these.

**The safety floor does not depend on class C.**  The Harness injects the
constitution stub into every briefing and records its hash and the hash of
the class C files in force in the evidence bundle (I17).  If a generator
produced a bad ``AGENTS.md``, the invariants still reach every worker.

The lint (I15) rejects a sync when a class C file:

* instructs agents to write under ``.pm/``, edit the ledger, create or
  edit claim, lease or heartbeat files, or bypass the Kernel or harness;
* instructs agents to skip, weaken or ignore verification, gates, review or
  the constitution;
* uses authority language that overrides the briefing ("this file
  overrides…", "ignore previous instructions");
* contains credential-shaped strings;
* adds URLs on domains outside an allowlist — these route to blind V2
  review rather than rejection;
* exceeds the token budget, which also bounds context cost.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

#: The severity that stops a sync.
REJECT = "reject"
#: The severity that routes a sync to blind V2 review instead.
REVIEW = "review"

#: Domains whose URLs are allowed in a class C file without review.
DEFAULT_ALLOWED_DOMAINS = (
    "github.com", "docs.github.com", "raw.githubusercontent.com",
    "pypi.org", "files.pythonhosted.org", "python.org", "docs.python.org",
    "localhost", "127.0.0.1",
)

# ---------------------------------------------------------------------------
# Rule 1: instructions that bypass the Kernel
# ---------------------------------------------------------------------------

_BYPASS_PATTERNS = (
    (r"(?:write|edit|modify|update|create|change|touch)\s+[^\n]{0,40}?\.pm/",
     "instructs an agent to write under .pm/"),
    (r"(?:edit|modify|update|change)\s+[^\n]{0,30}?\bledger\b",
     "instructs an agent to edit the ledger"),
    (r"(?:create|edit|modify|write)\s+[^\n]{0,30}?"
     r"(?:claim|lease|heartbeat)\s+files?",
     "instructs an agent to create or edit claim, lease or heartbeat files"),
    (r"\bbypass(?:ing)?\s+the\s+(?:kernel|pmk|harness)\b",
     "instructs an agent to bypass the Kernel"),
    (r"\bwithout\s+using\s+`?pmk`?\b",
     "instructs an agent to work without pmk"),
    (r"\bdo\s+not\s+use\s+`?pmk`?\b",
     "instructs an agent not to use pmk"),
    (r"\bedit\s+[^\n]{0,30}?\.pm/(?:events|tasks|views)/",
     "instructs an agent to edit the Kernel's own state files"),
    # -- found in real Caliber output (spike S2, 2026-10-22) -------------
    (r"git\s+add\s+[^\n]{0,200}?"
     r"(?:AGENTS\.md|CLAUDE\.md|CALIBER_LEARNINGS\.md|\.claude/|\.opencode/|"
     r"\.cursor/|\.agents/)",
     "instructs an agent to stage the managed context files, which the "
     "Kernel's scope check governs"),
    (r"(?:run|execute|invoke)\b[^\n]{0,60}?\bcaliber\s+"
     r"(?:refresh|init|regen|regenerate|sync)\b",
     "instructs an agent to run the context generator, which is a Kernel "
     "task and would make an unaccounted model call"),
    (r"\bMUST\b[^\n]{0,60}?\bcaliber\b",
     "instructs an agent that it must run the context generator"),
)

# ---------------------------------------------------------------------------
# Rule 2: instructions that weaken verification
# ---------------------------------------------------------------------------

_WEAKEN_PATTERNS = (
    (r"\bskip(?:ping)?\s+(?:the\s+)?(?:verification|verify|tests?|gates?|review)\b",
     "instructs an agent to skip verification"),
    (r"\b(?:without|no)\s+(?:running\s+)?(?:the\s+)?(?:verification|tests?|gates?)\b",
     "instructs an agent not to run verification"),
    (r"\bignore\s+the\s+constitution\b",
     "instructs an agent to ignore the constitution"),
    (r"\bweaken\s+(?:the\s+)?(?:verification|gates?|review)\b",
     "instructs an agent to weaken verification"),
    (r"\b(?:do\s+not|don't|never)\s+(?:need\s+to\s+)?"
     r"(?:run|run the|execute)\s+(?:the\s+)?(?:tests?|gates?|verification)\b",
     "instructs an agent not to run the tests or gates"),
    (r"\bmark\s+(?:the\s+)?task\s+as\s+done\s+without\b",
     "instructs an agent to mark a task done without evidence"),
)

# ---------------------------------------------------------------------------
# Rule 3: authority language that overrides the briefing
# ---------------------------------------------------------------------------

_OVERRIDE_PATTERNS = (
    (r"\bthis\s+file\s+overrides?\b",
     "claims to override the briefing"),
    (r"\bignore\s+(?:all\s+)?previous\s+instructions\b",
     "ignores previous instructions"),
    (r"\bdisregard\s+(?:all\s+)?(?:previous|prior|earlier)\b",
     "disregards previous instructions"),
    (r"\btakes?\s+precedence\s+over\s+the\s+(?:briefing|constitution)\b",
     "claims precedence over the briefing"),
    (r"\bsupercedes?\s+the\s+(?:briefing|constitution)\b",
     "claims to supersede the constitution"),
    (r"\byour\s+instructions?\s+are\s+(?:now\s+)?(?:the\s+)?"
     r"(?:highest|final)\s+priority\b",
     "claims the highest priority"),
    (r"\byou\s+are\s+no\s+longer\s+bound\s+by\b",
     "claims to be unbound by the constitution"),
    # -- found in real Caliber output (spike S2, 2026-10-22) -------------
    (r"\btreat\s+(?:them|these|it|this)\s+as\s+[^\n]{0,40}?\brules?\b",
     "tells the agent to treat generated content as project rules, which "
     "overrides the briefing"),
    (r"\btreat\s+(?:them|these|it|this)\s+as\s+"
     r"(?:authoritative|binding|mandatory|ground\s+truth)\b",
     "tells the agent to treat generated content as authoritative"),
)

# ---------------------------------------------------------------------------
# Rule 4: credential-shaped strings
# ---------------------------------------------------------------------------

_SECRET_PATTERNS = (
    (r"\bsk-[A-Za-z0-9_-]{16,}\b", "an OpenAI-style secret key"),
    (r"\bsk-ant-[A-Za-z0-9_-]{16,}\b", "an Anthropic-style secret key"),
    (r"\bAKIA[0-9A-Z]{16}\b", "an AWS access key id"),
    (r"\bgh[pousr]_[A-Za-z0-9]{30,}\b", "a GitHub token"),
    (r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b", "a Slack token"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "a private key"),
    (r"(?i)\b(?:api[_-]?key|secret|password|passwd|token)\s*[:=]\s*"
     r"[\"'][^\"'\s]{12,}[\"']",
     "a credential-shaped assignment"),
)

# ---------------------------------------------------------------------------
# Rule 5: URLs outside the allowlist
# ---------------------------------------------------------------------------

_URL_RE = re.compile(r"https?://([A-Za-z0-9._-]+)(?::\d+)?(?:/[^\s)\"'`]*)?")
_IMAGES_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


#: A negation cue.  The lint must not fire on "do not edit `.pm/`" or on
#: "never skip verification" — those are the *correct* instructions, and a
#: lint that blocks every legitimate file is worse than no lint at all.
_NEGATION = re.compile(
    r"(?:\bdo\s+not\b|\bdo\s+n't\b|\bdon'?t\b|\bnever\b|\bnot\b|\bno\b|"
    r"\bavoid(?:s|ed|ing)?\b|\bwithout\b|\bmust\s+not\b|\bshould\s+not\b|"
    r"\bshall\s+not\b|\bcannot\b|\bcan'?t\b|\brefus(?:e|es|ing)\b|"
    r"\bforbidden\b|\bprohibited\b|\binstead\s+of\b|\brather\s+than\b)",
    re.IGNORECASE)

#: How far back to look for a negation.  The window is the current
#: sentence, not a fixed number of characters: a negation in the previous
#: paragraph must not silence the current one.
_NEGATION_WINDOW = 60


def _is_negated(text: str, start: int) -> bool:
    """Is the match at *start* inside a negated instruction?

    ``do not edit .pm/`` and ``Never skip verification`` are the correct
    instructions, and the pilot's own generated files contain them.  A
    negation-aware lint is the difference between a control and an
    obstruction.

    The window is the current **sentence** — the text since the last
    paragraph break or sentence end.  Otherwise a negation in the
    previous paragraph would silence an instruction in this one.
    """
    window = text[max(0, start - _NEGATION_WINDOW):start]
    # Cut the window back to the last sentence or paragraph boundary.
    for boundary in ("\n\n", ". ", ":\n", "!\n", "?\n"):
        index = window.rfind(boundary)
        if index != -1:
            window = window[index + len(boundary):]
            break
    return bool(_NEGATION.search(window))


@dataclass
class LintFinding:
    """One lint finding."""

    rule: str
    detail: str
    severity: str = REJECT
    file: str = ""
    line: int = 0
    evidence: str = ""

    def to_dict(self) -> dict:
        return {"rule": self.rule, "detail": self.detail,
                "severity": self.severity, "file": self.file,
                "line": self.line, "evidence": self.evidence[:120]}


def _scan(text: str, patterns: Sequence[tuple[str, str]], rule: str,
          file: str) -> list[LintFinding]:
    findings: list[LintFinding] = []
    for pattern, detail in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if _is_negated(text, match.start()):
                # "do not edit .pm/" is the instruction we want.
                continue
            line = text.count("\n", 0, match.start()) + 1
            findings.append(LintFinding(rule=rule, detail=detail,
                                        severity=REJECT, file=file, line=line,
                                        evidence=match.group(0)))
    return findings


def estimate_tokens(text: str) -> int:
    """A crude token estimate: characters divided by four.

    The same crude estimate the gateway uses (QuotaGate v1.1 section 3).
    It is an estimate, and it is used as a *budget*, not as a measurement.
    """
    return len(text) // 4


def lint_text(text: str, *, file: str = "",
              allowed_domains: Iterable[str] = DEFAULT_ALLOWED_DOMAINS,
              max_tokens: int = 3000) -> list[LintFinding]:
    """Lint one class C file's text (I15)."""
    findings: list[LintFinding] = []

    findings += _scan(text, _BYPASS_PATTERNS, "bypass_kernel", file)
    findings += _scan(text, _WEAKEN_PATTERNS, "weaken_verification", file)
    findings += _scan(text, _OVERRIDE_PATTERNS, "authority_override", file)
    findings += _scan(text, _SECRET_PATTERNS, "credential_shaped", file)

    # -- URLs outside the allowlist: review, not reject -----------------
    allow = {d.lower() for d in allowed_domains}
    for match in _URL_RE.finditer(text):
        domain = match.group(1).lower()
        if domain in allow:
            continue
        # A bare domain is not a domain: "https://x" with no host is rare.
        findings.append(LintFinding(
            rule="url_not_allowlisted", severity=REVIEW, file=file,
            line=text.count("\n", 0, match.start()) + 1,
            detail=f"a URL on the domain {domain!r}, which is not allowlisted",
            evidence=match.group(0)))

    # -- the token budget -----------------------------------------------
    tokens = estimate_tokens(text)
    if max_tokens and tokens > max_tokens:
        findings.append(LintFinding(
            rule="token_budget", severity=REJECT, file=file, line=0,
            detail=(f"the file is about {tokens} tokens, over the "
                    f"{max_tokens} budget"),
            evidence=""))

    return findings


def expand_managed_paths(root: str | Path, managed_paths: Iterable[str],
                        exclude: Iterable[str] = ()) -> list[str]:
    """The concrete files the managed paths cover, minus the exclusions.

    A managed path may name a file or a directory.  A directory is expanded
    into the files under it, so that a new generated skill is covered
    without having to name it.

    *exclude* exists because the generator ships **its own** operational
    files alongside the generated ones.  Caliber's `setup-caliber`,
    `find-skills` and `save-learning` skills teach an agent to run Caliber,
    so they are the generator's machinery rather than generated project
    context, and they are not class C.  Left in, they would also make the
    lint reject every sync.
    """
    base = Path(root)
    excluded = {str(e).replace("\\", "/").strip("/") for e in exclude}
    out: list[str] = []

    def is_excluded(relative: str) -> bool:
        normalised = relative.replace("\\", "/")
        for item in excluded:
            if normalised == item or normalised.startswith(item + "/"):
                return True
        return False

    for entry in managed_paths:
        path = base / entry
        if path.is_file():
            if not is_excluded(entry):
                out.append(entry)
            continue
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if not child.is_file():
                    continue
                relative = str(child.relative_to(base)).replace("\\", "/")
                if is_excluded(relative):
                    continue
                out.append(relative)
    return out


def lint_files(root: str | Path, managed_paths: Iterable[str], *,
               allowed_domains: Iterable[str] = DEFAULT_ALLOWED_DOMAINS,
               max_tokens: int = 3000,
               exclude: Iterable[str] = ()) -> dict:
    """Lint every managed file under *root*."""
    base = Path(root)
    findings: list[LintFinding] = []
    checked: list[str] = []
    for relative in expand_managed_paths(base, managed_paths, exclude):
        path = base / relative
        checked.append(relative)
        findings += lint_text(path.read_text(encoding="utf-8",
                                             errors="replace"),
                              file=relative,
                              allowed_domains=allowed_domains,
                              max_tokens=max_tokens)
    return {
        "ok": not any(f.severity == REJECT for f in findings),
        "needs_review": any(f.severity == REVIEW for f in findings),
        "findings": [f.to_dict() for f in findings],
        "checked": checked,
    }


# ---------------------------------------------------------------------------
# Hashes and drift (I16)
# ---------------------------------------------------------------------------

def normalise_newlines(data: bytes) -> bytes:
    """Line endings to LF, so a hash does not depend on the checkout.

    Git's ``core.autocrlf`` is ``true`` by default on Windows, so a file
    written with LF in a worktree is checked out with CRLF.  Hashing the
    raw bytes would make every sync raise a false drift finding the moment
    it merged, because the recorded hash and the file on disk would differ
    in their line endings and nothing else.

    Hashing the normalised content makes the hash a property of the
    *content*, which is what a drift check is about.
    """
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def hash_context_files(root: str | Path, managed_paths: Iterable[str],
                       exclude: Iterable[str] = ()) -> dict[str, str]:
    """The SHA-256 of each managed file, for the drift check.

    The hash is of the **normalised** content, so it does not depend on
    the platform's line-ending convention.  See :func:`normalise_newlines`.
    """
    base = Path(root)
    out: dict[str, str] = {}
    for relative in expand_managed_paths(base, managed_paths, exclude):
        path = base / relative
        if path.is_file():
            out[relative] = hashlib.sha256(
                normalise_newlines(path.read_bytes())).hexdigest()
    return out


def drift_check(root: str | Path, managed_paths: Iterable[str],
                recorded: dict[str, str],
                exclude: Iterable[str] = ()) -> dict:
    """Compare the managed files with their recorded hashes (I16).

    A mismatch is an out-of-band edit: somebody changed a class C file
    without going through a sync.  The sentinel reports it; the Kernel can
    auto-revert to the last clean state.
    """
    current = hash_context_files(root, managed_paths, exclude)
    changed = []
    removed = []
    for path, digest in (recorded or {}).items():
        now = current.get(path)
        if now is None:
            removed.append(path)
        elif now != digest:
            changed.append({"file": path, "recorded": digest, "current": now})
    added = sorted(set(current) - set(recorded or {}))
    return {
        "ok": not changed and not removed,
        "changed": changed,
        "removed": removed,
        "added": added,
        "current": current,
    }


# ---------------------------------------------------------------------------
# The sync task (CIP Part B section 14.5)
# ---------------------------------------------------------------------------

@dataclass
class SyncResult:
    """The outcome of one context sync."""

    ok: bool = False
    noop: bool = False
    needs_review: bool = False
    rejected: bool = False
    reason: str = ""
    before_hash: dict = field(default_factory=dict)
    after_hash: dict = field(default_factory=dict)
    score: int | None = None
    previous_score: int | None = None
    lint: dict = field(default_factory=dict)
    generator_version: str = ""
    provider: str = ""
    diff_lines: int = 0
    #: The generator-managed blocks the sanitiser removed, with their full
    #: text, so that nothing is deleted silently (constitution point 8).
    removed_blocks: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok, "noop": self.noop,
            "needs_review": self.needs_review, "rejected": self.rejected,
            "reason": self.reason,
            "before_hash": self.before_hash, "after_hash": self.after_hash,
            "score": self.score, "previous_score": self.previous_score,
            "lint": self.lint, "generator_version": self.generator_version,
            "provider": self.provider, "diff_lines": self.diff_lines,
            "removed_blocks": self.removed_blocks,
        }


def run_lint_and_score(root: str | Path, managed_paths: Sequence[str], *,
                       policy: dict, score_command: Sequence[str] | None = None,
                       cwd: str | Path | None = None) -> tuple[dict, int | None]:
    """Lint the managed files and (optionally) run the score command.

    The score command is the generator's own read-only audit, e.g.
    ``caliber score --json``.  It is optional so that the Kernel's lint
    works with any generator, or with none.
    """
    context_policy = policy.get("context_sync", {}) or {}
    lint = lint_files(
        root, managed_paths,
        allowed_domains=context_policy.get("url_allowlist",
                                           DEFAULT_ALLOWED_DOMAINS),
        max_tokens=int(context_policy.get("max_agents_md_tokens", 3000)))

    score: int | None = None
    if score_command:
        import subprocess
        try:
            proc = subprocess.run(list(score_command), cwd=str(cwd or root),
                                  capture_output=True, timeout=300, text=True,
                                  encoding="utf-8", errors="replace")
            payload = json.loads(proc.stdout or "{}")
            score = payload.get("score")
        except (OSError, ValueError, subprocess.SubprocessError):
            score = None
    return lint, score


# ---------------------------------------------------------------------------
# Snapshots, for a one-command revert
# ---------------------------------------------------------------------------

#: A generator-managed block, e.g. ``<!-- caliber:managed:pre-commit -->``.
MANAGED_BLOCK = re.compile(
    r"<!--\s*([\w:.-]*managed:[\w-]+)\s*-->(.*?)<!--\s*/\s*\1\s*-->",
    re.DOTALL)


def sanitize_context_text(text: str, *,
                          allowed_domains: Iterable[str] = DEFAULT_ALLOWED_DOMAINS,
                          max_tokens: int = 3000) -> tuple[str, list[dict]]:
    """Remove the generator-managed blocks that the lint rejects.

    CIP section 8.6 step 1 asks a human to "read every generated file, and
    delete anything that tells an agent to write under `.pm/`, edit the
    ledger, claim files by hand, or bypass the Kernel or harness".  This
    does that part mechanically, and it does it **honestly**: every removed
    block is returned so the caller can record its full text in the event
    log.  Nothing is deleted silently (constitution point 8).

    A block that the lint does not object to is left exactly as it is.
    """
    removed: list[dict] = []

    def replace(match: re.Match) -> str:
        name = match.group(1)
        body = match.group(2)
        findings = lint_text(body, file=f"<{name}>",
                             allowed_domains=allowed_domains,
                             max_tokens=max_tokens)
        rejects = [f for f in findings if f.severity == REJECT]
        if not rejects:
            return match.group(0)
        removed.append({
            "block": name,
            "reason": rejects[0].detail,
            "all_reasons": [f.detail for f in rejects],
            "text": body,
        })
        return ""

    return MANAGED_BLOCK.sub(replace, text), removed


def sanitize_context_files(root: str | Path, managed_paths: Iterable[str], *,
                            allowed_domains: Iterable[str] = DEFAULT_ALLOWED_DOMAINS,
                            max_tokens: int = 3000,
                            exclude: Iterable[str] = ()) -> dict:
    """Sanitise every managed file in place, and report what was removed."""
    base = Path(root)
    removed: list[dict] = []
    touched: list[str] = []
    for relative in expand_managed_paths(base, managed_paths, exclude):
        path = base / relative
        original = path.read_text(encoding="utf-8", errors="replace")
        cleaned, blocks = sanitize_context_text(
            original, allowed_domains=allowed_domains, max_tokens=max_tokens)
        if blocks:
            path.write_text(cleaned, encoding="utf-8", newline="\n")
            touched.append(relative)
            for block in blocks:
                removed.append({"file": relative, **block})
    return {"ok": True, "removed": removed, "touched": touched}

def snapshot_files(root: str | Path, managed_paths: Iterable[str],
                   destination: str | Path) -> list[str]:
    """Copy the managed files into *destination*.

    A revert needs the *previous* content, and it must not delete
    anything: the current content is what the revert is superseding
    (invariant I9).  Snapshots make both true.
    """
    base = Path(root)
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for relative in managed_paths:
        source = base / relative
        if source.is_dir():
            for child in sorted(source.rglob("*")):
                if child.is_file():
                    rel = child.relative_to(base)
                    target = dest / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(child.read_bytes())
                    copied.append(str(rel).replace("\\", "/"))
            continue
        if source.is_file():
            target = dest / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
            copied.append(relative)
    return copied


def restore_snapshot(snapshot: str | Path, root: str | Path,
                     managed_paths: Iterable[str]) -> list[str]:
    """Restore the managed files from a snapshot.

    Only files the snapshot actually holds are restored, so a file created
    after the snapshot is left alone (and reported as not restored).
    """
    base = Path(root)
    source = Path(snapshot)
    restored: list[str] = []
    for relative in managed_paths:
        candidate = source / relative
        if not candidate.is_file():
            continue
        target = base / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(candidate.read_bytes())
        restored.append(relative)
    return restored
