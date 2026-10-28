"""Repository layout and paths.

The layout is pilot v1 Appendix A, with the fleet amendment's additions
(``src/fleet``, ``src/console``, ``.pm/fleet/``).  One module owns every
path so that no other module builds a path by string concatenation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

#: Directories created by ``pmk init``.
LAYOUT = (
    ".pm/events",
    ".pm/views",
    ".pm/tasks",
    ".pm/evidence",
    ".pm/quarantine",
    ".pm/conflicts",
    ".pm/briefings",
    ".pm/registry",
    ".pm/memory/facts",
    ".pm/memory/assumptions",
    ".pm/memory/patterns",
    ".pm/memory/incidents",
    ".pm/nohooks",
    ".pm/fleet/logs",
    "docs/sources",
    "pilot/spikes",
    "src/pmk",
    "src/fleet",
    "src/console",
    "src/quotagate",
    "tests/pmk",
    "tests/fleet",
    "tests/quotagate",
    "work",
)


@dataclass(frozen=True)
class Repo:
    """Every path the Kernel touches, derived from one root."""

    root: Path

    @classmethod
    def discover(cls, start: str | os.PathLike[str] | None = None) -> "Repo":
        """Find the repository root by walking up looking for ``.pm/``.

        Falls back to *start* itself when no ``.pm/`` is found, so a caller
        can always get a usable object and let ``ensure_layout`` create it.
        """
        current = Path(start or os.getcwd()).resolve()
        for candidate in [current, *current.parents]:
            if (candidate / ".pm").is_dir():
                return cls(candidate)
        return cls(current)

    # -- top level --------------------------------------------------------
    @property
    def pm(self) -> Path:
        return self.root / ".pm"

    @property
    def events_dir(self) -> Path:
        return self.pm / "events"

    @property
    def views_dir(self) -> Path:
        return self.pm / "views"

    @property
    def tasks_dir(self) -> Path:
        return self.pm / "tasks"

    @property
    def evidence_dir(self) -> Path:
        return self.pm / "evidence"

    @property
    def quarantine_dir(self) -> Path:
        return self.pm / "quarantine"

    @property
    def conflicts_dir(self) -> Path:
        return self.pm / "conflicts"

    @property
    def briefings_dir(self) -> Path:
        return self.pm / "briefings"

    @property
    def registry_dir(self) -> Path:
        return self.pm / "registry"

    @property
    def memory_dir(self) -> Path:
        return self.pm / "memory"

    @property
    def fleet_dir(self) -> Path:
        return self.pm / "fleet"

    @property
    def nohooks_dir(self) -> Path:
        """An empty directory used as ``core.hooksPath``.

        The fleet amendment section 7.2 requires an empty *directory* rather
        than ``/dev/null``: on Windows the null path is ``NUL``, which is not
        a directory and not accepted by git as a hooks path.
        """
        return self.pm / "nohooks"

    @property
    def work_dir(self) -> Path:
        """Per-lease worktrees."""
        return self.root / "work"

    # -- pinned files -----------------------------------------------------
    @property
    def policy_path(self) -> Path:
        return self.pm / "policy.toml"

    @property
    def constitution_path(self) -> Path:
        return self.pm / "constitution.md"

    @property
    def pins_path(self) -> Path:
        return self.pm / "pins.sha256"

    @property
    def agents_path(self) -> Path:
        """Fleet profiles (fleet amendment section 12.A)."""
        return self.root / "agents.toml"

    # -- views ------------------------------------------------------------
    @property
    def ledger_view(self) -> Path:
        return self.views_dir / "ledger.md"

    @property
    def status_view(self) -> Path:
        return self.views_dir / "status.md"

    @property
    def queue_view(self) -> Path:
        return self.views_dir / "queue.md"

    # -- operator surfaces ------------------------------------------------
    @property
    def stop_file(self) -> Path:
        """pilot v1 section 12.5 stop-the-line flag."""
        return self.root / "pilot" / "STOP"

    @property
    def pilot_dir(self) -> Path:
        return self.root / "pilot"

    @property
    def decisions_log(self) -> Path:
        return self.pilot_dir / "decisions.md"

    @property
    def state_file(self) -> Path:
        return self.pilot_dir / "STATE.md"

    @property
    def fleet_state_path(self) -> Path:
        """Project-local fleet state file (git-ignored)."""
        return self.fleet_dir / "fleet-state.json"

    # -- helpers ----------------------------------------------------------
    def ensure_layout(self) -> None:
        for relative in LAYOUT:
            (self.root / relative).mkdir(parents=True, exist_ok=True)
        # The nohooks directory must exist and be empty; git refuses to use a
        # hooks path that does not exist.
        self.nohooks_dir.mkdir(parents=True, exist_ok=True)
        for stray in self.nohooks_dir.iterdir():
            if stray.is_file():
                stray.unlink()

    def worktree_root(self) -> Path:
        """Where per-lease worktrees are created.

        ``.pm/policy.toml`` may override this.  The proposal's guess was
        ``C:\\w\\<project>`` to stay under the 260-character path limit, but
        the operator chose to keep everything inside the repository
        (decision D-01).
        """
        return self.work_dir

    def relative(self, path: Path) -> str:
        try:
            return str(Path(path).resolve().relative_to(self.root))
        except ValueError:
            return str(path)

    # -- git ---------------------------------------------------------------
    def git(self, *args: str, cwd: "Path | None" = None,
            timeout: int = 60) -> tuple[int, str, str]:
        """Run a git command in this repository.

        Returns ``(returncode, stdout, stderr)``.  Git failures are
        returned, not raised, because most callers want to *record* what
        git said (the evidence bundle keeps stdout and stderr hashes).
        """
        import subprocess
        try:
            out = subprocess.run(
                ["git", "-C", str(cwd or self.root), *args],
                capture_output=True, text=True, timeout=timeout,
                encoding="utf-8", errors="replace")
        except (OSError, subprocess.SubprocessError) as exc:
            return -1, "", str(exc)
        return out.returncode, out.stdout, out.stderr

    def head_commit(self) -> str:
        """The current HEAD commit, or ``""`` outside a git repository."""
        code, out, _ = self.git("rev-parse", "HEAD")
        return out.strip() if code == 0 else ""

    def default_branch(self) -> str:
        """The repository's current branch name (resolved from HEAD).

        Handles repositories where the branch is not 'main' (e.g. 'master').
        Falls back to 'main' if HEAD cannot be resolved.
        """
        code, out, _ = self.git("symbolic-ref", "--short", "HEAD")
        if code == 0 and out.strip():
            return out.strip()
        return "main"

    def __fspath__(self) -> str:
        return str(self.root)
