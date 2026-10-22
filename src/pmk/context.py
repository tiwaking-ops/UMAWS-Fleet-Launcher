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


def lint_files(root: str | Path, managed_paths: Iterable[str], *,
               allowed_domains: Iterable[str] = DEFAULT_ALLOWED_DOMAINS,
               max_tokens: int = 3000) -> dict:
    """Lint every managed file under *root*."""
    base = Path(root)
    findings: list[LintFinding] = []
    checked: list[str] = []
    for relative in managed_paths:
        path = base / relative
        if not path.is_file():
            continue
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file():
                    checked.append(str(child.relative_to(base)))
                    findings += lint_text(
                        child.read_text(encoding="utf-8", errors="replace"),
                        file=str(child.relative_to(base)),
                        allowed_domains=allowed_domains, max_tokens=max_tokens)
            continue
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

def hash_context_files(root: str | Path,
                       managed_paths: Iterable[str]) -> dict[str, str]:
    """The SHA-256 of each managed file, for the drift check."""
    base = Path(root)
    out: dict[str, str] = {}
    for relative in managed_paths:
        path = base / relative
        if path.is_file():
            out[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        elif path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file():
                    rel = str(child.relative_to(base)).replace("\\", "/")
                    out[rel] = hashlib.sha256(child.read_bytes()).hexdigest()
    return out


def drift_check(root: str | Path, managed_paths: Iterable[str],
                recorded: dict[str, str]) -> dict:
    """Compare the managed files with their recorded hashes (I16).

    A mismatch is an out-of-band edit: somebody changed a class C file
    without going through a sync.  The sentinel reports it; the Kernel can
    auto-revert to the last clean state.
    """
    current = hash_context_files(root, managed_paths)
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

    def to_dict(self) -> dict:
        return {
            "ok": self.ok, "noop": self.noop,
            "needs_review": self.needs_review, "rejected": self.rejected,
            "reason": self.reason,
            "before_hash": self.before_hash, "after_hash": self.after_hash,
            "score": self.score, "previous_score": self.previous_score,
            "lint": self.lint, "generator_version": self.generator_version,
            "provider": self.provider, "diff_lines": self.diff_lines,
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
