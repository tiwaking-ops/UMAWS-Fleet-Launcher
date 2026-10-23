"""Provenance: which model actually served a call.

The problem this solves (D-43's open question).  D-L12 stops a verifier from
being the same *declared family* as the implementer, but a declared family is
a guess about a string:

* ``kilo/kilo-auto/free`` is an opaque router, so the string tells you nothing
  about what served the call; a different declared family can still be the
  same underlying model checking its own work.
* Two genuinely different models in one family are rejected needlessly.

Both failures come from comparing **declarations** instead of **facts**.  The
fact is recoverable in one place: the gateway sits in the request path and
sees the upstream's answer, which names the model that served it.

Two sources, in order of trust:

1. The response body's ``model`` field - the upstream's own naming of what
   answered.  This is what hermes' proxy and Omniroute both return.
2. ``x-omniroute-decision`` (``strategy=auto; provider=cohere; ...``) - names
   the *provider* chosen, which is the best available when the body names a
   router alias.

Neither exists for a direct-CLI profile, because the Kernel never sees those
requests (``L-F2``).  Provenance for those stays empty, which is the honest
answer and which leaves D-L12's veto in force rather than pretending.

Values are per (task, profile, model) triple, so one task that was escalated
mid-flight records each model that actually worked on it.
"""

from __future__ import annotations

import sqlite3
import threading
import time

#: The header the Fleet sends so a call can be tied back to the work it did.
TASK_HEADER = "x-quotagate-task"

#: How long provenance stays useful.  Long enough to outlive a run and its
#: verification, short enough that the table is not a permanent record of
#: everything ever dispatched.
RETENTION_S = 7 * 24 * 3600


def served_from_response(body: dict | None, headers: dict | None) -> dict:
    """What actually served this call, from the upstream's own answer.

    Returns ``{}`` when nothing names it, so callers can distinguish "no
    provenance" from "provenance is an empty string".
    """
    out: dict = {}
    if isinstance(body, dict):
        model = str(body.get("model") or "").strip()
        if model:
            out["model"] = model
    decision = ""
    for key, value in (headers or {}).items():
        if str(key).lower() == "x-omniroute-decision":
            decision = str(value)
    if decision:
        out["decision"] = decision
        for part in decision.split(";"):
            part = part.strip()
            if part.startswith("provider="):
                out["provider"] = part.split("=", 1)[1]
    return out


class ProvenanceLedger:
    """SQLite, one row per observed call, keyed by task."""

    def __init__(self, db: sqlite3.Connection | None = None):
        self.db = db if db is not None else sqlite3.connect(":memory:",
                                                            check_same_thread=False)
        self._init_schema()
        self._lock = threading.RLock()

    def _init_schema(self) -> None:
        self.db.executescript("""
CREATE TABLE IF NOT EXISTS provenance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task TEXT NOT NULL,
    profile TEXT NOT NULL,
    deployment TEXT NOT NULL,
    served_model TEXT NOT NULL,
    served_provider TEXT NOT NULL DEFAULT '',
    decision TEXT NOT NULL DEFAULT '',
    request_id TEXT NOT NULL DEFAULT '',
    latency_ms INTEGER NOT NULL DEFAULT 0,
    at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS provenance_task ON provenance(task, at);
""")
        self.db.commit()

    # -- writing ---------------------------------------------------------
    def record(self, task: str, profile: str, deployment: str,
               served_model: str, *, served_provider: str = "",
               decision: str = "", request_id: str = "",
               latency_ms: int = 0, at: float | None = None) -> None:
        if not task:
            return                      # uncorrelated traffic, nothing to file
        at = time.time() if at is None else at
        with self._lock:
            self.db.execute(
                "INSERT INTO provenance (task, profile, deployment, "
                "served_model, served_provider, decision, request_id, "
                "latency_ms, at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (task, profile, deployment, served_model, served_provider,
                 decision, request_id, latency_ms, at))
            self.db.commit()

    # -- reading ---------------------------------------------------------
    def for_window(self, deployment: str, start: float,
                   end: float) -> list[dict]:
        """Everything a deployment served between *start* and *end*.

        Why a window and not a task id: the Fleet spawns a CLI **process**, so
        it cannot put a header on the requests the CLI makes to this gateway.
        A lease is exclusive to one worktree and a profile is capped by
        ``max_concurrent``, so a window on a deployment is attributable - the
        only calls a deployment made in that window were for that lease.

        The task header remains the preferred key where a client can send it
        (the gateway's own integrations), and both are accepted on read.
        """
        with self._lock:
            rows = self.db.execute(
                "SELECT task, profile, deployment, served_model, "
                "served_provider, decision, request_id, latency_ms, at "
                "FROM provenance WHERE deployment = ? AND at >= ? AND at <= ? "
                "ORDER BY at ASC", (deployment, start, end)).fetchall()
        return [dict(zip(
            ("task", "profile", "deployment", "served_model",
             "served_provider", "decision", "request_id",
             "latency_ms", "at"), row)) for row in rows]

    def for_task(self, task: str) -> list[dict]:
        """Every model that served work for *task*, oldest first."""
        with self._lock:
            rows = self.db.execute(
                "SELECT task, profile, deployment, served_model, "
                "served_provider, decision, request_id, latency_ms, at "
                "FROM provenance WHERE task = ? ORDER BY at ASC", (task,)).fetchall()
        out = []
        for row in rows:
            out.append({
                "task": row[0], "profile": row[1], "deployment": row[2],
                "served_model": row[3], "served_provider": row[4],
                "decision": row[5], "request_id": row[6],
                "latency_ms": row[7], "at": row[8],
            })
        return out

    def served_models(self, task: str) -> set[str]:
        """The set of models that served *task*.  Empty means unknown."""
        return {r["served_model"] for r in self.for_task(task) if r["served_model"]}

    def prune(self, older_than_s: float = RETENTION_S,
              now: float | None = None) -> int:
        now = time.time() if now is None else now
        with self._lock:
            cur = self.db.execute("DELETE FROM provenance WHERE at < ?",
                                  (now - older_than_s,))
            self.db.commit()
            return cur.rowcount
