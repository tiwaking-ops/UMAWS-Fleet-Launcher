"""S-P1 lock spike: can 20 processes append to one file under msvcrt.locking
with retry, without tearing a line?

Run:  py -3.12 pilot/spikes/lock_test.py

Verdict is written to stdout as one of:
    works | does-not-work | unknown

This is spike code, not production code.  It deliberately exercises the same
primitives as ``src/pmk/plat.py`` (``FileLock`` plus ``append_line_locked``)
so that a failure here is a failure there.
"""

from __future__ import annotations

import multiprocessing as mp
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from pmk import plat  # noqa: E402

PROCESSES = 20
LINES_PER_PROCESS = 25
LINE_WIDTH = 180


def _worker(path: str, worker_id: int, lines: int, width: int, q) -> None:
    """Append *lines* uniquely-numbered records, one lock acquisition each."""
    written = 0
    errors: list[str] = []
    for n in range(lines):
        # A wide payload with the characters that break naive line writers.
        payload = (f"w{worker_id:03d}n{n:03d} " + "x" * (width - 24)).ljust(width)
        record = f"{payload}\t{worker_id * 1000 + n}"
        try:
            plat.append_line_locked(path, record, timeout=60.0)
            written += 1
        except Exception as exc:  # noqa: BLE001 - reported to the parent
            errors.append(f"{type(exc).__name__}: {exc}")
    q.put((worker_id, written, errors))


def main() -> int:
    tmpdir = tempfile.mkdtemp(prefix="umaws-lock-spike-")
    path = os.path.join(tmpdir, "events.jsonl")
    # Seed the file so the lock range is valid (msvcrt refuses zero-length).
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("")

    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    procs = [
        ctx.Process(target=_worker,
                    args=(path, i, LINES_PER_PROCESS, LINE_WIDTH, q))
        for i in range(PROCESSES)
    ]

    t0 = time.monotonic()
    for p in procs:
        p.start()
    for p in procs:
        p.join(300)
    elapsed = time.monotonic() - t0

    results = []
    while not q.empty():
        results.append(q.get())
    alive = [p for p in procs if p.is_alive()]
    for p in alive:
        p.terminate()

    with open(path, "r", encoding="utf-8") as fh:
        raw_lines = fh.read().splitlines()

    expected = PROCESSES * LINES_PER_PROCESS
    errors = [e for _, _, errs in results for e in errs]

    # Validate every line against the exact record the worker should have
    # written.  Building the expected set (rather than a regex) avoids
    # guessing at padding: the payload is ljust()ed, so it carries trailing
    # spaces, and the id width varies from 1 to 4 digits.
    def expected_record(worker: int, seq: int) -> str:
        payload = (f"w{worker:03d}n{seq:03d} " + "x" * (LINE_WIDTH - 24)).ljust(LINE_WIDTH)
        return f"{payload}\t{worker * 1000 + seq}"

    expected_by_id: dict[str, str] = {}
    for w in range(PROCESSES):
        for n in range(LINES_PER_PROCESS):
            expected_by_id[str(w * 1000 + n)] = expected_record(w, n)

    seen_ids: list[str] = []
    torn: list[str] = []
    for ln in raw_lines:
        raw_id = ln.rsplit("\t", 1)[-1] if "\t" in ln else None
        if raw_id is None or raw_id not in expected_by_id:
            torn.append(ln)
            continue
        if ln != expected_by_id[raw_id]:
            torn.append(ln)
            continue
        seen_ids.append(raw_id)

    unique_ids = len(set(seen_ids))
    parsed = not torn
    missing = sorted(set(expected_by_id) - set(seen_ids), key=int)

    print(f"processes              : {PROCESSES}")
    print(f"lines per process      : {LINES_PER_PROCESS}")
    print(f"expected total lines   : {expected}")
    print(f"actual total lines     : {len(raw_lines)}")
    print(f"unique record ids      : {unique_ids}")
    print(f"torn/mismatched lines  : {len(torn)}")
    print(f"missing records        : {len(missing)}")
    print(f"malformed records      : {0 if parsed else 'yes'}")
    print(f"worker errors          : {len(errors)}")
    print(f"hanging processes      : {len(alive)}")
    print(f"elapsed seconds        : {elapsed:.2f}")
    if errors:
        for e in errors[:5]:
            print(f"  error: {e}")

    ok = (len(raw_lines) == expected
          and unique_ids == expected
          and set(seen_ids) == set(expected_by_id)
          and not torn
          and not errors
          and not alive
          and parsed)
    print()
    print("VERDICT:", "works" if ok else "does-not-work")
    print(f"artifact: {path}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
